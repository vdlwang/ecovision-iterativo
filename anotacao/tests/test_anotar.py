"""Testes das funções do anotar.py que não dependem do modelo."""

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
    anotar.preparar_saida(tmp_path, CLASSES)  # mesmas classes: ok
    with pytest.raises(ValueError, match="outras classes"):
        anotar.preparar_saida(tmp_path, CLASSES[:2])


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
