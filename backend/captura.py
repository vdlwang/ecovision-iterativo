"""
Captura de quadros da esteira para a anotação (tarefa T4 do OBJETIVO.md; plano
em backend/PLANO-CAPTURA.md). Sem câmera, serial nem YOLO: testável sem
hardware.

Quando gravar (deve_capturar): nunca a menos de intervalo_s (Δ) da captura
anterior. Com o motor ligado, a esteira anda a velocidade quase constante, e
o tempo dá o deslocamento: com Δ acima do tempo de travessia do campo da
câmera, um objeto não aparece em duas capturas. Depois de o motor ligar,
espera-se uma travessia, para não gravar de novo o objeto que estava parado
no campo. Com o motor desligado (ou em modo demonstração), só se o quadro
difere do último gravado (objetos postos à mão, esteira parada).

Cada quadro é gravado em <pasta>/<sessão>/<horário>.jpg (JPEG por Pillow,
com o horário de captura em UTC no EXIF: DateTimeOriginal, SubSecTimeOriginal
e OffsetTimeOriginal), e cada sessão tem um captura.jsonl: a primeira linha
com a configuração, depois uma por quadro. A importação (anotacao/importar.py)
lê o horário do EXIF para conferir que duas imagens não são próximas demais.
A gravação roda numa thread própria, com fila curta: o laço do YOLO não
espera o disco, e um quadro que não cabe na fila é descartado.
"""

import json
import logging
import queue
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread

import numpy as np
from PIL import Image

log = logging.getLogger("ecovision")

PADROES_CAPTURA = {
    "ativa": False,
    # relativa a backend/, como o model_path
    "pasta": "capturas",
    # Δ: espaço mínimo entre duas capturas; acima de travessia_s
    "intervalo_s": 10.0,
    # tempo de um objeto cruzar o campo da câmera com o motor ligado (medir na esteira)
    "travessia_s": 5.0,
    # diferença média (0-255, em cinza, na miniatura) para gravar com o motor desligado
    "diferenca_minima": 10.0,
    "qualidade_jpeg": 95,
}

LADO_MINIATURA = 64
TAMANHO_FILA = 4
# diferenca_quadros compara as miniaturas com o mesmo brilho médio
BRILHO_NORMALIZADO = 128.0
BRILHO_MINIMO_NORMALIZAR = 2.0

# Tags EXIF
TAG_DATETIME = 0x0132
TAG_IFD_EXIF = 0x8769
TAG_DATETIME_ORIGINAL = 0x9003
TAG_OFFSET_TIME_ORIGINAL = 0x9011
TAG_SUBSEC_TIME_ORIGINAL = 0x9291


def completar_config(cfg):
    """Configuração de captura com as chaves que faltam preenchidas pelos padrões."""
    return {**PADROES_CAPTURA, **(cfg or {})}


