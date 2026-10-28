"""Testes das funções do avaliar.py que não dependem do modelo."""

import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import avaliar  # noqa: E402

NOMES_DATASET = ["Battery", "Clear plastic bottle", "Drink can"]
NOMES = ["Drink can", "Clear plastic bottle"]


def test_ler_verdade_caixa_poligono_e_classes_de_fora(tmp_path):
    rotulo = tmp_path / "foto.txt"
    rotulo.write_text("1 0.5 0.5 0.2 0.4\n"
                      "2 0.1 0.2 0.3 0.2 0.3 0.6 0.1 0.6\n"
                      "\n"
                      "0 0.5 0.5 0.1 0.1\n", encoding="utf-8")
    verdade, fora = avaliar.ler_verdade(rotulo, NOMES_DATASET, NOMES)
    assert [c for c, _ in verdade] == [1, 0]
    assert verdade[0][1] == pytest.approx((0.4, 0.3, 0.6, 0.7))
    assert verdade[1][1] == pytest.approx((0.1, 0.2, 0.3, 0.6))
    assert fora == Counter({"Battery": 1})


def test_ler_verdade_recusa_linha_invalida(tmp_path):
    rotulo = tmp_path / "foto.txt"
    rotulo.write_text("1 0.5 0.5 0.2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inválida"):
        avaliar.ler_verdade(rotulo, NOMES_DATASET, NOMES)


def test_nomes_do_dataset_na_pasta_de_cima_e_como_dicionario(tmp_path):
    split = tmp_path / "validation"
    split.mkdir()
    (tmp_path / "data.yaml").write_text("names: {0: a, 1: b}\n", encoding="utf-8")
    assert avaliar.nomes_do_dataset(split) == ["a", "b"]
    with pytest.raises(ValueError, match="data.yaml"):
        avaliar.nomes_do_dataset(tmp_path / "outra" / "validation")


def test_consulta_mais_proxima():
    caixas = [(0, 0, 0.1, 0.1), (0.4, 0.4, 0.6, 0.6), (0.45, 0.4, 0.6, 0.6)]
    indice, iou = avaliar.consulta_mais_proxima(caixas, (0.4, 0.4, 0.6, 0.6))
    assert indice == 1 and iou == pytest.approx(1)


def test_casar_exige_classe_e_casa_cada_verdadeira_uma_vez():
    verdade = [(0, (0.1, 0.1, 0.3, 0.3)), (1, (0.5, 0.5, 0.9, 0.9))]
    deteccoes = [
        (0, 0.9, (0.1, 0.1, 0.3, 0.3)),     # acerto
        (0, 0.8, (0.1, 0.1, 0.31, 0.3)),    # mesma caixa de novo: falso positivo
        (0, 0.7, (0.5, 0.5, 0.9, 0.9)),     # lugar certo, classe errada
    ]
    assert avaliar.casar(deteccoes, verdade) == (1, 2, 1)
    assert avaliar.casar([], verdade) == (0, 0, 2)
