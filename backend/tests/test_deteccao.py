from pathlib import Path

import numpy as np
import pytest

from deteccao import (
    ESQUECER_TRILHA_S, REIDENTIFICAR_S, DisparosPorTrilha, cruzou_a_faixa, iou,
    taco_to_material, map_taco_to_material, deteccoes_do_quadro, material_votado,
)

# Os valores padrão de load_config() que importam aqui
CONFIG = {
    "roi_y_min": 0.45,
    "roi_y_max": 0.55,
    "class_to_angle": {"plastic": 50, "metal": 150, "glass": 130, "paper": 110},
}
ALTURA = 480
MODELO_PADRAO = Path(__file__).resolve().parents[2] / "yolo_models/taco/best.pt"


def deteccao(material="plastic", cy_norm=0.5, id_trilha=1, confianca=0.9, x=100.0):
    """Detecção com caixa de 40 px de altura centrada em cy_norm, da trilha id_trilha"""
    cy = cy_norm * ALTURA
    return {"class": "x", "material": material, "confidence": confianca,
            "bbox": [x, cy - 20, x + 100.0, cy + 20], "id": id_trilha}


def passar(disparos, trilha, config=CONFIG, ocupado=False, t0=0.0, dt=0.1):
    """Passa uma sequência de quadros [(detecções)] e devolve os disparos (não None)."""
    feitos = []
    for i, dets in enumerate(trilha):
        d = disparos.quadro(dets, ALTURA, config, t0 + i * dt, ocupado)
        if d:
            feitos.append(d)
    return feitos


def descendo(material="plastic", id_trilha=1, de=0.1, ate=0.9, passos=17, **kw):
    """Uma trilha que desce o quadro de `de` a `ate`, um quadro por posição."""
    return [[deteccao(material, de + (ate - de) * i / (passos - 1), id_trilha, **kw)]
            for i in range(passos)]


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


def test_quadro_leva_o_id_da_trilha():
    dets = deteccoes_do_quadro({0: "Drink can"}, np.array([0, 0]), np.array([0.9, 0.8]),
                               np.zeros((2, 4)), 0.35, ids=np.array([7.0, 9.0]))
    assert [d["id"] for d in dets] == [7, 9]
    assert all(type(d["id"]) is int for d in dets)
    sem = deteccoes_do_quadro({0: "Drink can"}, np.array([0]), np.array([0.9]), np.zeros((1, 4)), 0.35)
    assert sem[0]["id"] is None


# ==== DisparosPorTrilha (T15) ====

def test_dispara_uma_vez_por_trilha():
    feitos = passar(DisparosPorTrilha(), descendo("metal"))
    assert [(d["id"], d["material"], d["angulo"]) for d in feitos] == [(1, "metal", 150)]


def test_dois_objetos_proximos_disparam_os_dois():
    """Antes, o segundo era ignorado pelo cooldown fixo"""
    a, b = descendo("metal", 1), descendo("paper", 2, de=0.0, ate=0.8)
    quadros = [da + db for da, db in zip(a, b)]
    disparos = DisparosPorTrilha()
    feitos = [d for i, q in enumerate(quadros)
              if (d := disparos.quadro(q, ALTURA, CONFIG, i * 0.1, False))]
    assert sorted(d["material"] for d in feitos) == ["metal", "paper"]


def test_objeto_parado_na_faixa_dispara_uma_vez():
    parado = [[deteccao(cy_norm=0.5)]] * 100  # 10 s na faixa
    assert len(passar(DisparosPorTrilha(), parado)) == 1


def test_dispara_ao_atravessar_a_faixa_sem_quadro_dentro():
    """A 12 fps, um objeto rápido pula a faixa: 0.3 → 0.7"""
    feitos = passar(DisparosPorTrilha(), [[deteccao(cy_norm=0.3)], [deteccao(cy_norm=0.7)]])
    assert len(feitos) == 1


@pytest.mark.parametrize("cy_ant, cy, esperado", [
    (None, 0.5, True), (None, 0.45, True), (None, 0.55, True),
    (None, 0.44, False), (None, 0.56, False),
    (0.3, 0.7, True), (0.7, 0.3, True), (0.1, 0.3, False), (0.6, 0.9, False),
])
def test_cruzou_a_faixa(cy_ant, cy, esperado):
    assert cruzou_a_faixa(cy_ant, cy, CONFIG) is esperado


def test_material_pela_votacao_da_trilha():
    """A classe oscila; vale a soma das confianças, não o quadro do disparo"""
    quadros = [[deteccao("metal", 0.1 + 0.05 * i, confianca=0.8)] for i in range(6)]
    quadros.append([deteccao("plastic", 0.5, confianca=0.6)])  # quadro do disparo
    feitos = passar(DisparosPorTrilha(), quadros)
    assert feitos[0]["material"] == "metal"
    assert feitos[0]["votos"]["plastic"] == pytest.approx(0.6)


