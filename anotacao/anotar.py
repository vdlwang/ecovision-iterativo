"""
Anotação automática de imagens por um anotador intercambiável (hoje, o
Grounding DINO, de vocabulário aberto).

Recebe uma ou mais imagens e grava, no diretório de saída (formato em saida.py):

    <saida>/images/<nome>.jpg
    <saida>/propostas/<anotador>/<nome>.json   caixas propostas, com a confiança
    <saida>/imagens.csv                        status de cada imagem (pendente...)
    <saida>/data.yaml                          classes e revisadas.txt como treino
    <saida>/previa/<anotador>/<nome>.jpg       com --previa: caixas desenhadas
    <saida>/visualizar.html                    página para conferir propostas e rótulos

As propostas não são rótulos: labels/ só recebe as caixas depois da revisão,
ou com --aceitar, que copia as propostas como estão.

Uso:
    python anotacao/anotar.py foto.jpg [outra.jpg ...] -o anotacoes --previa
    python anotacao/anotar.py -o anotacoes --aceitar     # aceita as pendentes
"""

import argparse
import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps

import saida as formato
from saida import linha_yolo  # noqa: F401 (usada pelos testes e pelo avaliar.py)
from visualizar import gerar_pagina

DIR_SCRIPT = Path(__file__).resolve().parent
MODELO_PADRAO = "IDEA-Research/grounding-dino-tiny"
CONFIANCA_PADRAO = 0.35
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
        if not isinstance(c.get("reserva", False), bool):
            raise ValueError(f"{caminho}: classe {i} com 'reserva' que não é true nem false")
        nomes.add(c["nome"])
    if all(c.get("reserva") for c in classes):
        raise ValueError(f"{caminho}: ao menos uma classe não pode ser de reserva")
    fora = [c["nome"] for c in classes if c["nome"] not in carregar_nomes(caminho)]
    if fora:
        raise ValueError(f"{caminho}: classes fora de 'nomes': {', '.join(fora)}")
    return classes


def carregar_nomes(caminho):
    """
    Lê 'nomes' do classes.yaml: os nomes das classes dos rótulos, na ordem dos
    ids. Sem 'nomes', valem os nomes de 'classes', na ordem delas.
    """
    with open(caminho, encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}
    nomes = dados.get("nomes")
    if nomes is None:
        return [str(c.get("nome")) for c in dados.get("classes") or []]
    if not isinstance(nomes, list) or not nomes or not all(
            isinstance(n, str) and n.strip() for n in nomes):
        raise ValueError(f"{caminho}: 'nomes' deve ser uma lista de nomes não vazios")
    repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
    if repetidos:
        raise ValueError(f"{caminho}: nomes repetidos: {', '.join(repetidos)}")
    return nomes


def escolher_classe(pontuacoes, reservas, limiar):
    """
    Classe de uma consulta a partir da pontuação de cada classe: (classe,
    confiança). Vence a classe comum de maior pontuação; uma classe de reserva
    (reservas: índices) só vence se nenhuma comum chega ao limiar e ela chega.
    Assim o prompt genérico dá caixa ao objeto que as outras não reconhecem,
    sem tirar das comuns os que elas reconhecem.
    """
    comuns = [i for i in range(len(pontuacoes)) if i not in reservas]
    melhor = max(comuns, key=pontuacoes.__getitem__)
    if pontuacoes[melhor] < limiar and reservas:
        reserva = max(reservas, key=pontuacoes.__getitem__)
        if pontuacoes[reserva] >= limiar:
            return reserva, pontuacoes[reserva]
    return melhor, pontuacoes[melhor]


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


def abrir_imagem(caminho):
    """Abre a imagem em RGB já com a rotação do EXIF aplicada."""
    imagem = Image.open(caminho)
    girada = imagem.getexif().get(TAG_ORIENTACAO_EXIF, 1) != 1
    return ImageOps.exif_transpose(imagem).convert("RGB"), girada


