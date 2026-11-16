"""
Câmera aberta pelo backend com configuração fixa (etapa 6a do
backend/PLANO-CAPTURA.md). Antes, o Ultralytics abria a câmera só pelo
índice, na resolução, no formato e na exposição padrão do driver.

O bloco `camera` do config.json diz o que pedir (PADROES_CAMERA). `null` em
exposicao e temperatura_cor é o automático, posto de forma explícita a cada
abertura: no Linux, o driver guarda o último valor que qualquer programa pôs
(o ajustar_camera.py, o v4l2-ctl), e "não mexer" herdaria um manual velho.
Câmera sem o controle automático (a DV20 não tem balanço de branco
automático) só fica sem ele. Os outros campos em `null` não são mexidos.

Testado com o backend V4L2 (Linux); a tradução para DSHOW (Windows) segue a
documentação do OpenCV e NÃO foi testada.

`propriedades` e `conferir` são lógica pura; `abrir` e `LeitorCamera` recebem
a função que abre a VideoCapture, para os testes passarem uma câmera falsa.
"""

import logging
import sys
import time
from pathlib import Path
from threading import Condition, Thread

import cv2

log = logging.getLogger("ecovision")

PADROES_CAMERA = {
    "largura": None,
    "altura": None,
    # Formato do stream, ex.: "MJPG". YUYV em resolução alta cai para ~10 fps
    "fourcc": None,
    "fps": None,
    # None = automática; número = manual, na unidade do backend
    # (V4L2: exposure_time_absolute, em 100 µs; DSHOW: log2 de segundos)
    "exposicao": None,
    # None = balanço de branco automático; em kelvin = manual
    "temperatura_cor": None,
    # None = autofoco; número = foco manual fixo
    "foco": None,
    # None = não mexer
    "ganho": None,
    # Passado ao YOLO (o best.pt treinou com 640)
    "imgsz": 640,
}

# Valor do controle automático em cada backend: (manual, automático)
AUTO_EXPOSICAO = {"V4L2": (1, 3), "DSHOW": (0.25, 0.75)}
AUTO_LIGA_DESLIGA = (0, 1)

# Diferença tolerada entre o pedido e o lido de volta
TOLERANCIA = 0.5

# Sem quadro novo por este tempo, a leitura é dada como falha (reabre)
ESPERA_QUADRO_S = 10.0


def completar_config(cfg):
    """Bloco camera com as chaves que faltam preenchidas pelos padrões."""
    return {**PADROES_CAMERA, **(cfg or {})}


def nome_backend(plataforma=None):
    """Backend do OpenCV para câmeras locais: V4L2 no Linux, DSHOW no Windows, None nos outros."""
    plataforma = plataforma or sys.platform
    if plataforma.startswith("linux"):
        return "V4L2"
    if plataforma.startswith("win"):
        return "DSHOW"
    return None


def tipo_fonte(fonte):
    """'dispositivo' (índice ou /dev/video*), 'arquivo' (vídeo) ou 'url'."""
    if isinstance(fonte, int):
        return "dispositivo"
    texto = str(fonte).strip()
    if texto.isdigit() or texto.startswith("/dev/"):
        return "dispositivo"
    if "://" in texto:
        return "url"
    return "arquivo"


def normalizar_fonte(fonte):
    """'2' vira 2 (o frontend pode gravar o índice como texto)."""
    if isinstance(fonte, str) and fonte.strip().isdigit():
        return int(fonte.strip())
    return fonte


def fourcc_codigo(texto):
    return cv2.VideoWriter_fourcc(*texto)


def fourcc_texto(valor):
    v = int(valor)
    if v <= 0:
        return None
    return "".join(chr((v >> (8 * i)) & 0xFF) for i in range(4))


