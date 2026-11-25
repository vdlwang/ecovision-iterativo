"""
Captura de quadros da esteira para a anotação (tarefa T4 do OBJETIVO.md; plano
em backend/PLANO-CAPTURA.md). Sem câmera, serial nem YOLO: testável sem
hardware.

Quando gravar (deve_capturar): nunca a menos de intervalo_s (Δ) da captura
anterior. Com o motor ligado, por objeto novo (OcupacaoLona): quando um
objeto entra na lona vazia, a captura sai atraso_s depois, com ele mais
perto do centro do quadro; sem objeto, nada é gravado. O objeto novo vem do
teto aprendido da lona vazia, não do YOLO, para a base não ficar só com o que
o modelo já detecta; o YOLO é só reserva (BackupYolo), para o que o teto não
vê (objetos escuros), e cada captura registra o gatilho (OBJETIVO.md, "Captura sem duplicatas e vazamento").
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

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger("ecovision")

PADROES_CAPTURA = {
    "ativa": False,
    # relativa a backend/, como o model_path
    "pasta": "capturas",
    # Δ: espaço mínimo entre duas capturas; acima de travessia_s, com folga
    "intervalo_s": 4.0,
    # tempo de um objeto cruzar o campo da câmera com o motor ligado (~3 s
    # medidos na esteira em 2026-11-24, ~610 px/s num quadro de 1280 px)
    "travessia_s": 3.0,
    # motor ligado: a captura sai este tempo depois de um objeto entrar na lona
    # (do bordo ao centro do quadro: ~metade de travessia_s)
    "atraso_s": 1.5,
    # blocos vizinhos da miniatura (~20×20 px em 1280×720) acima do teto da
    # lona para haver objeto: o ruído da lona vazia sai em blocos soltos (maior
    # grupo de 3 nos quadros de 2026-11-24, margem 20; a lata deu 220), e um
    # objeto pequeno como uma tampa dá ~10-25. Antes, 3% do quadro (~69 blocos)
    "blocos_minimos": 6,
    # brilho (0-255, sem igualar) acima do teto de um bloco para contar como ocupado
    "margem_teto": 20.0,
    # reserva: uma trilha nova do YOLO (acima da confiança do config.json) que a
    # lona não viu dispara a captura, como a lona; o gatilho vai ao captura.jsonl
    "backup_yolo": True,
    # quadros com a trilha para ela contar: com 3, trilhas falsas na lona vazia
    # dispararam 2 de 9 capturas em 2026-11-25
    "quadros_trilha_yolo": 8,
    # tempo de uma volta da lona com o motor ligado (~15 s em 2026-11-24, com
    # folga): numa volta, todo trecho dela passa por todo bloco do quadro
    "volta_s": 18.0,
    # o teto é aprendido em tantas voltas: o máximo de cada uma, e o menor
    # deles. A lona aparece em todas; um objeto que passou numa só, não
    "voltas_aprendizado": 2,
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


def maior_regiao(mascara):
    """Tamanho, em blocos, do maior grupo de blocos vizinhos (8-conexo) da máscara."""
    n, _, stats, _ = cv2.connectedComponentsWithStats(mascara.astype(np.uint8), connectivity=8)
    return int(stats[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0


# Ocupada por mais que isto × travessia_s com o motor ligado: nenhum objeto
# fica tanto no campo andando; o teto é que ficou baixo (luz, câmera mexida)
# e é aprendido de novo
TRAVESSIAS_REFERENCIA_PRESA = 3
# ... e com pelo menos esta fração dos blocos acima do teto (objetos em
# sequência ocupam bem menos; a luz subindo ou a câmera mexida, quase tudo)
FRACAO_REFERENCIA_PRESA = 0.3


class OcupacaoLona:
    """
    Objeto novo na esteira pelo teto da lona, sem o YOLO. A lona não é
    uniforme (emenda, manchas) e anda, mas a luz e a câmera são fixas: em
    uma volta, todo trecho dela passa por todo bloco do quadro. O teto de
    cada bloco da miniatura é aprendido com o motor ligado em
    voltas_aprendizado janelas de volta_s: o maior brilho de cada janela, e
    o menor desses máximos. A emenda e as manchas da lona aparecem em toda
    janela e ficam no teto; um objeto que passou numa janela só, não (com o
    máximo de uma janela só, como antes, um objeto no aprendizado subia o
    teto na faixa inteira por onde passou, e a lona deixava de ver os
    objetos ali). Depois, um bloco mais claro que o teto mais margem_teto
    está ocupado, e há objeto quando o maior grupo de blocos ocupados
    vizinhos tem blocos_minimos (o ruído sai solto). Sem igualar o brilho:
    pede a exposição travada. Só objetos mais claros que a lona são vistos.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.reaprender()

    def reaprender(self):
        self.teto = None
        self.maximos = []  # o máximo de cada janela de volta_s já completa
        self.janela = None  # máximo da janela em curso
        self.janela_desde = None
        self.aprendida = False
        self.eventos = []  # "aprendendo", "aprendida", "presa": vão ao captura.jsonl
        self.ocupada, self.ocupada_desde = False, None
        self.ocupacao, self.regiao = 0.0, 0  # fração de blocos ocupados; maior grupo

    def quadro(self, mini, agora, motor_ligado):
        """Atualiza com a miniatura do quadro; True se um objeto acabou de entrar."""
        anterior = self.teto if self.aprendida else self.janela
        if anterior is not None and anterior.shape != mini.shape:
            self.reaprender()
        if not self.aprendida:
            # Só com a lona andando: parada, um trecho só passaria pelos
            # blocos; a janela em curso recomeça
            if not motor_ligado:
                self.janela, self.janela_desde = None, None
                return False
            if self.janela is None:
                if not self.maximos:
                    self.eventos.append("aprendendo")
                    log.info("Captura: aprendendo a lona (%d voltas de %.0f s com o motor ligado)",
                             self.cfg["voltas_aprendizado"], self.cfg["volta_s"])
                self.janela, self.janela_desde = mini.copy(), agora
            else:
                np.maximum(self.janela, mini, out=self.janela)
            if agora - self.janela_desde >= self.cfg["volta_s"]:
                self.maximos.append(self.janela)
                self.janela, self.janela_desde = None, None
                if len(self.maximos) >= self.cfg["voltas_aprendizado"]:
                    self.teto = np.minimum.reduce(self.maximos)
                    self.maximos = []
                    self.aprendida = True
                    self.eventos.append("aprendida")
                    log.info("Captura: lona aprendida")
            return False

        acima = mini > self.teto + self.cfg["margem_teto"]
        self.ocupacao = float(acima.mean())
        self.regiao = maior_regiao(acima)
        ocupada = self.regiao >= self.cfg["blocos_minimos"]
        entrou = ocupada and not self.ocupada
        if not ocupada or not motor_ligado:
            self.ocupada_desde = None
        elif self.ocupada_desde is None:
            self.ocupada_desde = agora
        elif self.ocupacao < FRACAO_REFERENCIA_PRESA:
            # Objetos passando em sequência mantêm a lona ocupada sem o teto
            # estar errado: só o quadro todo acima do teto (luz, câmera) conta
            self.ocupada_desde = agora
        elif agora - self.ocupada_desde > TRAVESSIAS_REFERENCIA_PRESA * self.cfg["travessia_s"]:
            log.info("Captura: %.0f%% da lona acima do teto há %.0f s com a esteira andando; "
                     "aprendendo de novo", 100 * self.ocupacao, agora - self.ocupada_desde)
            self.reaprender()
            self.eventos.append("presa")
            return False
        self.ocupada = ocupada
        return entrou


