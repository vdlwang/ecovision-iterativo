"""Testes das funções do anotar.py que não dependem do modelo."""

import json
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anotar  # noqa: E402
import importar  # noqa: E402
import saida as formato  # noqa: E402

CLASSES = [
    {"nome": "Garrafa", "prompt": "Plastic bottle", "material": "plastic"},
    {"nome": "Tampa", "prompt": "plastic bottle cap", "material": "plastic"},
    {"nome": "Lata", "prompt": "can", "material": "metal"},
]


def test_montar_prompt_formato_e_intervalos():
    texto, intervalos = anotar.montar_prompt(CLASSES)
    assert texto == "plastic bottle . plastic bottle cap . can ."
    assert [texto[a:b] for a, b in intervalos] == ["plastic bottle", "plastic bottle cap", "can"]


def test_classe_de_cada_token_ignora_especiais_e_pontos():
    texto, intervalos = anotar.montar_prompt(CLASSES)
    # offsets como os de um tokenizer BERT: [CLS], palavras, pontos, [SEP]
    offsets = [(0, 0)]
    pos = 0
    for palavra in texto.split(" "):
        offsets.append((pos, pos + len(palavra)))
        pos += len(palavra) + 1
    offsets.append((0, 0))
    assert anotar.classe_de_cada_token(offsets, intervalos) == [
        None, 0, 0, None, 1, 1, 1, None, 2, None, None]


def test_escolher_classe_com_reserva():
    # sem reserva: a de maior pontuação, mesmo abaixo do limiar
    assert anotar.escolher_classe([0.1, 0.3, 0.2], frozenset(), 0.35) == (1, 0.3)
    # a reserva (2) não tira de uma comum que chega ao limiar...
    assert anotar.escolher_classe([0.4, 0.1, 0.9], frozenset({2}), 0.35) == (0, 0.4)
    # ...só vence quando nenhuma comum chega e ela chega
    assert anotar.escolher_classe([0.2, 0.1, 0.5], frozenset({2}), 0.35) == (2, 0.5)
    assert anotar.escolher_classe([0.2, 0.1, 0.3], frozenset({2}), 0.35) == (0, 0.2)


def test_carregar_classes_valida_reserva(tmp_path):
    reserva = {"nome": "Lixo", "prompt": "trash", "material": "other", "reserva": True}
    assert anotar.carregar_classes(escrever_classes(tmp_path, CLASSES + [reserva]))[-1] == reserva
    with pytest.raises(ValueError, match="ao menos uma"):
        anotar.carregar_classes(escrever_classes(tmp_path, [reserva]))
    with pytest.raises(ValueError, match="reserva"):
        anotar.carregar_classes(escrever_classes(tmp_path, [dict(reserva, reserva="sim")]))


def test_iou():
    assert anotar.iou((0, 0, 1, 1), (0, 0, 1, 1)) == 1
    assert anotar.iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0
    assert anotar.iou((0, 0, 2, 1), (1, 0, 3, 1)) == pytest.approx(1 / 3)


def test_nms_suprime_sobreposta_de_qualquer_classe():
    a = (0, 0.9, (0.1, 0.1, 0.5, 0.5))
    b = (1, 0.6, (0.12, 0.1, 0.5, 0.52))   # mesmo objeto, outro prompt
    c = (2, 0.7, (0.6, 0.6, 0.9, 0.9))
    assert anotar.nms([b, c, a], 0.5) == [a, c]


def test_contida():
    assert anotar.contida((0.2, 0.2, 0.4, 0.4), (0, 0, 1, 1)) == 1
    assert anotar.contida((0, 0, 1, 1), (0.2, 0.2, 0.4, 0.4)) == pytest.approx(0.04)
    assert anotar.contida((0.5, 0, 1.5, 1), (0, 0, 1, 1)) == pytest.approx(0.5)
    assert anotar.contida((0.3, 0.3, 0.3, 0.5), (0, 0, 1, 1)) == 0  # sem área


def test_sem_contidas_remove_a_interna_menos_confiante():
    lata = (0, 0.37, (0.3, 0.3, 0.5, 0.5))
    topo_fraco = (1, 0.33, (0.32, 0.32, 0.45, 0.45))   # dentro da lata, menos confiante: sai
    topo_forte = (1, 0.38, (0.31, 0.31, 0.46, 0.46))   # dentro da lata, mais confiante: fica
    envolvente = (2, 0.22, (0.25, 0.25, 0.6, 0.6))     # envolve mais confiantes: fica
    longe = (0, 0.2, (0.7, 0.7, 0.8, 0.8))
    meio_dentro = (0, 0.1, (0.55, 0.3, 0.65, 0.4))     # metade dentro da envolvente: fica
    deteccoes = [lata, topo_fraco, topo_forte, envolvente, longe, meio_dentro]
    assert anotar.sem_contidas(deteccoes, 0.9) == [lata, topo_forte, envolvente, longe,
                                                   meio_dentro]
    assert anotar.sem_contidas(deteccoes, 0.45) == [lata, topo_forte, envolvente, longe]
    assert anotar.sem_contidas(deteccoes, 1.01) == deteccoes  # desligado


