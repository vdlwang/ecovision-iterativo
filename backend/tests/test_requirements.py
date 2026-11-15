"""Os requirements do backend têm versões fixas, e o ambiente as respeita."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
ARQUIVOS = ["requirements.txt", "requirements-dev.txt"]


def dependencias(nome_arquivo):
    """(pacote, versão) de cada linha do arquivo, sem comentários nem -r"""
    deps = []
    for linha in (BACKEND_DIR / nome_arquivo).read_text(encoding="utf-8").splitlines():
        linha = linha.split("#", 1)[0].strip()
        if not linha or linha.startswith("-r"):
            continue
        assert "==" in linha, f"{nome_arquivo}: versão não fixada em '{linha}'"
        pacote, versao = linha.split("==", 1)
        deps.append((pacote.strip(), versao.strip()))
    return deps


@pytest.mark.parametrize("nome_arquivo", ARQUIVOS)
def test_todas_as_versoes_fixadas(nome_arquivo):
    assert dependencias(nome_arquivo), f"{nome_arquivo} sem dependências"


@pytest.mark.parametrize(
    "pacote, versao",
    [dep for arq in ARQUIVOS for dep in dependencias(arq)],
)
def test_versao_instalada_igual_a_fixada(pacote, versao):
    try:
        instalada = version(pacote)
    except PackageNotFoundError:
        pytest.skip(f"{pacote} não instalado")
    # Builds CUDA do torch têm sufixo local (2.14.1+cu128), que o pip aceita no ==
    assert instalada.split("+", 1)[0] == versao
