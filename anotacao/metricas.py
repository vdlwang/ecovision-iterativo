"""
Métricas da anotação (RF13; OBJETIVO.md, tarefa T10), lidas do banco da
saída: nada roda modelo nem muda o banco.

    python anotacao/metricas.py anotacoes [--iou 0.5] [--json metricas.json]

1. Voto: imagens de treino votadas, aprovadas (e quantas na auditoria
   cega), reprovadas por motivo; imagens de teste unidas; pendentes sem voto.
2. Auditoria (T8): das aprovadas sorteadas já revisadas, a fração correta por
   inteiro (o revisor aceitou todas as caixas de consenso, sem trocar classe,
   remover nem acrescentar; descartar conta como erro), com o intervalo de
   Wilson de 95%, e o destino de cada caixa de consenso.
3. Correções: o desfecho de cada caixa revisada (aceita, classe corrigida,
   classe atribuída, adicionada de uma proposta ou de uma candidata), as
   caixas do voto removidas e as imagens descartadas, por grupo: reprovada,
   auditoria, aprovada (revista pelo filtro) e teste.
4. Tempo ativo de revisão: por imagem (mediana e média) e por objeto (soma
   dos tempos sobre a soma das caixas salvas), por grupo.
5. Anotadores frente à revisão: precisão e recall de cada anotador, das
   caixas visíveis da proposta que o voto usou contra as caixas salvas pelo
   revisor (casamento guloso, IoU >= --iou), sem e com a classe, separados
   em treino e teste. No treino, a revisão parte das caixas do voto e herda
   delas (viés de automação, seção 4); no teste, sem pré-anotação, a medida
   é menos enviesada, mas as caixas ainda vêm das candidatas dos anotadores.

Imagens descartadas não entram no item 5 (não têm caixas finais).

6. Avisos: estados que o banco não deveria ter (status sem a revisão que o
   explica, conjunto e resultado do voto que não batem) e limites da leitura
   (sem base de teste revisada, amostra da auditoria pequena, revisão com
   tempo zero).

Modo cego (medir(cega=True), o da aba de métricas do revisar.py): as
auditadas contam como reprovadas, e nada da auditoria aparece; senão, o
revisor veria o contador da auditoria subir ao salvar uma auditada.
"""

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

import saida as formato
from anotar import iou

IOU_PADRAO = 0.5
Z_95 = 1.959964
GRUPOS = ("falhou", "auditoria", "aprovada", "teste")
DESFECHOS = ("aceita", "classe_corrigida", "classe_atribuida", "adicionada")


def wilson(acertos, n, z=Z_95):
    """(proporção, mínimo, máximo) do intervalo de Wilson; None sem amostra."""
    if not n:
        return None
    p = acertos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return p, max(0.0, centro - margem), min(1.0, centro + margem)


def grupo(registro, cega=False):
    """
    De onde veio a imagem revisada: 'teste', 'auditoria' (aprovada
    sorteada), 'falhou' ou 'aprovada' (revista pelo filtro das aprovadas);
    None sem voto. cega: a auditada conta como 'falhou', como a página a
    mostra.
    """
    voto = registro["voto"]
    if voto is None:
        return None
    if registro["conjunto"] == "teste":
        return "teste"
    if voto["auditoria"]:
        return "falhou" if cega else "auditoria"
    return voto["resultado"]


def medir_voto(registros):
    treino = [r for r in registros if r["conjunto"] == "treino" and r["voto"]]
    aprovadas = [r for r in treino if r["voto"]["resultado"] == "aprovada"]
    motivos = Counter(r["voto"]["motivo"] for r in treino if r["voto"]["resultado"] == "falhou")
    return {
        "treino_votadas": len(treino),
        "aprovadas": len(aprovadas),
        "taxa_aprovacao": len(aprovadas) / len(treino) if treino else None,
        "auditadas": sum(r["voto"]["auditoria"] for r in aprovadas),
        "falhou": dict(sorted(motivos.items())),
        "teste_unidas": sum(1 for r in registros if r["conjunto"] == "teste" and r["voto"]),
        "sem_voto": sum(1 for r in registros if r["voto"] is None and r["status"] == "pendente"),
    }


def correta_por_inteiro(revisao):
    """O revisor salvou as caixas do voto como estavam: nenhuma troca, remoção ou acréscimo."""
    return (revisao["acao"] == "salvar" and revisao["removidas"] == 0
            and all(origem == "voto" and desfecho == "aceita"
                    for _, _, origem, desfecho in revisao["caixas"]))