# Trilha do YOLO ainda presente se vista há no máximo isto (o rastreador perde
# quadros); esquecida depois de TRAVESSIAS_REFERENCIA_PRESA × travessia_s sem ela
TRILHA_PRESENTE_S = 0.5


class BackupYolo:
    """
    Reserva da OcupacaoLona: trilhas do rastreador que a lona não viu. Cada
    trilha dispara no máximo uma vez, depois de quadros_trilha_yolo quadros;
    uma trilha vista com a lona ocupada (a lona já cuida do objeto) ou com o
    motor desligado (objeto parado no campo) fica coberta e não dispara.
    Traz de volta o viés de amostragem (só o que o modelo vê), por isso só
    como reserva e com o gatilho registrado (OBJETIVO.md, revista 2026-11-24).
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.vistas = {}  # id → [primeira vez, última vez, quadros]
        self.cobertas = set()

    def cobrir_todas(self):
        self.cobertas.update(self.vistas)

    def primeira_vez(self, trilha):
        return self.vistas[trilha][0]

    def presente(self, trilha, agora):
        v = self.vistas.get(trilha)
        return v is not None and agora - v[1] <= TRILHA_PRESENTE_S

    def quadro(self, trilhas, agora, cobrir):
        """Atualiza com os ids do quadro; devolve o id de uma trilha que acabou de contar, ou None."""
        for t in trilhas:
            v = self.vistas.setdefault(t, [agora, agora, 0])
            v[1] = agora
            v[2] += 1
            if cobrir:
                self.cobertas.add(t)
        esquecer = TRAVESSIAS_REFERENCIA_PRESA * self.cfg["travessia_s"]
        for t in [t for t, v in self.vistas.items() if agora - v[1] > esquecer]:
            del self.vistas[t]
            self.cobertas.discard(t)
        for t in trilhas:
            if t not in self.cobertas and self.vistas[t][2] >= self.cfg["quadros_trilha_yolo"]:
                self.cobertas.add(t)
                return t
        return None


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
        self.yolo = BackupYolo(self.cfg)
        self.pendente_em = None  # motor ligado: instante da captura de um objeto que entrou
        self.pendente_gatilho = None  # "lona" ou "yolo"
        self.pendente_trilha = None
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
            if ativa:
                # Ligar com a lona vazia aprende o teto de novo (um objeto que
                # passou no aprendizado anterior deixou o teto alto ali); as
                # trilhas que já estavam no campo não são novas
                self.lona.reaprender()
                self.yolo.cobrir_todas()
            if self.sessao is not None:
                horario = horario or datetime.now(timezone.utc)
                self.sessao.registrar({"tipo": "automatica", "ativa": ativa,
                                             "horario": horario.astimezone(timezone.utc).isoformat()})

    def reaprender_lona(self, motivo):
        """Esquece o teto da lona (foco, exposição ou ganho mudaram o brilho)."""
        with self._trava:
            if self.lona.teto is not None:
                log.info("Captura: %s; a lona será aprendida de novo", motivo)
            self.lona.reaprender()
            self._agendar(None, None)

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
            self._agendar(None, None)
            return False
        mini = miniatura(quadro_bgr)
        motor_ligado = ligado_desde is not None
        with self._trava:
            diferenca = None if motor_ligado else diferenca_quadros(mini, self.ultima_miniatura)
            # A lona é acompanhada com o motor desligado também (objeto posto
            # com a esteira parada não conta como novo ao ligar)
            entrou = self.lona.quadro(mini, agora, motor_ligado)
            for evento in self.lona.eventos:
                if self.sessao is not None:
                    self.sessao.registrar({"tipo": "lona", "evento": evento,
                                           "horario": horario.astimezone(timezone.utc).isoformat()})
            self.lona.eventos.clear()
            if entrou and motor_ligado and self.pendente_em is None:
                self._agendar(agora + self.cfg["atraso_s"], "lona")
                log.debug("Captura: objeto entrou na lona (%d blocos, %.1f%%)",
                          self.lona.regiao, 100 * self.lona.ocupacao)
            if self.cfg["backup_yolo"]:
                trilhas = [d["id"] for d in (info or {}).get("detections", [])
                           if d.get("id") is not None]
                trilha = self.yolo.quadro(trilhas, agora, self.lona.ocupada or not motor_ligado)
                if trilha is not None and self.pendente_em is None:
                    self._agendar(self.yolo.primeira_vez(trilha) + self.cfg["atraso_s"],
                                  "yolo", trilha)
                    log.debug("Captura: trilha #%d do YOLO que a lona não viu", trilha)
            if not motor_ligado:
                self._agendar(None, None)
            objeto_pronto, gatilho, trilha = False, None, None
            if self.pendente_em is not None and agora >= self.pendente_em:
                gatilho, trilha = self.pendente_gatilho, self.pendente_trilha
                objeto_pronto = (self.lona.ocupada if gatilho == "lona"
                                 else self.yolo.presente(trilha, agora))
                self._agendar(None, None)
            if not self.automatica or not deve_capturar(agora, self.ultima_captura, ligado_desde,
                                                        diferenca, self.cfg, objeto_pronto):
                return False
            return self._gravar(quadro_bgr, agora, horario, mini, {
                "origem": "automatica", "motor_ligado": motor_ligado,
                "gatilho": gatilho if motor_ligado else "diferenca",
                **({"trilha": trilha} if gatilho == "yolo" else {}),
                "diferenca": diferenca,
                "ocupacao": round(self.lona.ocupacao, 4) if motor_ligado else None,
                "regiao": self.lona.regiao if motor_ligado else None,
                **(info or {})})

    def _agendar(self, instante, gatilho, trilha=None):
        self.pendente_em, self.pendente_gatilho, self.pendente_trilha = instante, gatilho, trilha

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
