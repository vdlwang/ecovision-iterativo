"""
Voto 3oo3 entre os anotadores (OBJETIVO.md, seção 3; tarefa T6). Lê as
propostas vigentes de cada anotador no banco da saída e aprova a imagem só se
todos concordam: mesma quantidade de caixas, e cada caixa casa (mesma classe,
IoU >= 0,5) com uma de cada um dos outros. A aprovada recebe as caixas de
consenso (a mediana de cada coordenada; a confiança é a menor) como rótulo em
labels/ e entra no treino.txt; a que falha fica pendente, para a revisão.

    python anotacao/importar.py fotos/ -o anotacoes --lote 2026-11-14a
    python anotacao/anotar.py -o anotacoes --anotador grounding-dino   # e owlv2, yolo
    python anotacao/votar.py anotacoes [--anotadores grounding-dino owlv2 yolo]

Só vota imagens pendentes de lotes de treino com proposta de todos os
anotadores; as de teste vão à revisão sem pré-anotação (seção 4). Cada
anotador é lido no limiar de leitura gravado na proposta (--limiares troca),
com a classe sugerida mesmo abaixo de confianca_classe: ela só é escondida do
revisor. Rodar de novo vota as imagens novas e as que ganharam proposta nova;
--revotar vota de novo todas as pendentes. Cada voto fica no banco com as
propostas que usou; o banco está no saida.py.
"""

import argparse
import sys
from pathlib import Path
from statistics import median

import saida as formato
from anotar import iou

TRIO = ["grounding-dino", "owlv2", "yolo"]  # decisão 17 do OBJETIVO.md
IOU_VOTO = 0.5


def casar_mesma_classe(a, b, limiar_iou=IOU_VOTO):
    """
    Casamento guloso pelo IoU entre as detecções de dois anotadores, só entre
    caixas da mesma classe: {índice em a: índice em b} com IoU >= limiar_iou.
    """
    pares = sorted(((iou(da[2], db[2]), i, j) for i, da in enumerate(a)
                    for j, db in enumerate(b) if da[0] == db[0]), reverse=True)
    usadas_a, usadas_b, casados = set(), set(), {}
    for valor, i, j in pares:
        if valor < limiar_iou:
            break
        if i not in usadas_a and j not in usadas_b:
            usadas_a.add(i)
            usadas_b.add(j)
            casados[i] = j
    return casados


def consenso_por_caixa(listas, limiar_iou=IOU_VOTO):
    """
    As caixas em que os N anotadores concordam, sem exigir a imagem inteira:
    cada caixa do primeiro que casa (mesma classe, IoU >= limiar_iou) com uma
    de cada um dos outros, e essas entre si. [(classe, menor confiança,
    mediana de cada coordenada)].
    """
    base = listas[0]
    casamentos = [casar_mesma_classe(base, outra, limiar_iou) for outra in listas[1:]]
    consenso = []
    for i, (classe, conf, caixa) in enumerate(base):
        if not all(i in c for c in casamentos):
            continue
        grupo = [(conf, caixa)] + [(l[c[i]][1], l[c[i]][2]) for l, c in zip(listas[1:], casamentos)]
        caixas = [g[1] for g in grupo]
        if any(iou(x, y) < limiar_iou for k, x in enumerate(caixas) for y in caixas[k + 1:]):
            continue
        consenso.append((classe, min(g[0] for g in grupo),
                         tuple(median(c[k] for c in caixas) for k in range(4))))
    return consenso


def voto_estrito(listas, limiar_iou=IOU_VOTO):
    """
    Voto NooN estrito sobre as detecções de N anotadores numa imagem, cada
    lista já no limiar de leitura do seu anotador. Passa se todos propõem o
    mesmo número de caixas e cada caixa do primeiro casa (mesma classe, IoU >=
    limiar_iou) com uma de cada um dos outros, e essas também casam entre si.
    Imagem sem caixa não passa. Devolve (motivo, consenso): motivo None se
    passou, senão "vazia", "quantidade" ou "caixas"; consenso, [(classe, menor
    confiança, mediana de cada coordenada)] quando passa.
    """
    if not any(listas):
        return "vazia", []
    if len({len(l) for l in listas}) > 1:
        return "quantidade", []
    consenso = consenso_por_caixa(listas, limiar_iou)
    if len(consenso) != len(listas[0]):
        return "caixas", []
    return None, consenso


