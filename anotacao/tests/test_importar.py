"""Testes do importar.py."""

import os
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import importar  # noqa: E402
import saida as formato  # noqa: E402

NOMES = ["Garrafa", "Lata"]


def foto(pasta, nome, tamanho=(40, 20), orientacao=None):
    caminho = pasta / nome
    pasta.mkdir(parents=True, exist_ok=True)
    exif = Image.Exif()
    if orientacao:
        exif[importar.TAG_ORIENTACAO_EXIF] = orientacao
    Image.new("RGB", tamanho, (200, 30, 30)).save(caminho, exif=exif)
    return caminho


def test_importa_copia_registra_e_pula_as_ja_importadas(tmp_path):
    fotos = [foto(tmp_path / "f", "a.jpg"), foto(tmp_path / "f", "b.png")]
    saida = tmp_path / "saida"
    r = importar.importar(saida, fotos, "l1", NOMES, conjunto="teste", agora="2026-11-11")
    assert r == {"importadas": ["l1_a.jpg", "l1_b.png"], "puladas": [], "conjunto": "teste"}
    # cópia byte a byte: nada foi regravado
    assert (saida / "images" / "l1_a.jpg").read_bytes() == fotos[0].read_bytes()
    assert (saida / "imagens.csv").read_text() == (
        "nome,status,lote,conjunto\nl1_a.jpg,pendente,l1,teste\nl1_b.png,pendente,l1,teste\n")
    assert formato.ler_lotes(saida) == {"l1": {"conjunto": "teste", "regiao": None,
                                               "importado_em": "2026-11-11"}}
    assert yaml.safe_load((saida / "data.yaml").read_text())["names"] == {0: "Garrafa", 1: "Lata"}

    # De novo, com uma nova: a antiga é pulada, o conjunto do lote se mantém
    fotos.append(foto(tmp_path / "f", "c.jpg"))
    r = importar.importar(saida, fotos, "l1", NOMES)
    assert r["importadas"] == ["l1_c.jpg"] and r["puladas"] == ["l1_a.jpg", "l1_b.png"]
    assert r["conjunto"] == "teste"
    with pytest.raises(ValueError, match="não muda"):
        importar.importar(saida, fotos, "l1", NOMES, conjunto="treino")


def test_outro_lote_mesma_foto_nao_colide(tmp_path):
    a = foto(tmp_path / "f", "a.jpg")
    saida = tmp_path / "saida"
    importar.importar(saida, [a], "l1", NOMES, conjunto="treino")
    importar.importar(saida, [a], "l2", NOMES, conjunto="teste")
    _, linhas = formato.ler_estado(saida)
    assert {n: l["conjunto"] for n, l in linhas.items()} == {"l1_a.jpg": "treino",
                                                             "l2_a.jpg": "teste"}


def test_recusas(tmp_path):
    a = foto(tmp_path / "f", "a.jpg")
    saida = tmp_path / "saida"
    for lote in ("l_1", "", "-l", "l/1"):
        with pytest.raises(ValueError, match="lote inválido"):
            importar.importar(saida, [a], lote, NOMES)
    with pytest.raises(ValueError, match="repetidos"):
        importar.importar(saida, [a, foto(tmp_path / "g", "a.jpg")], "l1", NOMES)
    for regiao in ([0, 0, 1.2, 1], [0.5, 0, 0.4, 1], [0, 0.5, 1, 0.5]):
        with pytest.raises(ValueError, match="região"):
            importar.importar(saida, [a], "l1", NOMES, regiao=regiao)
    with pytest.raises(ValueError, match="conjunto"):
        importar.importar(saida, [a], "l1", NOMES, conjunto="validacao")
    importar.importar(saida, [a], "l1", NOMES, regiao=[0, 0.1, 1, 0.9])
    with pytest.raises(ValueError, match="região"):
        importar.importar(saida, [a], "l1", NOMES, regiao=[0, 0, 1, 1])


def test_regrava_so_a_girada_ou_grande(tmp_path):
    girada = foto(tmp_path / "f", "g.jpg", (40, 20), orientacao=6)  # girar 90°
    grande = foto(tmp_path / "f", "G.png", (400, 100))
    destino = tmp_path / "d"
    destino.mkdir()
    assert importar.gravar_imagem(girada, destino / "g.jpg") == "regravada"
    with Image.open(destino / "g.jpg") as imagem:
        assert imagem.size == (20, 40)
        assert imagem.getexif().get(importar.TAG_ORIENTACAO_EXIF, 1) == 1
    assert importar.gravar_imagem(grande, destino / "G.png") == "copia"
    assert importar.gravar_imagem(grande, destino / "G.png", lado_maximo=200) == "regravada"
    with Image.open(destino / "G.png") as imagem:
        assert imagem.size == (200, 50)


def test_link_quando_nao_regrava(tmp_path):
    a = foto(tmp_path / "f", "a.jpg")
    saida = tmp_path / "saida"
    importar.importar(saida, [a], "l1", NOMES, link=True)
    gravada = saida / "images" / "l1_a.jpg"
    assert gravada.read_bytes() == a.read_bytes()
    assert os.path.samefile(gravada, a)


def test_sorteio_por_lote_estavel_e_perto_de_um_em_cinco():
    assert importar.sortear_conjunto("2026-11-11a") == importar.sortear_conjunto("2026-11-11a")
    testes = sum(importar.sortear_conjunto(f"lote-{i}") == "teste" for i in range(2000))
    assert 320 <= testes <= 480  # 1 em 5 de 2000 = 400


def test_main_com_pasta(tmp_path, capsys):
    foto(tmp_path / "f", "a.jpg")
    foto(tmp_path / "f", "b.jpg")
    (tmp_path / "f" / "leia.txt").write_text("não é imagem")
    saida = tmp_path / "saida"
    importar.main([str(tmp_path / "f"), "-o", str(saida), "--lote", "l1", "--regiao",
                   "0", "0.1", "1", "0.9"])
    assert "2 imagem(ns) importada(s)" in capsys.readouterr().out
    assert formato.ler_lotes(saida)["l1"]["regiao"] == [0.0, 0.1, 1.0, 0.9]
    with pytest.raises(SystemExit):
        importar.main([str(tmp_path / "f"), "-o", str(saida)])  # sem --lote
