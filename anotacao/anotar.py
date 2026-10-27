"""
Anotação automática de imagens com o Grounding DINO (vocabulário aberto).

Recebe uma ou mais imagens e grava, no diretório de saída, a imagem e as
caixas no formato de detecção do YOLO (Ultralytics):

    <saida>/images/<nome>.jpg
    <saida>/labels/<nome>.txt    uma linha por objeto: id cx cy w h (0..1)
    <saida>/data.yaml            nomes das classes, na ordem de classes.yaml
    <saida>/previa/<nome>.jpg    com --previa: caixas desenhadas, para revisão

As anotações são propostas para um revisor humano, não rótulos finais.

Uso:
    python anotacao/anotar.py foto.jpg [outra.jpg ...] -o anotacoes --previa
"""

import argparse
import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps

DIR_SCRIPT = Path(__file__).resolve().parent
MODELO_PADRAO = "IDEA-Research/grounding-dino-tiny"
MATERIAIS = {"plastic", "metal", "glass", "paper", "other"}
TAG_ORIENTACAO_EXIF = 0x0112


def carregar_classes(caminho):
    """Lê classes.yaml e devolve a lista de {nome, prompt, material}."""
    with open(caminho, encoding="utf-8") as f:
        classes = (yaml.safe_load(f) or {}).get("classes") or []
    if not classes:
        raise ValueError(f"{caminho}: nenhuma classe em 'classes'")
    nomes = set()
    for i, c in enumerate(classes):
        for campo in ("nome", "prompt", "material"):
            if not str(c.get(campo, "")).strip():
                raise ValueError(f"{caminho}: classe {i} sem '{campo}'")
        if c["material"] not in MATERIAIS:
            raise ValueError(f"{caminho}: classe {i} com material '{c['material']}' "
                             f"(use {', '.join(sorted(MATERIAIS))})")
        if c["nome"] in nomes:
            raise ValueError(f"{caminho}: classe '{c['nome']}' repetida")
        nomes.add(c["nome"])
    return classes


def montar_prompt(classes):
    """
    Junta os prompts no formato do Grounding DINO ("a . b . c .") e devolve
    o texto e, para cada classe, o intervalo [inicio, fim) dela no texto.
    """
    texto = ""
    intervalos = []
    for c in classes:
        frase = c["prompt"].strip().lower()
        intervalos.append((len(texto), len(texto) + len(frase)))
        texto += frase + " . "
    return texto.strip(), intervalos


def classe_de_cada_token(offsets, intervalos):
    """
    Para cada token (offsets do tokenizer), o índice da classe cujo prompt o
    contém, ou None ([CLS], [SEP] e os pontos entre os prompts).
    """
    resultado = []
    for inicio, fim in offsets:
        classe = None
        if fim > inicio:
            for i, (a, b) in enumerate(intervalos):
                if a <= inicio < b:
                    classe = i
                    break
        resultado.append(classe)
    return resultado


