"""Testes das funções do anotar.py que não dependem do modelo."""

import json
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anotar  # noqa: E402

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


def test_iou():
    assert anotar.iou((0, 0, 1, 1), (0, 0, 1, 1)) == 1
    assert anotar.iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0
    assert anotar.iou((0, 0, 2, 1), (1, 0, 3, 1)) == pytest.approx(1 / 3)


def test_nms_suprime_sobreposta_de_qualquer_classe():
    a = (0, 0.9, (0.1, 0.1, 0.5, 0.5))
    b = (1, 0.6, (0.12, 0.1, 0.5, 0.52))   # mesmo objeto, outro prompt
    c = (2, 0.7, (0.6, 0.6, 0.9, 0.9))
    assert anotar.nms([b, c, a], 0.5) == [a, c]


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


def test_preparar_saida_recusa_outras_classes(tmp_path):
    anotar.preparar_saida(tmp_path, CLASSES)
    dados = yaml.safe_load((tmp_path / "data.yaml").read_text(encoding="utf-8"))
    assert dados["names"] == {0: "Garrafa", 1: "Tampa", 2: "Lata"}
    assert dados["train"] == dados["val"] == "revisadas.txt"
    assert (tmp_path / "imagens.csv").read_text() == "nome,status\n"
    anotar.preparar_saida(tmp_path, CLASSES)  # mesmas classes: ok
    with pytest.raises(ValueError, match="outras classes"):
        anotar.preparar_saida(tmp_path, CLASSES[:2])


def test_preparar_saida_recusa_formato_antigo(tmp_path):
    (tmp_path / "labels").mkdir()
    (tmp_path / "labels" / "foto.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    with pytest.raises(ValueError, match="formato antigo"):
        anotar.preparar_saida(tmp_path, CLASSES)


# --- anotar.py de ponta a ponta, com um anotador sintético no lugar do modelo ---

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
        return DETECCOES[imagem.info["stem"]]


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setitem(anotar.ANOTADORES, "falso", AnotadorFalso)
    original = anotar.abrir_imagem

    def abrir(caminho):  # deixa o anotador falso saber qual imagem recebeu
        imagem, girada = original(caminho)
        imagem.info["stem"] = Path(caminho).stem
        return imagem, girada
    monkeypatch.setattr(anotar, "abrir_imagem", abrir)

    fotos = []
    for nome in ("a.jpg", "b.png"):
        Image.new("RGB", (200, 100)).save(tmp_path / nome)
        fotos.append(str(tmp_path / nome))
    classes = escrever_classes(tmp_path, CLASSES)
    saida = tmp_path / "saida"
    base = ["-o", str(saida), "--anotador", "falso", "--classes", str(classes)]
    return fotos, saida, base


def test_main_grava_propostas_e_nao_rotulos(ambiente):
    fotos, saida, base = ambiente
    anotar.main(fotos + base + ["--previa"])

    proposta = json.loads((saida / "propostas" / "falso" / "a.json").read_text())
    assert proposta["anotador"] == "falso" and proposta["versao"] == "v1"
    assert (proposta["largura"], proposta["altura"]) == (200, 100)
    assert proposta["caixas"][0] == {"classe": "Lata", "confianca": 0.91,
                                     "caixa": [20.0, 20.0, 80.0, 60.0]}
    assert json.loads((saida / "propostas" / "falso" / "b.json").read_text())["caixas"] == []
    assert (saida / "imagens.csv").read_text() == "nome,status\na.jpg,pendente\nb.png,pendente\n"
    assert not list((saida / "labels").iterdir())
    assert (saida / "revisadas.txt").read_text() == ""
    assert (saida / "previa" / "falso" / "a.jpg").exists()
    assert (saida / "images" / "b.png").exists() and (saida / "visualizar.html").exists()

    with pytest.raises(SystemExit):  # já anotadas por este anotador
        anotar.main(fotos[:1] + base)
    anotar.main(fotos[:1] + base + ["--sobrescrever", "--falso-versao", "v2"])
    assert json.loads((saida / "propostas" / "falso" / "a.json").read_text())["versao"] == "v2"


def test_main_aceitar_reproduz_os_rotulos_de_antes(ambiente):
    fotos, saida, base = ambiente
    anotar.main(fotos + base)
    anotar.main(base + ["--aceitar"])
    # Os mesmos .txt que o anotar.py gravava antes, direto das detecções
    for stem, deteccoes in DETECCOES.items():
        esperado = "".join(anotar.linha_yolo(c, caixa) + "\n" for c, _, caixa in deteccoes)
        assert (saida / "labels" / f"{stem}.txt").read_text() == esperado
    assert (saida / "imagens.csv").read_text() == "nome,status\na.jpg,revisada\nb.png,revisada\n"
    assert (saida / "revisadas.txt").read_text() == "./images/a.jpg\n./images/b.png\n"


def test_main_sem_imagens_nem_aceitar(ambiente):
    _, _, base = ambiente
    with pytest.raises(SystemExit):
        anotar.main(base)


def test_imagem_girada_pelo_exif_e_gravada_ja_girada(tmp_path):
    origem = tmp_path / "foto.jpg"
    exif = Image.Exif()
    exif[anotar.TAG_ORIENTACAO_EXIF] = 6  # girar 90°
    Image.new("RGB", (40, 20)).save(origem, exif=exif)

    imagem, girada = anotar.abrir_imagem(origem)
    assert girada and imagem.size == (20, 40)
    destino = tmp_path / "saida.jpg"
    anotar.salvar_imagem(origem, imagem, girada, destino)
    gravada = Image.open(destino)
    assert gravada.size == (20, 40)
    assert gravada.getexif().get(anotar.TAG_ORIENTACAO_EXIF, 1) == 1