def test_linha_yolo():
    assert anotar.linha_yolo(3, (0.2, 0.4, 0.6, 0.5)) == "3 0.400000 0.450000 0.400000 0.100000"


def escrever_classes(tmp_path, classes):
    caminho = tmp_path / "classes.yaml"
    caminho.write_text(yaml.safe_dump({"classes": classes}), encoding="utf-8")
    return caminho


def test_carregar_classes_valida(tmp_path):
    assert anotar.carregar_classes(escrever_classes(tmp_path, CLASSES)) == CLASSES
    with pytest.raises(ValueError, match="material"):
        anotar.carregar_classes(escrever_classes(
            tmp_path, [{"nome": "x", "prompt": "x", "material": "vidro"}]))
    with pytest.raises(ValueError, match="repetida"):
        anotar.carregar_classes(escrever_classes(tmp_path, [CLASSES[0], CLASSES[0]]))
    with pytest.raises(ValueError, match="prompt"):
        anotar.carregar_classes(escrever_classes(tmp_path, [{"nome": "x", "material": "metal"}]))


def test_classes_yaml_do_repositorio_e_valido():
    assert anotar.carregar_classes(anotar.DIR_SCRIPT / "classes.yaml")
    nomes = anotar.carregar_nomes(anotar.DIR_SCRIPT / "classes.yaml")
    # TACO + Background, na ordem do legado/database e do best.pt
    legado = anotar.DIR_SCRIPT.parent / "legado/database/tcc-0CF/YOLO_dataset/data.yaml"
    assert nomes == yaml.safe_load(legado.read_text(encoding="utf-8"))["names"]
    assert len(nomes) == 61 and nomes[-1] == "Background"


def test_carregar_nomes(tmp_path):
    # Sem 'nomes', os de 'classes', na ordem delas
    assert anotar.carregar_nomes(escrever_classes(tmp_path, CLASSES)) == ["Garrafa", "Tampa", "Lata"]
    caminho = tmp_path / "c.yaml"
    caminho.write_text(yaml.safe_dump({"nomes": ["Lata", "Fundo", "Garrafa"],
                                       "classes": CLASSES[::2]}), encoding="utf-8")
    assert anotar.carregar_nomes(caminho) == ["Lata", "Fundo", "Garrafa"]
    assert anotar.carregar_classes(caminho) == CLASSES[::2]
    caminho.write_text(yaml.safe_dump({"nomes": ["Lata"], "classes": CLASSES}), encoding="utf-8")
    with pytest.raises(ValueError, match="fora de 'nomes': Garrafa, Tampa"):
        anotar.carregar_classes(caminho)
    caminho.write_text(yaml.safe_dump({"nomes": ["Lata", "Lata"]}), encoding="utf-8")
    with pytest.raises(ValueError, match="repetidos: Lata"):
        anotar.carregar_nomes(caminho)


def test_preparar_saida_refaz_ou_recusa_outras_classes(tmp_path):
    anotar.preparar_saida(tmp_path, ["Garrafa", "Tampa", "Lata"])
    dados = yaml.safe_load((tmp_path / "data.yaml").read_text(encoding="utf-8"))
    assert dados["names"] == {0: "Garrafa", 1: "Tampa", 2: "Lata"}
    assert dados["train"] == dados["val"] == "revisadas.txt"
    assert (tmp_path / "imagens.csv").read_text() == "nome,status\n"
    anotar.preparar_saida(tmp_path, ["Garrafa", "Tampa", "Lata"])  # mesmas classes: ok
    # Sem rótulos nem revisões, as propostas guardam o nome: o data.yaml é refeito
    anotar.preparar_saida(tmp_path, ["Lata", "Garrafa"])
    dados = yaml.safe_load((tmp_path / "data.yaml").read_text(encoding="utf-8"))
    assert dados["names"] == {0: "Lata", 1: "Garrafa"}
    # Fundo (.txt vazio) e descarte (revisão sem caixas) não guardam ids
    (tmp_path / "labels" / "a.txt").write_text("")
    (tmp_path / "revisoes").mkdir()
    (tmp_path / "revisoes" / "a.json").write_text('{"acao": "descartar", "caixas": []}')
    anotar.preparar_saida(tmp_path, ["Garrafa", "Lata"])
    for arquivo, texto in (("labels/a.txt", "1 0.5 0.5 0.1 0.1\n"),
                           ("revisoes/b.json", '{"caixas": [{"id": 1}]}')):
        (tmp_path / arquivo).write_text(texto)
        with pytest.raises(ValueError, match="outras classes"):
            anotar.preparar_saida(tmp_path, ["Garrafa"])
        (tmp_path / arquivo).unlink()
    (tmp_path / "labels" / "a.txt").write_text("")


