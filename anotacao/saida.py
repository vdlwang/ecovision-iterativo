"""
Formato do diretório de saída da anotação (PLANO-REVISAO.md, seção 1).

    <saida>/images/<nome>.jpg
    <saida>/propostas/<anotador>/<nome>.json   saída de cada anotador
    <saida>/labels/<nome>.txt                  caixas finais (YOLO), só após a revisão
    <saida>/imagens.csv                        nome, status de cada imagem
    <saida>/revisadas.txt                      gerado de imagens.csv; o data.yaml aponta para ele
    <saida>/data.yaml

O que o anotador propõe fica separado do que o revisor aprova: uma imagem sem
.txt em labels/ não entra no treino, em vez de entrar como fundo.
"""

import csv
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path

STATUS = ("pendente", "revisada", "descartada")
COLUNAS = ["nome", "status"]


def gravar_atomico(caminho, texto):
    """Grava num temporário e troca: um Ctrl+C no meio não deixa o arquivo pela metade."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(dir=caminho.parent, prefix=f".{caminho.name}.")
    try:
        with os.fdopen(descritor, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        os.replace(temporario, caminho)
    except BaseException:
        os.unlink(temporario)
        raise


def hash_classes(classes):
    """Identifica a lista de classes (nomes, prompts, materiais e ordem), não o arquivo."""
    texto = json.dumps(classes, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def linha_yolo(classe, caixa):
    """Caixa (x1, y1, x2, y2) normalizada -> linha 'id cx cy w h' do YOLO."""
    x1, y1, x2, y2 = caixa
    return (f"{classe} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} "
            f"{x2 - x1:.6f} {y2 - y1:.6f}")


# --- imagens.csv ----------------------------------------------------------

def ler_estado(saida):
    """
    imagens.csv -> (colunas, {nome: linha}), na ordem do arquivo. Colunas além
    de nome e status (do sistema completo) são preservadas. Sem o arquivo,
    devolve o estado vazio.
    """
    caminho = Path(saida) / "imagens.csv"
    if not caminho.exists():
        return list(COLUNAS), {}
    with open(caminho, encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        colunas = list(leitor.fieldnames or [])
        faltando = [c for c in COLUNAS if c not in colunas]
        if faltando:
            raise ValueError(f"{caminho}: faltam as colunas {', '.join(faltando)}")
        linhas = {}
        for linha in leitor:
            if linha["nome"] in linhas:
                raise ValueError(f"{caminho}: imagem '{linha['nome']}' repetida")
            linhas[linha["nome"]] = linha
    return colunas, linhas


def gravar_estado(saida, colunas, linhas):
    """Grava imagens.csv e regenera revisadas.txt a partir dele."""
    saida = Path(saida)
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=colunas, lineterminator="\n")
    escritor.writeheader()
    for linha in linhas.values():
        escritor.writerow({c: linha.get(c, "") for c in colunas})
    gravar_atomico(saida / "imagens.csv", buffer.getvalue())

    # "./" faz o Ultralytics resolver o caminho a partir da pasta do .txt
    revisadas = [f"./images/{nome}" for nome, linha in linhas.items()
                 if linha["status"] == "revisada"
                 and (saida / "labels" / f"{Path(nome).stem}.txt").exists()]
    gravar_atomico(saida / "revisadas.txt", "".join(r + "\n" for r in revisadas))


def registrar_imagem(linhas, nome):
    """
    Acrescenta a imagem como pendente; mantém o status de uma já registrada.
    Recusa outro arquivo com o mesmo nome sem extensão (o .json e o .txt colidiriam).
    """
    if nome in linhas:
        return
    for existente in linhas:
        if Path(existente).stem == Path(nome).stem:
            raise ValueError(f"'{nome}' colide com '{existente}', já registrada "
                             "(mesmo nome sem extensão)")
    linhas[nome] = {"nome": nome, "status": "pendente"}


# --- propostas ------------------------------------------------------------

def caminho_proposta(saida, anotador, nome):
    return Path(saida) / "propostas" / anotador / f"{Path(nome).stem}.json"


def montar_proposta(anotador, versao, parametros, classes, nome, tamanho, deteccoes):
    """
    deteccoes: [(id da classe, confianca, (x1, y1, x2, y2) normalizada)].
    A caixa vai em pixels da imagem gravada; a classe, pelo nome.
    """
    largura, altura = tamanho
    caixas = [{
        "classe": classes[classe]["nome"],
        "confianca": round(float(conf), 4),
        "caixa": [round(x1 * largura, 4), round(y1 * altura, 4),
                  round(x2 * largura, 4), round(y2 * altura, 4)],
    } for classe, conf, (x1, y1, x2, y2) in deteccoes]
    return {"anotador": anotador, "versao": versao, "parametros": parametros,
            "classes": hash_classes(classes), "imagem": nome,
            "largura": largura, "altura": altura, "caixas": caixas}


def gravar_proposta(saida, proposta):
    gravar_atomico(caminho_proposta(saida, proposta["anotador"], proposta["imagem"]),
                   json.dumps(proposta, ensure_ascii=False, indent=1) + "\n")


def ler_proposta(caminho):
    try:
        proposta = json.loads(Path(caminho).read_text(encoding="utf-8"))
        for campo in ("anotador", "largura", "altura", "caixas"):
            proposta[campo]
    except (ValueError, KeyError, TypeError) as erro:
        raise ValueError(f"{caminho}: proposta inválida ({erro})") from None
    return proposta


def caixas_normalizadas(proposta):
    """[(nome da classe, confianca, (x1, y1, x2, y2) normalizada)] de uma proposta."""
    largura, altura = proposta["largura"], proposta["altura"]
    return [(c["classe"], c["confianca"],
             (c["caixa"][0] / largura, c["caixa"][1] / altura,
              c["caixa"][2] / largura, c["caixa"][3] / altura))
            for c in proposta["caixas"]]


def anotadores(saida):
    """Nomes dos anotadores com propostas gravadas."""
    pasta = Path(saida) / "propostas"
    return sorted(p.name for p in pasta.iterdir() if p.is_dir()) if pasta.is_dir() else []


def aceitar(saida, anotador, classes, nomes=None):
    """
    Copia as propostas do anotador para labels/ e marca as imagens como
    revisadas: o comportamento antigo, proposta direto como rótulo. Só mexe nas
    pendentes (nomes=None: todas); devolve quantas aceitou.
    """
    ids = {c["nome"]: i for i, c in enumerate(classes)}
    colunas, linhas = ler_estado(saida)
    aceitas = 0
    for nome, linha in linhas.items():
        if linha["status"] != "pendente" or (nomes is not None and nome not in nomes):
            continue
        caminho = caminho_proposta(saida, anotador, nome)
        if not caminho.exists():
            continue
        texto = []
        for classe, _, caixa in caixas_normalizadas(ler_proposta(caminho)):
            if classe not in ids:
                raise ValueError(f"{caminho}: classe '{classe}' fora do classes.yaml")
            texto.append(linha_yolo(ids[classe], caixa) + "\n")
        gravar_atomico(Path(saida) / "labels" / f"{Path(nome).stem}.txt", "".join(texto))
        linha["status"] = "revisada"
        aceitas += 1
    gravar_estado(saida, colunas, linhas)
    return aceitas
