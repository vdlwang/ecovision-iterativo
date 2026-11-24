import json
import time
from datetime import datetime, timezone

import cv2
import numpy as np
import pytest

import camera
from camera import (LeitorCamera, abrir, aplicar_foco, conferir, fourcc_texto,
                    ler_foco, propriedades, tipo_fonte)
from captura import Capturador


class CameraFalsa:
    """VideoCapture falsa: guarda os set na ordem; os controles em `sem` são recusados."""

    def __init__(self, fonte=0, backend=None, sem=(), arredonda=None, quadros=3, aberta=True):
        self.fonte, self.backend = fonte, backend
        self.sem = set(sem)
        self.arredonda = arredonda or {}
        self.valores = {cv2.CAP_PROP_FRAME_WIDTH: 640, cv2.CAP_PROP_FRAME_HEIGHT: 480,
                        cv2.CAP_PROP_FPS: 30, cv2.CAP_PROP_FOURCC: cv2.VideoWriter_fourcc(*"YUYV")}
        self.sets = []
        self.quadros = quadros
        self.lidos = 0
        self.aberta = aberta
        self.solta = False

    def isOpened(self):
        return self.aberta

    def set(self, prop, valor):
        self.sets.append((prop, valor))
        if prop in self.sem:
            return False
        self.valores[prop] = self.arredonda.get(prop, valor)
        return True

    def get(self, prop):
        if prop in self.sem:
            return -1
        return self.valores.get(prop, 0)

    def read(self):
        if self.quadros is not None and self.lidos >= self.quadros:
            return False, None
        self.lidos += 1
        return True, np.full((4, 4, 3), self.lidos, dtype=np.uint8)

    def release(self):
        self.solta = True


def abridor(**kw):
    criadas = []

    def abrir_captura(fonte, backend):
        cap = CameraFalsa(fonte, backend, **kw)
        criadas.append(cap)
        return cap
    abrir_captura.criadas = criadas
    return abrir_captura


def nomes(pares):
    return [n for n, _p, _v in pares]


# ---- propriedades ----

def test_sem_bloco_so_poe_os_automaticos():
    pares = propriedades({}, "V4L2")
    assert nomes(pares) == ["exposicao_auto", "temperatura_cor_auto", "foco_auto"]
    assert dict((n, v) for n, _p, v in pares) == {
        "exposicao_auto": 3, "temperatura_cor_auto": 1, "foco_auto": 1}


def test_ordem_formato_antes_da_resolucao_e_auto_antes_do_manual():
    cfg = {"fourcc": "MJPG", "largura": 1280, "altura": 720, "fps": 30,
           "exposicao": 200, "ganho": 2, "temperatura_cor": 4500, "foco": 10}
    pares = propriedades(cfg, "V4L2")
    assert nomes(pares) == ["fourcc", "largura", "altura", "fps",
                            "exposicao_auto", "exposicao", "ganho",
                            "temperatura_cor_auto", "temperatura_cor",
                            "foco_auto", "foco"]
    valores = {n: v for n, _p, v in pares}
    assert valores["exposicao_auto"] == 1  # manual no V4L2
    assert valores["temperatura_cor_auto"] == 0
    assert valores["foco_auto"] == 0
    assert valores["fourcc"] == cv2.VideoWriter_fourcc(*"MJPG")


def test_controles_de_imagem_depois_do_ganho():
    cfg = {"ganho": 4, "contraste": 256, "saturacao": 384, "gama": 20}
    pares = propriedades(cfg, "V4L2")
    assert nomes(pares) == ["exposicao_auto", "ganho", "contraste", "saturacao", "gama",
                            "temperatura_cor_auto", "foco_auto"]
    assert propriedades({"saturacao": 384}, None) == []  # vídeo/URL: nada


def test_traducao_dshow():
    valores = {n: v for n, _p, v in propriedades({"exposicao": -6}, "DSHOW")}
    assert valores["exposicao_auto"] == 0.25
    assert valores["exposicao"] == -6
    assert {n: v for n, _p, v in propriedades({}, "DSHOW")}["exposicao_auto"] == 0.75