def medir_auditoria(registros):
    auditadas = [r for r in registros if grupo(r) == "auditoria"]
    revistas = [r for r in auditadas if r["revisao"]]
    corretas = sum(correta_por_inteiro(r["revisao"]) for r in revistas)
    caixas = Counter()
    for r in revistas:
        rev = r["revisao"]
        if rev["acao"] != "salvar":
            continue
        caixas.update(d for _, _, origem, d in rev["caixas"] if origem == "voto")
        caixas["removida"] += rev["removidas"]
        caixas["objeto_perdido"] += sum(1 for _, _, origem, _ in rev["caixas"] if origem != "voto")
    intervalo = wilson(corretas, len(revistas))
    return {
        "auditadas": len(auditadas),
        "revistas": len(revistas),
        "descartadas": sum(r["revisao"]["acao"] == "descartar" for r in revistas),
        "corretas": corretas,
        "fracao_correta": None if intervalo is None else
        {"p": intervalo[0], "ic95": [intervalo[1], intervalo[2]]},
        "caixas_consenso": {k: caixas[k] for k in ("aceita", "classe_corrigida", "removida")},
        "objetos_perdidos": caixas["objeto_perdido"],
    }


def medir_correcoes(registros, cega=False):
    por_grupo = {}
    for r in registros:
        g, rev = grupo(r, cega), r["revisao"]
        if g is None or rev is None:
            continue
        m = por_grupo.setdefault(g, {"salvas": 0, "descartadas": 0, "caixas": 0,
                                     "desfechos": Counter(), "adicionadas": Counter(),
                                     "removidas": 0})
        if rev["acao"] == "descartar":
            m["descartadas"] += 1
            continue
        m["salvas"] += 1
        m["caixas"] += len(rev["caixas"])
        m["removidas"] += rev["removidas"]
        for _, _, origem, desfecho in rev["caixas"]:
            m["desfechos"][desfecho] += 1
            if desfecho == "adicionada":
                m["adicionadas"][origem] += 1
    return {g: {**m, "desfechos": {d: m["desfechos"][d] for d in DESFECHOS},
                "adicionadas": dict(sorted(m["adicionadas"].items()))}
            for g, m in sorted(por_grupo.items(), key=lambda t: GRUPOS.index(t[0]))}


def medir_tempo(registros, cega=False):
    por_grupo = {}
    for r in registros:
        g, rev = grupo(r, cega), r["revisao"]
        if g is None or rev is None:
            continue
        for chave in (g, "todas"):
            m = por_grupo.setdefault(chave, {"tempos": [], "tempo_salvas": 0.0, "caixas": 0})
            m["tempos"].append(rev["tempo_ativo_s"])
            if rev["acao"] == "salvar":
                m["tempo_salvas"] += rev["tempo_ativo_s"]
                m["caixas"] += len(rev["caixas"])
    ordem = (*GRUPOS, "todas")
    return {g: {"revisoes": len(m["tempos"]),
                "mediana_s": statistics.median(m["tempos"]),
                "media_s": statistics.fmean(m["tempos"]),
                "por_objeto_s": m["tempo_salvas"] / m["caixas"] if m["caixas"] else None}
            for g, m in sorted(por_grupo.items(), key=lambda t: ordem.index(t[0]))}


def casar(previstas, verdade, limiar_iou, mesma_classe):
    """
    Casamento guloso pelo IoU, da maior sobreposição para a menor: quantos
    pares com IoU >= limiar_iou (e a mesma classe, se mesma_classe).
    previstas e verdade: [(classe, caixa)].
    """
    pares = sorted(((iou(p[1], v[1]), i, j) for i, p in enumerate(previstas)
                    for j, v in enumerate(verdade)
                    if not mesma_classe or p[0] == v[0]), reverse=True)
    usadas_p, usadas_v = set(), set()
    for valor, i, j in pares:
        if valor < limiar_iou:
            break
        if i not in usadas_p and j not in usadas_v:
            usadas_p.add(i)
            usadas_v.add(j)
    return len(usadas_p)


def medir_anotadores(registros, limiar_iou=IOU_PADRAO):
    """
    {conjunto: {anotador: {imagens, previstas, objetos, localizacao: {acertos,
    precisao, recall}, classe: {...}}}}, sobre as imagens salvas na revisão.
    """
    contas = {}
    for r in registros:
        rev = r["revisao"]
        if r["voto"] is None or rev is None or rev["acao"] != "salvar":
            continue
        verdade = [(classe, caixa) for classe, caixa, _, _ in rev["caixas"]]
        for proposta in r["voto"]["propostas"]:
            previstas = [(classe, caixa) for classe, conf, caixa in proposta["caixas"]
                         if conf >= proposta["limiar"]]
            m = contas.setdefault(r["conjunto"], {}).setdefault(
                proposta["anotador"], {"imagens": 0, "previstas": 0, "objetos": 0,
                                       "localizacao": 0, "classe": 0})
            m["imagens"] += 1
            m["previstas"] += len(previstas)
            m["objetos"] += len(verdade)
            m["localizacao"] += casar(previstas, verdade, limiar_iou, False)
            m["classe"] += casar(previstas, verdade, limiar_iou, True)

    def taxas(acertos, m):
        return {"acertos": acertos,
                "precisao": acertos / m["previstas"] if m["previstas"] else None,
                "recall": acertos / m["objetos"] if m["objetos"] else None}
    return {conjunto: {a: {"imagens": m["imagens"], "previstas": m["previstas"],
                           "objetos": m["objetos"],
                           "localizacao": taxas(m["localizacao"], m),
                           "classe": taxas(m["classe"], m)}
                       for a, m in sorted(por_anotador.items())}
            for conjunto, por_anotador in sorted(contas.items())}


