"""
Estado da anotação (PLANO-REVISAO.md, seções 1 e 6).

    <saida>/anotacoes.sqlite        fonte do estado: classes, lotes, imagens,
                                    execuções dos anotadores, propostas e revisões
    <saida>/images/<nome>.jpg       gravada pelo importar.py
    <saida>/labels/<stem>.txt       gerado do banco: caixas finais (YOLO) das revisadas
                                    e das aprovadas pelo voto (votar.py)
    <saida>/treino.txt, teste.txt   gerados do banco: as listas do data.yaml
    <saida>/revisadas.txt           gerado do banco: as revisadas por humano
    <saida>/data.yaml               gerado do banco (tabela classes e as listas)

O que o anotador propõe fica separado do que o revisor aprova: uma imagem sem
.txt em labels/ não entra no treino, em vez de entrar como fundo. Cada operação
grava primeiro no banco, numa transação, e depois os arquivos daquela imagem;
interrompida entre os dois, o banco vale, e exportar() refaz os arquivos.

Propostas e revisões nunca são apagadas nem alteradas: anotar de novo cria uma
proposta nova (a vigente de um anotador numa imagem é a de maior id), e cada
revisão é uma linha nova (a vigente é a de maior id).
"""

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import yaml
from PIL import Image

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
STATUS = ("pendente", "revisada", "descartada")
CONJUNTOS = ("treino", "teste")
VOTOS = ("aprovada", "falhou")
BANCO = "anotacoes.sqlite"
VERSAO_ESQUEMA = 3
ESPERA_S = 10        # quanto uma conexão espera por outra que está gravando
LOTE_SQL = 900       # parâmetros por consulta com IN (...)

# mkstemp cria o arquivo só para o dono (0600); os gravados aqui recebem o modo
# de um open() comum. A umask é lida uma vez, na importação, porque lê-la exige
# trocá-la, o que não é seguro com o servidor em várias threads.
_UMASK = os.umask(0)
os.umask(_UMASK)

ESQUEMA = f"""
CREATE TABLE classes (
    id INTEGER PRIMARY KEY CHECK (id >= 0),
    nome TEXT NOT NULL UNIQUE
);
CREATE TABLE lotes (
    nome TEXT PRIMARY KEY,
    conjunto TEXT NOT NULL CHECK (conjunto IN {CONJUNTOS}),
    regiao TEXT,
    importado_em TEXT NOT NULL
);
CREATE TABLE imagens (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    stem TEXT NOT NULL UNIQUE,
    largura INTEGER NOT NULL CHECK (largura > 0),
    altura INTEGER NOT NULL CHECK (altura > 0),
    lote TEXT NOT NULL REFERENCES lotes (nome),
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN {STATUS}),
    voto TEXT CHECK (voto IN {VOTOS}),
    motivo TEXT,
    criada_em TEXT NOT NULL
);
CREATE TABLE execucoes (
    id INTEGER PRIMARY KEY,
    anotador TEXT NOT NULL,
    tipo TEXT NOT NULL,
    versao TEXT,
    parametros TEXT NOT NULL,
    classes_hash TEXT,
    data TEXT NOT NULL
);
CREATE INDEX execucoes_anotador ON execucoes (anotador);
CREATE TABLE propostas (
    id INTEGER PRIMARY KEY,
    imagem_id INTEGER NOT NULL REFERENCES imagens (id),
    execucao_id INTEGER NOT NULL REFERENCES execucoes (id),
    data TEXT NOT NULL
);
CREATE INDEX propostas_imagem ON propostas (imagem_id);
CREATE TABLE caixas_propostas (
    proposta_id INTEGER NOT NULL REFERENCES propostas (id),
    indice INTEGER NOT NULL CHECK (indice >= 0),
    classe TEXT NOT NULL,
    confianca REAL NOT NULL CHECK (confianca BETWEEN 0 AND 1),
    x1 REAL NOT NULL, y1 REAL NOT NULL, x2 REAL NOT NULL, y2 REAL NOT NULL,
    CHECK (0 <= x1 AND x1 < x2 AND x2 <= 1 AND 0 <= y1 AND y1 < y2 AND y2 <= 1),
    PRIMARY KEY (proposta_id, indice)
);
CREATE TABLE revisoes (
    id INTEGER PRIMARY KEY,
    imagem_id INTEGER NOT NULL REFERENCES imagens (id),
    proposta_id INTEGER REFERENCES propostas (id),
    acao TEXT NOT NULL CHECK (acao IN ('salvar', 'descartar')),
    data TEXT NOT NULL,
    tempo_ativo_s REAL NOT NULL CHECK (tempo_ativo_s >= 0),
    revisor TEXT
);
CREATE INDEX revisoes_imagem ON revisoes (imagem_id);
CREATE TABLE caixas_revisao (
    revisao_id INTEGER NOT NULL REFERENCES revisoes (id),
    indice INTEGER NOT NULL CHECK (indice >= 0),
    classe_id INTEGER NOT NULL REFERENCES classes (id),
    x1 REAL NOT NULL, y1 REAL NOT NULL, x2 REAL NOT NULL, y2 REAL NOT NULL,
    proposta_indice INTEGER,
    desfecho TEXT NOT NULL CHECK (desfecho IN
        ('aceita', 'classe_corrigida', 'classe_atribuida', 'adicionada')),
    origem TEXT CHECK (origem IN ('candidata')),
    CHECK (0 <= x1 AND x1 < x2 AND x2 <= 1 AND 0 <= y1 AND y1 < y2 AND y2 <= 1),
    CHECK ((desfecho = 'adicionada') = (proposta_indice IS NULL)),
    PRIMARY KEY (revisao_id, indice)
);
-- A proposta vigente de cada anotador em cada imagem
CREATE VIEW propostas_vigentes AS
SELECT p.id, p.imagem_id, e.anotador FROM propostas p JOIN execucoes e ON e.id = p.execucao_id
WHERE p.id = (SELECT MAX(p2.id) FROM propostas p2 JOIN execucoes e2 ON e2.id = p2.execucao_id
              WHERE p2.imagem_id = p.imagem_id AND e2.anotador = e.anotador);
-- Voto (T6, votar.py): uma votação por rodada; um voto por imagem votada, com
-- as propostas que usou e, se aprovada, as caixas de consenso. O voto vigente
-- de uma imagem é o de maior id, e imagens.voto/motivo repetem o resultado dele.
CREATE TABLE votacoes (
    id INTEGER PRIMARY KEY,
    anotadores TEXT NOT NULL,
    parametros TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE votos (
    id INTEGER PRIMARY KEY,
    votacao_id INTEGER NOT NULL REFERENCES votacoes (id),
    imagem_id INTEGER NOT NULL REFERENCES imagens (id),
    resultado TEXT NOT NULL CHECK (resultado IN {VOTOS}),
    motivo TEXT,
    CHECK ((resultado = 'aprovada') = (motivo IS NULL))
);
CREATE INDEX votos_imagem ON votos (imagem_id);
CREATE TABLE votos_propostas (
    voto_id INTEGER NOT NULL REFERENCES votos (id),
    proposta_id INTEGER NOT NULL REFERENCES propostas (id),
    limiar REAL NOT NULL CHECK (limiar BETWEEN 0 AND 1),
    PRIMARY KEY (voto_id, proposta_id)
);
CREATE TABLE caixas_voto (
    voto_id INTEGER NOT NULL REFERENCES votos (id),
    indice INTEGER NOT NULL CHECK (indice >= 0),
    classe_id INTEGER NOT NULL REFERENCES classes (id),
    confianca REAL NOT NULL CHECK (confianca BETWEEN 0 AND 1),
    x1 REAL NOT NULL, y1 REAL NOT NULL, x2 REAL NOT NULL, y2 REAL NOT NULL,
    CHECK (0 <= x1 AND x1 < x2 AND x2 <= 1 AND 0 <= y1 AND y1 < y2 AND y2 <= 1),
    PRIMARY KEY (voto_id, indice)
);
"""