def test_sem_backend_so_formato_e_resolucao():
    pares = propriedades({"largura": 1280, "exposicao": 100}, None)
    assert nomes(pares) == ["largura"]


@pytest.mark.parametrize("fonte, tipo", [
    (0, "dispositivo"), ("2", "dispositivo"), ("/dev/video2", "dispositivo"),
    ("http://10.0.0.5:8080/video", "url"), ("rtsp://cam/stream", "url"),
    ("teste.mp4", "arquivo"),
])
def test_tipo_fonte(fonte, tipo):
    assert tipo_fonte(fonte) == tipo


# ---- conferir ----

def test_conferir_acusa_resolucao_arredondada():
    pedidos = propriedades({"largura": 1366, "altura": 768}, None)
    lidos = {"largura": 1280.0, "altura": 720.0}
    div = conferir(pedidos, lidos, {"largura": True, "altura": True})
    assert [d["campo"] for d in div] == ["largura", "altura"]


def test_conferir_fourcc_pelo_texto():
    pedidos = propriedades({"fourcc": "MJPG"}, None)
    mjpg = float(cv2.VideoWriter_fourcc(*"MJPG"))
    assert conferir(pedidos, {"fourcc": mjpg}, {"fourcc": True}) == []
    yuyv = float(cv2.VideoWriter_fourcc(*"YUYV"))
    assert conferir(pedidos, {"fourcc": yuyv}, {"fourcc": True}) == [
        {"campo": "fourcc", "pedido": "MJPG", "lido": "YUYV"}]


def test_conferir_ignora_automatico_que_a_camera_nao_tem():
    pedidos = propriedades({}, "V4L2")
    lidos = {"exposicao_auto": 3.0, "temperatura_cor_auto": -1.0, "foco_auto": -1.0}
    aceitos = {"exposicao_auto": True, "temperatura_cor_auto": False, "foco_auto": False}
    assert conferir(pedidos, lidos, aceitos) == []


def test_conferir_acusa_manual_recusado():
    pedidos = propriedades({"foco": 10}, "V4L2")
    lidos = {"exposicao_auto": 3.0, "temperatura_cor_auto": 1.0,
             "foco_auto": -1.0, "foco": -1.0}
    aceitos = {"exposicao_auto": True, "temperatura_cor_auto": True,
               "foco_auto": False, "foco": False}
    assert [d["campo"] for d in conferir(pedidos, lidos, aceitos)] == ["foco"]


# ---- abrir ----

def test_abrir_aplica_na_ordem_e_relata():
    ab = abridor(sem={cv2.CAP_PROP_AUTO_WB, cv2.CAP_PROP_AUTOFOCUS, cv2.CAP_PROP_FOCUS})
    cfg = {"fourcc": "MJPG", "largura": 1280, "altura": 720, "exposicao": 200}
    cap, rel = abrir("2", cfg, ab, plataforma="linux")
    assert cap.fonte == 2 and cap.backend == "V4L2"
    props = [p for p, _v in cap.sets]
    assert props[:3] == [cv2.CAP_PROP_FOURCC, cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT]
    assert props.index(cv2.CAP_PROP_AUTO_EXPOSURE) < props.index(cv2.CAP_PROP_EXPOSURE)
    assert rel["divergencias"] == []
    assert rel["efetivo"] == {"largura": 1280, "altura": 720, "fourcc": "MJPG", "fps": 30}
    assert rel["lido"]["fourcc"] == "MJPG"
    assert rel["imgsz"] == 640
    json.dumps(rel)  # vai ao captura.jsonl


def test_abrir_acusa_divergencia_sem_falhar(caplog):
    ab = abridor(arredonda={cv2.CAP_PROP_FRAME_WIDTH: 1280, cv2.CAP_PROP_FRAME_HEIGHT: 720})
    _cap, rel = abrir(0, {"largura": 1366, "altura": 768}, ab, plataforma="linux")
    assert [d["campo"] for d in rel["divergencias"]] == ["largura", "altura"]
    assert "largura pedido 1366, lido 1280" in caplog.text


