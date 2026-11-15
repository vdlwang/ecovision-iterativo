from pathlib import Path

import numpy as np
import pytest

from deteccao import (
    DETECTION_COOLDOWN, taco_to_material, map_taco_to_material,
    deteccoes_do_quadro, angulo_a_disparar,
)

# Os valores padrão de load_config() que importam aqui
CONFIG = {
    "roi_y_min": 0.45,
    "roi_y_max": 0.55,
    "class_to_angle": {"plastic": 50, "metal": 150, "glass": 130, "paper": 110},
}
ALTURA = 480
MODELO_PADRAO = Path(__file__).resolve().parents[2] / "yolo_models/taco/best.pt"


def deteccao(material="plastic", cy_norm=0.5):
    """Detecção com caixa de 40 px centrada em cy_norm"""
    cy = cy_norm * ALTURA
    return {"class": "x", "material": material, "confidence": 0.9,
            "bbox": [100.0, cy - 20, 200.0, cy + 20]}


# ==== map_taco_to_material ====

@pytest.mark.parametrize("classe, material", [
    ("drink can", "metal"),
    ("glass bottle", "glass"),
    ("corrugated carton", "paper"),
    ("clear plastic bottle", "plastic"),
    ("carded blister pack", "other"),
    ("cigarette", "other"),
])
def test_mapa_exemplos(classe, material):
    assert map_taco_to_material(classe) == material


def test_mapa_ignora_caixa_e_espacos():
    assert map_taco_to_material("  Drink Can ") == "metal"


def test_mapa_classe_desconhecida_vira_other():
    assert map_taco_to_material("Background") == "other"
    assert map_taco_to_material("") == "other"


def test_mapa_so_tem_materiais_validos():
    assert set(taco_to_material.values()) <= {"plastic", "metal", "glass", "paper", "other"}


def test_todas_as_classes_do_modelo_padrao_estao_mapeadas():
    """Cada classe do best.pt (fora o Background) tem entrada explícita na tabela"""
    ultralytics = pytest.importorskip("ultralytics")
    if not MODELO_PADRAO.exists():
        pytest.skip(f"{MODELO_PADRAO} não encontrado")
    nomes = ultralytics.YOLO(str(MODELO_PADRAO)).names.values()
    faltando = [n for n in nomes if n != "Background" and n.strip().lower() not in taco_to_material]
    assert faltando == []


# ==== deteccoes_do_quadro ====

def test_quadro_converte_caixas():
    dets = deteccoes_do_quadro(
        {0: "Drink can", 1: "Glass bottle"},
        np.array([0, 1]), np.array([0.9, 0.5], dtype=np.float32),
        np.array([[1, 2, 3, 4], [5, 6, 7, 8]], dtype=np.float32),
        0.35,
    )
    assert [d["class"] for d in dets] == ["drink can", "glass bottle"]
    assert [d["material"] for d in dets] == ["metal", "glass"]
    assert dets[1]["bbox"] == [5.0, 6.0, 7.0, 8.0]
    # Tipos nativos: o resultado vai para json.dumps
    assert all(type(d["confidence"]) is float for d in dets)
    assert all(type(v) is float for d in dets for v in d["bbox"])


def test_quadro_filtra_pela_confianca():
    confs = np.array([0.2, 0.35, 0.8])
    dets = deteccoes_do_quadro({0: "Drink can"}, np.zeros(3, dtype=int), confs,
                               np.zeros((3, 4)), 0.35)
    # Igual ao limite passa
    assert [round(d["confidence"], 2) for d in dets] == [0.35, 0.8]


def test_quadro_vazio():
    assert deteccoes_do_quadro({}, np.array([]), np.array([]), np.zeros((0, 4)), 0.35) == []


# ==== angulo_a_disparar ====

def test_dispara_no_centro_da_roi():
    assert angulo_a_disparar(deteccao("metal"), ALTURA, CONFIG, False, 10.0) == 150


def test_usa_o_angulo_atual_da_config():
    config = {**CONFIG, "class_to_angle": {**CONFIG["class_to_angle"], "glass": 125}}
    assert angulo_a_disparar(deteccao("glass"), ALTURA, config, False, 10.0) == 125


@pytest.mark.parametrize("cy_norm", [0.1, 0.44, 0.56, 0.9])
def test_nao_dispara_fora_da_roi(cy_norm):
    assert angulo_a_disparar(deteccao(cy_norm=cy_norm), ALTURA, CONFIG, False, 10.0) is None


@pytest.mark.parametrize("cy_norm", [0.45, 0.55])
def test_limites_da_roi_disparam(cy_norm):
    assert angulo_a_disparar(deteccao(cy_norm=cy_norm), ALTURA, CONFIG, False, 10.0) == 50


def test_nao_dispara_material_other():
    assert angulo_a_disparar(deteccao("other"), ALTURA, CONFIG, False, 10.0) is None


def test_nao_dispara_material_sem_angulo():
    config = {**CONFIG, "class_to_angle": {"plastic": 50}}
    assert angulo_a_disparar(deteccao("paper"), ALTURA, config, False, 10.0) is None


def test_nao_dispara_ocupado():
    assert angulo_a_disparar(deteccao(), ALTURA, CONFIG, True, 10.0) is None


def test_cooldown():
    assert angulo_a_disparar(deteccao(), ALTURA, CONFIG, False, DETECTION_COOLDOWN - 0.01) is None
    assert angulo_a_disparar(deteccao(), ALTURA, CONFIG, False, DETECTION_COOLDOWN) == 50