class GroundingDino:
    """
    Grounding DINO carregado uma vez, com o prompt das classes já tokenizado.

    Interface de todo anotador (ver ANOTADORES): o atributo nome, que é a pasta
    das propostas; opcoes(parser), que acrescenta as opções de linha de comando
    dele; criar(classes, args); e, na instância, versao, parametros e
    anotar(imagem) -> [(id da classe, confianca, (x1, y1, x2, y2) normalizada)].
    """

    nome = "grounding-dino"

    @staticmethod
    def opcoes(parser):
        grupo = parser.add_argument_group("grounding-dino")
        grupo.add_argument("--modelo", default=MODELO_PADRAO,
                           help=f"modelo do Hugging Face (padrão: {MODELO_PADRAO})")
        grupo.add_argument("--confianca", type=float, default=CONFIANCA_PADRAO,
                           help=f"confiança mínima por caixa (padrão: {CONFIANCA_PADRAO})")
        grupo.add_argument("--iou", type=float, default=0.5,
                           help="IoU acima do qual caixas sobrepostas viram uma (padrão: 0.5)")
        grupo.add_argument("--area-maxima", type=float, default=0.5,
                           help="descarta caixas maiores que essa fração da imagem "
                                "(padrão: 0.5)")

    @classmethod
    def criar(cls, classes, args):
        return cls(classes, args.modelo, args.dispositivo, args.confianca, args.iou,
                   args.area_maxima)

    def __init__(self, classes, modelo, dispositivo, confianca, limiar_iou, area_maxima):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.torch = torch
        self.dispositivo = dispositivo or ("cuda" if torch.cuda.is_available() else "cpu")
        self.confianca = confianca
        self.limiar_iou = limiar_iou
        self.area_maxima = area_maxima
        self.n_classes = len(classes)
        self.reservas = frozenset(i for i, c in enumerate(classes) if c.get("reserva"))
        self.versao = modelo
        self.parametros = {"confianca": confianca, "iou": limiar_iou,
                           "area_maxima": area_maxima}

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

    def pontuar(self, imagem):
        """
        Saída bruta do modelo, sem filtro: a pontuação de cada classe em cada
        consulta, tensor (consultas, classes), e as caixas (x1, y1, x2, y2)
        normalizadas e recortadas à imagem, lista com uma por consulta.
        """
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

        # pred_boxes: (cx, cy, w, h) normalizados pela imagem original
        caixas = [(max(0.0, cx - w / 2), max(0.0, cy - h / 2),
                   min(1.0, cx + w / 2), min(1.0, cy + h / 2))
                  for cx, cy, w, h in saida.pred_boxes[0].cpu().tolist()]
        return por_classe, caixas

    def filtrar(self, por_classe, caixas, confianca=None):
        """
        Saída de pontuar() -> [(classe, confianca, (x1, y1, x2, y2))] após os
        filtros e o NMS. confianca substitui a do construtor (para o avaliar.py).
        """
        if confianca is None:
            confianca = self.confianca
        deteccoes = []
        for pontuacoes, caixa in zip(por_classe.tolist(), caixas):
            classe, conf = escolher_classe(pontuacoes, self.reservas, confianca)
            if conf < confianca:
                continue
            area = (caixa[2] - caixa[0]) * (caixa[3] - caixa[1])
            # O Grounding DINO costuma propor uma caixa para a esteira inteira
            if caixa[2] > caixa[0] and caixa[3] > caixa[1] and area <= self.area_maxima:
                deteccoes.append((classe, conf, caixa))
        return nms(deteccoes, self.limiar_iou)

    def anotar(self, imagem):
        """Devolve [(classe, confianca, (x1, y1, x2, y2) normalizada)] após o NMS."""
        return self.filtrar(*self.pontuar(imagem))


# Anotadores disponíveis em --anotador, pelo nome
ANOTADORES = {a.nome: a for a in (GroundingDino,)}


def tem_ids_gravados(saida):
    """Se algum .txt de labels/ ou registro de revisoes/ guarda id de classe."""
    if any(t.read_text(encoding="utf-8").strip() for t in (saida / "labels").glob("*.txt")):
        return True
    return any(formato.ler_revisao(saida, r.name).get("caixas")
               for r in (saida / "revisoes").glob("*.json"))