def agora_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


# --- banco ------------------------------------------------------------------

def caminho_banco(saida):
    return Path(saida) / BANCO


def existe(saida):
    return caminho_banco(saida).is_file()


def conectar(saida):
    """
    Conexão com as chaves estrangeiras ligadas e a espera por outra que grava.
    Em modo de autocommit: escrever exige transacao(). Recusa banco de outra
    versão do esquema.
    """
    caminho = caminho_banco(saida)
    if not caminho.is_file():
        raise ValueError(f"{caminho} não existe: importe imagens antes (importar.py)")
    con = sqlite3.connect(caminho, timeout=ESPERA_S, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    versao = con.execute("PRAGMA user_version").fetchone()[0]
    if versao != VERSAO_ESQUEMA:
        con.close()
        # Sem migrações: o banco é recriado do zero (importar e anotar de novo)
        raise ValueError(f"{caminho}: esquema na versão {versao}, este código usa a "
                         f"{VERSAO_ESQUEMA}; apague a saída e importe de novo")
    return con


@contextmanager
def abrir(saida):
    con = conectar(saida)
    try:
        yield con
    finally:
        con.close()


@contextmanager
def transacao(con):
    """
    BEGIN IMMEDIATE: a trava de escrita vem no início, então conferir e gravar
    são uma operação só, mesmo com o revisar.py e o anotar.py ao mesmo tempo.
    """
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")


def criar_banco(saida):
    caminho = caminho_banco(saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho, isolation_level=None)
    try:
        # WAL: o servidor lê enquanto o anotar.py grava
        con.execute("PRAGMA journal_mode = WAL")
        con.executescript(f"BEGIN; {ESQUEMA} PRAGMA user_version = {VERSAO_ESQUEMA}; COMMIT;")
    finally:
        con.close()


def copia_seguranca(saida):
    """Copia o banco para anotacoes.sqlite.bak (API backup: consistente mesmo em uso)."""
    destino = sqlite3.connect(caminho_banco(saida).with_name(BANCO + ".bak"))
    try:
        with abrir(saida) as con:
            con.backup(destino)
    finally:
        destino.close()


def em_lotes(valores, tamanho=LOTE_SQL):
    valores = list(valores)
    for i in range(0, len(valores), tamanho):
        yield valores[i:i + tamanho]


# --- classes ----------------------------------------------------------------

def _nomes(con):
    return {r["id"]: r["nome"] for r in con.execute("SELECT id, nome FROM classes ORDER BY id")}


def preparar(saida, nomes):
    """
    Cria as pastas e o banco, se preciso, e grava as classes (nomes, na ordem
    dos ids) e o data.yaml. Classes novas no fim são acrescentadas; outra
    ordem ou classes removidas só se nenhuma revisão guarda caixas (as
    propostas guardam a classe pelo nome; fundo e descarte não têm caixas),
    senão os ids não bateriam. Recusa as saídas de formatos anteriores.
    """
    saida = Path(saida)
    if not existe(saida):
        if (saida / "imagens.csv").exists():
            raise ValueError(f"{saida} é do formato anterior ao SQLite (imagens.csv); "
                             "use outro diretório e importe de novo")
        rotulos = saida / "labels"
        if rotulos.is_dir() and any(t.read_text(encoding="utf-8").strip()
                                    for t in rotulos.glob("*.txt")):
            raise ValueError(f"{saida} é do formato antigo (labels/ sem banco), em que as "
                             "propostas eram gravadas como rótulos. Use outro diretório.")
    for pasta in ("images", "labels"):
        (saida / pasta).mkdir(parents=True, exist_ok=True)
    if not existe(saida):
        criar_banco(saida)
    nomes = list(nomes)
    with abrir(saida) as con:
        with transacao(con):
            atuais = list(_nomes(con).values())
            if atuais != nomes:
                if atuais == nomes[:len(atuais)]:
                    novas = list(enumerate(nomes))[len(atuais):]
                elif con.execute("SELECT 1 FROM caixas_revisao LIMIT 1").fetchone():
                    raise ValueError(f"{saida} tem outras classes ({', '.join(atuais)}) e já há "
                                     "revisões com caixas; os ids não bateriam. Só é possível "
                                     "acrescentar classes no fim. Use outro diretório de saída.")
                else:
                    con.execute("DELETE FROM classes")
                    novas = list(enumerate(nomes))
                con.executemany("INSERT INTO classes (id, nome) VALUES (?, ?)", novas)
        exportar_listas(con, saida)


def nomes_classes(saida):
    """
    {id: nome} das classes: do banco ou, numa pasta YOLO sem banco (gerada
    por outra ferramenta, para o visualizar.py), do data.yaml.
    """
    if existe(saida):
        with abrir(saida) as con:
            return _nomes(con)
    data_yaml = Path(saida) / "data.yaml"
    if not data_yaml.exists():
        raise ValueError(f"{data_yaml} não existe; é a saída do anotar.py?")
    with open(data_yaml, encoding="utf-8") as f:
        nomes = (yaml.safe_load(f) or {}).get("names") or {}
    if isinstance(nomes, list):
        nomes = dict(enumerate(nomes))
    return {int(i): n for i, n in nomes.items()}


# --- lotes e imagens --------------------------------------------------------

def ler_lotes(saida):
    """{lote: {conjunto, regiao, importado_em}}; {} sem banco."""
    if not existe(saida):
        return {}
    with abrir(saida) as con:
        return {r["nome"]: {"conjunto": r["conjunto"],
                            "regiao": None if r["regiao"] is None else json.loads(r["regiao"]),
                            "importado_em": r["importado_em"]}
                for r in con.execute("SELECT * FROM lotes ORDER BY nome")}


def ler_estado(saida):
    """
    {nome: {nome, status, lote, conjunto, voto, motivo, largura, altura}}, na
    ordem de registro; {} sem banco.
    """
    if not existe(saida):
        return {}
    with abrir(saida) as con:
        return {r["nome"]: dict(r) for r in con.execute(
            "SELECT i.nome, i.status, i.lote, l.conjunto, i.voto, i.motivo, i.largura, i.altura "
            "FROM imagens i JOIN lotes l ON l.nome = i.lote ORDER BY i.id")}


def conferir_colisoes(existentes, novos):
    """
    Recusa nome novo com o mesmo nome sem extensão de outro (já registrado ou
    da mesma leva): o .txt de labels/ colidiria. Nomes já registrados passam.
    """
    stems = {Path(n).stem: n for n in existentes}
    for nome in novos:
        if nome in existentes:
            continue
        stem = Path(nome).stem
        if stem in stems and stems[stem] != nome:
            raise ValueError(f"'{nome}' colide com '{stems[stem]}', já registrada "
                             "(mesmo nome sem extensão)")
        stems[stem] = nome


def registrar(saida, imagens, lote, dados_lote=None, agora=None):
    """
    Registra as imagens [(nome, largura, altura)] como pendentes, no lote dado,
    numa transação; as já registradas são puladas. Toda imagem é de um lote,
    que diz o conjunto (treino ou teste): só entra pelo importar.py. dados_lote
    {conjunto, regiao, importado_em} cria o lote se ele não existe; sem ele, o
    lote tem de existir. Devolve os nomes registrados.
    """
    agora = agora or agora_iso()
    with abrir(saida) as con:
        with transacao(con):
            if dados_lote is None:
                if con.execute("SELECT 1 FROM lotes WHERE nome = ?", (lote,)).fetchone() is None:
                    raise ValueError(f"lote '{lote}' não existe: importe as imagens pelo "
                                     "importar.py, que cria o lote com o conjunto")
            else:
                con.execute("INSERT OR IGNORE INTO lotes (nome, conjunto, regiao, importado_em) "
                            "VALUES (?, ?, ?, ?)",
                            (lote, dados_lote["conjunto"],
                             None if dados_lote.get("regiao") is None
                             else json.dumps(dados_lote["regiao"]),
                             dados_lote.get("importado_em") or agora))
            existentes = {r[0] for r in con.execute("SELECT nome FROM imagens")}
            conferir_colisoes(existentes, [n for n, _, _ in imagens])
            novas = [(n, Path(n).stem, int(w), int(h), lote, agora)
                     for n, w, h in imagens if n not in existentes]
            con.executemany("INSERT INTO imagens (nome, stem, largura, altura, lote, criada_em) "
                            "VALUES (?, ?, ?, ?, ?, ?)", novas)
    return [n for n, *_ in novas]


def dentro_da_regiao(caixa, regiao):
    """Se o centro da caixa (normalizada) cai na região [x1, y1, x2, y2]; sem região, sim."""
    if regiao is None:
        return True
    cx, cy = (caixa[0] + caixa[2]) / 2, (caixa[1] + caixa[3]) / 2
    return regiao[0] <= cx <= regiao[2] and regiao[1] <= cy <= regiao[3]


def _imagem(con, nome):
    return con.execute("SELECT id, nome, status, voto FROM imagens WHERE nome = ?",
                       (nome,)).fetchone()


# --- propostas ----------------------------------------------------------------

def nova_execucao(saida, anotador, tipo, versao, parametros, classes_hash=None, agora=None):
    """Uma rodada de um anotador (o anotar.py cria uma por chamada); devolve o id."""
    with abrir(saida) as con:
        with transacao(con):
            return con.execute(
                "INSERT INTO execucoes (anotador, tipo, versao, parametros, classes_hash, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (anotador, tipo, None if versao is None else str(versao),
                 json.dumps(parametros, ensure_ascii=False, sort_keys=True), classes_hash,
                 agora or agora_iso())).lastrowid


