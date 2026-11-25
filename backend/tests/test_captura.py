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

CFG = {**PADROES_CAPTURA, "intervalo_s": 10.0, "travessia_s": 5.0, "atraso_s": 1.0,
       "diferenca_minima": 10.0, "aprendizado_s": 5.0, "margem_teto": 20.0}
HORARIO = datetime(2026, 11, 15, 23, 29, 3, 146000, tzinfo=timezone.utc)


def quadro(valor=0, h=480, w=640):
    return np.full((h, w, 3), valor, dtype=np.uint8)


# ==== deve_capturar ====

def test_motor_ligado_so_com_objeto_pronto():
    assert not deve_capturar(120.0, None, ligado_desde=100.0, diferenca=None, cfg=CFG)
    assert deve_capturar(120.0, None, ligado_desde=100.0, diferenca=None, cfg=CFG,
                         objeto_pronto=True)


def test_intervalo_minimo_entre_capturas():
    assert not deve_capturar(119.9, 110.0, ligado_desde=100.0, diferenca=None, cfg=CFG,
                             objeto_pronto=True)
    assert deve_capturar(120.0, 110.0, ligado_desde=100.0, diferenca=None, cfg=CFG,
                         objeto_pronto=True)


def test_motor_ligado_ignora_diferenca():
    assert not deve_capturar(120.0, 110.0, ligado_desde=100.0, diferenca=200.0, cfg=CFG)


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


def cena(fundo=40, objeto=None, altura=480, largura=640):
    """Lona uniforme, com um objeto claro opcional (valor) no quarto de cima à esquerda."""
    q = np.full((altura, largura, 3), fundo, dtype=np.float32)
    if objeto is not None:
        q[: altura // 2, : largura // 2] = objeto
    return q


def test_diferenca():
    a, b = miniatura(cena(40)), miniatura(cena(40, objeto=200))
    assert diferenca_quadros(a, a) == 0
    assert diferenca_quadros(a, b) > 50
    assert diferenca_quadros(a, None) is None
    assert diferenca_quadros(a, miniatura(cena(40, altura=720, largura=1280))) is None


def test_diferenca_ignora_mudanca_global_de_brilho():
    # exposição automática: o mesmo quadro 1,5 vez mais claro não é cena nova
    a = miniatura(cena(40, objeto=120))
    b = miniatura(cena(60, objeto=180))
    assert diferenca_quadros(a, b) == pytest.approx(0, abs=1e-3)


def test_diferenca_objeto_novo_com_exposicao_mudada():
    # objeto posto e a câmera escurecendo o quadro em resposta: ainda é cena nova
    a = miniatura(cena(60))
    b = miniatura(cena(40, objeto=220))
    assert diferenca_quadros(a, b) > 10


def test_diferenca_quadro_preto_nao_escala():
    # quase preto (luz apagada): compara sem escalar, sem amplificar ruído
    a, b = miniatura(cena(0)), miniatura(cena(1))
    assert diferenca_quadros(a, b) == pytest.approx(1)


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
    # motor desligado: o primeiro quadro é gravado (não há anterior para comparar)
    assert cap.quadro(q, 105.0, HORARIO, ligado_desde=None, info={"fps": 12})
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
                     "altura": 480, "origem": "automatica", "motor_ligado": False,
                     "diferenca": None, "ocupacao": None, "fps": 12}


# ==== motor ligado: captura por objeto novo na lona ====

VAZIA = cena(40).astype(np.uint8)
OBJETO = cena(40, objeto=200).astype(np.uint8)  # ocupa um quarto do quadro


def rodar(cap, roteiro, ligado_desde=0.0, passo=0.1):
    """roteiro: [(início, fim, quadro)] em segundos; devolve os instantes gravados."""
    gravados = []
    for inicio, fim, q in roteiro:
        for t in np.arange(inicio, fim - 1e-9, passo):
            t = round(float(t), 3)
            if cap.quadro(q, t, HORARIO + timedelta(seconds=t), ligado_desde=ligado_desde):
                gravados.append(t)
    return gravados


def test_objeto_novo_grava_atraso_depois():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True  # só a decisão
    gravados = rodar(cap, [(0, 20, VAZIA), (20, 23, OBJETO), (23, 30, VAZIA)])
    assert gravados == [21.0]  # entrou em 20,0; atraso_s 1,0


def test_lona_vazia_nao_grava():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    assert rodar(cap, [(0, 60, VAZIA)]) == []


def test_variacao_de_brilho_dentro_da_margem_nao_e_objeto():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    mais_clara = cena(55).astype(np.uint8)  # 15 acima do teto; margem 20
    assert rodar(cap, [(0, 6, VAZIA), (6, 10, mais_clara), (10, 15, VAZIA)]) == []