def iou(a, b):
    """IoU entre duas caixas (x1, y1, x2, y2)."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    uniao = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / uniao if uniao > 0 else 0.0


def nms(deteccoes, limiar_iou):
    """
    Supressão de não máximos sem distinguir classe: o Grounding DINO costuma
    propor várias caixas para o mesmo objeto, às vezes com prompts diferentes.
    Cada detecção é (classe, confianca, (x1, y1, x2, y2)).
    """
    mantidas = []
    for d in sorted(deteccoes, key=lambda d: d[1], reverse=True):
        if all(iou(d[2], m[2]) < limiar_iou for m in mantidas):
            mantidas.append(d)
    return mantidas


def linha_yolo(classe, caixa):
    """Caixa (x1, y1, x2, y2) normalizada -> linha 'id cx cy w h' do YOLO."""
    x1, y1, x2, y2 = caixa
    return (f"{classe} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} "
            f"{x2 - x1:.6f} {y2 - y1:.6f}")


def abrir_imagem(caminho):
    """Abre a imagem em RGB já com a rotação do EXIF aplicada."""
    imagem = Image.open(caminho)
    girada = imagem.getexif().get(TAG_ORIENTACAO_EXIF, 1) != 1
    return ImageOps.exif_transpose(imagem).convert("RGB"), girada


class Anotador:
    """Grounding DINO carregado uma vez, com o prompt das classes já tokenizado."""

    def __init__(self, classes, modelo, dispositivo, confianca, limiar_iou, area_maxima):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.torch = torch
        self.dispositivo = dispositivo or ("cuda" if torch.cuda.is_available() else "cpu")
        self.confianca = confianca
        self.limiar_iou = limiar_iou
        self.area_maxima = area_maxima
        self.n_classes = len(classes)

        print(f"Carregando {modelo} em {self.dispositivo}...")
        self.processador = AutoProcessor.from_pretrained(modelo)
        self.modelo = AutoModelForZeroShotObjectDetection.from_pretrained(modelo)
        self.modelo.to(self.dispositivo).eval()

        self.texto, intervalos = montar_prompt(classes)
        tokens = self.processador.tokenizer(self.texto, return_offsets_mapping=True)
        limite = getattr(self.modelo.config, "max_text_len", 256)
        if len(tokens["input_ids"]) > limite:
            raise ValueError(f"Prompts longos demais: {len(tokens['input_ids'])} tokens "
                             f"(máximo {limite}). Reduza as classes ou os prompts.")
        self.input_ids = tokens["input_ids"]
        self.token_classe = classe_de_cada_token(tokens["offset_mapping"], intervalos)

    def anotar(self, imagem):
        """Devolve [(classe, confianca, (x1, y1, x2, y2) normalizada)] após o NMS."""
        torch = self.torch
        entradas = self.processador(images=imagem, text=self.texto, return_tensors="pt")
        if entradas["input_ids"][0].tolist() != self.input_ids:
            raise RuntimeError("Tokenização do processador difere da do tokenizer")
        entradas = entradas.to(self.dispositivo)
        with torch.no_grad():
            saida = self.modelo(**entradas)

        # logits: (consultas, tokens); a confiança de uma classe numa caixa é
        # a maior entre os tokens do prompt dela
        logits = saida.logits[0, :, :len(self.token_classe)].sigmoid().cpu()
        por_classe = torch.zeros(logits.shape[0], self.n_classes)
        for t, c in enumerate(self.token_classe):
            if c is not None:
                por_classe[:, c] = torch.maximum(por_classe[:, c], logits[:, t])
        confiancas, classes = por_classe.max(dim=1)

        # pred_boxes: (cx, cy, w, h) normalizados pela imagem original
        caixas = saida.pred_boxes[0].cpu()
        deteccoes = []
        for conf, classe, (cx, cy, w, h) in zip(confiancas.tolist(), classes.tolist(),
                                                caixas.tolist()):
            if conf < self.confianca:
                continue
            caixa = (max(0.0, cx - w / 2), max(0.0, cy - h / 2),
                     min(1.0, cx + w / 2), min(1.0, cy + h / 2))
            area = (caixa[2] - caixa[0]) * (caixa[3] - caixa[1])
            # O Grounding DINO costuma propor uma caixa para a esteira inteira
            if caixa[2] > caixa[0] and caixa[3] > caixa[1] and area <= self.area_maxima:
                deteccoes.append((classe, conf, caixa))
        return nms(deteccoes, self.limiar_iou)


def preparar_saida(saida, classes):
    """Cria as pastas e o data.yaml; recusa um data.yaml com outras classes."""
    for pasta in ("images", "labels"):
        (saida / pasta).mkdir(parents=True, exist_ok=True)
    nomes = {i: c["nome"] for i, c in enumerate(classes)}
    data_yaml = saida / "data.yaml"
    if data_yaml.exists():
        with open(data_yaml, encoding="utf-8") as f:
            existentes = (yaml.safe_load(f) or {}).get("names")
        if existentes != nomes:
            raise ValueError(f"{data_yaml} tem outras classes; os ids não bateriam. "
                             "Use outro diretório de saída.")
        return
    with open(data_yaml, "w", encoding="utf-8") as f:
        # Sem 'path': o Ultralytics usa a pasta do data.yaml. Ainda sem divisão
        # treino/validação (a divisão deve ser por sessão, monografia 5.3.5).
        yaml.safe_dump({"train": "images", "val": "images", "names": nomes},
                       f, allow_unicode=True, sort_keys=False)


def salvar_imagem(origem, imagem, girada, destino):
    """
    Copia a imagem como está; se o EXIF a girava, grava a versão já girada,
    para que as caixas valham para qualquer leitor, respeite ele o EXIF ou não.
    """
    if girada:
        imagem.save(destino, quality=95)
    else:
        shutil.copy2(origem, destino)


def desenhar_previa(imagem, deteccoes, classes, destino):
    previa = imagem.copy()
    desenho = ImageDraw.Draw(previa)
    largura, altura = previa.size
    espessura = max(2, round(min(largura, altura) / 300))
    fonte = ImageFont.load_default(size=max(12, round(min(largura, altura) / 50)))
    for classe, conf, (x1, y1, x2, y2) in deteccoes:
        caixa = (x1 * largura, y1 * altura, x2 * largura, y2 * altura)
        desenho.rectangle(caixa, outline=(34, 197, 94), width=espessura)
        rotulo = f"{classes[classe]['nome']} {conf:.2f}"
        fundo = desenho.textbbox((caixa[0], caixa[1]), rotulo, font=fonte, anchor="lb")
        desenho.rectangle(fundo, fill=(34, 197, 94))
        desenho.text((caixa[0], caixa[1]), rotulo, fill=(0, 0, 0), font=fonte, anchor="lb")
    previa.save(destino, quality=90)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera anotações YOLO com o Grounding DINO.")
    parser.add_argument("imagens", nargs="+", type=Path, help="caminho de uma ou mais imagens")
    parser.add_argument("-o", "--saida", type=Path, default=Path("anotacoes"),
                        help="diretório de saída (padrão: ./anotacoes)")
    parser.add_argument("--classes", type=Path, default=DIR_SCRIPT / "classes.yaml",
                        help="lista de classes (padrão: anotacao/classes.yaml)")
    parser.add_argument("--modelo", default=MODELO_PADRAO,
                        help=f"modelo do Hugging Face (padrão: {MODELO_PADRAO})")
    parser.add_argument("--confianca", type=float, default=0.35,
                        help="confiança mínima por caixa (padrão: 0.35)")
    parser.add_argument("--iou", type=float, default=0.5,
                        help="IoU acima do qual caixas sobrepostas viram uma (padrão: 0.5)")
    parser.add_argument("--area-maxima", type=float, default=0.5,
                        help="descarta caixas maiores que essa fração da imagem (padrão: 0.5)")
    parser.add_argument("--dispositivo", help="cuda ou cpu (padrão: cuda se houver)")
    parser.add_argument("--previa", action="store_true",
                        help="grava também previa/<nome>.jpg com as caixas desenhadas")
    parser.add_argument("--sobrescrever", action="store_true",
                        help="substitui imagens que já estão na saída")
    args = parser.parse_args(argv)

    classes = carregar_classes(args.classes)

    for caminho in args.imagens:
        if not caminho.is_file():
            parser.error(f"imagem não encontrada: {caminho}")
    # O .txt é nomeado pelo nome sem extensão: foto.jpg e foto.png colidiriam
    nomes = [c.stem for c in args.imagens]
    repetidos = {n for n in nomes if nomes.count(n) > 1}
    if repetidos:
        parser.error(f"nomes de arquivo repetidos na entrada: {', '.join(sorted(repetidos))}")
    if not args.sobrescrever:
        existentes = [n for n in nomes if (args.saida / "labels" / f"{n}.txt").exists()]
        if existentes:
            parser.error(f"já anotadas em {args.saida}: {', '.join(existentes)} "
                         "(use --sobrescrever)")

    preparar_saida(args.saida, classes)
    if args.previa:
        (args.saida / "previa").mkdir(exist_ok=True)

    anotador = Anotador(classes, args.modelo, args.dispositivo, args.confianca, args.iou,
                        args.area_maxima)

    for caminho in args.imagens:
        imagem, girada = abrir_imagem(caminho)
        deteccoes = anotador.anotar(imagem)

        salvar_imagem(caminho, imagem, girada, args.saida / "images" / caminho.name)
        linhas = [linha_yolo(classe, caixa) for classe, _, caixa in deteccoes]
        (args.saida / "labels" / f"{caminho.stem}.txt").write_text(
            "".join(l + "\n" for l in linhas), encoding="utf-8")
        if args.previa:
            desenhar_previa(imagem, deteccoes, classes,
                            args.saida / "previa" / f"{caminho.stem}.jpg")

        resumo = ", ".join(f"{classes[c]['nome']} {conf:.2f}" for c, conf, _ in deteccoes)
        print(f"{caminho.name}: {len(deteccoes)} objeto(s){': ' + resumo if resumo else ''}")

    print(f"Anotações em {args.saida.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
