"""Testes do formato do diretório de saída (saida.py)."""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saida as formato  # noqa: E402

CLASSES = [
    {"nome": "Garrafa", "prompt": "plastic bottle", "material": "plastic"},
    {"nome": "Lata", "prompt": "can", "material": "metal"},
]


def test_estado_preserva_colunas_extras_e_gera_revisadas(tmp_path):
    (tmp_path / "labels").mkdir()
    (tmp_path / "labels" / "a.txt").write_text("")
    colunas = ["nome", "status", "lote"]
    linhas = {
        "a.jpg": {"nome": "a.jpg", "status": "revisada", "lote": "1"},
        "b.jpg": {"nome": "b.jpg", "status": "revisada", "lote": "1"},  # sem labels/
        "c.jpg": {"nome": "c.jpg", "status": "pendente", "lote": "2"},
    }
    formato.gravar_estado(tmp_path, colunas, linhas)
    assert formato.ler_estado(tmp_path) == (colunas, linhas)
    assert (tmp_path / "revisadas.txt").read_text() == "./images/a.jpg\n"
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".")]  # sem temporários


def test_estado_vazio_e_invalido(tmp_path):
    assert formato.ler_estado(tmp_path) == (["nome", "status"], {})
    (tmp_path / "imagens.csv").write_text("nome\na.jpg\n")
    with pytest.raises(ValueError, match="status"):
        formato.ler_estado(tmp_path)
    (tmp_path / "imagens.csv").write_text("nome,status\na.jpg,pendente\na.jpg,revisada\n")
    with pytest.raises(ValueError, match="repetida"):
        formato.ler_estado(tmp_path)


def test_registrar_imagem_mantem_status_e_recusa_colisao():
    linhas = {"a.jpg": {"nome": "a.jpg", "status": "revisada"}}
    formato.registrar_imagem(linhas, "a.jpg")
    formato.registrar_imagem(linhas, "b.png")
    assert linhas["a.jpg"]["status"] == "revisada"
    assert linhas["b.png"] == {"nome": "b.png", "status": "pendente"}
    with pytest.raises(ValueError, match="colide"):
        formato.registrar_imagem(linhas, "a.png")


def test_proposta_em_pixels_volta_a_mesma_linha_yolo(tmp_path):
    deteccoes = [(1, 0.876543, (0.123457, 0.2, 0.654321, 0.9)), (0, 0.4, (0.0, 0.0, 1.0, 1.0))]
    proposta = formato.montar_proposta("falso", "v1", {"p": 1}, CLASSES, "foto.jpg",
                                       (4032, 3024), deteccoes)
    assert proposta["caixas"][0] == {"classe": "Lata", "confianca": 0.8765,
                                     "caixa": [497.7786, 604.8, 2638.2223, 2721.6]}
    assert proposta["classes"] == formato.hash_classes(CLASSES)
    formato.gravar_proposta(tmp_path, proposta)
    caminho = tmp_path / "propostas" / "falso" / "foto.json"
    lida = formato.ler_proposta(caminho)
    assert lida == json.loads(json.dumps(proposta))
    normalizadas = formato.caixas_normalizadas(lida)
    assert [n[0] for n in normalizadas] == ["Lata", "Garrafa"]
    for (classe, _, caixa), (_, _, original) in zip(normalizadas, deteccoes):
        assert formato.linha_yolo(0, caixa) == formato.linha_yolo(0, original)


def test_ler_proposta_invalida(tmp_path):
    caminho = tmp_path / "x.json"
    caminho.write_text('{"anotador": "a"}')
    with pytest.raises(ValueError, match="x.json"):
        formato.ler_proposta(caminho)


def test_hash_classes_muda_com_a_ordem():
    assert formato.hash_classes(CLASSES) != formato.hash_classes(CLASSES[::-1])


def gravar(saida, anotador, nome, deteccoes):
    formato.gravar_proposta(saida, formato.montar_proposta(
        anotador, "v1", {}, CLASSES, nome, (100, 50), deteccoes))


def escrever_data_yaml(saida, nomes):
    (saida / "data.yaml").write_text(json.dumps({"names": dict(enumerate(nomes))}),
                                     encoding="utf-8")


def test_aceitar_so_pendentes_e_escolhidas(tmp_path):
    (tmp_path / "labels").mkdir()
    linhas = {n: {"nome": n, "status": s} for n, s in
              [("a.jpg", "pendente"), ("b.jpg", "pendente"), ("c.jpg", "descartada"),
               ("d.jpg", "pendente")]}
    formato.gravar_estado(tmp_path, ["nome", "status"], linhas)
    escrever_data_yaml(tmp_path, ["Fundo", "Garrafa", "Lata"])
    for nome in ("a.jpg", "b.jpg", "c.jpg"):  # d.jpg sem proposta
        gravar(tmp_path, "falso", nome, [(1, 0.9, (0.1, 0.2, 0.5, 0.6))])
    gravar(tmp_path, "outro", "d.jpg", [])

    assert formato.aceitar(tmp_path, "falso", {"a.jpg"}) == 1
    assert formato.aceitar(tmp_path, "falso") == 1  # só b.jpg sobra
    _, estado = formato.ler_estado(tmp_path)
    assert {n: l["status"] for n, l in estado.items()} == {
        "a.jpg": "revisada", "b.jpg": "revisada", "c.jpg": "descartada", "d.jpg": "pendente"}
    assert (tmp_path / "labels" / "a.txt").read_text() == \
        "2 0.300000 0.400000 0.400000 0.400000\n"
    assert not (tmp_path / "labels" / "c.txt").exists()
    assert (tmp_path / "revisadas.txt").read_text() == "./images/a.jpg\n./images/b.jpg\n"
    assert formato.anotadores(tmp_path) == ["falso", "outro"]


def test_aceitar_recusa_classe_desconhecida(tmp_path):
    formato.gravar_estado(tmp_path, ["nome", "status"],
                          {"a.jpg": {"nome": "a.jpg", "status": "pendente"}})
    escrever_data_yaml(tmp_path, ["Garrafa"])
    gravar(tmp_path, "falso", "a.jpg", [(1, 0.9, (0.1, 0.2, 0.5, 0.6))])
    with pytest.raises(ValueError, match="Lata"):
        formato.aceitar(tmp_path, "falso")


def test_gravar_atomico_usa_o_modo_de_um_open_comum(tmp_path):
    formato.gravar_atomico(tmp_path / "a.txt", "x")
    (tmp_path / "b.txt").write_text("x")
    assert stat.S_IMODE(os.stat(tmp_path / "a.txt").st_mode) == \
        stat.S_IMODE(os.stat(tmp_path / "b.txt").st_mode)