def gravar_proposta(saida, execucao, nome, caixas, agora=None):
    """
    caixas: [(nome da classe, confianca, (x1, y1, x2, y2) normalizada)], todas
    as do anotador a partir do piso dele, cada uma com a classe. A proposta
    não esconde nem separa nada: quem lê aplica os limiares gravados nos
    parametros da execução (separar()). Devolve o id.
    """
    with abrir(saida) as con:
        with transacao(con):
            imagem = _imagem(con, nome)
            if imagem is None:
                raise ValueError(f"imagem '{nome}' não registrada")
            proposta = con.execute(
                "INSERT INTO propostas (imagem_id, execucao_id, data) VALUES (?, ?, ?)",
                (imagem["id"], execucao, agora or agora_iso())).lastrowid
            con.executemany(
                "INSERT INTO caixas_propostas (proposta_id, indice, classe, confianca, "
                "x1, y1, x2, y2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(proposta, k, classe, round(float(conf), 4), *(round(float(v), 6) for v in caixa))
                 for k, (classe, conf, caixa) in enumerate(caixas)])
    return proposta


def nova_proposta(saida, anotador, nome, caixas, parametros=None, versao=None, tipo=None,
                  classes_hash=None, agora=None):
    """Execução avulsa com uma proposta só (testes e uso manual); devolve o id da proposta."""
    execucao = nova_execucao(saida, anotador, tipo or anotador, versao, parametros or {},
                             classes_hash, agora)
    return gravar_proposta(saida, execucao, nome, caixas, agora)