def test_aprendizado_nao_grava():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    # nos primeiros aprendizado_s (5 s) nada é objeto; depois, é
    assert rodar(cap, [(0, 2, VAZIA), (2, 4, OBJETO), (4, 8, VAZIA)]) == []
    assert cap.lona.aprendida


def test_aprendizado_so_conta_com_motor_ligado():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    cap.cfg = {**cap.cfg, "diferenca_minima": 1e9}  # só a lona importa
    rodar(cap, [(0, 10, VAZIA)], ligado_desde=None)
    assert not cap.lona.aprendida and cap.lona.teto is None
    rodar(cap, [(10, 16, VAZIA)], ligado_desde=10.0)
    assert cap.lona.aprendida


def lona_andando(t, objeto=False, velocidade=160):
    """
    Lona não uniforme (textura, emenda escura, mancha clara) que anda para a
    direita, sob uma luz fixa mais forte no centro; volta em 640/160 = 4 s.
    """
    rng = np.random.default_rng(7)
    faixa = rng.uniform(25, 60, 640)
    faixa[100:120] = 8     # emenda
    faixa[400:430] = 95    # mancha
    luz = 0.7 + 0.6 * np.exp(-((np.arange(640) - 320) / 200) ** 2)
    linha = np.roll(faixa, int(round(t * velocidade))) * luz
    q = np.repeat(linha[None, :, None], 480, axis=0).repeat(3, axis=2)
    if objeto:
        q[150:330, 250:400] = 200
    return np.clip(q, 0, 255).astype(np.uint8)


def test_lona_irregular_andando_so_grava_objeto():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    gravados = []
    for t in np.arange(0, 40, 0.1):
        t = round(float(t), 3)
        q = lona_andando(t, objeto=20 <= t < 23)
        if cap.quadro(q, t, HORARIO + timedelta(seconds=t), ligado_desde=0.0):
            gravados.append(t)
    assert gravados == [21.0]


def test_objeto_dentro_do_intervalo_nao_grava():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: (setattr(cap, "ultima_captura", a[1]) or True)
    roteiro = [(0, 8, VAZIA), (8, 11, OBJETO), (11, 13, VAZIA),
               (13, 16, OBJETO),  # entra 4 s depois da captura (Δ = 10): não grava
               (16, 25, VAZIA), (25, 28, OBJETO), (28, 30, VAZIA)]
    assert rodar(cap, roteiro) == [9.0, 26.0]


def test_objeto_que_sai_antes_do_atraso_nao_grava():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    assert rodar(cap, [(0, 8, VAZIA), (8, 8.5, OBJETO), (8.5, 12, VAZIA)]) == []


def test_objeto_parado_ao_ligar_nao_e_novo():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    # posto com o motor desligado (o ramo da diferença é desligado aqui: só a lona importa)
    cap.cfg = {**cap.cfg, "diferenca_minima": 1e9}
    rodar(cap, [(0, 6, VAZIA)], ligado_desde=0.0)
    rodar(cap, [(6, 8, VAZIA), (8, 10, OBJETO)], ligado_desde=None)
    assert rodar(cap, [(10, 12, OBJETO), (12, 20, VAZIA)], ligado_desde=10.0) == []


def test_teto_baixo_e_aprendido_de_novo():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    # a luz sobe depois do aprendizado: a lona vazia passa do teto, fica
    # "ocupada" por mais de 3 × travessia_s (15 s, até 21 s), o teto é aprendido
    # de novo (5 s) e o objeto seguinte é capturado
    clara, objeto = cena(80).astype(np.uint8), cena(80, objeto=200).astype(np.uint8)
    gravados = rodar(cap, [(0, 6, VAZIA), (6, 30, clara), (30, 33, objeto)])
    assert gravados == [7.0, 31.0]  # 7,0: a luz subindo em 6 s parece objeto entrando


def test_objeto_no_aprendizado_sobe_o_teto():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    # o objeto do aprendizado (200) esconde outro igual no mesmo lugar, não um mais claro
    roteiro = [(0, 2, VAZIA), (2, 4, OBJETO), (4, 15, VAZIA), (15, 18, OBJETO),
               (18, 30, VAZIA), (30, 33, cena(40, objeto=250).astype(np.uint8))]
    assert rodar(cap, roteiro) == [31.0]


def test_ligar_automatica_e_mudar_camera_aprendem_de_novo():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    rodar(cap, [(0, 6, VAZIA)])
    assert cap.lona.aprendida
    cap.reaprender_lona("exposicao da câmera mudou")
    assert not cap.lona.aprendida
    rodar(cap, [(6, 12, VAZIA)])
    cap.definir_automatica(False)
    cap.definir_automatica(True)
    assert not cap.lona.aprendida


