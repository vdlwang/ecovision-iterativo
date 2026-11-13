"""
Anotação automática de imagens por um anotador intercambiável (hoje, o
Grounding DINO e o OWLv2, detectores de vocabulário aberto, e o YOLO da
equipe, de conjunto fechado).

Anota as imagens já importadas pelo importar.py (o armazenamento comum,
<saida>/images/) e grava as propostas, com a confiança de cada caixa, no banco
da saída (<saida>/anotacoes.sqlite, formato em saida.py), uma execução por
chamada. Antes, copia o banco para anotacoes.sqlite.bak. Grava também:

    <saida>/previa/<anotador>/<nome>.jpg       com --previa: caixas desenhadas
    <saida>/visualizar.html                    página para conferir propostas e rótulos

Só anota imagens pendentes, e não copia nem muda imagens. Caixas com o centro
fora da região de interesse do lote são descartadas.

As propostas não são rótulos: labels/ só recebe as caixas depois da revisão,
ou com --aceitar, que as grava como uma revisão sem mudança.

Uso:
    python anotacao/importar.py fotos/ -o anotacoes --lote 2026-11-11a
    python anotacao/anotar.py -o anotacoes --previa      # as pendentes ainda sem proposta
    python anotacao/anotar.py 2026-11-11a_foto.jpg -o anotacoes --sobrescrever
    python anotacao/anotar.py -o anotacoes --aceitar     # aceita as pendentes
    python anotacao/anotar.py -o anotacoes --exportar    # refaz labels/ e data.yaml do banco
"""

import argparse
import re
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps

import saida as formato
from saida import linha_yolo  # noqa: F401 (usada pelos testes e pelo avaliar.py)
from visualizar import gerar_pagina

DIR_SCRIPT = Path(__file__).resolve().parent
MODELO_PADRAO = "IDEA-Research/grounding-dino-tiny"
# Limiares de detecção (OBJETIVO.md, seções 5 e 6). A proposta guarda todas as
# caixas a partir do piso; os outros dois são de leitura (decisão 16): a página
# mostra a partir de CONFIANCA, oferece as de baixo como candidatas do clique e
# esconde a classe abaixo de CONFIANCA_CLASSE.
PISO_PADRAO = 0.05            # caixa por clique: 81% dos objetos sem caixa (2026-11-11)
CONFIANCA_PADRAO = 0.20       # pela cobertura sem classe (2026-11-11)
CONFIANCA_CLASSE_PADRAO = 0.35  # viés de automação (2026-11-11)
IOU_PADRAO = 0.5
AREA_MAXIMA_PADRAO = 0.5      # o Grounding DINO costuma propor a esteira inteira
CONTENCAO_PADRAO = 0.9        # caixa contida numa maior e mais confiante sai (2026-11-11)
MATERIAIS = {"plastic", "metal", "glass", "paper", "other"}
TAG_ORIENTACAO_EXIF = 0x0112


def prompts(classe):
    """
    Os prompts de uma classe, em minúsculas: o campo prompt é um texto ou uma
    lista deles (vários prompts por classe; a classe recebe a maior pontuação).
    """
    p = classe["prompt"]
    return [t.strip().lower() for t in ([p] if isinstance(p, str) else p)]