def _propostas(con, condicao, parametros=()):
    """Propostas que satisfazem a condição SQL (sobre p, e, i), com as caixas."""
    linhas = con.execute(
        "SELECT p.id, p.data, i.nome AS imagem, e.anotador, e.tipo, e.versao, e.parametros, "
        "e.classes_hash FROM propostas p JOIN execucoes e ON e.id = p.execucao_id "
        f"JOIN imagens i ON i.id = p.imagem_id WHERE {condicao} ORDER BY p.id",
        parametros).fetchall()
    propostas = {r["id"]: {"id": r["id"], "anotador": r["anotador"], "tipo": r["tipo"],
                           "versao": r["versao"], "parametros": json.loads(r["parametros"]),
                           "classes": r["classes_hash"], "imagem": r["imagem"],
                           "data": r["data"], "caixas": []}
                 for r in linhas}
    for ids in em_lotes(propostas):
        for c in con.execute(
                "SELECT proposta_id, classe, confianca, x1, y1, x2, y2 FROM caixas_propostas "
                f"WHERE proposta_id IN ({','.join('?' * len(ids))}) "
                "ORDER BY proposta_id, indice", ids):
            propostas[c["proposta_id"]]["caixas"].append(
                (c["classe"], c["confianca"], (c["x1"], c["y1"], c["x2"], c["y2"])))
    return list(propostas.values())


VIGENTE = "p.id IN (SELECT id FROM propostas_vigentes WHERE anotador = ?)"


def _proposta(con, anotador, nome, proposta_id=None):
    condicao, parametros = (f"{VIGENTE} AND i.nome = ?", (anotador, nome))
    if proposta_id is not None:
        condicao, parametros = "p.id = ? AND e.anotador = ? AND i.nome = ?", \
            (proposta_id, anotador, nome)
    encontradas = _propostas(con, condicao, parametros)
    return encontradas[0] if encontradas else None


def ler_proposta(saida, anotador, nome, proposta_id=None):
    """
    A proposta vigente do anotador na imagem (ou a de proposta_id, se for
    dela): {id, anotador, tipo, versao, parametros, classes, imagem, data,
    caixas: [(classe, confianca, caixa normalizada)]}; None se não há.
    """
    if not existe(saida):
        return None
    with abrir(saida) as con:
        return _proposta(con, anotador, nome, proposta_id)


def propostas_atuais(saida, anotador):
    """{nome da imagem: proposta vigente do anotador}, numa consulta só."""
    if not existe(saida):
        return {}
    with abrir(saida) as con:
        return {p["imagem"]: p for p in _propostas(con, VIGENTE, (anotador,))}


def imagens_com_proposta(saida, anotador):
    if not existe(saida):
        return set()
    with abrir(saida) as con:
        return {r[0] for r in con.execute(
            "SELECT i.nome FROM propostas_vigentes v JOIN imagens i ON i.id = v.imagem_id "
            "WHERE v.anotador = ?", (anotador,))}


def anotadores(saida):
    """Nomes dos anotadores com propostas gravadas."""
    if not existe(saida):
        return []
    with abrir(saida) as con:
        return [r[0] for r in con.execute(
            "SELECT DISTINCT e.anotador FROM execucoes e JOIN propostas p ON p.execucao_id = e.id "
            "ORDER BY e.anotador")]


def caixas_normalizadas(proposta):
    """[(nome da classe, confianca, (x1, y1, x2, y2) normalizada)] de uma proposta."""
    return proposta["caixas"]


def limiares(proposta):
    """(confianca, confianca_classe) de leitura, gravados pelo anotador; 0 se faltarem."""
    parametros = proposta.get("parametros") or {}
    return (float(parametros.get("confianca", 0.0)),
            float(parametros.get("confianca_classe", 0.0)))


