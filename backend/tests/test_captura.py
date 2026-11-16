import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from PIL import Image

from captura import (
    PADROES_CAPTURA, TAG_DATETIME_ORIGINAL, TAG_IFD_EXIF, TAG_OFFSET_TIME_ORIGINAL,
    TAG_SUBSEC_TIME_ORIGINAL, Capturador, carimbo, completar_config, deve_capturar,
    diferenca_quadros, miniatura,
)

CFG = {**PADROES_CAPTURA, "intervalo_s": 10.0, "travessia_s": 5.0, "diferenca_minima": 10.0}
HORARIO = datetime(2026, 11, 15, 23, 29, 3, 146000, tzinfo=timezone.utc)


def quadro(valor=0, h=480, w=640):
    return np.full((h, w, 3), valor, dtype=np.uint8)


# ==== deve_capturar ====

def test_primeira_captura_com_motor_ligado_espera_travessia():
    assert not deve_capturar(104.0, None, ligado_desde=100.0, diferenca=None, cfg=CFG)
    assert deve_capturar(105.0, None, ligado_desde=100.0, diferenca=None, cfg=CFG)


def test_intervalo_minimo_entre_capturas():
    assert not deve_capturar(119.9, 110.0, ligado_desde=100.0, diferenca=None, cfg=CFG)
    assert deve_capturar(120.0, 110.0, ligado_desde=100.0, diferenca=None, cfg=CFG)


def test_motor_ligado_ignora_diferenca():
    assert deve_capturar(120.0, 110.0, ligado_desde=100.0, diferenca=0.0, cfg=CFG)


def test_religar_espera_travessia_mesmo_com_intervalo_cumprido():
    # última captura há muito tempo, mas o motor acabou de ligar
    assert not deve_capturar(200.0, 100.0, ligado_desde=198.0, diferenca=None, cfg=CFG)


def test_motor_desligado_depende_da_diferenca():
    assert not deve_capturar(120.0, 100.0, ligado_desde=None, diferenca=9.9, cfg=CFG)
    assert deve_capturar(120.0, 100.0, ligado_desde=None, diferenca=10.0, cfg=CFG)
    # sem quadro anterior para comparar
    assert deve_capturar(120.0, None, ligado_desde=None, diferenca=None, cfg=CFG)


def test_motor_desligado_tambem_respeita_intervalo():
    assert not deve_capturar(105.0, 100.0, ligado_desde=None, diferenca=200.0, cfg=CFG)


# ==== miniatura e diferença ====

def test_miniatura_reduz_e_converte_para_cinza():
    m = miniatura(quadro(90, 1080, 1920))
    assert max(m.shape) <= 64 and m.ndim == 2
    assert m.mean() == pytest.approx(90)


def test_diferenca():
    a, b = miniatura(quadro(0)), miniatura(quadro(30))
    assert diferenca_quadros(a, a) == 0
    assert diferenca_quadros(a, b) == pytest.approx(30)
    assert diferenca_quadros(a, None) is None
    assert diferenca_quadros(a, miniatura(quadro(0, 720, 1280))) is None


def test_completar_config():
    cfg = completar_config({"intervalo_s": 3})
    assert cfg["intervalo_s"] == 3 and cfg["travessia_s"] == PADROES_CAPTURA["travessia_s"]
    assert completar_config(None) == PADROES_CAPTURA


def test_carimbo_em_utc():
    local = HORARIO.astimezone(timezone(timedelta(hours=-3)))
    assert carimbo(local) == "20261115T232903.146Z"


# ==== Capturador ====

def ler_jsonl(pasta):
    return [json.loads(l) for l in (pasta / "captura.jsonl").read_text(encoding="utf-8").splitlines()]


def test_grava_quadro_com_exif_e_registro(tmp_path):
    cap = Capturador(tmp_path, CFG, {"camera_index": 0})
    q = quadro(0)
    q[:, :, 2] = 255  # vermelho em BGR
    assert cap.quadro(q, 105.0, HORARIO, ligado_desde=100.0, info={"fps": 12})
    cap.fechar()

    [sessao] = list(tmp_path.iterdir())
    assert sessao.name == "20261115T232903"
    imagem = Image.open(sessao / "20261115T232903.146Z.jpg")
    assert imagem.size == (640, 480)
    r, g, b = imagem.convert("RGB").getpixel((10, 10))
    assert r > 200 and g < 50 and b < 50
    ifd = imagem.getexif().get_ifd(TAG_IFD_EXIF)
    assert ifd[TAG_DATETIME_ORIGINAL] == "2026:11:15 23:29:03"
    assert ifd[TAG_SUBSEC_TIME_ORIGINAL] == "146"
    assert ifd[TAG_OFFSET_TIME_ORIGINAL] == "+00:00"

    cabecalho, linha = ler_jsonl(sessao)
    assert cabecalho["tipo"] == "sessao" and cabecalho["camera_index"] == 0
    assert cabecalho["captura"]["intervalo_s"] == 10.0
    assert linha == {"tipo": "quadro", "arquivo": "20261115T232903.146Z.jpg",
                     "horario": "2026-11-15T23:29:03.146000+00:00", "largura": 640,
                     "altura": 480, "motor_ligado": True, "diferenca": None, "fps": 12}


def test_esteira_ligada_grava_a_cada_intervalo(tmp_path):
    cap = Capturador(tmp_path, CFG)
    gravados = [t for t in np.arange(100.0, 140.0, 0.5)
                if cap.quadro(quadro(0), t, HORARIO + timedelta(seconds=t), ligado_desde=100.0)]
    cap.fechar()
    assert gravados == [105.0, 115.0, 125.0, 135.0]
    assert cap.sessao.gravados == 4


def test_esteira_parada_grava_so_quando_muda(tmp_path):
    cap = Capturador(tmp_path, CFG)
    valores = [0, 0, 5, 5, 60, 60, 60]  # cena muda no quadro 4
    gravados = [i for i, v in enumerate(valores)
                if cap.quadro(quadro(v), 100.0 + 20 * i, HORARIO + timedelta(seconds=20 * i),
                              ligado_desde=None)]
    cap.fechar()
    assert gravados == [0, 4]


def test_sem_captura_nao_cria_pasta(tmp_path):
    cap = Capturador(tmp_path / "capturas", CFG)
    assert not cap.quadro(quadro(0), 101.0, HORARIO, ligado_desde=100.0)
    cap.fechar()
    assert not (tmp_path / "capturas").exists()


def test_fila_cheia_descarta(tmp_path, monkeypatch):
    import captura
    monkeypatch.setattr(captura, "TAMANHO_FILA", 1)
    cap = Capturador(tmp_path, {**CFG, "intervalo_s": 0.0})
    # trava a thread de gravação para a fila encher
    cap.quadro(quadro(0), 105.0, HORARIO, ligado_desde=100.0)
    sessao = cap.sessao
    sessao.fila.put(None)  # encerra o laço: os próximos ficam na fila
    sessao.thread.join()
    assert cap.quadro(quadro(0), 106.0, HORARIO + timedelta(seconds=1), ligado_desde=100.0)
    assert not cap.quadro(quadro(0), 107.0, HORARIO + timedelta(seconds=2), ligado_desde=100.0)
    assert sessao.descartados == 1
    # o descartado não conta como captura
    assert cap.ultima_captura == 106.0
