"""
Captura de quadros da esteira para a anotação (tarefa T4 do OBJETIVO.md; plano
em backend/PLANO-CAPTURA.md). Sem câmera, serial nem YOLO: testável sem
hardware.

Quando gravar (deve_capturar): nunca a menos de intervalo_s (Δ) da captura
anterior. Com o motor ligado, por objeto novo (OcupacaoLona): quando um
objeto entra na lona vazia, a captura sai atraso_s depois, com ele mais
perto do centro do quadro; sem objeto, nada é gravado. O objeto novo vem da
diferença para a lona vazia, não do YOLO, para a base não ficar só com o que
o modelo já detecta (OBJETIVO.md, "Captura sem duplicatas e vazamento").
Com Δ acima do tempo de travessia do campo da câmera, um objeto não aparece
em duas capturas. Com o motor desligado (ou em modo demonstração), só se o
quadro difere do último gravado (objetos postos à mão, esteira parada).

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
    # motor ligado: a captura sai este tempo depois de um objeto entrar na lona
    # (do bordo ao centro do quadro: ~metade de travessia_s)
    "atraso_s": 1.0,
    # fração da miniatura diferente da lona vazia para haver objeto (lona vazia
    # deu 0-1,8%, com objeto 5,3-96%, na sessão de 2026-11-18)
    "ocupacao_minima": 0.03,
    # diferença de um bloco da miniatura (0-255, brilho igualado) para contar como ocupado
    "limiar_bloco": 40.0,
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
    # Roda em todo quadro com o motor ligado: subamostrar antes de converter
    # (1280×720: 26 ms → ~2 ms), mantendo ~4×4 pixels por bloco
    q = np.asarray(quadro)
    passo = max(1, max(q.shape[:2]) // (lado * 4))
    q = q[::passo, ::passo].astype(np.float32)
    if q.ndim == 3:
        q = q.mean(axis=2)
    bloco = max(1, -(-max(q.shape) // lado))  # arredondado para cima: no máximo `lado` blocos
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


def fracao_ocupada(mini, referencia, limiar_bloco):
    """Fração dos blocos da miniatura que diferem da lona vazia (brilho igualado)."""
    if referencia is None or mini.shape != referencia.shape:
        return 0.0
    d = np.abs(normalizar_brilho(mini) - normalizar_brilho(referencia))
    return float((d > limiar_bloco).mean())


# Lona vazia: a referência acompanha mudanças lentas (luz) pela média móvel
ALFA_REFERENCIA = 0.05
# Ocupada por mais que isto × travessia_s com o motor ligado: nenhum objeto
# fica tanto no campo andando; a referência é que ficou errada (câmera mexida,
# primeiro quadro com objeto) e é refeita pelo quadro atual
TRAVESSIAS_REFERENCIA_PRESA = 3


class OcupacaoLona:
    """
    Objeto novo na esteira pela diferença para a lona vazia, sem o YOLO.
    A referência é o primeiro quadro e depois a média dos quadros vazios. Ela
    começa provisória (o primeiro quadro pode ter um objeto parado no campo):
    só dispara depois de o quadro ficar igual a ela por travessia_s com o motor
    ligado, o que um objeto andando na esteira não faz.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.referencia = None
        self.ocupada = False
        self.ocupada_desde = None  # só conta com o motor ligado
        self.vazia_desde = None  # idem
        self.confirmada = False
        self.ocupacao = 0.0

    def _refazer(self, mini):
        self.referencia = mini.copy()
        self.ocupada, self.ocupada_desde, self.vazia_desde = False, None, None
        self.confirmada, self.ocupacao = False, 0.0

    def quadro(self, mini, agora, motor_ligado):
        """Atualiza com a miniatura do quadro; True se um objeto acabou de entrar."""
        if self.referencia is None or self.referencia.shape != mini.shape:
            self._refazer(mini)
            return False
        self.ocupacao = fracao_ocupada(mini, self.referencia, self.cfg["limiar_bloco"])
        ocupada = self.ocupacao >= self.cfg["ocupacao_minima"]
        entrou = ocupada and not self.ocupada and self.confirmada
        if not ocupada:
            self.ocupada_desde = None
            self.referencia = (1 - ALFA_REFERENCIA) * self.referencia + ALFA_REFERENCIA * mini
            if not motor_ligado:
                self.vazia_desde = None
            elif self.vazia_desde is None:
                self.vazia_desde = agora
            elif not self.confirmada and agora - self.vazia_desde >= self.cfg["travessia_s"]:
                self.confirmada = True
                log.debug("Captura: referência da lona vazia confirmada")
        else:
            self.vazia_desde = None
            if not motor_ligado:
                self.ocupada_desde = None
            elif self.ocupada_desde is None:
                self.ocupada_desde = agora
            elif agora - self.ocupada_desde > TRAVESSIAS_REFERENCIA_PRESA * self.cfg["travessia_s"]:
                log.info("Captura: lona ocupada há %.0f s com a esteira andando; referência refeita",
                         agora - self.ocupada_desde)
                self._refazer(mini)
                return False
        self.ocupada = ocupada
        return entrou