def preparar_saida(saida, nomes):
    """
    Cria as pastas, o data.yaml (nomes: os de carregar_nomes, na ordem dos ids)
    e o imagens.csv. Um data.yaml com outras classes é refeito se nenhum rótulo
    ou revisão guarda ids (as propostas guardam a classe pelo nome; fundo e
    descarte não têm caixas); senão, é recusado, porque os ids não bateriam. Recusa também uma saída do
    formato antigo (labels/ sem imagens.csv), em que as propostas eram
    gravadas direto como rótulos.
    """
    for pasta in ("images", "labels", "propostas"):
        (saida / pasta).mkdir(parents=True, exist_ok=True)
    if not (saida / "imagens.csv").exists() and any((saida / "labels").glob("*.txt")):
        raise ValueError(f"{saida} é do formato antigo (labels/ sem imagens.csv), em que "
                         "as propostas eram gravadas como rótulos. Use outro diretório.")
    nomes = dict(enumerate(nomes))
    data_yaml = saida / "data.yaml"
    existentes = None
    if data_yaml.exists():
        with open(data_yaml, encoding="utf-8") as f:
            existentes = (yaml.safe_load(f) or {}).get("names")
        if isinstance(existentes, list):
            existentes = dict(enumerate(existentes))
    if existentes != nomes:
        if existentes is not None and tem_ids_gravados(saida):
            raise ValueError(f"{data_yaml} tem outras classes e já há rótulos ou revisões "
                             "com caixas; os ids não bateriam. Use outro diretório de saída.")
        # Sem 'path': o Ultralytics usa a pasta do data.yaml. Só as revisadas,
        # e ainda sem divisão treino/validação (por sessão, monografia 5.3.5).
        formato.gravar_atomico(data_yaml, yaml.safe_dump(
            {"train": "revisadas.txt", "val": "revisadas.txt", "names": nomes},
            allow_unicode=True, sort_keys=False))
    if not (saida / "imagens.csv").exists():
        formato.gravar_estado(saida, list(formato.COLUNAS), {})


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
    parser = argparse.ArgumentParser(
        description="Propõe caixas para as imagens com um anotador automático.")
    parser.add_argument("imagens", nargs="*", type=Path, help="caminho de uma ou mais imagens")
    parser.add_argument("-o", "--saida", type=Path, default=Path("anotacoes"),
                        help="diretório de saída (padrão: ./anotacoes)")
    parser.add_argument("--anotador", choices=sorted(ANOTADORES), default=GroundingDino.nome,
                        help=f"anotador (padrão: {GroundingDino.nome})")
    parser.add_argument("--classes", type=Path, default=DIR_SCRIPT / "classes.yaml",
                        help="lista de classes (padrão: anotacao/classes.yaml)")
    parser.add_argument("--dispositivo", help="cuda ou cpu (padrão: cuda se houver)")
    parser.add_argument("--previa", action="store_true",
                        help="grava também previa/<anotador>/<nome>.jpg com as caixas desenhadas")
    parser.add_argument("--sobrescrever", action="store_true",
                        help="anota de novo imagens que já têm proposta deste anotador")
    parser.add_argument("--aceitar", action="store_true",
                        help="copia as propostas do anotador para labels/ como rótulos finais "
                             "e marca as imagens como revisadas (só as pendentes; sem "
                             "imagens na linha de comando, todas)")
    for anotador in ANOTADORES.values():
        anotador.opcoes(parser)
    args = parser.parse_args(argv)
    if not args.imagens and not args.aceitar:
        parser.error("informe as imagens a anotar, ou --aceitar")

    classes = carregar_classes(args.classes)
    nomes_classes = carregar_nomes(args.classes)

    for caminho in args.imagens:
        if not caminho.is_file():
            parser.error(f"imagem não encontrada: {caminho}")
    # A proposta é nomeada pelo nome sem extensão: foto.jpg e foto.png colidiriam
    nomes = [c.stem for c in args.imagens]
    repetidos = {n for n in nomes if nomes.count(n) > 1}
    if repetidos:
        parser.error(f"nomes de arquivo repetidos na entrada: {', '.join(sorted(repetidos))}")
    if not args.sobrescrever:
        existentes = [c.name for c in args.imagens
                      if formato.caminho_proposta(args.saida, args.anotador, c.name).exists()]
        if existentes:
            parser.error(f"já anotadas por {args.anotador} em {args.saida}: "
                         f"{', '.join(existentes)} (use --sobrescrever)")

    preparar_saida(args.saida, nomes_classes)
    colunas, linhas = formato.ler_estado(args.saida)
    for caminho in args.imagens:
        formato.registrar_imagem(dict(linhas), caminho.name)  # só confere colisões

    if args.imagens:
        if args.previa:
            (args.saida / "previa" / args.anotador).mkdir(parents=True, exist_ok=True)
        anotador = ANOTADORES[args.anotador].criar(classes, args)

    for caminho in args.imagens:
        imagem, girada = abrir_imagem(caminho)
        deteccoes = anotador.anotar(imagem)

        salvar_imagem(caminho, imagem, girada, args.saida / "images" / caminho.name)
        formato.gravar_proposta(args.saida, formato.montar_proposta(
            anotador.nome, anotador.versao, anotador.parametros, classes, caminho.name,
            imagem.size, deteccoes))
        # Grava o estado a cada imagem: interrompido, o que já foi feito vale
        formato.registrar_imagem(linhas, caminho.name)
        formato.gravar_estado(args.saida, colunas, linhas)
        if args.previa:
            desenhar_previa(imagem, deteccoes, classes,
                            args.saida / "previa" / args.anotador / f"{caminho.stem}.jpg")

        resumo = ", ".join(f"{classes[c]['nome']} {conf:.2f}" for c, conf, _ in deteccoes)
        print(f"{caminho.name}: {len(deteccoes)} objeto(s){': ' + resumo if resumo else ''}")

    if args.aceitar:
        escolhidas = {c.name for c in args.imagens} if args.imagens else None
        aceitas = formato.aceitar(args.saida, args.anotador, escolhidas)
        print(f"{aceitas} imagem(ns) aceita(s): propostas de {args.anotador} copiadas "
              "para labels/")

    pagina = gerar_pagina(args.saida)
    print(f"Anotações em {args.saida.resolve()}")
    print(f"Para conferir, abra no navegador: {pagina.resolve().as_uri()}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