MINIMO_AUDITORIA = 20   # abaixo disso, o intervalo da auditoria é largo demais para concluir


def avisos(registros, m, cega=False):
    """
    Avisos sobre os dados medidos, em texto: estados que o banco não deveria
    ter e limites da leitura. cega: sem os que falam da auditoria.
    """
    lista = []

    def contar(condicao):
        return [r["nome"] for r in registros if condicao(r)]

    def exemplos(nomes):
        return ", ".join(nomes[:3]) + (f" e mais {len(nomes) - 3}" if len(nomes) > 3 else "")

    for nomes, texto in (
            (contar(lambda r: r["status"] != "pendente" and r["revisao"] is None),
             "revisada ou descartada sem revisão registrada"),
            (contar(lambda r: r["status"] == "pendente" and r["revisao"] is not None),
             "pendente com revisão registrada"),
            (contar(lambda r: r["revisao"] is not None and r["voto"] is None),
             "revisão sem voto (toda revisão parte de um voto)"),
            (contar(lambda r: r["voto"] is not None
                    and (r["conjunto"] == "teste") != (r["voto"]["resultado"] == "uniao")),
             "conjunto e resultado do voto não batem (teste é sempre união)"),
            (contar(lambda r: r["revisao"] is not None and r["revisao"]["acao"] == "descartar"
                    and r["status"] != "descartada"),
             "revisão vigente descarta, mas o status não é descartada"),
            (contar(lambda r: r["revisao"] is not None and r["revisao"]["acao"] == "salvar"
                    and r["status"] != "revisada"),
             "revisão vigente salva, mas o status não é revisada")):
        if nomes:
            lista.append(f"Inconsistência: {len(nomes)} imagem(ns) com {texto}: {exemplos(nomes)}")

    sem_tempo = contar(lambda r: r["revisao"] is not None and not r["revisao"]["tempo_ativo_s"])
    if sem_tempo:
        lista.append(f"{len(sem_tempo)} revisão(ões) com tempo ativo zero (gravadas fora da "
                     f"página?), que puxam o tempo para baixo: {exemplos(sem_tempo)}")
    if not any(r["conjunto"] == "teste" and r["revisao"] is not None
               and r["revisao"]["acao"] == "salvar" for r in registros):
        lista.append("Nenhuma imagem de teste revisada: a precisão e o recall dos anotadores são "
                     "só do treino, enviesados pela revisão que parte do voto; e o teste.txt "
                     "vazio impede o treino do YOLO")
    if not cega:
        a = m["auditoria"]
        if a["auditadas"] and a["revistas"] < MINIMO_AUDITORIA:
            lista.append(f"Auditoria: {a['revistas']} de {a['auditadas']} auditada(s) revista(s); "
                         f"com menos de {MINIMO_AUDITORIA}, o intervalo de confiança é largo "
                         "demais para concluir sobre o erro das aprovadas")
    return lista


def medir(registros, limiar_iou=IOU_PADRAO, cega=False):
    """
    Todas as medidas. cega (aba de métricas do revisar.py): sem o bloco da
    auditoria, com as auditadas no grupo 'falhou' e, no voto, só o que a
    página mostra: aprovadas fora da auditoria e "a revisar" (reprovadas e
    auditadas), sem a taxa nem os motivos.
    """
    m = {"voto": medir_voto(registros), "auditoria": medir_auditoria(registros),
         "correcoes": medir_correcoes(registros, cega), "tempo": medir_tempo(registros, cega),
         "anotadores": medir_anotadores(registros, limiar_iou), "iou": limiar_iou,
         "cega": cega}
    m["avisos"] = avisos(registros, m, cega)
    if cega:
        # O bloco do voto como a página o mostra: as auditadas estão entre as
        # "a revisar", e o motivo não vem (a soma dos motivos contra as "a
        # revisar" daria o número de auditadas)
        v = m["voto"]
        m["voto"] = {"treino_votadas": v["treino_votadas"],
                     "aprovadas": v["aprovadas"] - v["auditadas"],
                     "a_revisar": sum(v["falhou"].values()) + v["auditadas"],
                     "teste_unidas": v["teste_unidas"], "sem_voto": v["sem_voto"]}
        del m["auditoria"]
    return m