def separar(proposta):
    """
    Aplica os limiares de leitura da proposta (decisão 16):
    - visiveis: {índice na proposta: (classe, confianca, caixa, classe_visivel)},
      as caixas com confianca >= confianca, que a página mostra; classe_visivel
      é False abaixo de confianca_classe, e a página não recebe a classe (o
      revisor a dá sem ver a do anotador);
    - candidatas: [(índice, confianca, caixa)], as de baixo, para a caixa por
      clique.
    O índice é o da lista completa, estável qualquer que seja o limiar.
    """
    confianca, confianca_classe = limiares(proposta)
    visiveis, candidatas = {}, []
    for k, (classe, conf, caixa) in enumerate(caixas_normalizadas(proposta)):
        if conf >= confianca:
            visiveis[k] = (classe, conf, caixa, conf >= confianca_classe)
        else:
            candidatas.append((k, conf, caixa))
    return visiveis, candidatas


# --- arquivos gerados do banco --------------------------------------------------

# Imagem com rótulo final: revisada por humano, ou pendente e aprovada pelo voto
COM_ROTULO = "(i.status = 'revisada' OR (i.status = 'pendente' AND i.voto = 'aprovada'))"
LISTAS = {
    # OBJETIVO.md, seção 2: o treino recebe as aprovadas e as revisadas; o
    # teste, só as revisadas (o voto não roda no teste)
    "treino.txt": f"l.conjunto = 'treino' AND {COM_ROTULO}",
    "teste.txt": "l.conjunto = 'teste' AND i.status = 'revisada'",
    "revisadas.txt": "i.status = 'revisada'",
}


def exportar_listas(con, saida):
    """
    treino.txt, teste.txt, revisadas.txt e o data.yaml, que aponta para as
    duas primeiras: o val do treino do YOLO é a base de teste, anotada por
    humanos sem pré-anotação de classe (OBJETIVO.md, seção 4). Sem imagem de
    teste revisada, o teste.txt fica vazio e não dá para treinar, de propósito.
    """
    saida = Path(saida)
    for arquivo, condicao in LISTAS.items():
        # "./" faz o Ultralytics resolver o caminho a partir da pasta do .txt
        nomes = [f"./images/{r[0]}" for r in con.execute(
            "SELECT i.nome FROM imagens i JOIN lotes l ON l.nome = i.lote "
            f"WHERE {condicao} ORDER BY i.id")]
        gravar_atomico(saida / arquivo, "".join(n + "\n" for n in nomes))
    # Sem 'path': o Ultralytics usa a pasta do data.yaml
    gravar_atomico(saida / "data.yaml", yaml.safe_dump(
        {"train": "treino.txt", "val": "teste.txt", "names": _nomes(con)},
        allow_unicode=True, sort_keys=False))


def _revisao_vigente(con, imagem_id):
    return con.execute("SELECT * FROM revisoes WHERE imagem_id = ? ORDER BY id DESC LIMIT 1",
                       (imagem_id,)).fetchone()


def _caixas_revisao(con, revisao_id):
    return con.execute("SELECT * FROM caixas_revisao WHERE revisao_id = ? ORDER BY indice",
                       (revisao_id,)).fetchall()


def _voto_vigente(con, imagem_id):
    return con.execute("SELECT * FROM votos WHERE imagem_id = ? ORDER BY id DESC LIMIT 1",
                       (imagem_id,)).fetchone()


def _caixas_voto(con, voto_id):
    return con.execute("SELECT * FROM caixas_voto WHERE voto_id = ? ORDER BY indice",
                       (voto_id,)).fetchall()


def _caixas_finais(con, imagem):
    """
    As caixas finais (linhas de caixas_revisao ou caixas_voto) da imagem, ou
    None se ela não tem rótulo: as da revisão vigente, se revisada; as do voto
    vigente, se pendente e aprovada. A revisão humana sempre vale mais.
    """
    if imagem["status"] == "revisada":
        revisao = _revisao_vigente(con, imagem["id"])
        if revisao is not None and revisao["acao"] == "salvar":
            return _caixas_revisao(con, revisao["id"])
    elif imagem["status"] == "pendente" and imagem["voto"] == "aprovada":
        voto = _voto_vigente(con, imagem["id"])
        if voto is not None and voto["resultado"] == "aprovada":
            return _caixas_voto(con, voto["id"])
    return None


def _exportar_rotulo(con, saida, imagem):
    """labels/<stem>.txt da imagem com as caixas finais; sem rótulo final, nenhum."""
    rotulo = Path(saida) / "labels" / f"{Path(imagem['nome']).stem}.txt"
    caixas = _caixas_finais(con, imagem)
    if caixas is None:
        rotulo.unlink(missing_ok=True)
        return
    gravar_atomico(rotulo, "".join(
        linha_yolo(c["classe_id"], (c["x1"], c["y1"], c["x2"], c["y2"])) + "\n"
        for c in caixas))


def exportar(saida):
    """
    Refaz do banco todos os arquivos gerados: labels/ (e apaga os .txt de
    imagens sem rótulo final), as listas e o data.yaml (exportar_listas).
    """
    saida = Path(saida)
    (saida / "labels").mkdir(parents=True, exist_ok=True)
    with abrir(saida) as con:
        imagens = con.execute("SELECT id, nome, status, voto FROM imagens").fetchall()
        for imagem in imagens:
            _exportar_rotulo(con, saida, imagem)
        stems = {Path(i["nome"]).stem for i in imagens if _caixas_finais(con, i) is not None}
        for rotulo in (saida / "labels").glob("*.txt"):
            if rotulo.stem not in stems:
                rotulo.unlink()
        exportar_listas(con, saida)


