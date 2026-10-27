"""Testes do visualizar.py."""

import json
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import visualizar  # noqa: E402


@pytest.fixture
def saida(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "labels").mkdir()
    (tmp_path / "data.yaml").write_text(
        yaml.safe_dump({"names": {0: "Garrafa", 1: "Lata"}}), encoding="utf-8")
    for nome in ("a.jpg", "b c.png", "sem.jpg"):
        Image.new("RGB", (8, 8)).save(tmp_path / "images" / nome)
    (tmp_path / "images" / "notas.txt").write_text("não é imagem")
    (tmp_path / "labels" / "a.txt").write_text("0 0.5 0.5 0.2 0.4\n\nlixo\n1 0.1 0.1 0.1\n")
    (tmp_path / "labels" / "b c.txt").write_text("")
    return tmp_path


def test_coletar(saida):
    classes, imagens = visualizar.coletar(saida)
    assert classes == {"0": "Garrafa", "1": "Lata"}
    por_nome = {im["nome"]: im for im in imagens}
    assert set(por_nome) == {"a.jpg", "b c.png", "sem.jpg"}
    assert por_nome["a.jpg"]["caixas"] == [[0, 0.5, 0.5, 0.2, 0.4]]
    assert por_nome["a.jpg"]["invalidas"] == 2
    assert por_nome["b c.png"]["caixas"] == [] and not por_nome["b c.png"]["sem_rotulo"]
    assert por_nome["b c.png"]["src"] == "images/b%20c.png"
    assert por_nome["sem.jpg"]["sem_rotulo"]


def test_coletar_sem_data_yaml(tmp_path):
    with pytest.raises(ValueError, match="data.yaml"):
        visualizar.coletar(tmp_path)


def test_gerar_pagina_embute_dados_sem_fechar_o_script(saida):
    (saida / "data.yaml").write_text(
        yaml.safe_dump({"names": {0: "a</script>b", 1: "Lata"}}), encoding="utf-8")
    html = visualizar.gerar_pagina(saida).read_text(encoding="utf-8")
    assert "__DADOS__" not in html
    inicio = html.index("const DADOS = ") + len("const DADOS = ")
    trecho = html[inicio:html.index(";\n", inicio)]
    assert "</script>" not in trecho
    dados = json.loads(trecho.replace("<\\/", "</"))
    assert dados["classes"]["0"] == "a</script>b"
    assert len(dados["imagens"]) == 3