def decisor(limiares=None, limiar_iou=IOU_VOTO):
    """
    A função de decisão que o saida.votar() chama com as propostas de uma
    imagem. limiares: um por anotador, None para o gravado na proposta.
    """
    def decidir(propostas):
        usados, listas = [], []
        for proposta, limiar in zip(propostas, limiares or [None] * len(propostas)):
            limiar = formato.limiares(proposta)[0] if limiar is None else limiar
            usados.append(limiar)
            listas.append([c for c in formato.caixas_normalizadas(proposta) if c[1] >= limiar])
        motivo, consenso = voto_estrito(listas, limiar_iou)
        return motivo, consenso, usados
    return decidir


def votar(saida, anotadores=TRIO, limiares=None, limiar_iou=IOU_VOTO, revotar=False,
          agora=None):
    """Vota as imagens da saída (saida.votar); devolve o resumo dele."""
    if limiares is not None and len(limiares) != len(anotadores):
        raise ValueError("um limiar por anotador")
    parametros = {"iou": limiar_iou,
                  "limiares": dict(zip(anotadores, limiares or [None] * len(anotadores)))}
    return formato.votar(saida, anotadores, decisor(limiares, limiar_iou), parametros,
                         revotar, agora)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Voto NooN estrito entre anotadores: aprova as imagens de treino em que "
                    "todos concordam e grava as caixas de consenso como rótulo.")
    parser.add_argument("saida", type=Path, help="saída anotada (importar.py e anotar.py)")
    parser.add_argument("--anotadores", nargs="+", default=TRIO, metavar="ANOTADOR",
                        help=f"quem vota, ao menos dois (padrão: {' '.join(TRIO)})")
    parser.add_argument("--limiares", nargs="+", metavar="L",
                        help="limiar de leitura de cada anotador, na mesma ordem; 'g' usa o "
                             "gravado na proposta (padrão: todos gravados)")
    parser.add_argument("--iou", type=float, default=IOU_VOTO,
                        help=f"IoU mínimo para duas caixas casarem (padrão: {IOU_VOTO})")
    parser.add_argument("--revotar", action="store_true",
                        help="vota de novo todas as pendentes, mesmo as já votadas com as "
                             "mesmas propostas")
    args = parser.parse_args(argv)
    if len(args.anotadores) < 2:
        parser.error("--anotadores: ao menos dois")
    limiares = None
    if args.limiares:
        if len(args.limiares) != len(args.anotadores):
            parser.error("--limiares precisa de um limiar por anotador")
        try:
            limiares = [None if l == "g" else float(l) for l in args.limiares]
        except ValueError:
            parser.error("--limiares: números ou 'g'")
        if any(l is not None and not 0 <= l <= 1 for l in limiares):
            parser.error("--limiares: entre 0 e 1")
    if not 0 < args.iou <= 1:
        parser.error("--iou: entre 0 e 1")
    if not formato.existe(args.saida):
        raise ValueError(f"{args.saida} não tem banco: importe e anote antes")
    sem_proposta = [a for a in args.anotadores if a not in formato.anotadores(args.saida)]
    if sem_proposta:
        raise ValueError(f"nenhuma proposta de {', '.join(sem_proposta)} em {args.saida} "
                         f"(anotadores com propostas: "
                         f"{', '.join(formato.anotadores(args.saida)) or 'nenhum'})")

    r = votar(args.saida, args.anotadores, limiares, args.iou, args.revotar)
    votadas = len(r["aprovadas"]) + len(r["falhou"])
    print(f"Voto {len(args.anotadores)}oo{len(args.anotadores)} de "
          f"{', '.join(args.anotadores)}: {votadas} imagem(ns) votada(s)")
    if votadas:
        motivos = {}
        for m in r["falhou"].values():
            motivos[m] = motivos.get(m, 0) + 1
        print(f"  aprovadas: {len(r['aprovadas'])} ({len(r['aprovadas']) / votadas:.0%}); "
              f"falharam: {len(r['falhou'])}"
              + (f" ({', '.join(f'{m} {q}' for m, q in sorted(motivos.items()))})"
                 if motivos else ""))
    print(f"  puladas: {r['ja_votadas']} já votada(s) com as mesmas propostas, "
          f"{r['incompletas']} sem proposta de todos, {r['teste']} de teste")
    linhas = (args.saida / "treino.txt").read_text(encoding="utf-8").splitlines()
    print(f"treino.txt: {len(linhas)} imagem(ns) (aprovadas e revisadas)")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