# --- leitura de uma imagem, para as páginas ---------------------------------

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
    O que as páginas mostram de uma imagem: status (None se não registrada),
    caixas finais (do .txt de labels/, gerado do banco; None sem .txt), linhas
    inválidas do .txt, as propostas vigentes visíveis de cada anotador
    (separar()), no formato de caixa_json mais o "indice" na proposta (a de
    classe escondida vem com id e nome None), e propostas_ids {anotador: id},
    que a página devolve ao salvar. com_candidatas: também as candidatas de
    cada anotador, {"indice", "conf", "caixa"} (só a página de revisão as usa;
    na estática, pesariam no HTML).
    """
    saida = Path(saida)
    ids = {n: i for i, n in nomes.items()}
    finais, invalidas = ler_rotulos(saida / "labels" / f"{Path(nome).stem}.txt")
    propostas, candidatas, propostas_ids = {}, {}, {}
    if anotadores_saida and existe(saida):
        with abrir(saida) as con:
            for anotador in anotadores_saida:
                proposta = _proposta(con, anotador, nome)
                if proposta is None:
                    continue
                visiveis, abaixo = separar(proposta)
                propostas_ids[anotador] = proposta["id"]
                propostas[anotador] = [
                    dict(caixa_json(ids.get(classe) if mostra else None,
                                    classe if mostra else None, conf, caixa), indice=k)
                    for k, (classe, conf, caixa, mostra) in visiveis.items()]
                candidatas[anotador] = [{"indice": k, "conf": conf,
                                         "caixa": [round(v, 6) for v in caixa]}
                                        for k, conf, caixa in abaixo]
    dados = {
        "nome": nome,
        "status": linha_estado["status"] if linha_estado else None,
        "final": None if finais is None else [
            caixa_json(i, nomes.get(i, f"classe {i}"), None, c) for i, c in finais],
        "invalidas": invalidas,
        "propostas": propostas,
        "propostas_ids": propostas_ids,
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


def validar_caixas(caixas, nomes, visiveis, candidatas=()):
    """
    Confere as caixas finais vindas da página e devolve-as como
    [(id, (x1, y1, x2, y2), índice da proposta ou None, origem ou None)].
    visiveis e candidatas: as do anotador de base, de separar(). Uma caixa que
    vem de uma proposta cita o índice dela, que tem de ser de uma visível.
    Enquanto a página não move caixas, ela tem de ter as coordenadas da
    proposta, e uma adicionada com origem "candidata", as de uma candidata.
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
                    or proposta not in visiveis):
                raise RevisaoInvalida(f"caixa {i}: proposta {proposta!r} não existe")
            if proposta in usadas:
                raise RevisaoInvalida(f"caixa {i}: proposta {proposta} usada duas vezes")
            usadas.add(proposta)
            original = visiveis[proposta][2]
            if any(abs(a - b) > TOLERANCIA_CAIXA for a, b in zip(caixa, original)):
                raise RevisaoInvalida(f"caixa {i}: coordenadas diferentes das da proposta "
                                      f"{proposta} (mover caixas está adiado, decisão 12)")
            caixa = original  # sem o arredondamento da página
            if origem is not None:
                raise RevisaoInvalida(f"caixa {i}: caixa de proposta não tem origem")
        elif origem is not None:
            if origem not in ORIGENS:
                raise RevisaoInvalida(f"caixa {i}: origem {origem!r} desconhecida")
            iguais = [c for _, _, c in candidatas
                      if all(abs(a - b) <= TOLERANCIA_CAIXA for a, b in zip(caixa, c))]
            if not iguais:
                raise RevisaoInvalida(f"caixa {i}: não é nenhuma das candidatas do anotador "
                                      "de base (mover caixas está adiado, decisão 12)")
            caixa = iguais[0]
        resultado.append((id_classe, caixa, proposta, origem))
    return resultado


def desfechos(caixas, visiveis, ids):
    """
    Desfecho de cada caixa final frente à proposta de origem: 'aceita',
    'classe_corrigida', 'classe_atribuida' (a classe da proposta estava
    escondida do revisor) ou 'adicionada' (sem proposta). ids: {nome da classe: id}.
    """
    resultado = []
    for id_classe, caixa, proposta, origem in caixas:
        if proposta is None:
            desfecho = "adicionada"
        elif not visiveis[proposta][3]:
            desfecho = "classe_atribuida"
        elif ids.get(visiveis[proposta][0]) == id_classe:
            desfecho = "aceita"
        else:
            desfecho = "classe_corrigida"
        resultado.append((id_classe, caixa, proposta, origem, desfecho))
    return resultado