def test_other_nao_vota():
    assert material_votado({"other": 5.0, "paper": 0.3}) == "paper"
    assert material_votado({"other": 5.0}) is None
    assert passar(DisparosPorTrilha(), descendo("other")) == []


def test_usa_o_angulo_atual_da_config():
    config = {**CONFIG, "class_to_angle": {**CONFIG["class_to_angle"], "glass": 125}}
    assert passar(DisparosPorTrilha(), descendo("glass"), config)[0]["angulo"] == 125


def test_material_sem_angulo_nao_dispara():
    config = {**CONFIG, "class_to_angle": {"plastic": 50}}
    assert passar(DisparosPorTrilha(), descendo("paper"), config) == []


def test_fora_da_faixa_nao_dispara():
    acima = [[deteccao(cy_norm=0.1 + 0.02 * i)] for i in range(10)]  # até 0.28
    assert passar(DisparosPorTrilha(), acima) == []


def test_sem_id_nao_dispara():
    assert passar(DisparosPorTrilha(), descendo(id_trilha=None)) == []


def test_ocupado_nao_dispara_e_conta_como_perdida_ao_sair_da_faixa():
    disparos = DisparosPorTrilha()
    quadros = descendo()  # passa pela faixa no quadro 8 (0.5)
    passar(disparos, quadros[:9], ocupado=True)
    assert disparos.perdidas_ocupado == []  # ainda na faixa
    passar(disparos, quadros[9:], ocupado=True, t0=0.9)
    assert disparos.perdidas_ocupado == [1]  # uma vez só
    disparos.quadro([], ALTURA, CONFIG, 10.0 + ESQUECER_TRILHA_S, False)
    assert disparos.perdidas_ocupado == [1] and disparos.trilhas == {}


def test_some_dentro_da_faixa_ocupada_conta_ao_ser_esquecida():
    disparos = DisparosPorTrilha()
    passar(disparos, [[deteccao(cy_norm=0.5)]], ocupado=True)
    disparos.quadro([], ALTURA, CONFIG, ESQUECER_TRILHA_S + 1, False)
    assert disparos.perdidas_ocupado == [1]


def test_cruzou_ocupado_nao_dispara_depois():
    """A trilha que passou da faixa com o servo ocupado não dispara atrasada"""
    disparos = DisparosPorTrilha()
    quadros = descendo()
    meio = len(quadros) // 2 + 2
    assert passar(disparos, quadros[:meio], ocupado=True) == []
    assert passar(disparos, quadros[meio:], t0=meio * 0.1) == []


def test_ainda_na_faixa_dispara_quando_o_servo_libera():
    disparos = DisparosPorTrilha()
    assert passar(disparos, [[deteccao(cy_norm=0.47)]], ocupado=True) == []
    assert len(passar(disparos, [[deteccao(cy_norm=0.5)]], t0=0.1)) == 1


def test_segunda_trilha_no_mesmo_quadro_conta_como_ocupada():
    disparos = DisparosPorTrilha()
    feito = disparos.quadro([deteccao("metal", 0.5, 1), deteccao("paper", 0.5, 2, x=300.0)],
                            ALTURA, CONFIG, 0.0, False)
    assert feito["id"] == 1
    assert disparos.trilhas[2]["cruzou_ocupado"]


def test_id_trocado_herda_o_disparo():
    """O rastreador perde o objeto e o acha de novo com outro ID: não dispara de novo"""
    disparos = DisparosPorTrilha()
    assert len(passar(disparos, [[deteccao(cy_norm=0.48)], [deteccao(cy_norm=0.5)]])) == 1
    # Some um quadro e volta logo abaixo, com ID novo
    novo = disparos.quadro([deteccao(cy_norm=0.52, id_trilha=2)], ALTURA, CONFIG, 0.3, False)
    assert novo is None
    assert disparos.trilhas[2]["herdou"] == 1


def test_id_novo_longe_ou_tarde_nao_herda():
    disparos = DisparosPorTrilha()
    passar(disparos, [[deteccao(cy_norm=0.5)]])
    # Outro objeto ao lado (sem sobreposição), logo depois: dispara
    assert disparos.quadro([deteccao(cy_norm=0.5, id_trilha=2, x=400.0)], ALTURA, CONFIG, 0.2, False)
    # Na mesma posição, mas depois de REIDENTIFICAR_S: é outro objeto
    assert disparos.quadro([deteccao(cy_norm=0.5, id_trilha=3)], ALTURA, CONFIG,
                           REIDENTIFICAR_S + 0.5, False)


def test_reiniciar_esquece_as_trilhas():
    disparos = DisparosPorTrilha()
    passar(disparos, descendo())
    disparos.reiniciar()
    # Câmera reaberta: o rastreador recomeça os IDs, e o ID 1 é outro objeto
    assert len(passar(disparos, descendo(), t0=100.0)) == 1


def test_iou():
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert iou([0, 0, 10, 10], [5, 0, 15, 10]) == pytest.approx(1 / 3)
