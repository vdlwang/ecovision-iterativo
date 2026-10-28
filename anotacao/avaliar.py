"""
Avalia o anotador automático nas fotos rotuladas pela equipe.

Duas medidas, sobre um ou mais datasets no formato YOLO (padrão: as quatro
validações de legado/database):

1. Classificação: para cada caixa verdadeira, a consulta do modelo que mais se
   sobrepõe a ela e a classe que o modelo dá a essa consulta. Separa o erro de
   classe do erro de localização.
2. Detecção: o anotar.py completo (filtros e NMS) em vários limiares de
   confiança; acerto é IoU >= 0,5 com uma caixa verdadeira da mesma classe.

Os rótulos da equipe usam os nomes TACO; só entram as classes de classes.yaml,
casadas pelo nome. Polígonos (formato de segmentação) viram a caixa que os
contém.

Uso:
    python anotacao/avaliar.py
    python anotacao/avaliar.py legado/database/tcc-0CF/YOLO_dataset/validation \\
        --modelo IDEA-Research/grounding-dino-base
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

import anotar

DIR_REPO = anotar.DIR_SCRIPT.parent
DATASETS_PADRAO = sorted((DIR_REPO / "legado" / "database").glob("tcc-*/YOLO_dataset/validation"))
LIMIARES_PADRAO = [0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
IOU_ACERTO = 0.5
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def nomes_do_dataset(pasta):
    """Nomes das classes do data.yaml na pasta do split ou na de cima."""
    for data_yaml in (pasta / "data.yaml", pasta.parent / "data.yaml"):
        if data_yaml.exists():
            with open(data_yaml, encoding="utf-8") as f:
                nomes = (yaml.safe_load(f) or {}).get("names") or []
            return list(nomes.values()) if isinstance(nomes, dict) else list(nomes)
    raise ValueError(f"data.yaml não encontrado em {pasta} nem em {pasta.parent}")


def ler_verdade(caminho, nomes_dataset, nomes):
    """
    Rótulos de um .txt YOLO (caixa 'id cx cy w h' ou polígono 'id x1 y1 x2 y2 ...')
    -> ([(classe em nomes, (x1, y1, x2, y2))], Counter dos nomes fora de nomes).
    """
    verdade, fora = [], Counter()
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if not partes:
            continue
        nome = nomes_dataset[int(partes[0])]
        valores = [float(v) for v in partes[1:]]
        if len(valores) == 4:
            cx, cy, w, h = valores
            caixa = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        elif len(valores) >= 6 and len(valores) % 2 == 0:
            xs, ys = valores[0::2], valores[1::2]
            caixa = (min(xs), min(ys), max(xs), max(ys))
        else:
            raise ValueError(f"{caminho}: linha inválida: {linha!r}")
        if nome in nomes:
            verdade.append((nomes.index(nome), caixa))
        else:
            fora[nome] += 1
    return verdade, fora


def listar_imagens(pastas):
    """[(imagem, .txt, nomes do dataset)] das pastas com images/ e labels/."""
    itens = []
    for pasta in pastas:
        nomes_dataset = nomes_do_dataset(pasta)
        imagens = sorted(p for p in (pasta / "images").iterdir()
                         if p.suffix.lower() in EXTENSOES_IMAGEM)
        if not imagens:
            raise ValueError(f"nenhuma imagem em {pasta / 'images'}")
        for imagem in imagens:
            rotulo = pasta / "labels" / f"{imagem.stem}.txt"
            if rotulo.exists():
                itens.append((imagem, rotulo, nomes_dataset))
    return itens


def consulta_mais_proxima(caixas, caixa):
    """Índice e IoU da caixa de caixas que mais se sobrepõe a caixa."""
    ious = [anotar.iou(caixa, c) for c in caixas]
    melhor = max(range(len(ious)), key=ious.__getitem__)
    return melhor, ious[melhor]


def casar(deteccoes, verdade, limiar_iou=IOU_ACERTO):
    """
    Casamento guloso, da detecção mais confiante para a menos; cada caixa
    verdadeira casa com uma detecção só. Devolve (acertos, falsos positivos,
    falsos negativos).
    """
    usadas = set()
    acertos = 0
    for classe, _, caixa in sorted(deteccoes, key=lambda d: d[1], reverse=True):
        candidatas = [(anotar.iou(caixa, v), i) for i, (c, v) in enumerate(verdade)
                      if i not in usadas and c == classe]
        melhor = max(candidatas, default=(0.0, None))
        if melhor[0] >= limiar_iou:
            usadas.add(melhor[1])
            acertos += 1
    return acertos, len(deteccoes) - acertos, len(verdade) - acertos


def imprimir_classificacao(matriz, classes):
    """matriz: Counter de (verdadeira, prevista ou None se não localizada)."""
    nomes = [c["nome"] for c in classes]
    materiais = [c["material"] for c in classes]
    largura = max(len(n) for n in nomes)
    print("\nClassificação (linhas: classe verdadeira; colunas: prevista)")
    print(" " * (largura + 4) + "".join(f"{i:>5}" for i in range(len(nomes)))
          + "  n.loc  acerto")
    for v, nome in enumerate(nomes):
        linha = [matriz[(v, p)] for p in range(len(nomes))]
        total = sum(linha)
        acerto = f"{linha[v] / total:6.0%}" if total else "     -"
        print(f"{v:>2}  {nome:<{largura}}" + "".join(f"{n:>5}" for n in linha)
              + f"{matriz[(v, None)]:>7}  {acerto}")

    localizadas = sum(n for (v, p), n in matriz.items() if p is not None)
    classe_certa = sum(n for (v, p), n in matriz.items() if p == v)
    material_certo = sum(n for (v, p), n in matriz.items()
                         if p is not None and materiais[p] == materiais[v])
    nao_localizadas = sum(n for (v, p), n in matriz.items() if p is None)
    if localizadas:
        print(f"\nClasse certa: {classe_certa}/{localizadas} ({classe_certa / localizadas:.0%}); "
              f"material certo: {material_certo}/{localizadas} "
              f"({material_certo / localizadas:.0%}); "
              f"não localizadas (IoU < {IOU_ACERTO}): {nao_localizadas}")


def imprimir_deteccao(contagens):
    """contagens: {limiar: [acertos, falsos positivos, falsos negativos]}."""
    print(f"\nDetecção (acerto: IoU >= {IOU_ACERTO} e mesma classe)")
    print("limiar  acertos  FP     FN    precisão  recall")
    for limiar, (tp, fp, fn) in sorted(contagens.items()):
        precisao = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        print(f"{limiar:5.2f}   {tp:6d}  {fp:5d}  {fn:5d}  {precisao:8.2f}  {recall:6.2f}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Avalia o anotador nas fotos rotuladas.")
    parser.add_argument("datasets", nargs="*", type=Path, default=DATASETS_PADRAO,
                        help="pastas com images/ e labels/ (padrão: validações de "
                             "legado/database)")
    parser.add_argument("--classes", type=Path, default=anotar.DIR_SCRIPT / "classes.yaml",
                        help="lista de classes (padrão: anotacao/classes.yaml)")
    parser.add_argument("--modelo", default=anotar.MODELO_PADRAO,
                        help=f"modelo do Hugging Face (padrão: {anotar.MODELO_PADRAO})")
    parser.add_argument("--limiares", type=float, nargs="+", default=LIMIARES_PADRAO,
                        help="limiares de confiança da detecção")
    parser.add_argument("--iou", type=float, default=0.5, help="IoU do NMS (padrão: 0.5)")
    parser.add_argument("--area-maxima", type=float, default=0.5,
                        help="fração máxima da imagem por caixa (padrão: 0.5)")
    parser.add_argument("--dispositivo", help="cuda ou cpu (padrão: cuda se houver)")
    args = parser.parse_args(argv)

    if not args.datasets:
        parser.error("nenhum dataset informado nem encontrado em legado/database")
    classes = anotar.carregar_classes(args.classes)
    nomes = [c["nome"] for c in classes]
    itens = listar_imagens(args.datasets)
    print(f"{len(itens)} imagem(ns) rotulada(s) em {len(args.datasets)} dataset(s)")

    anotador = anotar.Anotador(classes, args.modelo, args.dispositivo, min(args.limiares),
                               args.iou, args.area_maxima)
    matriz = Counter()
    contagens = {limiar: [0, 0, 0] for limiar in args.limiares}
    fora = Counter()
    for i, (imagem, rotulo, nomes_dataset) in enumerate(itens, 1):
        verdade, fora_imagem = ler_verdade(rotulo, nomes_dataset, nomes)
        fora += fora_imagem
        por_classe, caixas = anotador.pontuar(anotar.abrir_imagem(imagem)[0])

        for classe, caixa in verdade:
            consulta, iou = consulta_mais_proxima(caixas, caixa)
            prevista = int(por_classe[consulta].argmax()) if iou >= IOU_ACERTO else None
            matriz[(classe, prevista)] += 1

        for limiar in args.limiares:
            resultado = casar(anotador.filtrar(por_classe, caixas, limiar), verdade)
            contagens[limiar] = [a + b for a, b in zip(contagens[limiar], resultado)]
        print(f"\r{i}/{len(itens)}", end="", flush=True)
    print()

    print(f"Caixas verdadeiras nas classes de {args.classes.name}: {sum(matriz.values())}")
    if fora:
        print("Ignoradas (fora das classes): "
              + ", ".join(f"{n} {q}" for n, q in fora.most_common()))
    imprimir_classificacao(matriz, classes)
    imprimir_deteccao(contagens)


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