def _gravar_revisao(con, imagem, proposta_id, acao, agora, tempo, revisor, caixas):
    """Insere a revisão e as caixas [(id, caixa, proposta, origem, desfecho)] e muda o status."""
    revisao = con.execute(
        "INSERT INTO revisoes (imagem_id, proposta_id, acao, data, tempo_ativo_s, revisor) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (imagem["id"], proposta_id, acao, agora, round(float(tempo), 1), revisor)).lastrowid
    con.executemany(
        "INSERT INTO caixas_revisao (revisao_id, indice, classe_id, x1, y1, x2, y2, "
        "proposta_indice, desfecho, origem) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(revisao, k, i, *c, p, d, o) for k, (i, c, p, o, d) in enumerate(caixas)])
    con.execute("UPDATE imagens SET status = ? WHERE id = ?",
                ("revisada" if acao == "salvar" else "descartada", imagem["id"]))
    return revisao


def revisar(saida, nome, pedido, agora):
    """
    Aplica a revisão de uma imagem pendente (aprovada pelo voto ou não). pedido: {acao, base, proposta_id,
    caixas, tempo_ativo_s}, como a página envia; proposta_id, se vier, tem de
    ser a proposta vigente do anotador base (senão, outra foi gravada depois
    que a página a abriu: 409). Grava a revisão e o status numa transação e
    depois o .txt e o revisadas.txt. Devolve o registro (ler_revisao).
    """
    saida = Path(saida)
    if not isinstance(pedido, dict) or pedido.get("acao") not in ACOES:
        raise RevisaoInvalida(f"'acao' deve ser uma de {', '.join(ACOES)}")
    tempo = pedido.get("tempo_ativo_s", 0)
    if not isinstance(tempo, (int, float)) or isinstance(tempo, bool) or tempo < 0:
        raise RevisaoInvalida("'tempo_ativo_s' deve ser um número não negativo")
    base, proposta_id = pedido.get("base"), pedido.get("proposta_id")
    if base is not None and not isinstance(base, str):
        raise RevisaoInvalida("'base' deve ser o nome de um anotador")
    if proposta_id is not None and (base is None or not isinstance(proposta_id, int)
                                    or isinstance(proposta_id, bool)):
        raise RevisaoInvalida("'proposta_id' deve ser um inteiro, com 'base'")

    with abrir(saida) as con:
        with transacao(con):
            imagem = _imagem(con, nome)
            if imagem is None:
                raise RevisaoInvalida(f"imagem '{nome}' não está registrada", 404)
            if imagem["status"] != "pendente":
                raise RevisaoInvalida(f"'{nome}' está {imagem['status']}; só pendentes são "
                                      "editáveis (reabrir é a fase 5)", 409)
            nomes = _nomes(con)
            proposta, visiveis, candidatas = None, {}, []
            if base is not None:
                proposta = _proposta(con, base, nome)
                if proposta is None:
                    raise RevisaoInvalida(f"'{nome}' não tem proposta de '{base}'")
                if proposta_id is not None and proposta_id != proposta["id"]:
                    raise RevisaoInvalida(
                        f"a proposta {proposta_id} de '{base}' não é mais a vigente (é a "
                        f"{proposta['id']}): o anotador gravou outra depois que a página foi "
                        "aberta; recarregue", 409)
                visiveis, candidatas = separar(proposta)
            if pedido["acao"] == "salvar":
                caixas = desfechos(validar_caixas(pedido.get("caixas", []), nomes, visiveis,
                                                  candidatas),
                                   visiveis, {n: i for i, n in nomes.items()})
            else:
                caixas = []
            _gravar_revisao(con, imagem, None if proposta is None else proposta["id"],
                            pedido["acao"], agora, tempo, None, caixas)
        _exportar_rotulo(con, saida, _imagem(con, nome))
        exportar_listas(con, saida)
    return ler_revisao(saida, nome)


def ler_revisao(saida, nome):
    """
    A revisão vigente da imagem, ou None: {imagem, acao, data, tempo_ativo_s,
    revisor, base: {anotador, versao, classes, limiares, proposta_id} ou None,
    caixas: [{id, caixa, proposta, desfecho[, origem]}], removidas}. As
    removidas são as caixas visíveis da proposta base que nenhuma caixa cita.
    """
    if not existe(saida):
        return None
    with abrir(saida) as con:
        imagem = _imagem(con, nome)
        revisao = None if imagem is None else _revisao_vigente(con, imagem["id"])
        if revisao is None:
            return None
        caixas = []
        for c in _caixas_revisao(con, revisao["id"]):
            item = {"id": c["classe_id"], "caixa": [round(c[k], 6) for k in ("x1", "y1", "x2", "y2")],
                    "proposta": c["proposta_indice"], "desfecho": c["desfecho"]}
            if c["origem"] is not None:
                item["origem"] = c["origem"]
            caixas.append(item)
        base, removidas = None, []
        if revisao["proposta_id"] is not None:
            proposta = _propostas(con, "p.id = ?", (revisao["proposta_id"],))[0]
            usadas = {c["proposta"] for c in caixas if c["proposta"] is not None}
            removidas = [k for k in separar(proposta)[0] if k not in usadas]
            base = {"anotador": proposta["anotador"], "versao": proposta["versao"],
                    "classes": proposta["classes"], "proposta_id": proposta["id"],
                    "limiares": dict(zip(("confianca", "confianca_classe"), limiares(proposta)))}
        return {"imagem": nome, "acao": revisao["acao"], "data": revisao["data"],
                "tempo_ativo_s": revisao["tempo_ativo_s"], "revisor": revisao["revisor"],
                "base": base, "caixas": caixas, "removidas": removidas}


def aceitar(saida, anotador, nomes=None, agora=None):
    """
    Grava as propostas vigentes do anotador como revisão (revisor "aceitar",
    tempo 0) e marca as imagens como revisadas: o comportamento antigo,
    proposta direto como rótulo. Só as caixas visíveis (separar()); só mexe
    nas pendentes (nomes=None: todas). Imagem com caixa de classe escondida
    fica pendente: a classe dela é do revisor. Devolve (quantas aceitou,
    [imagens deixadas pendentes por caixa sem classe]).
    """
    agora = agora or agora_iso()
    aceitas, sem_classe = [], []
    with abrir(saida) as con:
        with transacao(con):
            ids = {n: i for i, n in _nomes(con).items()}
            for proposta in _propostas(con, f"{VIGENTE} AND i.status = 'pendente'", (anotador,)):
                nome = proposta["imagem"]
                if nomes is not None and nome not in nomes:
                    continue
                visiveis, _ = separar(proposta)
                if not all(mostra for _, _, _, mostra in visiveis.values()):
                    sem_classe.append(nome)
                    continue
                fora = [classe for classe, _, _, _ in visiveis.values() if classe not in ids]
                if fora:
                    raise ValueError(f"proposta de {anotador} em {nome}: classe '{fora[0]}' "
                                     "fora do data.yaml")
                caixas = [(ids[classe], caixa, k, None, "aceita")
                          for k, (classe, _, caixa, _) in visiveis.items()]
                _gravar_revisao(con, _imagem(con, nome), proposta["id"], "salvar", agora, 0,
                                "aceitar", caixas)
                aceitas.append(nome)
        for nome in aceitas:
            _exportar_rotulo(con, saida, _imagem(con, nome))
        exportar_listas(con, saida)
    return len(aceitas), sem_classe


# --- voto (OBJETIVO.md, seção 3; T6) -----------------------------------------

def votar(saida, anotadores, decidir, parametros=None, revotar=False, agora=None):
    """
    Vota, numa transação, as imagens pendentes de lotes de treino com proposta vigente de todos os anotadores. Pula as que já têm voto
    sobre essas mesmas propostas, a não ser com revotar; as de teste não são
    votadas (vão à união sem classe e à revisão, T9).

    decidir(propostas) recebe as propostas vigentes, na ordem de anotadores, e
    devolve (motivo, consenso, limiares): motivo None se aprovada;
    consenso [(nome da classe, confianca, caixa normalizada)]; limiares, o de
    leitura que usou em cada proposta. Uma caixa de consenso de classe fora da
    tabela classes reprova a imagem ("classe_fora"): não teria id no .txt.

    Grava a votação, um voto por imagem com as propostas que usou e as caixas
    de consenso, e voto/motivo em imagens; depois, os .txt das votadas e as
    listas. Devolve {aprovadas: [nomes], falhou: {nome: motivo}, incompletas,
    ja_votadas, teste} (os três últimos, contagens).
    """
    anotadores = list(anotadores)
    if len(set(anotadores)) != len(anotadores) or len(anotadores) < 2:
        raise ValueError("o voto precisa de ao menos dois anotadores, sem repetição")
    agora = agora or agora_iso()
    resultado = {"aprovadas": [], "falhou": {}, "incompletas": 0, "ja_votadas": 0, "teste": 0}
    with abrir(saida) as con:
        with transacao(con):
            ids = {n: i for i, n in _nomes(con).items()}
            imagens = con.execute(
                "SELECT i.id, i.nome, l.conjunto FROM imagens i "
                "JOIN lotes l ON l.nome = i.lote WHERE i.status = 'pendente' "
                "ORDER BY i.id").fetchall()
            vigentes = [{p["imagem"]: p for p in _propostas(con, VIGENTE, (a,))}
                        for a in anotadores]
            votacao = None
            for imagem in imagens:
                nome = imagem["nome"]
                if imagem["conjunto"] == "teste":
                    resultado["teste"] += 1
                    continue
                if not all(nome in v for v in vigentes):
                    resultado["incompletas"] += 1
                    continue
                propostas = [v[nome] for v in vigentes]
                anterior = _voto_vigente(con, imagem["id"])
                if anterior is not None and not revotar and {
                        r[0] for r in con.execute(
                            "SELECT proposta_id FROM votos_propostas WHERE voto_id = ?",
                            (anterior["id"],))} == {p["id"] for p in propostas}:
                    resultado["ja_votadas"] += 1
                    continue
                motivo, consenso, limiares_usados = decidir(propostas)
                if motivo is None and any(c[0] not in ids for c in consenso):
                    motivo, consenso = "classe_fora", []
                if votacao is None:
                    votacao = con.execute(
                        "INSERT INTO votacoes (anotadores, parametros, data) VALUES (?, ?, ?)",
                        (json.dumps(anotadores, ensure_ascii=False),
                         json.dumps(parametros or {}, ensure_ascii=False, sort_keys=True),
                         agora)).lastrowid
                voto = con.execute(
                    "INSERT INTO votos (votacao_id, imagem_id, resultado, motivo) "
                    "VALUES (?, ?, ?, ?)",
                    (votacao, imagem["id"], "falhou" if motivo else "aprovada",
                     motivo)).lastrowid
                con.executemany(
                    "INSERT INTO votos_propostas (voto_id, proposta_id, limiar) VALUES (?, ?, ?)",
                    [(voto, p["id"], float(l)) for p, l in zip(propostas, limiares_usados)])
                con.executemany(
                    "INSERT INTO caixas_voto (voto_id, indice, classe_id, confianca, "
                    "x1, y1, x2, y2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [(voto, k, ids[classe], round(float(conf), 4),
                      *(round(float(v), 6) for v in caixa))
                     for k, (classe, conf, caixa) in enumerate(consenso)])
                con.execute("UPDATE imagens SET voto = ?, motivo = ? WHERE id = ?",
                            ("falhou" if motivo else "aprovada", motivo, imagem["id"]))
                if motivo:
                    resultado["falhou"][nome] = motivo
                else:
                    resultado["aprovadas"].append(nome)
        for nome in [*resultado["aprovadas"], *resultado["falhou"]]:
            _exportar_rotulo(con, saida, _imagem(con, nome))
        exportar_listas(con, saida)
    return resultado