def propriedades(cfg, backend):
    """
    Traduz o bloco camera em [(nome, propriedade OpenCV, valor)], na ordem de
    aplicação: formato antes da resolução, e o automático desligado antes do
    valor manual. backend: 'V4L2', 'DSHOW' ou None (só formato, resolução e fps).
    """
    cfg = completar_config(cfg)
    pares = []
    if cfg["fourcc"]:
        pares.append(("fourcc", cv2.CAP_PROP_FOURCC, fourcc_codigo(cfg["fourcc"])))
    if cfg["largura"] is not None:
        pares.append(("largura", cv2.CAP_PROP_FRAME_WIDTH, cfg["largura"]))
    if cfg["altura"] is not None:
        pares.append(("altura", cv2.CAP_PROP_FRAME_HEIGHT, cfg["altura"]))
    if cfg["fps"] is not None:
        pares.append(("fps", cv2.CAP_PROP_FPS, cfg["fps"]))
    if backend is None:
        return pares

    manual, automatico = AUTO_EXPOSICAO[backend]
    if cfg["exposicao"] is None:
        pares.append(("exposicao_auto", cv2.CAP_PROP_AUTO_EXPOSURE, automatico))
    else:
        pares.append(("exposicao_auto", cv2.CAP_PROP_AUTO_EXPOSURE, manual))
        pares.append(("exposicao", cv2.CAP_PROP_EXPOSURE, cfg["exposicao"]))
    if cfg["ganho"] is not None:
        pares.append(("ganho", cv2.CAP_PROP_GAIN, cfg["ganho"]))

    desliga, liga = AUTO_LIGA_DESLIGA
    if cfg["temperatura_cor"] is None:
        pares.append(("temperatura_cor_auto", cv2.CAP_PROP_AUTO_WB, liga))
    else:
        pares.append(("temperatura_cor_auto", cv2.CAP_PROP_AUTO_WB, desliga))
        pares.append(("temperatura_cor", cv2.CAP_PROP_WB_TEMPERATURE, cfg["temperatura_cor"]))
    if cfg["foco"] is None:
        pares.append(("foco_auto", cv2.CAP_PROP_AUTOFOCUS, liga))
    else:
        pares.append(("foco_auto", cv2.CAP_PROP_AUTOFOCUS, desliga))
        pares.append(("foco", cv2.CAP_PROP_FOCUS, cfg["foco"]))
    return pares


def opcional(nome):
    """Os automáticos postos por padrão: a câmera sem o controle não é divergência."""
    return nome.endswith("_auto")


def conferir(pedidos, lidos, aceitos):
    """
    Lista as divergências entre o pedido e o lido de volta.

    pedidos: saída de propriedades(); lidos: {nome: valor lido}; aceitos:
    {nome: retorno do set}. Um automático que a câmera não tem (set recusado
    e leitura -1 ou 0) não conta: é o caso de não ter o controle.
    """
    divergencias = []
    for nome, _prop, valor in pedidos:
        lido = lidos.get(nome)
        if opcional(nome) and not aceitos.get(nome) and lido in (None, -1, 0):
            continue
        if nome == "fourcc":
            pedido_txt, lido_txt = fourcc_texto(valor), fourcc_texto(lido or 0)
            if pedido_txt != lido_txt:
                divergencias.append({"campo": nome, "pedido": pedido_txt, "lido": lido_txt})
            continue
        if lido is None or abs(float(lido) - float(valor)) > TOLERANCIA:
            divergencias.append({"campo": nome, "pedido": valor, "lido": lido})
    return divergencias


def efetivos(cap):
    """Resolução, formato e fps que a câmera diz entregar."""
    return {
        "largura": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "altura": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fourcc": fourcc_texto(cap.get(cv2.CAP_PROP_FOURCC)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
    }


def _abrir_videocapture(fonte, backend):
    if backend is None:
        return cv2.VideoCapture(fonte)
    return cv2.VideoCapture(fonte, getattr(cv2, "CAP_" + backend))