def miniatura(quadro, lado=LADO_MINIATURA):
    """Quadro (H×W×3 ou H×W) em cinza, reduzido pela média de blocos a ~lado no maior lado."""
    q = np.asarray(quadro, dtype=np.float32)
    if q.ndim == 3:
        q = q.mean(axis=2)
    bloco = max(1, max(q.shape) // lado)
    h, w = (q.shape[0] // bloco) * bloco, (q.shape[1] // bloco) * bloco
    q = q[:h, :w]
    return q.reshape(h // bloco, bloco, w // bloco, bloco).mean(axis=(1, 3))


def normalizar_brilho(m, alvo=BRILHO_NORMALIZADO):
    """
    Miniatura escalada para brilho médio `alvo`. Sem iluminação controlada, a
    exposição e o ganho ficam no automático (PLANO-CAPTURA, 6b), e a câmera
    clareia ou escurece o quadro inteiro sozinha; escalar pela média tira essa
    mudança global e deixa a de conteúdo. Quadro quase preto fica como está.
    """
    media = float(m.mean())
    return m if media < BRILHO_MINIMO_NORMALIZAR else m * (alvo / media)


def diferenca_quadros(a, b):
    """
    Diferença absoluta média entre duas miniaturas, com o brilho médio de cada
    uma igualado antes (normalizar_brilho); None se não há como comparar.
    """
    if a is None or b is None or a.shape != b.shape:
        return None
    return float(np.abs(normalizar_brilho(a) - normalizar_brilho(b)).mean())


def deve_capturar(agora, ultima_captura, ligado_desde, diferenca, cfg):
    """
    Decide se o quadro atual é gravado. Tempos em segundos de time.monotonic().

    ultima_captura: instante da captura anterior (None se nenhuma).
    ligado_desde: instante em que o motor ligou (None se desligado ou demo).
    diferenca: diferenca_quadros entre o quadro e o último gravado (None se
    não há último ou não dá para comparar); só pesa com o motor desligado.
    """
    if ultima_captura is not None and agora - ultima_captura < cfg["intervalo_s"]:
        return False
    if ligado_desde is not None:
        return agora - ligado_desde >= cfg["travessia_s"]
    return diferenca is None or diferenca >= cfg["diferenca_minima"]


def carimbo(horario):
    """'20261115T232903.146Z' para um datetime com fuso (convertido para UTC)."""
    h = horario.astimezone(timezone.utc)
    return h.strftime("%Y%m%dT%H%M%S.") + f"{h.microsecond // 1000:03d}Z"


def exif_horario(horario):
    """EXIF com o horário de captura em UTC (data, milissegundos e fuso +00:00)."""
    h = horario.astimezone(timezone.utc)
    texto = h.strftime("%Y:%m:%d %H:%M:%S")
    exif = Image.Exif()
    exif[TAG_DATETIME] = texto
    ifd = exif.get_ifd(TAG_IFD_EXIF)
    ifd[TAG_DATETIME_ORIGINAL] = texto
    ifd[TAG_SUBSEC_TIME_ORIGINAL] = f"{h.microsecond // 1000:03d}"
    ifd[TAG_OFFSET_TIME_ORIGINAL] = "+00:00"
    return exif


class Sessao:
    """Uma pasta de capturas, com a thread que grava os quadros e o captura.jsonl."""

    def __init__(self, pasta, cabecalho, qualidade):
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=False)
        self.qualidade = qualidade
        self.registro = self.pasta / "captura.jsonl"
        # A thread de gravação e a do YOLO (reabertura da câmera) escrevem no registro
        self._trava_registro = Lock()
        self._escrever_linha({"tipo": "sessao", **cabecalho})
        self.fila = queue.Queue(maxsize=TAMANHO_FILA)
        self.gravados = 0
        self.descartados = 0
        self.thread = Thread(target=self._laco, name="captura", daemon=True)
        self.thread.start()

    def _escrever_linha(self, dados):
        with self._trava_registro, open(self.registro, "a", encoding="utf-8") as f:
            f.write(json.dumps(dados, ensure_ascii=False) + "\n")

    def enviar(self, quadro_bgr, horario, info):
        """Põe o quadro na fila de gravação; False (e descarta) se a fila está cheia."""
        try:
            self.fila.put_nowait((quadro_bgr, horario, info))
            return True
        except queue.Full:
            self.descartados += 1
            log.warning("Captura: fila cheia, quadro descartado (%d até agora)", self.descartados)
            return False

    def _laco(self):
        while True:
            item = self.fila.get()
            if item is None:
                return
            quadro, horario, info = item
            nome = carimbo(horario) + ".jpg"
            try:
                imagem = Image.fromarray(np.ascontiguousarray(quadro[:, :, ::-1]))  # BGR → RGB
                imagem.save(self.pasta / nome, quality=self.qualidade, exif=exif_horario(horario))
                self._escrever_linha({"tipo": "quadro", "arquivo": nome,
                                      "horario": horario.astimezone(timezone.utc).isoformat(),
                                      "largura": imagem.width, "altura": imagem.height, **info})
                self.gravados += 1
                log.debug("Captura: %s", nome)
            except Exception:
                log.exception("Captura: falha ao gravar %s", nome)

    def fechar(self):
        """Grava o que está na fila e encerra a thread."""
        self.fila.put(None)
        self.thread.join()


class Capturador:
    """Decide e grava as capturas de uma execução do backend (a sessão nasce na primeira)."""

    def __init__(self, pasta_base, cfg, cabecalho=None):
        self.pasta_base = Path(pasta_base)
        self.cfg = completar_config(cfg)
        self.cabecalho = cabecalho or {}
        self.sessao = None
        self.ultima_captura = None
        self.ultima_miniatura = None

    def camera_aberta(self, relatorio, horario=None):
        """
        Registra a câmera (camera.abrir: pedido, lido de volta, efetivo). Antes
        da primeira captura, vai na linha da sessão; depois (reabertura), numa
        linha "camera" do captura.jsonl.
        """
        if self.sessao is None:
            self.cabecalho["camera"] = relatorio
            return
        horario = horario or datetime.now(timezone.utc)
        self.sessao._escrever_linha({"tipo": "camera",
                                     "horario": horario.astimezone(timezone.utc).isoformat(),
                                     "camera": relatorio})

    def quadro(self, quadro_bgr, agora, horario, ligado_desde, info=None):
        """
        Avalia um quadro do laço do YOLO; grava se deve_capturar. Devolve True se
        o quadro foi para a fila. agora: time.monotonic(); horario: datetime com fuso.
        """
        mini = None
        diferenca = None
        if ligado_desde is None:
            # Esteira parada: a decisão depende do conteúdo
            mini = miniatura(quadro_bgr)
            diferenca = diferenca_quadros(mini, self.ultima_miniatura)
        if not deve_capturar(agora, self.ultima_captura, ligado_desde, diferenca, self.cfg):
            return False
        if self.sessao is None:
            pasta = self.pasta_base / carimbo(horario).split(".")[0]
            self.sessao = Sessao(pasta, {"inicio": horario.astimezone(timezone.utc).isoformat(),
                                         "captura": self.cfg, **self.cabecalho},
                                 self.cfg["qualidade_jpeg"])
            log.info("Captura: gravando em %s", pasta)
        dados = {"motor_ligado": ligado_desde is not None,
                 "diferenca": diferenca, **(info or {})}
        if not self.sessao.enviar(quadro_bgr.copy(), horario, dados):
            return False
        self.ultima_captura = agora
        self.ultima_miniatura = mini if mini is not None else miniatura(quadro_bgr)
        return True

    def fechar(self):
        if self.sessao is not None:
            self.sessao.fechar()
            log.info("Captura: %d quadros gravados em %s (%d descartados)",
                     self.sessao.gravados, self.sessao.pasta, self.sessao.descartados)
