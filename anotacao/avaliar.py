"""
Avalia as propostas gravadas de um anotador contra as fotos rotuladas pela
equipe (OBJETIVO.md, seção 6). Não roda modelo: lê o que o anotar.py gravou
numa saída e casa cada imagem com o rótulo dela pelo nome original (sem o
prefixo <lote>_ do importar.py).

    python anotacao/importar.py legado/database/tcc-0CF/YOLO_dataset/validation/images \
        -o validacao --lote tcc-0CF --link              # e os outros cenários
    python anotacao/anotar.py -o validacao --anotador grounding-dino
    python anotacao/avaliar.py validacao --anotador grounding-dino [--json resultado.json]

Medidas, com IoU >= 0,5 como acerto de posição:
1. Cobertura sem classe, por limiar de leitura: objetos com alguma caixa,
   imagens completas, caixas por imagem e caixas que sobram (a remover).
2. Classe e material das caixas que cobrem um objeto, no limiar de leitura
   gravado na proposta, com a matriz de confusão.
3. Acerto de classe por faixa de confiança (para escolher confianca_classe).
4. Precisão e recall com classe, por limiar.
5. Caixa por clique: nos objetos sem caixa visível, se a 1ª (ou uma das 3
   primeiras) candidata no centro do objeto tem IoU >= 0,75.
6. Com --comparar OUTRO: erro conjunto de classe dos dois anotadores, nos
   objetos que ambos cobrem, contra o esperado com erros independentes dada a
   classe verdadeira (dependência entre anotadores, para o voto).
7. Com --voto A B C: só o voto 3oo3 estrito (seção 3) entre os anotadores,
   com a taxa de aprovação e a fração das aprovadas corretas por inteiro.

Os rótulos da equipe usam os nomes TACO; só entram as classes de classes.yaml,
casadas pelo nome. Polígonos viram a caixa que os contém. Antes, valem as
correções de correcoes_rotulos.yaml (a equipe rotulou todo vidro como Glass
bottle), sem editar legado/.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import median

import yaml

import anotar
import saida as formato

DIR_REPO = anotar.DIR_SCRIPT.parent
DATASETS_PADRAO = sorted((DIR_REPO / "legado" / "database").glob("tcc-*/YOLO_dataset/validation"))
CORRECOES_PADRAO = anotar.DIR_SCRIPT / "correcoes_rotulos.yaml"
LIMIARES_PADRAO = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
FAIXAS = [0.05, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 1.01]
IOU_ACERTO = 0.5
IOU_CLIQUE = 0.75   # candidata "certa" no clique
IOU_PRESENTE = 0.9  # a página esconde candidatas quase iguais a uma caixa já presente
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def nomes_do_dataset(pasta):
    """Nomes das classes do data.yaml na pasta do split ou na de cima."""
    for data_yaml in (pasta / "data.yaml", pasta.parent / "data.yaml"):
        if data_yaml.exists():
            with open(data_yaml, encoding="utf-8") as f:
                nomes = (yaml.safe_load(f) or {}).get("names") or []
            return list(nomes.values()) if isinstance(nomes, dict) else list(nomes)
    raise ValueError(f"data.yaml não encontrado em {pasta} nem em {pasta.parent}")


def carregar_correcoes(caminho):
    """
    correcoes_rotulos.yaml -> {.txt resolvido: {linha (1..): (de, para)}}. As
    chaves do arquivo são relativas à raiz do repositório.
    """
    with open(caminho, encoding="utf-8") as f:
        dados = (yaml.safe_load(f) or {}).get("correcoes") or {}
    correcoes = {}
    for arquivo, itens in dados.items():
        por_linha = {}
        for item in itens:
            try:
                linha, de, para = int(item["linha"]), item["de"], item["para"]
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"{caminho}: correção inválida em {arquivo}: {item!r}") from None
            if linha in por_linha:
                raise ValueError(f"{caminho}: linha {linha} de {arquivo} corrigida duas vezes")
            por_linha[linha] = (de, para)
        correcoes[(DIR_REPO / arquivo).resolve()] = por_linha
    return correcoes


def ler_verdade(caminho, nomes_dataset, nomes, correcoes=None):
    """
    Rótulos de um .txt YOLO (caixa 'id cx cy w h' ou polígono 'id x1 y1 x2 y2 ...')
    -> ([(classe em nomes, (x1, y1, x2, y2))], Counter dos nomes fora de nomes).
    correcoes: {linha (1..): (classe no .txt, classe correta)} deste arquivo; a
    classe no .txt é conferida.
    """
    correcoes = dict(correcoes or {})
    verdade, fora = [], Counter()
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
        partes = linha.split()
        if not partes:
            continue
        nome = nomes_dataset[int(partes[0])]
        if numero in correcoes:
            de, para = correcoes.pop(numero)
            if nome != de:
                raise ValueError(f"{caminho}: linha {numero} é {nome}, a correção esperava {de}")
            nome = para
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
    if correcoes:
        raise ValueError(f"{caminho}: correções para linhas que não existem: "
                         f"{', '.join(map(str, sorted(correcoes)))}")
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


def casar_sem_classe(deteccoes, verdade, limiar_iou=IOU_ACERTO):
    """
    Casamento guloso pelo IoU, sem olhar a classe: cada detecção e cada caixa
    verdadeira entram em um par só. Devolve [(índice da detecção, índice da
    verdadeira)] com IoU >= limiar_iou.
    """
    pares = sorted(((anotar.iou(d[2], v[1]), di, vi) for di, d in enumerate(deteccoes)
                    for vi, v in enumerate(verdade)), reverse=True)
    usadas_d, usadas_v, casados = set(), set(), []
    for iou, di, vi in pares:
        if iou < limiar_iou:
            break
        if di not in usadas_d and vi not in usadas_v:
            usadas_d.add(di)
            usadas_v.add(vi)
            casados.append((di, vi))
    return casados


def indexar_verdade(pastas):
    """
    {nome original da imagem: (.txt, nomes do dataset)} das pastas de rótulos.
    Um nome em duas pastas é recusado: não daria para saber qual rótulo vale.
    """
    indice = {}
    for imagem, rotulo, nomes_dataset in listar_imagens(pastas):
        if imagem.name in indice:
            raise ValueError(f"imagem {imagem.name} em mais de uma pasta de rótulos: "
                             f"{indice[imagem.name][0]} e {rotulo}")
        indice[imagem.name] = (rotulo, nomes_dataset)
    return indice


def nome_original(nome, lote):
    """O nome antes do importar.py, que prefixa <lote>_."""
    prefixo = f"{lote}_" if lote else ""
    return nome[len(prefixo):] if prefixo and nome.startswith(prefixo) else nome


def carregar_pares(saida, anotador, indice_verdade, nomes, correcoes):
    """
    [(nome, proposta, deteccoes, verdade)] das imagens da saída com proposta do
    anotador e rótulo da equipe. deteccoes: [(classe em nomes ou None se fora,
    confianca, caixa)], da mais confiante para a menos. Devolve também os nomes
    sem rótulo e o Counter das classes da equipe fora de nomes.
    """
    _, linhas = formato.ler_estado(saida)
    pares, sem_rotulo, fora = [], [], Counter()
    for nome, linha in linhas.items():
        caminho = formato.caminho_proposta(saida, anotador, nome)
        if not caminho.exists():
            continue
        original = nome_original(nome, linha.get("lote"))
        if original not in indice_verdade:
            sem_rotulo.append(nome)
            continue
        rotulo, nomes_dataset = indice_verdade[original]
        verdade, fora_imagem = ler_verdade(rotulo, nomes_dataset, nomes,
                                           correcoes.get(rotulo.resolve()))
        fora += fora_imagem
        proposta = formato.ler_proposta(caminho)
        deteccoes = sorted(((nomes.index(c) if c in nomes else None, conf, caixa)
                            for c, conf, caixa in formato.caixas_normalizadas(proposta)),
                           key=lambda d: d[1], reverse=True)
        pares.append((nome, proposta, deteccoes, verdade))
    return pares, sem_rotulo, fora


def medir_cobertura(pares, limiares, materiais):
    """
    Por limiar: objetos cobertos (alguma caixa com IoU >= 0,5, qualquer classe),
    imagens completas, caixas, sobra, e classe e material certos entre as
    caixas que cobrem um objeto.
    """
    resultado = {}
    for limiar in limiares:
        c = Counter()
        for _, _, deteccoes, verdade in pares:
            dets = [d for d in deteccoes if d[1] >= limiar]
            casados = casar_sem_classe(dets, verdade)
            c["objetos"] += len(verdade)
            c["cobertos"] += len(casados)
            c["completas"] += len(casados) == len(verdade)
            c["caixas"] += len(dets)
            c["sobra"] += len(dets) - len(casados)
            for di, vi in casados:
                prevista, real = dets[di][0], verdade[vi][0]
                c["classe_certa"] += prevista == real
                c["material_certo"] += (prevista is not None
                                        and materiais[prevista] == materiais[real])
        n = len(pares)
        resultado[limiar] = {
            "cobertura": c["cobertos"] / c["objetos"] if c["objetos"] else 0.0,
            "completas": c["completas"] / n if n else 0.0,
            "caixas_por_imagem": c["caixas"] / n if n else 0.0,
            "sobra_por_imagem": c["sobra"] / n if n else 0.0,
            "classe_certa": c["classe_certa"] / c["cobertos"] if c["cobertos"] else 0.0,
            "material_certo": c["material_certo"] / c["cobertos"] if c["cobertos"] else 0.0,
        }
    return resultado


def medir_deteccao(pares, limiares):
    """Por limiar: acertos (IoU >= 0,5 e mesma classe), falsos positivos e negativos."""
    resultado = {}
    for limiar in limiares:
        tp = fp = fn = 0
        for _, _, deteccoes, verdade in pares:
            a, b, c = casar([d for d in deteccoes if d[1] >= limiar], verdade)
            tp, fp, fn = tp + a, fp + b, fn + c
        resultado[limiar] = {"acertos": tp, "falsos_positivos": fp, "falsos_negativos": fn,
                             "precisao": tp / (tp + fp) if tp + fp else 0.0,
                             "recall": tp / (tp + fn) if tp + fn else 0.0}
    return resultado


def medir_confusao(pares):
    """
    Counter de (classe verdadeira, prevista), no limiar de leitura gravado em
    cada proposta. prevista: o índice da classe; "outra" se a caixa que cobre
    o objeto tem classe fora de classes.yaml; None se nenhuma caixa visível o
    cobre.
    """
    matriz = Counter()
    for _, proposta, deteccoes, verdade in pares:
        confianca, _ = formato.limiares(proposta)
        dets = [d for d in deteccoes if d[1] >= confianca]
        cobertas = {vi: "outra" if dets[di][0] is None else dets[di][0]
                    for di, vi in casar_sem_classe(dets, verdade)}
        for vi, (real, _) in enumerate(verdade):
            matriz[(real, cobertas.get(vi))] += 1
    return matriz


def medir_faixas(pares, faixas=FAIXAS):
    """
    Por faixa de confiança [a, b): caixas, as que cobrem um objeto e, destas, as
    de classe certa. Casamento sobre todas as caixas gravadas.
    """
    c = {(a, b): Counter() for a, b in zip(faixas, faixas[1:])}
    for _, _, deteccoes, verdade in pares:
        casados = dict(casar_sem_classe(deteccoes, verdade))
        for di, (prevista, conf, _) in enumerate(deteccoes):
            faixa = next((f for f in c if f[0] <= conf < f[1]), None)
            if faixa is None:
                continue
            c[faixa]["caixas"] += 1
            if di in casados:
                c[faixa]["cobrem"] += 1
                c[faixa]["classe_certa"] += prevista == verdade[casados[di]][0]
    return {f: dict(v) for f, v in c.items()}


def medir_clique(pares):
    """
    Caixa por clique, como a página a oferece: nos objetos que nenhuma caixa
    visível cobre, as candidatas (abaixo do limiar de leitura) que contêm o
    centro do objeto, menos as quase iguais a uma visível, da mais confiante
    para a menos. Conta se a 1ª e se uma das 3 primeiras têm IoU >= 0,75.
    """
    c = Counter()
    for _, proposta, deteccoes, verdade in pares:
        confianca, _ = formato.limiares(proposta)
        visiveis = [d for d in deteccoes if d[1] >= confianca]
        candidatas = [d for d in deteccoes if d[1] < confianca]
        c["candidatas"] += len(candidatas)
        cobertas = {vi for _, vi in casar_sem_classe(visiveis, verdade)}
        for vi, (_, caixa) in enumerate(verdade):
            if vi in cobertas:
                continue
            c["sem_caixa"] += 1
            cx, cy = (caixa[0] + caixa[2]) / 2, (caixa[1] + caixa[3]) / 2
            no_ponto = [d for d in candidatas
                        if d[2][0] <= cx <= d[2][2] and d[2][1] <= cy <= d[2][3]
                        and not any(anotar.iou(v[2], d[2]) >= IOU_PRESENTE for v in visiveis)]
            ious = [anotar.iou(d[2], caixa) for d in no_ponto]
            c["primeira"] += any(i >= IOU_CLIQUE for i in ious[:1])
            c["tres_primeiras"] += any(i >= IOU_CLIQUE for i in ious[:3])
    n = len(pares)
    return {"sem_caixa": c["sem_caixa"], "primeira": c["primeira"],
            "tres_primeiras": c["tres_primeiras"],
            "candidatas_por_imagem": c["candidatas"] / n if n else 0.0}


def classe_por_objeto(deteccoes, verdade, limiar):
    """
    {índice da caixa verdadeira: classe prevista} pelas caixas a partir do
    limiar, com o casamento sem classe; "outra" se a classe está fora de
    classes.yaml. Objetos sem caixa ficam de fora.
    """
    dets = [d for d in deteccoes if d[1] >= limiar]
    return {vi: "outra" if dets[di][0] is None else dets[di][0]
            for di, vi in casar_sem_classe(dets, verdade)}


def medir_erro_conjunto(pares_a, pares_b, materiais, limiar_a=None, limiar_b=None):
    """
    Dependência entre os erros de classe de dois anotadores (OBJETIVO.md,
    seção 5), sobre os objetos que os dois cobrem. limiar None: o de leitura
    gravado em cada proposta. O voto aprova o erro em que os dois concordam na
    mesma classe errada; o esperado é o que dariam erros independentes dada a
    classe verdadeira (o mesmo acerto de cada um por classe, sorteado à parte),
    para que uma classe difícil para todos não conte como dependência.
    """
    por_nome_b = {nome: (proposta, deteccoes) for nome, proposta, deteccoes, _ in pares_b}
    objetos = []   # (real, prevista por a, prevista por b)
    imagens = 0
    for nome, proposta_a, deteccoes_a, verdade in pares_a:
        if nome not in por_nome_b:
            continue
        proposta_b, deteccoes_b = por_nome_b[nome]
        imagens += 1
        la = formato.limiares(proposta_a)[0] if limiar_a is None else limiar_a
        lb = formato.limiares(proposta_b)[0] if limiar_b is None else limiar_b
        pa = classe_por_objeto(deteccoes_a, verdade, la)
        pb = classe_por_objeto(deteccoes_b, verdade, lb)
        objetos += [(verdade[vi][0], pa[vi], pb[vi]) for vi in pa.keys() & pb.keys()]

    def material(c):
        return None if c == "outra" else materiais[c]

    n = len(objetos)
    c = Counter()
    por_real = {}
    erros_iguais = Counter()
    for real, a, b in objetos:
        ea, eb = a != real, b != real
        c["erro_a"] += ea
        c["erro_b"] += eb
        c["ambos_erram"] += ea and eb
        c["concordam"] += a == b
        c["concordam_errado"] += a == b != real
        c["material_concordam_errado"] += (material(a) == material(b) != materiais[real])
        if a == b != real:
            erros_iguais[(real, a)] += 1
        r = por_real.setdefault(real, {"n": 0, "a": Counter(), "b": Counter(),
                                       "ea": 0, "eb": 0})
        r["n"] += 1
        r["a"][a] += 1
        r["b"][b] += 1
        r["ea"] += ea
        r["eb"] += eb
    # Esperado com erros independentes dada a classe verdadeira
    esperado_ambos = sum(r["ea"] * r["eb"] / r["n"] for r in por_real.values())
    esperado_iguais = sum(r["a"][k] * r["b"][k] / r["n"] for real, r in por_real.items()
                          for k in r["a"] if k != real)
    # Correlação (phi) entre os indicadores de erro
    n11 = c["ambos_erram"]
    n10, n01 = c["erro_a"] - n11, c["erro_b"] - n11
    n00 = n - n11 - n10 - n01
    denominador = (c["erro_a"] * (n - c["erro_a"]) * c["erro_b"] * (n - c["erro_b"])) ** 0.5
    return {
        "imagens": imagens, "objetos": n, **c,
        "esperado_ambos_erram": esperado_ambos,
        "esperado_concordam_errado": esperado_iguais,
        "phi": (n11 * n00 - n10 * n01) / denominador if denominador else 0.0,
        "_erros_iguais": erros_iguais,
    }


def imprimir_erro_conjunto(r, a, b, classes):
    nomes = [c["nome"] for c in classes]
    n = r["objetos"]
    print(f"\nErro conjunto de {a} e {b}: {n} objeto(s) cobertos pelos dois, "
          f"em {r['imagens']} imagem(ns)")
    if not n:
        return
    print(f"  {a} erra a classe: {r['erro_a']} ({r['erro_a'] / n:.0%}); "
          f"{b}: {r['erro_b']} ({r['erro_b'] / n:.0%})")
    print(f"  os dois erram: {r['ambos_erram']} (esperado se independentes dada a classe: "
          f"{r['esperado_ambos_erram']:.1f}); phi dos erros: {r['phi']:.2f}")
    print(f"  concordam na classe: {r['concordam']} ({r['concordam'] / n:.0%}); "
          f"desses, errados: {r['concordam_errado']} "
          f"({r['concordam_errado'] / r['concordam']:.0%} das concordâncias)"
          if r["concordam"] else "  nunca concordam na classe")
    print(f"  mesma classe errada (o voto aprovaria): {r['concordam_errado']} "
          f"(esperado se independentes: {r['esperado_concordam_errado']:.1f}); "
          f"mesmo material errado: {r['material_concordam_errado']}")
    for (real, prevista), q in r["_erros_iguais"].most_common():
        print(f"    {nomes[real]} -> {prevista if prevista == 'outra' else nomes[prevista]}: {q}")


def casar_mesma_classe(a, b, limiar_iou=IOU_ACERTO):
    """
    Casamento guloso pelo IoU entre as detecções de dois anotadores, só entre
    caixas da mesma classe: {índice em a: índice em b} com IoU >= limiar_iou.
    """
    pares = sorted(((anotar.iou(da[2], db[2]), i, j) for i, da in enumerate(a)
                    for j, db in enumerate(b) if da[0] == db[0]), reverse=True)
    usadas_a, usadas_b, casados = set(), set(), {}
    for iou, i, j in pares:
        if iou < limiar_iou:
            break
        if i not in usadas_a and j not in usadas_b:
            usadas_a.add(i)
            usadas_b.add(j)
            casados[i] = j
    return casados


def consenso_por_caixa(listas, limiar_iou=IOU_ACERTO):
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
        if any(anotar.iou(x, y) < limiar_iou for k, x in enumerate(caixas) for y in caixas[k + 1:]):
            continue
        consenso.append((classe, min(g[0] for g in grupo),
                         tuple(median(c[k] for c in caixas) for k in range(4))))
    return consenso


def votar(listas, limiar_iou=IOU_ACERTO):
    """
    Voto NooN estrito (OBJETIVO.md, seção 3) sobre as detecções de N
    anotadores numa imagem, cada lista já no limiar de leitura do seu
    anotador. Passa se todos propõem o mesmo número de caixas e cada caixa do
    primeiro casa (mesma classe, IoU >= limiar_iou) com uma de cada um dos
    outros, e essas também casam entre si. Imagem sem caixa não passa.
    Devolve (motivo, consenso): motivo None se passou, senão "vazia",
    "quantidade" ou "caixas"; consenso, [(classe, menor confiança, mediana
    de cada coordenada)] quando passa.
    """
    if not any(listas):
        return "vazia", []
    if len({len(l) for l in listas}) > 1:
        return "quantidade", []
    consenso = consenso_por_caixa(listas, limiar_iou)
    if len(consenso) != len(listas[0]):
        return "caixas", []
    return None, consenso


def medir_voto(pares_por_anotador, limiares, materiais, limiar_iou=IOU_ACERTO):
    """
    O voto sobre as imagens com proposta de todos os anotadores e rótulo da
    equipe. limiares: um por anotador (None: o gravado na proposta). Mede a
    taxa de aprovação, os motivos de reprovação e, nas aprovadas, quantas
    estão corretas por inteiro (cada objeto com uma caixa de consenso de IoU
    >= 0,5 e mesma classe, sem caixa a mais), e o mesmo só com o material.
    """
    por_nome = [{nome: (proposta, dets) for nome, proposta, dets, _ in pares}
                for pares in pares_por_anotador]
    c = Counter()
    erros = Counter()   # (verdadeira, prevista) nas caixas aprovadas erradas
    for nome, _, _, verdade in pares_por_anotador[0]:
        if not all(nome in p for p in por_nome):
            continue
        listas = []
        for p, limiar in zip(por_nome, limiares):
            proposta, dets = p[nome]
            l = formato.limiares(proposta)[0] if limiar is None else limiar
            listas.append([d for d in dets if d[1] >= l])
        c["imagens"] += 1
        c["objetos"] += len(verdade)
        # Por caixa: o que o voto aprovaria se aprovasse caixas, não imagens
        por_caixa = consenso_por_caixa(listas, limiar_iou)
        c["caixas_consenso"] += len(por_caixa)
        c["caixas_consenso_certas"] += casar(por_caixa, verdade, limiar_iou)[0]
        c["objetos_com_consenso"] += len(casar_sem_classe(por_caixa, verdade, limiar_iou))
        motivo, consenso = votar(listas, limiar_iou)
        if motivo:
            c[f"reprovada_{motivo}"] += 1
            continue
        c["aprovadas"] += 1
        c["objetos_aprovados"] += len(verdade)
        c["caixas_aprovadas"] += len(consenso)
        acertos = casar(consenso, verdade, limiar_iou)[0]
        c["caixas_certas"] += acertos
        c["corretas"] += acertos == len(verdade) == len(consenso)
        por_material = [(None if d[0] is None else materiais[d[0]], d[1], d[2])
                        for d in consenso]
        verdade_material = [(materiais[v[0]], v[1]) for v in verdade]
        c["corretas_material"] += (casar(por_material, verdade_material, limiar_iou)[0]
                                   == len(verdade) == len(consenso))
        for di, vi in casar_sem_classe(consenso, verdade, limiar_iou):
            if consenso[di][0] != verdade[vi][0]:
                erros[(verdade[vi][0], "outra" if consenso[di][0] is None
                       else consenso[di][0])] += 1
    return {**c, "_erros": erros}


def imprimir_voto(r, anotadores, limiares, classes):
    nomes = [c["nome"] for c in classes]
    n, a = r.get("imagens", 0), r.get("aprovadas", 0)
    rotulo = ", ".join(f"{x} ({'gravado' if l is None else l})"
                       for x, l in zip(anotadores, limiares))
    print(f"\nVoto {len(anotadores)}oo{len(anotadores)} de {rotulo}: {n} imagem(ns)")
    if not n:
        return
    print(f"  aprovadas: {a} ({a / n:.0%}); reprovadas por quantidade de caixas: "
          f"{r.get('reprovada_quantidade', 0)}, por caixa ou classe sem par: "
          f"{r.get('reprovada_caixas', 0)}, vazias: {r.get('reprovada_vazia', 0)}")
    if a:
        print(f"  aprovadas corretas por inteiro: {r['corretas']} ({r['corretas'] / a:.0%}); "
              f"só pelo material: {r['corretas_material']} ({r['corretas_material'] / a:.0%})")
        print(f"  caixas aprovadas: {r['caixas_aprovadas']}, certas: {r['caixas_certas']} "
              f"({r['caixas_certas'] / r['caixas_aprovadas']:.0%}); objetos nas aprovadas: "
              f"{r['objetos_aprovados']} de {r['objetos']} ({r['objetos_aprovados'] / r['objetos']:.0%})")
    k = r.get("caixas_consenso", 0)
    if k:
        print(f"  por caixa (sem exigir a imagem inteira): {k} caixas com consenso, certas "
              f"{r['caixas_consenso_certas']} ({r['caixas_consenso_certas'] / k:.0%}); "
              f"objetos com caixa de consenso: {r['objetos_com_consenso']} de {r['objetos']} "
              f"({r['objetos_com_consenso'] / r['objetos']:.0%})")
    for (real, prevista), q in r["_erros"].most_common():
        print(f"    {nomes[real]} -> {prevista if prevista == 'outra' else nomes[prevista]}: {q}")


def pct(v):
    return f"{v:4.0%}"


def imprimir(resultado, classes):
    nomes = [c["nome"] for c in classes]
    print("\nCobertura sem classe (objeto com alguma caixa de IoU >= 0,5, qualquer classe)")
    print("limiar  cobertos  completas  caixas/img  sobra/img  classe certa  material certo")
    for limiar, r in resultado["cobertura"].items():
        print(f"{limiar:5.2f}   {pct(r['cobertura']):>8}  {pct(r['completas']):>9}  "
              f"{r['caixas_por_imagem']:10.1f}  {r['sobra_por_imagem']:9.1f}  "
              f"{pct(r['classe_certa']):>12}  {pct(r['material_certo']):>14}")

    matriz = resultado["_matriz"]
    largura = max(len(n) for n in nomes)
    print("\nClassificação no limiar de leitura da proposta (linhas: verdadeira; colunas: "
          "prevista; s.cx: sem caixa visível; outra: fora de classes.yaml)")
    print(" " * (largura + 4) + "".join(f"{i:>5}" for i in range(len(nomes)))
          + "  outra  s.cx  acerto")
    for v, nome in enumerate(nomes):
        linha = [matriz[(v, p)] for p in range(len(nomes))]
        outra = sum(n for (r, p), n in matriz.items() if r == v and p == "outra")
        cobertas = sum(linha) + outra
        acerto = f"{linha[v] / cobertas:6.0%}" if cobertas else "     -"
        print(f"{v:>2}  {nome:<{largura}}" + "".join(f"{n:>5}" for n in linha)
              + f"{outra:>7}{matriz[(v, None)]:>6}  {acerto}")

    print("\nClasse por faixa de confiança (todas as caixas gravadas)")
    print("faixa        caixas  cobrem objeto  classe certa (das que cobrem)")
    for (a, b), r in resultado["faixas"].items():
        caixas, cobrem, certa = r.get("caixas", 0), r.get("cobrem", 0), r.get("classe_certa", 0)
        print(f"{a:.2f}-{min(b, 1):.2f}   {caixas:6d}   {cobrem:5d} ({pct(cobrem / caixas) if caixas else '   -'})"
              f"   {certa:5d} ({pct(certa / cobrem) if cobrem else '   -'})")

    print("\nDetecção (acerto: IoU >= 0,5 e mesma classe)")
    print("limiar  acertos  FP     FN    precisão  recall")
    for limiar, r in resultado["deteccao"].items():
        print(f"{limiar:5.2f}   {r['acertos']:6d}  {r['falsos_positivos']:5d}  "
              f"{r['falsos_negativos']:5d}  {r['precisao']:8.2f}  {r['recall']:6.2f}")

    c = resultado["clique"]
    if c["sem_caixa"]:
        print(f"\nCaixa por clique: {c['sem_caixa']} objeto(s) sem caixa visível; a 1ª candidata "
              f"no centro acerta (IoU >= {IOU_CLIQUE}) {c['primeira']} ({c['primeira'] / c['sem_caixa']:.0%}), "
              f"uma das 3 primeiras {c['tres_primeiras']} ({c['tres_primeiras'] / c['sem_caixa']:.0%}); "
              f"{c['candidatas_por_imagem']:.1f} candidata(s) por imagem")
    else:
        print("\nCaixa por clique: todo objeto tem caixa visível")


def avaliar(saida, anotador, classes, pastas_verdade, correcoes, limiares):
    """Todas as medidas, num dicionário (o --json grava este dicionário)."""
    nomes = [c["nome"] for c in classes]
    materiais = [c["material"] for c in classes]
    pares, sem_rotulo, fora = carregar_pares(saida, anotador, indexar_verdade(pastas_verdade),
                                             nomes, correcoes)
    if not pares:
        raise ValueError(f"nenhuma imagem de {saida} tem proposta de {anotador} e rótulo da "
                         "equipe")
    # Abaixo do piso de alguma proposta, faltariam caixas: o limiar não é medido
    piso = max(float((proposta.get("parametros") or {}).get("piso", 0.0))
               for _, proposta, _, _ in pares)
    abaixo = [l for l in limiares if l < piso]
    limiares = sorted(l for l in limiares if l >= piso)
    return {
        "anotador": anotador,
        "imagens": len(pares),
        "objetos": sum(len(v) for _, _, _, v in pares),
        "sem_rotulo": sem_rotulo,
        "fora_das_classes": dict(fora),
        "limiares_abaixo_do_piso": abaixo,
        "cobertura": medir_cobertura(pares, limiares, materiais),
        "deteccao": medir_deteccao(pares, limiares),
        "faixas": medir_faixas(pares),
        "clique": medir_clique(pares),
        "_matriz": medir_confusao(pares),
    }


def para_json(resultado, classes):
    """O resultado sem tuplas nas chaves, para gravar em JSON."""
    nomes = [c["nome"] for c in classes]
    nome = lambda i: "sem caixa" if i is None else i if i == "outra" else nomes[i]  # noqa: E731
    dados = {k: v for k, v in resultado.items() if k != "_matriz"}
    dados["cobertura"] = {str(k): v for k, v in resultado["cobertura"].items()}
    dados["deteccao"] = {str(k): v for k, v in resultado["deteccao"].items()}
    dados["faixas"] = {f"{a}-{b}": v for (a, b), v in resultado["faixas"].items()}
    dados["confusao"] = [{"verdadeira": nomes[r], "prevista": nome(p), "n": n}
                         for (r, p), n in sorted(resultado["_matriz"].items(),
                                                 key=lambda x: (x[0][0], str(x[0][1])))]
    return dados


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Avalia as propostas gravadas de um anotador contra os rótulos da equipe.")
    parser.add_argument("saida", type=Path, help="saída anotada (importar.py e anotar.py)")
    parser.add_argument("--anotador", default=anotar.GroundingDino.nome,
                        help=f"anotador avaliado (padrão: {anotar.GroundingDino.nome})")
    parser.add_argument("--verdade", type=Path, nargs="+", default=DATASETS_PADRAO,
                        help="pastas com images/ e labels/ da equipe (padrão: as quatro "
                             "validações de legado/database)")
    parser.add_argument("--classes", type=Path, default=anotar.DIR_SCRIPT / "classes.yaml",
                        help="classes avaliadas (padrão: anotacao/classes.yaml)")
    parser.add_argument("--correcoes", type=Path, default=CORRECOES_PADRAO,
                        help="correções dos rótulos (padrão: anotacao/correcoes_rotulos.yaml)")
    parser.add_argument("--sem-correcoes", action="store_true",
                        help="usa os rótulos da equipe como estão")
    parser.add_argument("--limiares", type=float, nargs="+", default=LIMIARES_PADRAO,
                        help="limiares de leitura da cobertura e da detecção")
    parser.add_argument("--comparar", metavar="ANOTADOR",
                        help="mede também o erro conjunto de classe com este outro anotador "
                             "(dependência entre anotadores, para o voto)")
    parser.add_argument("--limiares-par", type=float, nargs=2, metavar=("A", "B"),
                        help="limiares de leitura do --anotador e do --comparar no erro "
                             "conjunto (padrão: os gravados nas propostas)")
    parser.add_argument("--voto", nargs="+", metavar="ANOTADOR",
                        help="mede só o voto NooN estrito entre estes anotadores (o primeiro "
                             "dá a ordem; --anotador é ignorado)")
    parser.add_argument("--limiares-voto", nargs="+", metavar="L",
                        help="limiar de leitura de cada anotador do --voto, na mesma ordem; "
                             "'g' usa o gravado na proposta (padrão: todos gravados)")
    parser.add_argument("--json", type=Path, help="grava também as medidas neste arquivo")
    args = parser.parse_args(argv)
    if args.limiares_par and not args.comparar:
        parser.error("--limiares-par só vale com --comparar")
    if args.limiares_voto and (not args.voto or len(args.limiares_voto) != len(args.voto)):
        parser.error("--limiares-voto precisa de um limiar por anotador do --voto")
    if args.voto and len(args.voto) < 2:
        parser.error("--voto precisa de ao menos dois anotadores")

    if not args.verdade:
        parser.error("nenhuma pasta de rótulos informada nem encontrada em legado/database")
    classes = anotar.carregar_classes(args.classes)
    correcoes = {} if args.sem_correcoes else carregar_correcoes(args.correcoes)
    if args.voto:
        try:
            limiares = [None if l == "g" else float(l)
                        for l in (args.limiares_voto or ["g"] * len(args.voto))]
        except ValueError:
            parser.error("--limiares-voto: números ou 'g'")
        nomes = [c["nome"] for c in classes]
        indice = indexar_verdade(args.verdade)
        pares = []
        for a in args.voto:
            pares.append(carregar_pares(args.saida, a, indice, nomes, correcoes)[0])
            if not pares[-1]:
                raise ValueError(f"nenhuma imagem de {args.saida} tem proposta de {a} "
                                 "e rótulo da equipe")
        r = medir_voto(pares, limiares, [c["material"] for c in classes])
        imprimir_voto(r, args.voto, limiares, classes)
        if args.json:
            dados = {"voto": args.voto, "limiares": limiares,
                     **{k: v for k, v in r.items() if k != "_erros"},
                     "erros": [{"verdadeira": nomes[v], "prevista": p if p == "outra"
                                else nomes[p], "n": q} for (v, p), q in r["_erros"].most_common()]}
            formato.gravar_atomico(args.json, json.dumps(dados, ensure_ascii=False, indent=1) + "\n")
            print(f"\nMedidas gravadas em {args.json}")
        return
    resultado = avaliar(args.saida, args.anotador, classes, args.verdade, correcoes,
                        args.limiares)

    print(f"{args.anotador}: {resultado['imagens']} imagem(ns) com rótulo, "
          f"{resultado['objetos']} caixa(s) verdadeira(s) nas classes de {args.classes.name}")
    if resultado["sem_rotulo"]:
        print(f"Sem rótulo da equipe (ignoradas): {len(resultado['sem_rotulo'])}")
    if resultado["fora_das_classes"]:
        print("Rótulos fora das classes (ignorados): "
              + ", ".join(f"{n} {q}" for n, q in Counter(resultado["fora_das_classes"]).most_common()))
    if resultado["limiares_abaixo_do_piso"]:
        print("Limiares abaixo do piso das propostas (sem caixas gravadas ali), ignorados: "
              + ", ".join(map(str, resultado["limiares_abaixo_do_piso"])))
    imprimir(resultado, classes)
    dados = para_json(resultado, classes)
    if args.comparar:
        nomes = [c["nome"] for c in classes]
        indice = indexar_verdade(args.verdade)
        pares = [carregar_pares(args.saida, a, indice, nomes, correcoes)[0]
                 for a in (args.anotador, args.comparar)]
        if not pares[1]:
            raise ValueError(f"nenhuma imagem de {args.saida} tem proposta de {args.comparar} "
                             "e rótulo da equipe")
        conjunto = medir_erro_conjunto(*pares, [c["material"] for c in classes],
                                       *(args.limiares_par or (None, None)))
        imprimir_erro_conjunto(conjunto, args.anotador, args.comparar, classes)
        dados["erro_conjunto"] = {
            "com": args.comparar, "limiares": args.limiares_par,
            **{k: v for k, v in conjunto.items() if k != "_erros_iguais"},
            "erros_iguais": [{"verdadeira": nomes[r],
                              "prevista": p if p == "outra" else nomes[p], "n": q}
                             for (r, p), q in conjunto["_erros_iguais"].most_common()]}
    if args.json:
        formato.gravar_atomico(args.json, json.dumps(dados, ensure_ascii=False, indent=1) + "\n")
        print(f"\nMedidas gravadas em {args.json}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