def abrir(fonte, cfg, abrir_captura=_abrir_videocapture, plataforma=None):
    """
    Abre a fonte e aplica o bloco camera. Devolve (captura, relatório); levanta
    RuntimeError se não abre. O relatório vai ao log e ao captura.jsonl.
    """
    cfg = completar_config(cfg)
    fonte = normalizar_fonte(fonte)
    tipo = tipo_fonte(fonte)
    backend = nome_backend(plataforma) if tipo == "dispositivo" else None
    cap = abrir_captura(fonte, backend)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"não foi possível abrir a câmera {fonte!r}")

    relatorio = {"fonte": fonte, "tipo": tipo, "backend": backend,
                 "pedido": {k: v for k, v in cfg.items() if k != "imgsz"},
                 "imgsz": cfg["imgsz"]}
    if tipo != "dispositivo":
        # Vídeo ou stream de rede: nada se aplica
        pedidos = propriedades(cfg, None)
        if pedidos:
            log.warning("Câmera %s é %s: o bloco camera não se aplica", fonte, tipo)
        relatorio.update(lido={}, divergencias=[], efetivo=efetivos(cap))
        return cap, relatorio

    pedidos = propriedades(cfg, backend)
    aceitos = {}
    for nome, prop, valor in pedidos:
        aceitos[nome] = bool(cap.set(prop, valor))
    lidos = {nome: cap.get(prop) for nome, prop, _valor in pedidos}
    divergencias = conferir(pedidos, lidos, aceitos)
    lidos_legiveis = {n: (fourcc_texto(v) if n == "fourcc" else v) for n, v in lidos.items()}
    relatorio.update(lido=lidos_legiveis, divergencias=divergencias, efetivo=efetivos(cap))
    for d in divergencias:
        log.warning("Câmera: %s pedido %s, lido %s", d["campo"], d["pedido"], d["lido"])
    return cap, relatorio


def descrever(relatorio):
    """Linha de log da abertura: resolução, formato e fps efetivos."""
    e = relatorio["efetivo"]
    return (f"Câmera {relatorio['fonte']} ({relatorio['backend'] or relatorio['tipo']}): "
            f"{e['largura']}x{e['altura']} {e['fourcc'] or '?'} {e['fps']:.0f} fps, "
            f"imgsz {relatorio['imgsz']}")


class LeitorCamera:
    """
    Lê a câmera numa thread própria (`camera`) e guarda só o quadro mais
    recente, como o LoadStreams do Ultralytics: sem isso, o buffer do OpenCV
    acumula quadros, e o YOLO veria a esteira atrasada. Um vídeo (arquivo) é
    lido no ritmo do seu fps, como se fosse uma câmera, e termina no fim.
    """

    def __init__(self, fonte, cfg, abrir_captura=_abrir_videocapture, plataforma=None):
        self.cap, self.relatorio = abrir(fonte, cfg, abrir_captura, plataforma)
        self._cond = Condition()
        self._quadro = None
        self._numero = 0
        self._entregue = 0
        self._ativo = True
        self._ritmo = None
        if self.relatorio["tipo"] == "arquivo":
            fps = self.relatorio["efetivo"]["fps"] or 0
            self._ritmo = 1.0 / fps if fps > 0 else None
        self._thread = Thread(target=self._laco, name="camera", daemon=True)
        self._thread.start()

    def _laco(self):
        proximo = time.monotonic()
        while self._ativo:
            ok, quadro = self.cap.read()
            if not ok:
                break
            with self._cond:
                self._quadro = quadro
                self._numero += 1
                self._cond.notify_all()
            if self._ritmo:
                proximo += self._ritmo
                espera = proximo - time.monotonic()
                if espera > 0:
                    time.sleep(espera)
        with self._cond:
            self._ativo = False
            self._cond.notify_all()

    def proximo(self, espera=ESPERA_QUADRO_S):
        """
        O quadro mais recente que ainda não foi entregue; None se a leitura
        terminou (falha ou fim do vídeo) ou se nenhum quadro novo chegou em
        `espera` segundos.
        """
        with self._cond:
            chegou = self._cond.wait_for(
                lambda: self._numero > self._entregue or not self._ativo, timeout=espera)
            if not chegou or self._numero == self._entregue:
                return None
            self._entregue = self._numero
            return self._quadro

    def fechar(self):
        self._ativo = False
        self._thread.join(timeout=2)
        self.cap.release()