def ler_voto(saida, nome):
    """
    O voto vigente da imagem, ou None: {imagem, resultado, motivo, data,
    anotadores, parametros, propostas: [{id, anotador, limiar}], caixas:
    [{id, conf, caixa}]}.
    """
    if not existe(saida):
        return None
    with abrir(saida) as con:
        imagem = _imagem(con, nome)
        voto = None if imagem is None else _voto_vigente(con, imagem["id"])
        if voto is None:
            return None
        votacao = con.execute("SELECT * FROM votacoes WHERE id = ?",
                              (voto["votacao_id"],)).fetchone()
        propostas = [{"id": r["proposta_id"], "anotador": r["anotador"], "limiar": r["limiar"]}
                     for r in con.execute(
                         "SELECT vp.proposta_id, vp.limiar, e.anotador FROM votos_propostas vp "
                         "JOIN propostas p ON p.id = vp.proposta_id "
                         "JOIN execucoes e ON e.id = p.execucao_id WHERE vp.voto_id = ? "
                         "ORDER BY vp.proposta_id", (voto["id"],))]
        return {"imagem": nome, "resultado": voto["resultado"], "motivo": voto["motivo"],
                "data": votacao["data"], "anotadores": json.loads(votacao["anotadores"]),
                "parametros": json.loads(votacao["parametros"]), "propostas": propostas,
                "caixas": [{"id": c["classe_id"], "conf": c["confianca"],
                            "caixa": [round(c[k], 6) for k in ("x1", "y1", "x2", "y2")]}
                           for c in _caixas_voto(con, voto["id"])]}