def test_url_nao_recebe_propriedades(caplog):
    ab = abridor()
    cap, rel = abrir("http://10.0.0.5:8080/video", {"largura": 1280}, ab, plataforma="linux")
    assert cap.sets == [] and cap.backend is None
    assert rel["tipo"] == "url"
    assert "não se aplica" in caplog.text


def test_url_com_senha_autentica_de_cara(monkeypatch):
    monkeypatch.delenv(camera.VAR_OPCOES_FFMPEG, raising=False)
    abrir("http://10.0.0.5:8080/video", {}, abridor(), plataforma="linux")
    assert camera.VAR_OPCOES_FFMPEG not in __import__("os").environ
    abrir("https://u:s@10.0.0.5:4444/video/mjpeg", {}, abridor(), plataforma="linux")
    assert __import__("os").environ[camera.VAR_OPCOES_FFMPEG] == "auth_type;basic"
    monkeypatch.setenv(camera.VAR_OPCOES_FFMPEG, "timeout;5000000")
    abrir("https://u:s@10.0.0.5:4444/video/mjpeg", {}, abridor(), plataforma="linux")
    assert __import__("os").environ[camera.VAR_OPCOES_FFMPEG] == "timeout;5000000|auth_type;basic"


def test_url_sem_bloco_nao_avisa(caplog):
    _cap, _rel = abrir("http://x/video", {}, abridor(), plataforma="linux")
    assert "não se aplica" not in caplog.text


def test_abrir_falha_levanta():
    with pytest.raises(RuntimeError):
        abrir(5, {}, abridor(aberta=False), plataforma="linux")


# ---- LeitorCamera ----

def test_leitor_entrega_o_mais_recente_e_termina():
    ab = abridor(quadros=3)
    leitor = LeitorCamera(0, {}, ab, plataforma="linux")
    leitor._thread.join(timeout=2)  # a falsa lê tudo de uma vez
    quadro = leitor.proximo(espera=1)
    assert quadro[0, 0, 0] == 3  # pulou os anteriores
    assert leitor.proximo(espera=1) is None  # leitura terminou
    leitor.fechar()
    assert ab.criadas[0].solta


def test_leitor_sem_quadro_novo_devolve_none():
    class Parada(CameraFalsa):
        """Entrega um quadro e trava (cabo mexido): só falha meio segundo depois."""
        def read(self):
            if self.lidos == 0:
                return super().read()
            time.sleep(0.5)
            return False, None
    leitor = LeitorCamera(0, {}, lambda f, b: Parada(f, b), plataforma="linux")
    assert leitor.proximo(espera=1) is not None
    assert leitor.proximo(espera=0.1) is None  # nada novo a tempo
    leitor.fechar()


def test_fechar_nao_solta_a_captura_durante_um_read():
    """Stream de rede parado: soltar a captura no meio do read() derrubava o processo."""
    import threading
    liberar = threading.Event()

    class Presa(CameraFalsa):
        def read(self):
            if self.lidos == 0:
                return super().read()
            assert not self.solta, "release() durante o read()"
            liberar.wait(5)
            assert not self.solta, "release() durante o read()"
            return False, None

    criadas = []

    def abrir_captura(f, b):
        criadas.append(Presa(f, b))
        return criadas[-1]
    leitor = LeitorCamera("https://u:s@cam/video/mjpeg", {}, abrir_captura, plataforma="linux")
    assert leitor.proximo(espera=1) is not None
    assert leitor.fechar(espera=0.1) is False  # thread presa no read()
    assert not criadas[0].solta
    liberar.set()
    leitor._thread.join(timeout=2)
    assert criadas[0].solta  # solta pela própria thread, depois do read()


def test_leitor_reaplica_ao_reabrir():
    ab = abridor(quadros=1)
    for _ in range(2):
        LeitorCamera(0, {"largura": 1280}, ab, plataforma="linux").fechar()
    assert all((cv2.CAP_PROP_FRAME_WIDTH, 1280) in c.sets for c in ab.criadas)