def pct(x):
    return "—" if x is None else f"{x:.0%}"


def segundos(x):
    return "—" if x is None else f"{x:.1f} s"


def imprimir(m):
    v = m["voto"]
    print("== Voto ==")
    print(f"treino: {v['treino_votadas']} votada(s), {v['aprovadas']} aprovada(s) "
          f"({pct(v['taxa_aprovacao'])}; {v['auditadas']} na auditoria cega)")
    if v["falhou"]:
        print("  reprovadas: " + ", ".join(f"{k} {q}" for k, q in v["falhou"].items()))
    print(f"teste: {v['teste_unidas']} unida(s); pendentes sem voto: {v['sem_voto']}")

    a = m["auditoria"]
    print("\n== Auditoria (aprovadas sorteadas, já revistas) ==")
    if not a["revistas"]:
        print(f"{a['auditadas']} auditada(s), nenhuma revista ainda")
    else:
        f = a["fracao_correta"]
        print(f"{a['revistas']} de {a['auditadas']} revista(s): {a['corretas']} correta(s) por "
              f"inteiro, {pct(f['p'])} (IC 95%: {pct(f['ic95'][0])} a {pct(f['ic95'][1])}); "
              f"{a['descartadas']} descartada(s)")
        c = a["caixas_consenso"]
        print(f"  caixas de consenso: {c['aceita']} aceita(s), {c['classe_corrigida']} com a "
              f"classe corrigida, {c['removida']} removida(s); {a['objetos_perdidos']} objeto(s) "
              "que o voto não tinha")

    print("\n== Correções (revisão vigente, por grupo) ==")
    if not m["correcoes"]:
        print("nenhuma revisão")
    for g, c in m["correcoes"].items():
        d = c["desfechos"]
        print(f"{g}: {c['salvas']} salva(s), {c['descartadas']} descartada(s); {c['caixas']} "
              f"caixa(s): {d['aceita']} aceita(s), {d['classe_corrigida']} classe corrigida, "
              f"{d['classe_atribuida']} classe atribuída, {d['adicionada']} adicionada(s)"
              + (f" ({', '.join(f'{o} {q}' for o, q in c['adicionadas'].items())})"
                 if c["adicionadas"] else "")
              + f"; {c['removidas']} removida(s) do voto")

    print("\n== Tempo ativo de revisão ==")
    if not m["tempo"]:
        print("nenhuma revisão")
    for g, t in m["tempo"].items():
        print(f"{g}: {t['revisoes']} revisão(ões), por imagem {segundos(t['mediana_s'])} "
              f"(mediana) e {segundos(t['media_s'])} (média), por objeto "
              f"{segundos(t['por_objeto_s'])}")

    if m["avisos"]:
        print("\n== Avisos ==")
        for aviso in m["avisos"]:
            print(f"- {aviso}")

    print(f"\n== Anotadores frente à revisão (IoU >= {m['iou']}) ==")
    if not m["anotadores"]:
        print("nenhuma imagem salva na revisão")
    for conjunto, por_anotador in m["anotadores"].items():
        print(f"{conjunto}:")
        for anotador, x in por_anotador.items():
            loc, cls = x["localizacao"], x["classe"]
            print(f"  {anotador}: {x['imagens']} imagem(ns), {x['previstas']} caixa(s) contra "
                  f"{x['objetos']} objeto(s); localização P {pct(loc['precisao'])} "
                  f"R {pct(loc['recall'])}; com a classe P {pct(cls['precisao'])} "
                  f"R {pct(cls['recall'])}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Métricas da anotação, lidas do banco da saída.")
    parser.add_argument("saida", type=Path, help="saída anotada")
    parser.add_argument("--iou", type=float, default=IOU_PADRAO,
                        help=f"IoU mínimo para casar caixa de anotador e da revisão "
                             f"(padrão: {IOU_PADRAO})")
    parser.add_argument("--json", type=Path, help="grava também todas as medidas neste arquivo")
    args = parser.parse_args(argv)
    if not 0 < args.iou <= 1:
        parser.error("--iou: entre 0 e 1")
    if not formato.existe(args.saida):
        raise ValueError(f"{args.saida} não tem banco: importe, anote e vote antes")
    m = medir(formato.ler_registros(args.saida), args.iou)
    imprimir(m)
    if args.json:
        args.json.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nMedidas em {args.json}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