def deve_capturar(agora, ultima_captura, ligado_desde, diferenca, cfg, objeto_pronto=False):
    """
    Decide se o quadro atual é gravado. Tempos em segundos de time.monotonic().

    ultima_captura: instante da captura anterior (None se nenhuma).
    ligado_desde: instante em que o motor ligou (None se desligado ou demo).
    diferenca: diferenca_quadros entre o quadro e o último gravado (None se
    não há último ou não dá para comparar); só pesa com o motor desligado.
    objeto_pronto: motor ligado, passou atraso_s desde que um objeto entrou
    na lona e ele ainda está nela; só pesa com o motor ligado.
    """
    if ultima_captura is not None and agora - ultima_captura < cfg["intervalo_s"]:
        return False
    if ligado_desde is not None:
        return objeto_pronto
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

    def registrar(self, dados):
        """
        Linha do captura.jsonl que não é quadro (câmera reaberta, automática):
        pela fila, para sair na ordem certa entre os quadros. Espera vaga.
        """
        self.fila.put(("linha", dados))

    def _laco(self):
        while True:
            item = self.fila.get()
            if item is None:
                return
            if isinstance(item[0], str):  # ("linha", dados); quadro é array
                self._escrever_linha(item[1])
                continue
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

    def __init__(self, pasta_base, cfg, cabecalho=None, automatica=True):
        self.pasta_base = Path(pasta_base)
        self.cfg = completar_config(cfg)
        self.cabecalho = cabecalho or {}
        self.sessao = None
        self.ultima_captura = None
        self.ultima_miniatura = None
        # Captura automática (deve_capturar); ligada e desligada pelo Monitor.
        # Desligada, só a manual grava.
        self.automatica = automatica
        self.lona = OcupacaoLona(self.cfg)
        self.pendente_em = None  # motor ligado: instante da captura de um objeto que entrou
        self._trava = Lock()  # quadro() roda na thread do YOLO; manual(), na do WebSocket

    @property
    def gravados(self):
        return self.sessao.gravados if self.sessao is not None else 0

    def definir_automatica(self, ativa, horario=None):
        """Liga ou desliga a captura automática; a mudança vai ao captura.jsonl."""
        with self._trava:
            if ativa == self.automatica:
                return
            self.automatica = ativa
            log.info("Captura automática %s", "ligada" if ativa else "desligada")
            if self.sessao is not None:
                horario = horario or datetime.now(timezone.utc)
                self.sessao.registrar({"tipo": "automatica", "ativa": ativa,
                                             "horario": horario.astimezone(timezone.utc).isoformat()})

    def _abrir_sessao(self, horario):
        if self.sessao is None:
            pasta = self.pasta_base / carimbo(horario).split(".")[0]
            self.sessao = Sessao(pasta, {"inicio": horario.astimezone(timezone.utc).isoformat(),
                                         "captura": {**self.cfg, "automatica": self.automatica},
                                         **self.cabecalho},
                                 self.cfg["qualidade_jpeg"])
            log.info("Captura: gravando em %s", pasta)

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
        self.sessao.registrar({"tipo": "camera",
                                     "horario": horario.astimezone(timezone.utc).isoformat(),
                                     "camera": relatorio})

    def quadro(self, quadro_bgr, agora, horario, ligado_desde, info=None):
        """
        Avalia um quadro do laço do YOLO; grava se deve_capturar. Devolve True se
        o quadro foi para a fila. agora: time.monotonic(); horario: datetime com fuso.
        """
        if not self.automatica:
            self.pendente_em = None
            return False
        mini = miniatura(quadro_bgr)
        motor_ligado = ligado_desde is not None
        with self._trava:
            diferenca = None if motor_ligado else diferenca_quadros(mini, self.ultima_miniatura)
            # A lona é acompanhada com o motor desligado também (referência vazia
            # atualizada; objeto parado no campo não conta como novo ao ligar)
            if self.lona.quadro(mini, agora, motor_ligado) and motor_ligado \
                    and self.pendente_em is None:
                self.pendente_em = agora + self.cfg["atraso_s"]
                log.debug("Captura: objeto entrou na lona (%.1f%%)", 100 * self.lona.ocupacao)
            if not motor_ligado:
                self.pendente_em = None
            objeto_pronto = False
            if self.pendente_em is not None and agora >= self.pendente_em:
                self.pendente_em = None
                objeto_pronto = self.lona.ocupada
            if not self.automatica or not deve_capturar(agora, self.ultima_captura, ligado_desde,
                                                        diferenca, self.cfg, objeto_pronto):
                return False
            return self._gravar(quadro_bgr, agora, horario, mini, {
                "origem": "automatica", "motor_ligado": motor_ligado,
                "diferenca": diferenca,
                "ocupacao": round(self.lona.ocupacao, 4) if motor_ligado else None,
                **(info or {})})

    def manual(self, quadro_bgr, agora, horario, ligado_desde, info=None):
        """
        Grava o quadro já, sem deve_capturar (botão do Monitor). Conta como
        captura para o espaçamento: a automática espera Δ depois dela. Uma manual
        a menos de Δ de outra captura é acusada pelo importar.py --janela, que
        põe as duas no mesmo conjunto. Devolve o nome do arquivo, ou None se a
        fila estava cheia.
        """
        with self._trava:
            nome = carimbo(horario) + ".jpg"
            ok = self._gravar(quadro_bgr, agora, horario, None, {
                "origem": "manual", "motor_ligado": ligado_desde is not None,
                "diferenca": None, **(info or {})})
            return nome if ok else None

    def _gravar(self, quadro_bgr, agora, horario, mini, dados):
        self._abrir_sessao(horario)
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