def test_desligar_automatica_cancela_pendente():
    cap = Capturador("/nao/usado", CFG)
    cap._gravar = lambda *a: True
    rodar(cap, [(0, 8, VAZIA), (8, 8.5, OBJETO)])
    assert cap.pendente_em is not None
    cap.definir_automatica(False)
    rodar(cap, [(8.5, 9.0, OBJETO)])
    cap.definir_automatica(True)
    # religada, aprende a lona de novo: o objeto que ficou não é gravado
    assert rodar(cap, [(9.0, 11, OBJETO)]) == []


# ==== motor desligado ====


def test_esteira_parada_grava_so_quando_muda(tmp_path):
    cap = Capturador(tmp_path, CFG)
    # lona vazia; a mesma, mais clara (exposição automática); objeto posto no quadro 4
    quadros = [cena(40), cena(40), cena(42), cena(60), cena(40, objeto=200),
               cena(40, objeto=200), cena(42, objeto=210)]
    gravados = [i for i, q in enumerate(quadros)
                if cap.quadro(q.astype(np.uint8), 100.0 + 20 * i,
                              HORARIO + timedelta(seconds=20 * i), ligado_desde=None)]
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
    # trava a thread de gravação para a fila encher (motor desligado, cena alternando)
    cap.quadro(VAZIA, 105.0, HORARIO, ligado_desde=None)
    sessao = cap.sessao
    sessao.fila.put(None)  # encerra o laço: os próximos ficam na fila
    sessao.thread.join()
    assert cap.quadro(OBJETO, 106.0, HORARIO + timedelta(seconds=1), ligado_desde=None)
    assert not cap.quadro(VAZIA, 107.0, HORARIO + timedelta(seconds=2), ligado_desde=None)
    assert sessao.descartados == 1
    # o descartado não conta como captura
    assert cap.ultima_captura == 106.0


# ==== automática ligada/desligada e captura manual (Monitor) ====

def test_automatica_desligada_nao_grava_nem_cria_pasta(tmp_path):
    cap = Capturador(tmp_path / "capturas", CFG, automatica=False)
    assert not cap.quadro(quadro(0), 105.0, HORARIO, ligado_desde=100.0)
    cap.fechar()
    assert not (tmp_path / "capturas").exists()
    assert cap.gravados == 0


def test_manual_grava_sem_esperar_intervalo_nem_travessia(tmp_path):
    cap = Capturador(tmp_path, CFG, automatica=False)
    assert cap.manual(quadro(0), 100.5, HORARIO, ligado_desde=100.0) == "20261115T232903.146Z.jpg"
    assert cap.manual(quadro(0), 101.0, HORARIO + timedelta(seconds=0.5), ligado_desde=100.0)
    cap.fechar()
    [sessao] = list(tmp_path.iterdir())
    cabecalho, *linhas = ler_jsonl(sessao)
    assert cabecalho["captura"]["automatica"] is False
    assert [l["origem"] for l in linhas] == ["manual", "manual"]
    assert cap.gravados == 2


def test_manual_conta_para_o_intervalo_da_automatica(tmp_path):
    cap = Capturador(tmp_path, CFG)
    assert cap.manual(VAZIA, 110.0, HORARIO, ligado_desde=None)
    assert not cap.quadro(OBJETO, 115.0, HORARIO, ligado_desde=None)
    assert cap.quadro(OBJETO, 120.0, HORARIO + timedelta(seconds=10), ligado_desde=None)
    cap.fechar()


def test_ligar_e_desligar_a_automatica_vai_ao_registro(tmp_path):
    cap = Capturador(tmp_path, CFG)
    assert cap.quadro(VAZIA, 105.0, HORARIO, ligado_desde=None)
    cap.definir_automatica(False, HORARIO + timedelta(seconds=1))
    assert not cap.quadro(OBJETO, 120.0, HORARIO + timedelta(seconds=15), ligado_desde=None)
    cap.definir_automatica(True, HORARIO + timedelta(seconds=20))
    cap.definir_automatica(True)  # sem mudança: nada registrado
    assert cap.quadro(OBJETO, 130.0, HORARIO + timedelta(seconds=25), ligado_desde=None)
    cap.fechar()
    [sessao] = list(tmp_path.iterdir())
    tipos = [(l["tipo"], l.get("ativa")) for l in ler_jsonl(sessao)]
    assert tipos == [("sessao", None), ("quadro", None), ("automatica", False),
                     ("automatica", True), ("quadro", None)]