def carregar_classes(caminho):
    """Lê classes.yaml e devolve a lista de {nome, prompt, material}."""
    with open(caminho, encoding="utf-8") as f:
        classes = (yaml.safe_load(f) or {}).get("classes") or []
    if not classes:
        raise ValueError(f"{caminho}: nenhuma classe em 'classes'")
    nomes = set()
    for i, c in enumerate(classes):
        for campo in ("nome", "material"):
            if not str(c.get(campo, "")).strip():
                raise ValueError(f"{caminho}: classe {i} sem '{campo}'")
        p = c.get("prompt")
        lista = [p] if isinstance(p, str) else p
        if not isinstance(lista, list) or not lista or not all(
                isinstance(t, str) and t.strip() for t in lista):
            raise ValueError(f"{caminho}: classe {i} sem 'prompt' (um texto ou uma lista "
                             "de textos não vazios)")
        if len(set(prompts(c))) != len(lista):
            raise ValueError(f"{caminho}: classe {i} com prompt repetido")
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
    o texto e, para cada prompt, (inicio, fim, classe): o intervalo [inicio,
    fim) dele no texto e o índice da classe. Uma classe com vários prompts
    tem um intervalo por prompt.
    """
    texto = ""
    intervalos = []
    for i, c in enumerate(classes):
        for frase in prompts(c):
            intervalos.append((len(texto), len(texto) + len(frase), i))
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
            for a, b, i in intervalos:
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


def contida(a, b):
    """Fração da área de a que está dentro de b."""
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    if not area_a:
        return 0.0
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / area_a


def sem_contidas(deteccoes, limiar):
    """
    Remove a caixa contida (fração >= limiar da área dela) numa caixa maior e
    mais confiante, de qualquer classe: o Grounding DINO propõe partes do
    objeto (o topo da lata como tampa) e duplicatas menores, que o NMS não
    pega porque o IoU entre elas é baixo. A caixa grande que envolve uma
    menor mais confiante fica: costuma ser o objeto inteiro, com a parte mais
    confiante que ele. limiar >= 1 só remove caixas inteiramente contidas;
    acima de 1, nenhuma.
    """
    def area(c):
        return (c[2] - c[0]) * (c[3] - c[1])
    return [d for d in deteccoes
            if not any(o[1] > d[1] and area(o[2]) > area(d[2]) and contida(d[2], o[2]) >= limiar
                       for o in deteccoes)]


def abrir_imagem(caminho):
    """Abre a imagem em RGB já com a rotação do EXIF aplicada."""
    imagem = Image.open(caminho)
    girada = imagem.getexif().get(TAG_ORIENTACAO_EXIF, 1) != 1
    return ImageOps.exif_transpose(imagem).convert("RGB"), girada


class Detector:
    """
    Base dos anotadores que detectam: o que não depende do modelo. Uma
    subclasse define nome (a pasta das propostas) e MODELO_PADRAO, e implementa
    só carregar() e pontuar(imagem); a base escolhe a classe de cada caixa
    (com a classe de reserva), descarta as fora da área máxima e abaixo do piso,
    e aplica o NMS sem classe e a remoção das contidas.

    Interface de todo anotador (ver ANOTADORES), detector ou não: o atributo
    nome; opcoes(parser), com as opções próprias dele (as comuns de detecção
    estão em main()); criar(classes, args); e, na instância, versao, parametros
    e anotar(imagem) -> [(id da classe, confianca, (x1, y1, x2, y2) normalizada)],
    todas as caixas a partir do piso. parametros traz confianca e
    confianca_classe, os limiares de leitura (saida.separar()).
    """

    nome = None
    MODELO_PADRAO = None

    @classmethod
    def opcoes(cls, parser):
        """Opções próprias do detector; as comuns (main()) servem a todos."""

    @classmethod
    def argumentos(cls, args):
        """Argumentos próprios do construtor, tirados das opções de opcoes()."""
        return {}

    @classmethod
    def criar(cls, classes, args):
        return cls(classes, modelo=args.modelo, dispositivo=args.dispositivo,
                   piso=args.piso, confianca=args.confianca,
                   confianca_classe=args.confianca_classe, limiar_iou=args.iou,
                   area_maxima=args.area_maxima, contencao=args.contencao,
                   **cls.argumentos(args))

    def __init__(self, classes, modelo=None, dispositivo=None, piso=PISO_PADRAO,
                 confianca=CONFIANCA_PADRAO, confianca_classe=CONFIANCA_CLASSE_PADRAO,
                 limiar_iou=IOU_PADRAO, area_maxima=AREA_MAXIMA_PADRAO,
                 contencao=CONTENCAO_PADRAO):
        if not 0 <= piso <= confianca <= 1:
            raise ValueError(f"limiares inválidos: piso {piso} e confiança {confianca} "
                             "(0 <= piso <= confiança <= 1)")
        self.classes = classes
        self.n_classes = len(classes)
        self.reservas = frozenset(i for i, c in enumerate(classes) if c.get("reserva"))
        self.versao = modelo or self.MODELO_PADRAO
        self.dispositivo = dispositivo
        self.piso = piso
        self.confianca = confianca
        self.limiar_iou = limiar_iou
        self.area_maxima = area_maxima
        self.contencao = contencao
        self.parametros = {"piso": piso, "confianca": confianca,
                           "confianca_classe": confianca_classe, "iou": limiar_iou,
                           "area_maxima": area_maxima, "contencao": contencao}
        self.carregar()

    def carregar(self):
        """Carrega o modelo (self.versao) em self.dispositivo, se dado."""
        raise NotImplementedError

    def pontuar(self, imagem):
        """
        Saída bruta do modelo para uma imagem PIL em RGB: (pontuacoes, caixas).
        pontuacoes: a pontuação de cada classe (na ordem de classes) em cada
        caixa, lista de listas ou tensor (caixas, classes); caixas: (x1, y1,
        x2, y2) normalizadas de 0 a 1, uma por linha de pontuacoes.
        """
        raise NotImplementedError

    def filtrar(self, pontuacoes, caixas, piso=None):
        """
        Saída de pontuar() -> [(classe, confianca, (x1, y1, x2, y2))], da mais
        confiante para a menos, após o piso, a área máxima, o NMS e a remoção
        das contidas. piso substitui o do construtor (avaliar.py).
        """
        piso = self.piso if piso is None else piso
        linhas = pontuacoes.tolist() if hasattr(pontuacoes, "tolist") else pontuacoes
        deteccoes = []
        for linha, caixa in zip(linhas, caixas):
            # A reserva compete pelo limiar de leitura, não pelo piso: é o que
            # decide se alguma classe comum "chegou"
            classe, conf = escolher_classe(linha, self.reservas, self.confianca)
            if conf < piso:
                continue
            area = (caixa[2] - caixa[0]) * (caixa[3] - caixa[1])
            if caixa[2] > caixa[0] and caixa[3] > caixa[1] and area <= self.area_maxima:
                deteccoes.append((classe, conf, caixa))
        return sem_contidas(nms(deteccoes, self.limiar_iou), self.contencao)

    def anotar(self, imagem):
        return self.filtrar(*self.pontuar(imagem))


class GroundingDino(Detector):
    """Grounding DINO, com o prompt das classes já tokenizado."""

    nome = "grounding-dino"
    MODELO_PADRAO = MODELO_PADRAO

    def carregar(self):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.torch = torch
        self.dispositivo = self.dispositivo or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Carregando {self.versao} em {self.dispositivo}...")
        self.processador = AutoProcessor.from_pretrained(self.versao)
        self.modelo = AutoModelForZeroShotObjectDetection.from_pretrained(self.versao)
        self.modelo.to(self.dispositivo).eval()

        self.texto, intervalos = montar_prompt(self.classes)
        tokens = self.processador.tokenizer(self.texto, return_offsets_mapping=True)
        limite = getattr(self.modelo.config, "max_text_len", 256)
        if len(tokens["input_ids"]) > limite:
            raise ValueError(f"Prompts longos demais: {len(tokens['input_ids'])} tokens "
                             f"(máximo {limite}). Reduza as classes ou os prompts.")
        self.input_ids = tokens["input_ids"]
        self.token_classe = classe_de_cada_token(tokens["offset_mapping"], intervalos)

    def pontuar(self, imagem):
        """
        As 900 consultas do modelo: tensor (consultas, classes) e as caixas
        recortadas à imagem. A pontuação de uma classe numa consulta é a maior
        entre os tokens do prompt dela.
        """
        torch = self.torch
        entradas = self.processador(images=imagem, text=self.texto, return_tensors="pt")
        if entradas["input_ids"][0].tolist() != self.input_ids:
            raise RuntimeError("Tokenização do processador difere da do tokenizer")
        entradas = entradas.to(self.dispositivo)
        with torch.no_grad():
            saida = self.modelo(**entradas)

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


def caixas_owlv2(pred_boxes, largura, altura):
    """
    Caixas do OWLv2 (cx, cy, w, h), normalizadas pela imagem quadrada que o
    processador monta (a original no canto superior esquerdo, completada
    embaixo ou à direita), para (x1, y1, x2, y2) normalizadas pela original
    e recortadas a ela.
    """
    lado = max(largura, altura)
    sx, sy = lado / largura, lado / altura
    return [(max(0.0, (cx - w / 2) * sx), max(0.0, (cy - h / 2) * sy),
             min(1.0, (cx + w / 2) * sx), min(1.0, (cy + h / 2) * sy))
            for cx, cy, w, h in pred_boxes]


class Owlv2(Detector):
    """
    OWLv2 (CLIP adaptado à detecção): uma consulta de texto por prompt,
    pontuada em cada fragmento da imagem, sem mapeamento por token; a classe
    recebe a maior entre as consultas dos seus prompts.
    """

    nome = "owlv2"
    MODELO_PADRAO = "google/owlv2-base-patch16-ensemble"

    @classmethod
    def opcoes(cls, parser):
        grupo = parser.add_argument_group("owlv2")
        grupo.add_argument("--owlv2-frase", default="{}",
                           help="modelo da consulta de cada classe, com {} no lugar do "
                                "prompt (ex.: 'a photo of a {}'; padrão: o prompt puro)")

    @classmethod
    def argumentos(cls, args):
        return {"frase": args.owlv2_frase}

    def __init__(self, classes, frase="{}", **kwargs):
        if "{}" not in frase:
            raise ValueError(f"--owlv2-frase sem {{}}: {frase!r}")
        self.frase = frase
        super().__init__(classes, **kwargs)
        self.parametros["frase"] = frase

    def carregar(self):
        import torch
        from transformers import Owlv2ForObjectDetection, Owlv2Processor

        self.torch = torch
        self.dispositivo = self.dispositivo or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Carregando {self.versao} em {self.dispositivo}...")
        self.processador = Owlv2Processor.from_pretrained(self.versao)
        self.modelo = Owlv2ForObjectDetection.from_pretrained(self.versao)
        self.modelo.to(self.dispositivo).eval()
        self.textos, self.classe_da_consulta = [], []
        for i, c in enumerate(self.classes):
            for p in prompts(c):
                self.textos.append(self.frase.format(p))
                self.classe_da_consulta.append(i)
        # O texto das consultas não muda: tokeniza uma vez só
        self.entradas_texto = self.processador(text=[self.textos], return_tensors="pt",
                                               padding="max_length", truncation=True)
        limite = self.processador.tokenizer.model_max_length
        longos = [t for t in self.textos
                  if len(self.processador.tokenizer(t)["input_ids"]) > limite]
        if longos:
            raise ValueError(f"Consultas longas demais para o OWLv2 (máximo {limite} "
                             f"tokens): {', '.join(longos)}")

    def pontuar(self, imagem):
        """
        Um fragmento da imagem por caixa (3600 no base, a 960 px): tensor
        (caixas, classes) com o sigmoide do logit de cada consulta; a classe
        fica com a maior entre as consultas dos seus prompts.
        """
        torch = self.torch
        entradas = self.processador(images=imagem, return_tensors="pt")
        entradas.update(self.entradas_texto)
        entradas = entradas.to(self.dispositivo)
        with torch.no_grad():
            saida = self.modelo(**entradas)
        por_consulta = saida.logits[0].sigmoid().cpu()
        pontuacoes = torch.zeros(por_consulta.shape[0], self.n_classes)
        for q, c in enumerate(self.classe_da_consulta):
            pontuacoes[:, c] = torch.maximum(pontuacoes[:, c], por_consulta[:, q])
        return pontuacoes, caixas_owlv2(saida.pred_boxes[0].cpu().tolist(), *imagem.size)


def colunas_yolo(classes, nomes_modelo):
    """
    Para cada classe de classes.yaml, o id dela no modelo YOLO (nomes_modelo:
    {id: nome}, o model.names do Ultralytics), casada pelo nome. Recusa classe
    que o modelo não conhece.
    """
    ids = {n: i for i, n in nomes_modelo.items()}
    fora = [c["nome"] for c in classes if c["nome"] not in ids]
    if fora:
        raise ValueError(f"classes que o modelo YOLO não tem: {', '.join(fora)}")
    return [ids[c["nome"]] for c in classes]


class Yolo(Detector):
    """
    YOLO de conjunto fechado (Ultralytics), por padrão o best.pt da equipe
    (YOLOv8s do TACO com fine-tuning nas fotos do projeto). Não usa os
    prompts: as classes de classes.yaml são casadas pelo nome com as do
    modelo. pontuar() devolve a saída crua da rede, antes do NMS do
    Ultralytics: a pontuação de cada classe de classes.yaml em cada âncora, e
    a classe vencedora sai só entre elas, como nos outros detectores.
    """

    nome = "yolo"
    MODELO_PADRAO = "yolo_models/taco/best.pt"
    LADO_PADRAO = 640   # imgsz do treino do best.pt (e o padrão do backend)

    @classmethod
    def opcoes(cls, parser):
        grupo = parser.add_argument_group("yolo")
        grupo.add_argument("--yolo-lado", type=int, default=cls.LADO_PADRAO,
                           help="lado maior da imagem na entrada da rede, múltiplo de 32 "
                                f"(padrão: {cls.LADO_PADRAO}, o do treino do best.pt)")

    @classmethod
    def argumentos(cls, args):
        return {"lado": args.yolo_lado}

    def __init__(self, classes, lado=LADO_PADRAO, **kwargs):
        if lado <= 0 or lado % 32:
            raise ValueError(f"--yolo-lado tem de ser múltiplo positivo de 32: {lado}")
        self.lado = lado
        super().__init__(classes, **kwargs)
        self.parametros["lado"] = lado

    def carregar(self):
        import torch
        from ultralytics import YOLO
        from ultralytics.data.augment import LetterBox

        self.torch = torch
        self.dispositivo = self.dispositivo or ("cuda" if torch.cuda.is_available() else "cpu")
        caminho = Path(self.versao)
        if not caminho.is_absolute() and not caminho.exists():
            caminho = DIR_SCRIPT.parent / caminho   # relativo à raiz do repositório
        print(f"Carregando {caminho} em {self.dispositivo}...")
        yolo = YOLO(str(caminho))
        self.colunas = colunas_yolo(self.classes, yolo.names)
        self.rede = yolo.model.to(self.dispositivo).eval()
        passo = int(self.rede.stride.max())
        # Mesmo pré-processamento do predict() do Ultralytics: lado maior em
        # self.lado, completado com cinza só até o múltiplo do passo
        self.letterbox = LetterBox((self.lado, self.lado), auto=True, stride=passo)

    def pontuar(self, imagem):
        """
        As âncoras da rede (8400 a 640x640, menos com a sobra cortada) com alguma classe de classes.yaml
        a partir do piso: tensor (caixas, classes) e as caixas na imagem
        original, normalizadas.
        """
        import numpy as np
        from ultralytics.utils import ops

        torch = self.torch
        original = np.asarray(imagem)
        entrada = self.letterbox(image=original)
        tensor = torch.from_numpy(np.ascontiguousarray(entrada.transpose(2, 0, 1)))
        tensor = tensor.to(self.dispositivo).float().unsqueeze(0) / 255
        with torch.no_grad():
            saida = self.rede(tensor)
        saida = (saida[0] if isinstance(saida, (list, tuple)) else saida)[0]   # (4 + nc, âncoras)
        pontuacoes = saida[4:][self.colunas].T            # (âncoras, classes)
        manter = pontuacoes.max(dim=1).values >= self.piso
        pontuacoes = pontuacoes[manter].cpu()
        caixas = ops.scale_boxes(tensor.shape[2:], ops.xywh2xyxy(saida[:4].T[manter]),
                                 original.shape[:2]).cpu()
        altura, largura = original.shape[:2]
        caixas = [(max(0.0, x1 / largura), max(0.0, y1 / altura),
                   min(1.0, x2 / largura), min(1.0, y2 / altura))
                  for x1, y1, x2, y2 in caixas.tolist()]
        return pontuacoes, caixas


# Anotadores disponíveis em --anotador, pelo nome
ANOTADORES = {a.nome: a for a in (GroundingDino, Owlv2, Yolo)}


def desenhar_previa(imagem, deteccoes, classes, destino, confianca=0.0, confianca_classe=0.0):
    """As caixas que a página mostraria (a partir de confianca), "sem classe" abaixo de confianca_classe."""
    previa = imagem.copy()
    desenho = ImageDraw.Draw(previa)
    largura, altura = previa.size
    espessura = max(2, round(min(largura, altura) / 300))
    fonte = ImageFont.load_default(size=max(12, round(min(largura, altura) / 50)))
    for classe, conf, (x1, y1, x2, y2) in deteccoes:
        if conf < confianca:
            continue
        caixa = (x1 * largura, y1 * altura, x2 * largura, y2 * altura)
        desenho.rectangle(caixa, outline=(34, 197, 94), width=espessura)
        nome = classes[classe]["nome"] if conf >= confianca_classe else "sem classe"
        rotulo = f"{nome} {conf:.2f}"
        fundo = desenho.textbbox((caixa[0], caixa[1]), rotulo, font=fonte, anchor="lb")
        desenho.rectangle(fundo, fill=(34, 197, 94))
        desenho.text((caixa[0], caixa[1]), rotulo, fill=(0, 0, 0), font=fonte, anchor="lb")
    previa.save(destino, quality=90)


def escolher_imagens(parser, args, linhas):
    """
    As imagens a anotar, entre as importadas: as pedidas na linha de comando ou,
    sem nenhuma, as pendentes ainda sem proposta deste anotador (todas as
    pendentes com --sobrescrever). Só pendentes: anotar de novo uma revisada ou
    descartada trocaria a proposta que o registro da revisão cita.
    """
    ja_anotadas = formato.imagens_com_proposta(args.saida, args.pasta)
    if not args.imagens:
        return [n for n, linha in linhas.items() if linha["status"] == "pendente"
                and (args.sobrescrever or n not in ja_anotadas)]
    pedidas = list(dict.fromkeys(Path(i).name for i in args.imagens))
    fora = [n for n in pedidas if n not in linhas]
    if fora:
        parser.error(f"não importadas em {args.saida}: {', '.join(fora)} "
                     "(importe antes com o importar.py)")
    nao_pendentes = [n for n in pedidas if linhas[n]["status"] != "pendente"]
    if nao_pendentes:
        print(f"Puladas (já {', '.join(sorted({linhas[n]['status'] for n in nao_pendentes}))}): "
              f"{', '.join(nao_pendentes)}")
    pedidas = [n for n in pedidas if n not in nao_pendentes]
    if not args.sobrescrever:
        existentes = [n for n in pedidas if n in ja_anotadas]
        if existentes:
            parser.error(f"já anotadas por {args.pasta} em {args.saida}: "
                         f"{', '.join(existentes)} (use --sobrescrever)")
    return pedidas


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Propõe caixas para as imagens importadas com um anotador automático.")
    parser.add_argument("imagens", nargs="*",
                        help="nomes de imagens já importadas (padrão: as pendentes ainda sem "
                             "proposta deste anotador)")
    parser.add_argument("-o", "--saida", type=Path, default=Path("anotacoes"),
                        help="diretório de saída, já com imagens importadas (padrão: ./anotacoes)")
    parser.add_argument("--anotador", choices=sorted(ANOTADORES), default=GroundingDino.nome,
                        help=f"anotador (padrão: {GroundingDino.nome})")
    parser.add_argument("--nome", help="nome com que as propostas são gravadas (padrão: o do "
                                       "anotador); para rodar o mesmo "
                                       "anotador com outra configuração na mesma saída, como "
                                       "outro peso do YOLO")
    parser.add_argument("--classes", type=Path, default=DIR_SCRIPT / "classes.yaml",
                        help="lista de classes (padrão: anotacao/classes.yaml)")
    parser.add_argument("--dispositivo", help="cuda ou cpu (padrão: cuda se houver)")
    parser.add_argument("--previa", action="store_true",
                        help="grava também previa/<anotador>/<nome>.jpg com as caixas desenhadas")
    parser.add_argument("--sobrescrever", action="store_true",
                        help="anota de novo imagens pendentes que já têm proposta deste "
                             "anotador (grava uma proposta nova; a anterior fica no banco)")
    parser.add_argument("--aceitar", action="store_true",
                        help="grava as propostas do anotador como revisão (labels/) e marca "
                             "as imagens como revisadas (só as pendentes; sem imagens na "
                             "linha de comando, todas)")
    parser.add_argument("--exportar", action="store_true",
                        help="só refaz do banco os arquivos gerados (data.yaml, labels/, "
                             "revisadas.txt) e sai")
    deteccao = parser.add_argument_group(
        "detecção", "a proposta guarda todas as caixas a partir do piso; --confianca e "
                    "--confianca-classe são gravados nela e aplicados por quem lê")
    deteccao.add_argument("--modelo", help="modelo do anotador (padrão: o do anotador; "
                                           f"grounding-dino: {MODELO_PADRAO}; "
                                           f"owlv2: {Owlv2.MODELO_PADRAO}; "
                                           f"yolo: {Yolo.MODELO_PADRAO})")
    deteccao.add_argument("--piso", type=float, default=PISO_PADRAO,
                          help="confiança mínima gravada; as caixas entre o piso e --confianca "
                               f"são as candidatas da caixa por clique (padrão: {PISO_PADRAO})")
    deteccao.add_argument("--confianca", type=float, default=CONFIANCA_PADRAO,
                          help="a página mostra as caixas a partir dessa confiança "
                               f"(padrão: {CONFIANCA_PADRAO})")
    deteccao.add_argument("--confianca-classe", type=float, default=CONFIANCA_CLASSE_PADRAO,
                          help="abaixo dessa, a página mostra a caixa sem classe, e o revisor "
                               f"tem de dá-la; 0 desliga (padrão: {CONFIANCA_CLASSE_PADRAO})")
    deteccao.add_argument("--iou", type=float, default=IOU_PADRAO,
                          help="IoU acima do qual caixas sobrepostas viram uma, qualquer que "
                               f"seja a classe (padrão: {IOU_PADRAO})")
    deteccao.add_argument("--area-maxima", type=float, default=AREA_MAXIMA_PADRAO,
                          help="descarta caixas maiores que essa fração da imagem "
                               f"(padrão: {AREA_MAXIMA_PADRAO})")
    deteccao.add_argument("--contencao", type=float, default=CONTENCAO_PADRAO,
                          help="remove a caixa contida nessa fração numa maior e mais "
                               f"confiante; acima de 1 desliga (padrão: {CONTENCAO_PADRAO})")
    for anotador in ANOTADORES.values():
        anotador.opcoes(parser)
    args = parser.parse_args(argv)
    if not 0 <= args.piso <= args.confianca <= 1:
        parser.error("os limiares têm de valer 0 <= --piso <= --confianca <= 1")
    if args.nome is not None and not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", args.nome):
        parser.error("--nome só com minúsculas, dígitos, '.', '_' e '-'")
    args.pasta = args.nome or args.anotador

    if not formato.existe(args.saida):
        parser.error(f"{args.saida} não tem imagens importadas (use o importar.py antes)")
    if args.exportar:
        formato.exportar(args.saida)
        print(f"Arquivos refeitos do banco em {args.saida.resolve()}")
        return
    classes = carregar_classes(args.classes)
    formato.preparar(args.saida, carregar_nomes(args.classes))
    linhas = formato.ler_estado(args.saida)
    lotes = formato.ler_lotes(args.saida)
    alvo = escolher_imagens(parser, args, linhas)
    if not alvo and not args.aceitar:
        print(f"Nada a anotar com {args.pasta} em {args.saida}.")

    if alvo:
        if args.previa:
            (args.saida / "previa" / args.pasta).mkdir(parents=True, exist_ok=True)
        anotador = ANOTADORES[args.anotador].criar(classes, args)
        # Os limiares de leitura vão na execução; um anotador que não os define
        # recebe os da linha de comando
        parametros = {"confianca": args.confianca, "confianca_classe": args.confianca_classe,
                      **anotador.parametros}
        formato.copia_seguranca(args.saida)
        execucao = formato.nova_execucao(args.saida, args.pasta, anotador.nome, anotador.versao,
                                         parametros, formato.hash_classes(classes))

    for nome in alvo:
        imagem, _ = abrir_imagem(args.saida / "images" / nome)
        deteccoes = anotador.anotar(imagem)
        # Região de interesse do lote: fora dela (pelo centro da caixa), é fundo fixo
        regiao = lotes.get(linhas[nome].get("lote"), {}).get("regiao")
        deteccoes = [d for d in deteccoes if formato.dentro_da_regiao(d[2], regiao)]

        formato.gravar_proposta(args.saida, execucao, nome,
                                [(classes[c]["nome"], conf, caixa) for c, conf, caixa in deteccoes])
        if args.previa:
            desenhar_previa(imagem, deteccoes, classes,
                            args.saida / "previa" / args.pasta / f"{Path(nome).stem}.jpg",
                            parametros["confianca"], parametros["confianca_classe"])

        visiveis = [(c, conf) for c, conf, _ in deteccoes if conf >= parametros["confianca"]]
        resumo = ", ".join(
            f"{classes[c]['nome'] if conf >= parametros['confianca_classe'] else 'sem classe'} "
            f"{conf:.2f}" for c, conf in visiveis)
        print(f"{nome}: {len(visiveis)} objeto(s){': ' + resumo if resumo else ''} "
              f"(+{len(deteccoes) - len(visiveis)} candidata(s))")

    if args.aceitar:
        escolhidas = set(alvo) if args.imagens else None
        aceitas, sem_classe = formato.aceitar(args.saida, args.pasta, escolhidas)
        print(f"{aceitas} imagem(ns) aceita(s): propostas de {args.pasta} gravadas como "
              "revisão e copiadas para labels/")
        if sem_classe:
            print(f"{len(sem_classe)} imagem(ns) continuam pendentes, com caixa sem classe "
                  f"(revise-as na página): {', '.join(sem_classe)}")

    pagina = gerar_pagina(args.saida)
    print(f"Anotações em {args.saida.resolve()}")
    print(f"Para conferir, abra no navegador: {pagina.resolve().as_uri()}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