# ---- foco ao vivo ----

def test_ler_foco_com_autofoco_nao_da_valor():
    cap = CameraFalsa()
    cap.valores[cv2.CAP_PROP_AUTOFOCUS] = 1
    assert ler_foco(cap) == {"auto": True, "valor": None}


def test_travar_desliga_o_autofoco_sem_mexer_na_lente():
    cap = CameraFalsa()
    cap.valores[cv2.CAP_PROP_AUTOFOCUS] = 1
    cap.valores[cv2.CAP_PROP_FOCUS] = 34  # onde o autofoco deixou
    assert aplicar_foco(cap, "travar") == {"auto": False, "valor": 34}
    assert cap.sets == [(cv2.CAP_PROP_AUTOFOCUS, 0)]


def test_manual_desliga_o_autofoco_antes_do_valor():
    cap = CameraFalsa()
    assert aplicar_foco(cap, "manual", 120) == {"auto": False, "valor": 120}
    assert cap.sets == [(cv2.CAP_PROP_AUTOFOCUS, 0), (cv2.CAP_PROP_FOCUS, 120)]


def test_auto_e_recusa():
    cap = CameraFalsa()
    assert aplicar_foco(cap, "auto") == {"auto": True, "valor": None}
    sem = CameraFalsa(sem=[cv2.CAP_PROP_AUTOFOCUS, cv2.CAP_PROP_FOCUS])
    assert "erro" in aplicar_foco(sem, "manual", 50)


def test_leitor_aplica_o_foco_na_thread_da_camera():
    import threading
    mudou = threading.Event()
    recebidos = []

    class Lenta(CameraFalsa):
        def read(self):
            time.sleep(0.01)
            return True, np.zeros((4, 4, 3), dtype=np.uint8)

    def ao_mudar(estado):
        recebidos.append((estado, threading.current_thread().name))
        mudou.set()

    leitor = LeitorCamera(0, {}, lambda f, b: Lenta(f, b), plataforma="linux",
                          ao_mudar_foco=ao_mudar)
    assert leitor.foco == {"auto": True, "valor": None}  # padrão: autofoco
    assert leitor.pedir_foco("manual", 80.0)
    assert mudou.wait(2)
    leitor.fechar()
    assert recebidos == [({"auto": False, "valor": 80.0}, "camera")]
    assert leitor.foco == {"auto": False, "valor": 80.0}


def test_leitor_de_url_nao_tem_foco():
    leitor = LeitorCamera("http://x/video", {}, abridor(quadros=1), plataforma="linux")
    assert leitor.foco is None
    assert leitor.pedir_foco("auto") is False
    with pytest.raises(ValueError):
        leitor.pedir_foco("manual")
    leitor.fechar()


# ---- registro na captura ----

def test_camera_no_captura_jsonl(tmp_path):
    cap = Capturador(tmp_path, {"intervalo_s": 0, "travessia_s": 0})
    cap.camera_aberta({"fonte": 2, "tipo": "dispositivo", "efetivo": {"largura": 1280}})
    quadro = np.zeros((8, 8, 3), dtype=np.uint8)
    h = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)
    assert cap.quadro(quadro, 0.0, h, None)  # motor desligado: o primeiro quadro grava
    cap.camera_aberta({"fonte": 2, "tipo": "dispositivo", "efetivo": {"largura": 640}},
                      horario=h)
    cap.fechar()
    linhas = [json.loads(l) for l in (cap.sessao.registro).read_text().splitlines()]
    assert linhas[0]["tipo"] == "sessao" and linhas[0]["camera"]["efetivo"]["largura"] == 1280
    assert {"camera", "quadro"} == {l["tipo"] for l in linhas[1:]}
    reaberta = next(l for l in linhas if l["tipo"] == "camera")
    assert reaberta["camera"]["efetivo"]["largura"] == 640


def test_fourcc_texto():
    assert fourcc_texto(cv2.VideoWriter_fourcc(*"MJPG")) == "MJPG"
    assert fourcc_texto(0) is None
    assert fourcc_texto(-1) is None
