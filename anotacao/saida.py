"""
Formato do diretório de saída da anotação (PLANO-REVISAO.md, seção 1).

    <saida>/images/<nome>.jpg                  gravada pelo importar.py
    <saida>/lotes.yaml                         por lote: conjunto, região de interesse
    <saida>/propostas/<anotador>/<nome>.json   saída de cada anotador
    <saida>/labels/<nome>.txt                  caixas finais (YOLO), só após a revisão
    <saida>/imagens.csv                        nome, status, lote, conjunto de cada imagem
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

import yaml
from PIL import Image

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
STATUS = ("pendente", "revisada", "descartada")

# mkstemp cria o arquivo só para o dono (0600); os gravados aqui recebem o modo
# de um open() comum. A umask é lida uma vez, na importação, porque lê-la exige
# trocá-la, o que não é seguro com o servidor em várias threads.
_UMASK = os.umask(0)
os.umask(_UMASK)
COLUNAS = ["nome", "status"]


def gravar_atomico(caminho, texto):
    """Grava num temporário e troca: um Ctrl+C no meio não deixa o arquivo pela metade."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(dir=caminho.parent, prefix=f".{caminho.name}.")
    try:
        with os.fdopen(descritor, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        os.chmod(temporario, 0o666 & ~_UMASK)
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


def ler_lotes(saida):
    """lotes.yaml (do importar.py) -> {lote: {conjunto, regiao, importado_em}}; {} se não existe."""
    caminho = Path(saida) / "lotes.yaml"
    if not caminho.exists():
        return {}
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def gravar_lotes(saida, lotes):
    gravar_atomico(Path(saida) / "lotes.yaml",
                   yaml.safe_dump(lotes, allow_unicode=True, sort_keys=True))


def dentro_da_regiao(caixa, regiao):
    """Se o centro da caixa (normalizada) cai na região [x1, y1, x2, y2]; sem região, sim."""
    if regiao is None:
        return True
    cx, cy = (caixa[0] + caixa[2]) / 2, (caixa[1] + caixa[3]) / 2
    return regiao[0] <= cx <= regiao[2] and regiao[1] <= cy <= regiao[3]


# --- propostas ------------------------------------------------------------

def caminho_proposta(saida, anotador, nome):
    return Path(saida) / "propostas" / anotador / f"{Path(nome).stem}.json"


def montar_proposta(anotador, versao, parametros, classes, nome, tamanho, deteccoes,
                    confianca_classe=0.0, candidatas=()):
    """
    deteccoes: [(id da classe, confianca, (x1, y1, x2, y2) normalizada)].
    A caixa vai em pixels da imagem gravada; a classe, pelo nome. Abaixo de
    confianca_classe, a caixa vai sem classe ("classe": null), para o revisor
    dá-la sem ver a do anotador; esta fica em "sugerida", que as páginas não
    mostram e as métricas (T10) podem usar. candidatas: [(confianca, caixa
    normalizada)], para a caixa por clique na página; vão sem classe.
    """
    largura, altura = tamanho
    caixas = []
    for classe, conf, (x1, y1, x2, y2) in deteccoes:
        caixa = {"classe": classes[classe]["nome"]}
        if conf < confianca_classe:
            caixa = {"classe": None, "sugerida": caixa["classe"]}
        caixa["confianca"] = round(float(conf), 4)
        caixa["caixa"] = [round(x1 * largura, 4), round(y1 * altura, 4),
                          round(x2 * largura, 4), round(y2 * altura, 4)]
        caixas.append(caixa)
    proposta = {"anotador": anotador, "versao": versao, "parametros": parametros,
                "classes": hash_classes(classes), "imagem": nome,
                "largura": largura, "altura": altura, "caixas": caixas}
    if candidatas:
        proposta["candidatas"] = [
            {"confianca": round(float(conf), 4),
             "caixa": [round(x1 * largura, 4), round(y1 * altura, 4),
                       round(x2 * largura, 4), round(y2 * altura, 4)]}
            for conf, (x1, y1, x2, y2) in candidatas]
    return proposta


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
    """
    [(nome da classe, confianca, (x1, y1, x2, y2) normalizada)] de uma
    proposta; nome None para caixa proposta sem classe.
    """
    largura, altura = proposta["largura"], proposta["altura"]
    return [(c["classe"], c["confianca"],
             (c["caixa"][0] / largura, c["caixa"][1] / altura,
              c["caixa"][2] / largura, c["caixa"][3] / altura))
            for c in proposta["caixas"]]


def candidatas_normalizadas(proposta):
    """[(confianca, (x1, y1, x2, y2) normalizada)] das candidatas; [] se não houver."""
    largura, altura = proposta["largura"], proposta["altura"]
    return [(c["confianca"], (c["caixa"][0] / largura, c["caixa"][1] / altura,
                              c["caixa"][2] / largura, c["caixa"][3] / altura))
            for c in proposta.get("candidatas", [])]


def anotadores(saida):
    """Nomes dos anotadores com propostas gravadas."""
    pasta = Path(saida) / "propostas"
    return sorted(p.name for p in pasta.iterdir() if p.is_dir()) if pasta.is_dir() else []


def aceitar(saida, anotador, nomes=None):
    """
    Copia as propostas do anotador para labels/, com os ids do data.yaml, e
    marca as imagens como revisadas: o comportamento antigo, proposta direto
    como rótulo. Só mexe nas pendentes (nomes=None: todas). Imagem com caixa
    sem classe fica pendente: a classe dela é do revisor. Devolve (quantas
    aceitou, [imagens deixadas pendentes por caixa sem classe]).
    """
    ids = {n: i for i, n in nomes_classes(saida).items()}
    colunas, linhas = ler_estado(saida)
    aceitas, sem_classe = 0, []
    for nome, linha in linhas.items():
        if linha["status"] != "pendente" or (nomes is not None and nome not in nomes):
            continue
        caminho = caminho_proposta(saida, anotador, nome)
        if not caminho.exists():
            continue
        caixas = caixas_normalizadas(ler_proposta(caminho))
        if any(classe is None for classe, _, _ in caixas):
            sem_classe.append(nome)
            continue
        texto = []
        for classe, _, caixa in caixas:
            if classe not in ids:
                raise ValueError(f"{caminho}: classe '{classe}' fora do data.yaml")
            texto.append(linha_yolo(ids[classe], caixa) + "\n")
        gravar_atomico(Path(saida) / "labels" / f"{Path(nome).stem}.txt", "".join(texto))
        linha["status"] = "revisada"
        aceitas += 1
    gravar_estado(saida, colunas, linhas)
    return aceitas, sem_classe


# --- leitura de uma imagem, para as páginas ---------------------------------

def nomes_classes(saida):
    """Nomes das classes do data.yaml, {id: nome}."""
    data_yaml = Path(saida) / "data.yaml"
    if not data_yaml.exists():
        raise ValueError(f"{data_yaml} não existe; é a saída do anotar.py?")
    with open(data_yaml, encoding="utf-8") as f:
        nomes = (yaml.safe_load(f) or {}).get("names") or {}
    if isinstance(nomes, list):
        nomes = dict(enumerate(nomes))
    return {int(i): n for i, n in nomes.items()}


def ler_rotulos(caminho):
    """
    Linhas 'id cx cy w h' de um .txt -> ([(id, (x1, y1, x2, y2))], quantas
    linhas foram ignoradas); (None, 0) se o arquivo não existe.
    """
    caixas, invalidas = [], 0
    if not caminho.exists():
        return None, 0
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if not partes:
            continue
        try:
            if len(partes) != 5:
                raise ValueError
            cx, cy, w, h = (float(p) for p in partes[1:])
            caixas.append((int(partes[0]), (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)))
        except ValueError:
            invalidas += 1
    return caixas, invalidas


def caixa_json(id_classe, nome, confianca, caixa):
    """Caixa como as páginas a recebem; id None para classe fora do data.yaml."""
    return {"id": id_classe, "nome": nome, "conf": confianca,
            "caixa": [round(v, 6) for v in caixa]}


def ler_imagem(saida, nome, nomes, anotadores_saida, linha_estado, com_candidatas=False):
    """
    O que as páginas mostram de uma imagem: status (None fora do imagens.csv),
    caixas finais (None sem .txt), linhas inválidas do .txt e as propostas de
    cada anotador, com as caixas no formato de caixa_json. com_candidatas: também
    as candidatas de cada anotador, {"conf", "caixa"} (só a página de revisão
    as usa; na estática, pesariam no HTML).
    """
    saida = Path(saida)
    ids = {n: i for i, n in nomes.items()}
    finais, invalidas = ler_rotulos(saida / "labels" / f"{Path(nome).stem}.txt")
    propostas, candidatas = {}, {}
    for anotador in anotadores_saida:
        caminho = caminho_proposta(saida, anotador, nome)
        if caminho.exists():
            proposta = ler_proposta(caminho)
            propostas[anotador] = [caixa_json(ids.get(classe), classe, conf, caixa)
                                   for classe, conf, caixa in caixas_normalizadas(proposta)]
            candidatas[anotador] = [{"conf": conf, "caixa": [round(v, 6) for v in caixa]}
                                    for conf, caixa in candidatas_normalizadas(proposta)]
    dados = {
        "nome": nome,
        "status": linha_estado["status"] if linha_estado else None,
        "final": None if finais is None else [
            caixa_json(i, nomes.get(i, f"classe {i}"), None, c) for i, c in finais],
        "invalidas": invalidas,
        "propostas": propostas,
    }
    if com_candidatas:
        dados["candidatas"] = candidatas
    return dados


def tamanho_imagem(caminho):
    """(largura, altura) lendo só o cabeçalho."""
    with Image.open(caminho) as imagem:
        return imagem.size


# --- revisão (PLANO-REVISAO.md, seção 5) ------------------------------------

ACOES = ("salvar", "descartar")
ORIGENS = ("candidata",)  # de onde veio uma caixa adicionada; "desenho" na fase 4
TOLERANCIA_CAIXA = 1e-5  # caixa "igual" à da proposta, em coordenadas normalizadas


class RevisaoInvalida(ValueError):
    """Pedido de revisão recusado; status sugere o código HTTP."""

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


def caminho_revisao(saida, nome):
    return Path(saida) / "revisoes" / f"{Path(nome).stem}.json"


def ler_revisao(saida, nome):
    caminho = caminho_revisao(saida, nome)
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except ValueError as erro:
        raise ValueError(f"{caminho}: registro inválido ({erro})") from None


def validar_caixas(caixas, nomes, propostas, candidatas=()):
    """
    Confere as caixas finais vindas da página e devolve-as como
    [(id, (x1, y1, x2, y2), índice da proposta ou None, origem ou None)].
    propostas: as caixas normalizadas do anotador de base; candidatas: as
    candidatas dele. Enquanto a página não move caixas (fase 4), uma caixa que
    vem de uma proposta tem de ter as coordenadas dela, e uma adicionada com
    origem "candidata", as de uma candidata.
    """
    if not isinstance(caixas, list):
        raise RevisaoInvalida("'caixas' deve ser uma lista")
    usadas, resultado = set(), []
    for i, c in enumerate(caixas):
        try:
            id_classe, caixa, proposta = c["id"], c["caixa"], c.get("proposta")
            origem = c.get("origem")
            caixa = tuple(float(v) for v in caixa)
        except (KeyError, TypeError, ValueError, AttributeError):
            raise RevisaoInvalida(f"caixa {i} inválida: {c!r}") from None
        if not isinstance(id_classe, int) or isinstance(id_classe, bool) or id_classe not in nomes:
            raise RevisaoInvalida(f"caixa {i}: classe {id_classe!r} fora do data.yaml")
        if len(caixa) != 4 or not (0 <= caixa[0] < caixa[2] <= 1 and 0 <= caixa[1] < caixa[3] <= 1):
            raise RevisaoInvalida(f"caixa {i}: coordenadas fora de [0, 1] ou invertidas: {caixa}")
        if proposta is not None:
            if (not isinstance(proposta, int) or isinstance(proposta, bool)
                    or not 0 <= proposta < len(propostas)):
                raise RevisaoInvalida(f"caixa {i}: proposta {proposta!r} não existe")
            if proposta in usadas:
                raise RevisaoInvalida(f"caixa {i}: proposta {proposta} usada duas vezes")
            usadas.add(proposta)
            original = propostas[proposta][2]
            if any(abs(a - b) > TOLERANCIA_CAIXA for a, b in zip(caixa, original)):
                raise RevisaoInvalida(f"caixa {i}: coordenadas diferentes das da proposta "
                                      f"{proposta} (mover caixas é a fase 4)")
            caixa = original  # sem o arredondamento da página
            if origem is not None:
                raise RevisaoInvalida(f"caixa {i}: caixa de proposta não tem origem")
        elif origem is not None:
            if origem not in ORIGENS:
                raise RevisaoInvalida(f"caixa {i}: origem {origem!r} desconhecida")
            iguais = [c for _, c in candidatas
                      if all(abs(a - b) <= TOLERANCIA_CAIXA for a, b in zip(caixa, c))]
            if not iguais:
                raise RevisaoInvalida(f"caixa {i}: não é nenhuma das candidatas do anotador "
                                      "de base (mover caixas é a fase 4)")
            caixa = iguais[0]
        resultado.append((id_classe, caixa, proposta, origem))
    return resultado


def desfechos(caixas, propostas, ids):
    """
    Desfecho de cada caixa final frente à proposta de origem: 'aceita',
    'classe_corrigida', 'classe_atribuida' (proposta sem classe) ou
    'adicionada' (sem proposta); e os índices das propostas removidas.
    ids: {nome da classe: id}.
    """
    registro = []
    for id_classe, caixa, proposta, origem in caixas:
        if proposta is None:
            desfecho = "adicionada"
        elif propostas[proposta][0] is None:
            desfecho = "classe_atribuida"
        elif ids.get(propostas[proposta][0]) == id_classe:
            desfecho = "aceita"
        else:
            desfecho = "classe_corrigida"
        item = {"id": id_classe, "caixa": [round(v, 6) for v in caixa],
                "proposta": proposta, "desfecho": desfecho}
        if origem is not None:
            item["origem"] = origem
        registro.append(item)
    usadas = {p for _, _, p, _ in caixas if p is not None}
    return registro, [i for i in range(len(propostas)) if i not in usadas]


def revisar(saida, nome, pedido, agora):
    """
    Aplica a revisão de uma imagem pendente. pedido: {acao, base, caixas,
    tempo_ativo_s}, como a página envia. Grava labels/, depois revisoes/ e por
    último o status em imagens.csv: interrompida no meio, a imagem continua
    pendente. Guarda só a última revisão. Devolve o registro gravado.
    """
    saida = Path(saida)
    colunas, linhas = ler_estado(saida)
    if nome not in linhas:
        raise RevisaoInvalida(f"imagem '{nome}' não está no imagens.csv", 404)
    if linhas[nome]["status"] != "pendente":
        raise RevisaoInvalida(f"'{nome}' está {linhas[nome]['status']}; só pendentes são "
                              "editáveis (reabrir é a fase 5)", 409)
    if not isinstance(pedido, dict) or pedido.get("acao") not in ACOES:
        raise RevisaoInvalida(f"'acao' deve ser uma de {', '.join(ACOES)}")
    tempo = pedido.get("tempo_ativo_s", 0)
    if not isinstance(tempo, (int, float)) or isinstance(tempo, bool) or tempo < 0:
        raise RevisaoInvalida("'tempo_ativo_s' deve ser um número não negativo")

    nomes = nomes_classes(saida)
    base = pedido.get("base")
    proposta, propostas, candidatas = None, [], []
    if base is not None:
        caminho = caminho_proposta(saida, str(base), nome) if base in anotadores(saida) else None
        if caminho is None or not caminho.exists():
            raise RevisaoInvalida(f"'{nome}' não tem proposta de '{base}'")
        proposta = ler_proposta(caminho)
        propostas = caixas_normalizadas(proposta)
        candidatas = candidatas_normalizadas(proposta)

    rotulo = saida / "labels" / f"{Path(nome).stem}.txt"
    if pedido["acao"] == "salvar":
        caixas = validar_caixas(pedido.get("caixas", []), nomes, propostas, candidatas)
        registro_caixas, removidas = desfechos(caixas, propostas, {n: i for i, n in nomes.items()})
        gravar_atomico(rotulo, "".join(linha_yolo(i, c) + "\n" for i, c, _, _ in caixas))
        status = "revisada"
    else:
        registro_caixas, removidas = [], list(range(len(propostas)))
        rotulo.unlink(missing_ok=True)
        status = "descartada"

    registro = {
        "imagem": nome, "acao": pedido["acao"], "data": agora,
        "tempo_ativo_s": round(float(tempo), 1), "revisor": None,
        "base": None if proposta is None else {
            "anotador": proposta["anotador"], "versao": proposta.get("versao"),
            "classes": proposta.get("classes")},
        "caixas": registro_caixas, "removidas": removidas,
    }
    gravar_atomico(caminho_revisao(saida, nome),
                   json.dumps(registro, ensure_ascii=False, indent=1) + "\n")
    linhas[nome]["status"] = status
    gravar_estado(saida, colunas, linhas)
    return registro
