"""Testes do revisar.py, com o servidor numa thread e propostas sintéticas."""

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import revisar  # noqa: E402
import saida as formato  # noqa: E402

CLASSES = [
    {"nome": "Garrafa", "prompt": "plastic bottle", "material": "plastic"},
    {"nome": "Lata", "prompt": "can", "material": "metal"},
]


def proposta(nome, caixas):
    return {"anotador": "falso", "versao": "v1", "imagem": nome, "largura": 40, "altura": 20,
            "caixas": [{"classe": c, "confianca": conf, "caixa": [4, 2, 20, 10]}
                       for c, conf in caixas]}


@pytest.fixture
def saida(tmp_path):
    for pasta in ("images", "labels"):
        (tmp_path / pasta).mkdir()
    (tmp_path / "data.yaml").write_text(
        yaml.safe_dump({"names": {0: "Garrafa", 1: "Lata"}}), encoding="utf-8")
    for nome in ("a.jpg", "b c.png", "d.jpg", "e.jpg", "f.jpg"):
        Image.new("RGB", (40, 20)).save(tmp_path / "images" / nome)
    (tmp_path / "images" / "fora.jpg").write_bytes(b"")   # fora do imagens.csv
    (tmp_path / "segredo.txt").write_text("não deve sair")
    formato.gravar_estado(tmp_path, ["nome", "status"], {
        n: {"nome": n, "status": s} for n, s in [
            ("a.jpg", "pendente"), ("b c.png", "pendente"), ("d.jpg", "pendente"),
            ("e.jpg", "revisada"), ("f.jpg", "descartada")]})
    formato.gravar_proposta(tmp_path, proposta("a.jpg", [("Lata", 0.9), ("Garrafa", 0.6)]))
    formato.gravar_proposta(tmp_path, proposta("b c.png", [("Lata", 0.3)]))
    formato.gravar_proposta(tmp_path, proposta("d.jpg", []))
    (tmp_path / "labels" / "e.txt").write_text("1 0.5 0.5 0.2 0.4\n")
    return tmp_path


@pytest.fixture
def servidor(saida):
    srv = revisar.criar_servidor(saida, CLASSES, porta=0)
    thread = threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def pedir(url):
    """(status, tipo, corpo) sem levantar exceção nos erros HTTP."""
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.headers["Content-Type"], r.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.headers["Content-Type"], erro.read()


def pedir_json(url):
    status, tipo, corpo = pedir(url)
    assert tipo.startswith("application/json")
    return status, json.loads(corpo)


def test_pagina(servidor):
    status, tipo, corpo = pedir(servidor + "/")
    assert status == 200 and tipo.startswith("text/html")
    assert b"/api/imagens" in corpo


def test_classes_com_material(servidor):
    assert pedir_json(servidor + "/api/classes") == (200, [
        {"id": 0, "nome": "Garrafa", "material": "plastic"},
        {"id": 1, "nome": "Lata", "material": "metal"}])


def test_fila_pendentes_mais_incertas_antes(servidor):
    status, dados = pedir_json(servidor + "/api/imagens")
    assert status == 200
    assert [i["nome"] for i in dados["imagens"]] == ["d.jpg", "b c.png", "a.jpg"]
    a = dados["imagens"][2]
    assert a == {"nome": "a.jpg", "status": "pendente", "anotadores": ["falso"],
                 "n_caixas": {"falso": 2}, "confianca_min": 0.6, "tem_final": False}
    assert dados["anotadores"] == ["falso"]
    assert dados["contagem"] == {"pendente": 3, "revisada": 1, "descartada": 1}


def test_fila_filtro_e_ordem(servidor):
    _, dados = pedir_json(servidor + "/api/imagens?status=todas&ordem=nome")
    assert [i["nome"] for i in dados["imagens"]] == ["a.jpg", "b c.png", "d.jpg", "e.jpg",
                                                     "f.jpg"]
    _, dados = pedir_json(servidor + "/api/imagens?status=revisada")
    assert [(i["nome"], i["tem_final"], i["anotadores"]) for i in dados["imagens"]] == [
        ("e.jpg", True, [])]
    assert pedir_json(servidor + "/api/imagens?status=aprovada")[0] == 400
    assert pedir_json(servidor + "/api/imagens?ordem=data")[0] == 400


def test_detalhe_da_imagem(servidor):
    status, dados = pedir_json(servidor + "/api/imagens/b%20c.png")
    assert status == 200
    assert dados == {
        "nome": "b c.png", "status": "pendente", "final": None, "invalidas": 0,
        "propostas": {"falso": [{"id": 1, "nome": "Lata", "conf": 0.3,
                                 "caixa": [0.1, 0.1, 0.5, 0.5]}]},
        "largura": 40, "altura": 20, "revisao": None}
    _, dados = pedir_json(servidor + "/api/imagens/e.jpg")
    assert dados["final"] == [{"id": 1, "nome": "Lata", "conf": None,
                               "caixa": [0.4, 0.3, 0.6, 0.7]}]


def test_imagem(servidor):
    status, tipo, corpo = pedir(servidor + "/images/b%20c.png")
    assert status == 200 and tipo == "image/png" and corpo.startswith(b"\x89PNG")


@pytest.mark.parametrize("rota", [
    "/images/fora.jpg", "/api/imagens/fora.jpg", "/images/..%2Fsegredo.txt",
    "/images/../segredo.txt", "/api/imagens/..%2Fdata.yaml", "/images/", "/nada"])
def test_404_fora_do_csv_e_fora_da_saida(servidor, rota):
    status, _, corpo = pedir(servidor + rota)
    assert status == 404, rota
    assert b"n\xc3\xa3o deve sair" not in corpo


def test_main_recusa_saida_sem_imagens_csv(tmp_path):
    (tmp_path / "data.yaml").write_text("names: {0: a}\n")
    with pytest.raises(ValueError, match="imagens.csv"):
        revisar.main([str(tmp_path)])