def test_preparar_saida_recusa_formato_antigo(tmp_path):
    (tmp_path / "labels").mkdir()
    (tmp_path / "labels" / "foto.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    with pytest.raises(ValueError, match="formato antigo"):
        anotar.preparar_saida(tmp_path, ["Garrafa"])


# --- anotar.py de ponta a ponta, com um anotador sintético no lugar do modelo ---

# Os ids dos rótulos vêm de 'nomes', não da ordem de 'classes'
NOMES = ["Fundo", "Lata", "Garrafa", "Tampa"]
DETECCOES = {
    "a": [(2, 0.91, (0.1, 0.2, 0.4, 0.6)), (0, 0.42, (0.5, 0.5, 0.9, 0.8))],
    "b": [],
}


class AnotadorFalso:
    nome = "falso"

    @staticmethod
    def opcoes(parser):
        parser.add_argument_group("falso").add_argument("--falso-versao", default="v1")

    @classmethod
    def criar(cls, classes, args):
        anotador = cls()
        anotador.versao = args.falso_versao
        anotador.parametros = {}
        return anotador

    def anotar(self, imagem):
        # nome importado: <lote>_<nome original>
        return DETECCOES[imagem.info["stem"].split("_", 1)[1]]


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setitem(anotar.ANOTADORES, "falso", AnotadorFalso)
    original = anotar.abrir_imagem

    def abrir(caminho):  # deixa o anotador falso saber qual imagem recebeu
        imagem, girada = original(caminho)
        imagem.info["stem"] = Path(caminho).stem
        return imagem, girada
    monkeypatch.setattr(anotar, "abrir_imagem", abrir)

    fotos = tmp_path / "fotos"
    fotos.mkdir()
    for nome in ("a.jpg", "b.png"):
        Image.new("RGB", (200, 100)).save(fotos / nome)
    classes = tmp_path / "classes.yaml"
    classes.write_text(yaml.safe_dump({"nomes": NOMES, "classes": CLASSES}), encoding="utf-8")
    saida = tmp_path / "saida"
    importar.main([str(fotos), "-o", str(saida), "--lote", "l1", "--conjunto", "treino",
                   "--classes", str(classes)])
    base = ["-o", str(saida), "--anotador", "falso", "--classes", str(classes)]
    return fotos, saida, base


def proposta_de(saida, nome):
    return json.loads((saida / "propostas" / "falso" / f"{nome}.json").read_text())


def test_main_anota_as_importadas_sem_copiar(ambiente, capsys):
    _, saida, base = ambiente
    imagens_antes = sorted(p.name for p in (saida / "images").iterdir())
    anotar.main(base + ["--previa"])

    proposta = proposta_de(saida, "l1_a")
    assert proposta["anotador"] == "falso" and proposta["versao"] == "v1"
    assert proposta["imagem"] == "l1_a.jpg"
    assert (proposta["largura"], proposta["altura"]) == (200, 100)
    assert proposta["caixas"][0] == {"classe": "Lata", "confianca": 0.91,
                                     "caixa": [20.0, 20.0, 80.0, 60.0]}
    assert proposta_de(saida, "l1_b")["caixas"] == []
    assert (saida / "imagens.csv").read_text() == (
        "nome,status,lote,conjunto\nl1_a.jpg,pendente,l1,treino\nl1_b.png,pendente,l1,treino\n")
    assert sorted(p.name for p in (saida / "images").iterdir()) == imagens_antes
    assert not list((saida / "labels").iterdir())
    assert (saida / "revisadas.txt").read_text() == ""
    assert yaml.safe_load((saida / "data.yaml").read_text())["names"] == dict(enumerate(NOMES))
    assert (saida / "previa" / "falso" / "l1_a.jpg").exists()
    assert (saida / "visualizar.html").exists()

    # De novo, sem nomes: nada a anotar (todas já têm proposta)
    anotar.main(base)
    assert "Nada a anotar" in capsys.readouterr().out
    with pytest.raises(SystemExit):  # já anotada por este anotador
        anotar.main(["l1_a.jpg"] + base)
    with pytest.raises(SystemExit):  # não importada
        anotar.main(["c.jpg"] + base)
    anotar.main(["l1_a.jpg"] + base + ["--sobrescrever", "--falso-versao", "v2"])
    assert proposta_de(saida, "l1_a")["versao"] == "v2"
    assert proposta_de(saida, "l1_b")["versao"] == "v1"


def test_main_so_anota_pendentes(ambiente, capsys):
    _, saida, base = ambiente
    anotar.main(base)
    colunas, linhas = formato.ler_estado(saida)
    linhas["l1_b.png"]["status"] = "descartada"
    formato.gravar_estado(saida, colunas, linhas)
    anotar.main(base + ["--sobrescrever", "--falso-versao", "v2"])
    assert proposta_de(saida, "l1_a")["versao"] == "v2"
    assert proposta_de(saida, "l1_b")["versao"] == "v1"  # descartada: intocada
    anotar.main(["l1_b.png"] + base + ["--sobrescrever", "--falso-versao", "v3"])
    assert "Puladas (já descartada): l1_b.png" in capsys.readouterr().out
    assert proposta_de(saida, "l1_b")["versao"] == "v1"


def test_main_regiao_de_interesse_pelo_centro(tmp_path, ambiente):
    fotos, saida, base = ambiente
    classes = base[base.index("--classes") + 1]
    # Lote com região à esquerda: a Lata (centro x=0,25) fica, a Garrafa (0,7) sai
    importar.main([str(fotos / "a.jpg"), "-o", str(saida), "--lote", "l2", "--regiao",
                   "0", "0", "0.3", "1", "--classes", classes])
    anotar.main(["l2_a.jpg"] + base)
    assert [c["classe"] for c in proposta_de(saida, "l2_a")["caixas"]] == ["Lata"]


def test_main_aceitar_reproduz_os_rotulos_de_antes(ambiente):
    _, saida, base = ambiente
    anotar.main(base)
    anotar.main(base + ["--aceitar"])
    # Os mesmos .txt que o anotar.py gravava antes, direto das detecções, com
    # o id de cada classe em NOMES
    for stem, deteccoes in DETECCOES.items():
        esperado = "".join(anotar.linha_yolo(NOMES.index(CLASSES[c]["nome"]), caixa) + "\n"
                           for c, _, caixa in deteccoes)
        assert (saida / "labels" / f"l1_{stem}.txt").read_text() == esperado
    assert (saida / "imagens.csv").read_text() == (
        "nome,status,lote,conjunto\nl1_a.jpg,revisada,l1,treino\nl1_b.png,revisada,l1,treino\n")
    assert (saida / "revisadas.txt").read_text() == "./images/l1_a.jpg\n./images/l1_b.png\n"


def test_main_grava_candidatas_de_quem_tem_propor(ambiente, monkeypatch):
    _, saida, base = ambiente
    monkeypatch.setattr(AnotadorFalso, "propor", lambda self, imagem: (
        self.anotar(imagem), [(0.07, (0.0, 0.0, 0.5, 0.5))]), raising=False)
    anotar.main(["l1_a.jpg"] + base)
    proposta = proposta_de(saida, "l1_a")
    assert proposta["candidatas"] == [{"confianca": 0.07, "caixa": [0.0, 0.0, 100.0, 50.0]}]
    assert len(proposta["caixas"]) == 2


def test_main_confianca_classe(ambiente):
    _, saida, base = ambiente
    anotar.main(["l1_a.jpg"] + base + ["--confianca-classe", "0.5", "--previa"])
    proposta = proposta_de(saida, "l1_a")
    # Garrafa (0.42) fica sem classe; Lata (0.91) mantém
    assert [c["classe"] for c in proposta["caixas"]] == ["Lata", None]
    assert proposta["caixas"][1]["sugerida"] == "Garrafa"
    assert proposta["parametros"]["confianca_classe"] == 0.5
    anotar.main(base + ["--aceitar"])  # l1_a tem caixa sem classe: continua pendente
    _, linhas = formato.ler_estado(saida)
    assert linhas["l1_a.jpg"]["status"] == "pendente"


def test_main_recusa_saida_sem_importacao(tmp_path, ambiente):
    _, _, base = ambiente
    base = list(base)
    base[base.index("-o") + 1] = str(tmp_path / "vazia")
    with pytest.raises(SystemExit):
        anotar.main(base)
