"""
EcoVision - Sistema de Reciclagem com IA
Backend local: YOLO + ESP32 Serial + WebSocket
"""

from ultralytics import YOLO
import serial
import time
import cv2
import base64
import json
import argparse
from datetime import datetime, timezone
import asyncio
import logging
import websockets
from pathlib import Path
from threading import Thread, Lock

from deteccao import deteccoes_do_quadro, DisparosPorTrilha
from motor import EstadoMotor
from captura import Capturador, PADROES_CAPTURA, completar_config
from camera import LeitorCamera, PADROES_CAMERA, ESPERA_QUADRO_S, descrever
from camera import completar_config as completar_camera

# ==== Logging ====
# INFO por padrão; --debug=true mostra também cada comando enviado ao
# ESP32 e as detecções de cada quadro. Bibliotecas (websockets etc.) ficam em WARNING.
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s.%(msecs)03d %(levelname)-7s [%(threadName)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ecovision")
log.setLevel(logging.INFO)  # main() troca para DEBUG com --debug=true

# ==== Configuração ====
BACKEND_DIR = Path(__file__).parent
CONFIG_FILE = BACKEND_DIR / "config.json"

# Espera antes de reabrir a câmera depois de uma falha (em segundos)
CAMERA_RETRY_SECONDS = 5
# Espera entre tentativas de abrir a serial (sem porta no início ou depois de uma falha)
SERIAL_RETRY_SECONDS = 5

# O conf passado ao YOLO fica fixo enquanto o stream roda; por isso o modelo
# roda com este piso e o filtro por config['confidence'] é feito a cada quadro
CONF_MINIMA_MODELO = 0.1

# Rastreador do Ultralytics (T15): cada caixa ganha o ID da trilha, e o servo
# dispara uma vez por objeto (deteccao.DisparosPorTrilha)
RASTREADOR = "bytetrack.yaml"

# Configuração padrão: a da tese, mais o bloco da captura (T4)
CONFIG_PADRAO = {
    "serial_port": "COM8",
    "baud_rate": 115200,
    "camera_index": 0,
    "model_path": "../yolo_models/taco/best.pt",
    "confidence": 0.35,
    "roi_y_min": 0.45,
    "roi_y_max": 0.55,
    "class_to_angle": {
        "plastic": 50,
        "metal": 150,
        "glass": 130,
        "paper": 110
    },
    "servo_actuation_seconds": 5.0,
    # detection_cooldown: ignorado; o disparo é uma vez por objeto rastreado (T15)
    "captura": PADROES_CAPTURA,
    # Resolução, formato, exposição... pedidos à câmera (camera.py); null = padrão
    "camera": PADROES_CAMERA,
}

def load_config():
    """Carrega config.json, completando as chaves que faltam com os padrões.

    Um config.json de uma versão anterior (sem class_to_angle, sem o bloco
    captura...) funciona sem ser editado; o arquivo só é regravado quando a UI
    salva. Sem o arquivo, ele é criado com os padrões.
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            lido = json.load(f)
        faltando = [k for k in CONFIG_PADRAO if k not in lido]
        if faltando:
            log.warning("config.json sem %s; usando os padrões", ", ".join(faltando))
        cfg = {**json.loads(json.dumps(CONFIG_PADRAO)), **lido}
        cfg['captura'] = completar_config(cfg.get('captura'))
        cfg['camera'] = completar_camera(cfg.get('camera'))
        return cfg

    default_config = json.loads(json.dumps(CONFIG_PADRAO))
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2)
    return default_config

config = load_config()

# O handler do WebSocket (Salvar) e a thread da câmera (foco) gravam o arquivo
config_lock = Lock()

def salvar_config():
    """Grava a configuração em memória no config.json."""
    with config_lock, open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

# ==== Estado Global ====
class SystemState:
    def __init__(self):
        # Último comando de motor que saiu pela serial; desligado no início e
        # depois de um reset do ESP32 (motor.py)
        self.motor = EstadoMotor()
        self.processing = False
        self.processing_started_at = 0.0
        self.current_detections = []
        self.fps = 0
        self.serial_port = None
        self.websocket_clients = set()
        # Último quadro da câmera e as detecções dele, para a captura manual
        # (o handler do WebSocket roda noutra thread; a tupla é trocada inteira)
        self.ultimo_quadro = None
        # Câmera aberta agora (LeitorCamera), para o ajuste de foco pelo Monitor
        self.leitor = None

state = SystemState()
SERVER_LOOP: asyncio.AbstractEventLoop | None = None
# Captura de quadros para a anotação (T4): sempre existe, para a captura
# manual; a automática começa como --capturar/captura.ativa e muda pelo Monitor
capturador: Capturador | None = None

# ==== Serial (ESP32) ====
# A thread do YOLO (ângulos) e o handler do WebSocket (motor, teste de ângulo)
# escrevem na mesma porta; a trava impede que duas linhas se misturem
serial_lock = Lock()

def send_line(ser, msg):
    """Envia comando via serial"""
    if ser is None:
        log.warning("[DEMO] Serial indisponível; comando ignorado: %s", msg.strip())
        return False
    try:
        if not msg.endswith("\n"):
            msg += "\n"
        with serial_lock:
            ser.write(msg.encode("utf-8"))
            ser.flush()
        log.debug("→ ESP32: %s", msg.strip())
        return True
    except Exception as exc:
        # Quando a serial está ocupada ou inacessível no Windows o pyserial
        # levanta PermissionError("WriteFile failed..."). Neste caso
        # desativamos a serial para evitar quedas no WebSocket e seguimos em
        # modo demonstração.
        log.error("[DEMO] Falha ao enviar para serial (%s); desativando serial até reabrir", exc)
        state.serial_port = None
        return False

def read_serial_loop(ser):
    """Registra tudo o que o ESP32 envia, até a porta cair (roda na thread `serial`).

    Ninguém espera resposta depois de mandar um comando: o firmware só
    responde a um ângulo quando ele sai da fila (até 5 s por item), então a
    resposta lida logo após um comando podia ser a de outro.
    """
    while state.serial_port is ser:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
        except Exception as exc:
            if state.serial_port is ser:
                log.error("[DEMO] Falha ao ler da serial (%s); desativando serial até reabrir", exc)
                state.serial_port = None
            return
        if line:
            log.info("ESP32: %s", line)
            if state.motor.linha_recebida(line):
                log.warning("ESP32 reiniciou: motor marcado como desligado")

def motor_on(ser):
    """Liga o motor da esteira (o estado só muda se o comando foi enviado)"""
    state.motor.comando(True, send_line(ser, "MOTOR ON"), time.monotonic())

def motor_off(ser):
    """Desliga o motor da esteira (o estado só muda se o comando foi enviado)"""
    state.motor.comando(False, send_line(ser, "MOTOR OFF"), time.monotonic())

def send_angle(ser, angle):
    """Envia ângulo para o servo"""
    send_line(ser, str(angle))

# ==== WebSocket Server ====
async def websocket_handler(websocket):
    """Gerencia conexões WebSocket (compatível com websockets≥12)."""
    try:
        state.websocket_clients.add(websocket)
        log.info("Cliente WebSocket conectado. Total: %d", len(state.websocket_clients))
        async for message in websocket:
            try:
                data = json.loads(message)
                
                # Comandos do frontend
                if 'command' in data:
                    cmd = data['command']
                    if cmd == 'MOTOR ON':
                        motor_on(state.serial_port)
                    elif cmd == 'MOTOR OFF':
                        motor_off(state.serial_port)
                    elif cmd.isdigit():
                        # Comando de ângulo direto
                        send_angle(state.serial_port, int(cmd))
                
                # Captura (T4): automática ligada/desligada, ou um quadro agora
                elif data.get('type') == 'captura_automatica':
                    if capturador is not None:
                        capturador.definir_automatica(bool(data.get('ativa')))
                elif data.get('type') == 'capturar':
                    await websocket.send(json.dumps(capturar_manual()))

                # Foco da câmera: automático, travado onde está ou manual
                elif data.get('type') == 'foco':
                    pedir_foco(data.get('modo'), data.get('valor'))

                # Atualização de configuração
                elif data.get('type') == 'config':
                    if 'confidence' in data:
                        config['confidence'] = data['confidence']
                        log.info("Confiança atualizada: %s", config['confidence'])
                
                # Envia a configuração atual (os painéis pedem ao conectar)
                elif data.get('type') == 'get_config':
                    await websocket.send(json.dumps({**config, 'type': 'config'}))

                # Salvar configuração
                elif data.get('type') == 'save_config':
                    config.update({k: v for k, v in data.items() if k != 'type'})
                    config.pop('type', None)  # chave gravada por versões anteriores
                    salvar_config()
                    log.info("Configuração salva em config.json")
                
            except Exception as e:
                log.exception("Erro ao processar mensagem WebSocket: %s", e)
    
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        state.websocket_clients.discard(websocket)
        envios_pendentes.pop(websocket, None)
        log.info("Cliente WebSocket desconectado. Total: %d", len(state.websocket_clients))

def pedir_foco(modo, valor):
    """Repassa o ajuste de foco do Monitor à câmera aberta (aplicado na thread dela)."""
    leitor = state.leitor
    if leitor is None:
        log.warning("Foco: nenhuma câmera aberta")
        return
    try:
        valor = None if valor is None else float(valor)
        if not leitor.pedir_foco(modo, valor):
            log.warning("Foco: a fonte %s não tem controle de foco", config['camera_index'])
    except (TypeError, ValueError) as e:
        log.warning("Foco: pedido inválido (%s)", e)

def foco_mudou(estado):
    """
    Foco aplicado (thread da câmera): vai ao config.json, para valer na
    próxima abertura da câmera e na próxima execução. Travado, grava a
    posição em que o autofoco deixou a lente.
    """
    if 'erro' in estado:
        return
    config['camera']['foco'] = None if estado['auto'] else estado['valor']
    salvar_config()

# Captura manual: o último quadro só vale se a câmera o entregou há pouco
QUADRO_MANUAL_MAX_S = 2.0

def capturar_manual():
    """Grava o último quadro da câmera; resposta ao cliente que pediu."""
    resposta = {'type': 'captura_manual', 'ok': False, 'arquivo': None, 'erro': None}
    ultimo = state.ultimo_quadro
    agora = time.monotonic()
    if capturador is None or ultimo is None or agora - ultimo[2] > QUADRO_MANUAL_MAX_S:
        resposta['erro'] = 'sem quadro recente da câmera'
        return resposta
    quadro, detections, _ = ultimo
    nome = capturador.manual(quadro, agora, datetime.now(timezone.utc),
                             state.motor.ligado_desde, {"detections": detections, "fps": state.fps})
    if nome is None:
        resposta['erro'] = 'fila de gravação cheia'
    else:
        resposta.update(ok=True, arquivo=nome)
        log.info("Captura manual: %s", nome)
    return resposta

# Envio em andamento por cliente. Um cliente lento perde quadros em vez de
# acumular envios no loop, e não atrasa os outros.
envios_pendentes = {}

def broadcast_frame(message):
    """Envia o quadro a cada cliente que já recebeu o anterior (roda no loop do WebSocket)"""
    for client in state.websocket_clients:
        envio = envios_pendentes.get(client)
        if envio is not None and not envio.done():
            continue
        envio = asyncio.ensure_future(client.send(message))
        # Conexão fechada no meio do envio: a saída do cliente é tratada no handler
        envio.add_done_callback(lambda t: t.cancelled() or t.exception())
        envios_pendentes[client] = envio

# ==== YOLO Processing ====
encerrando = False

def abrir_serial():
    """Abre a porta do config.json e espera o reset do ESP32"""
    ser = serial.Serial(config['serial_port'], config['baud_rate'], timeout=1)
    try:
        time.sleep(2.5)  # Aguarda reset do ESP32
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        ser.close()
        raise
    return ser

def manter_serial():
    """
    Thread `serial`: abre a porta, registra o que o ESP32 envia e, se a porta
    cai (cabo USB mexido, falha de escrita), tenta reabri-la a cada
    SERIAL_RETRY_SECONDS, como a câmera. Sem porta, o backend segue em modo
    demonstração enquanto isso. O motor só é ligado na conexão da partida: uma
    reconexão não religa a esteira (o ESP32 volta do reset com o motor parado,
    e o backend lê `ESP32 pronto.`).
    """
    partida = True
    avisou = False
    while not encerrando:
        try:
            ser = abrir_serial()
        except Exception as e:
            if not avisou:
                log.warning("Erro ao conectar serial (%s); modo demonstração, nova tentativa a cada %d s",
                            e, SERIAL_RETRY_SECONDS)
                avisou = True
            else:
                log.debug("Serial ainda indisponível: %s", e)
            partida = False
            time.sleep(SERIAL_RETRY_SECONDS)
            continue
        avisou = False
        state.serial_port = ser
        log.info("Serial conectada: %s", config['serial_port'])
        if partida:
            motor_on(ser)  # liga o motor ao iniciar o backend
            partida = False
        read_serial_loop(ser)  # volta quando a porta cai
        if encerrando:
            return
        try:
            ser.close()
        except Exception:
            pass
        log.warning("Serial perdida; tentando reabrir a cada %d s", SERIAL_RETRY_SECONDS)
        time.sleep(SERIAL_RETRY_SECONDS)

def process_yolo_stream():
    """Thread principal: YOLO + WebSocket broadcast (a serial tem a sua thread)"""
    # Carregar YOLO
    log.info("Carregando modelo YOLO: %s", config['model_path'])
    # Caminho relativo é resolvido a partir de backend/, não do diretório atual
    model_path = Path(config['model_path'])
    if not model_path.is_absolute():
        model_path = BACKEND_DIR / model_path
    model = YOLO(str(model_path))

    # Se a câmera não abre ou o stream cai (URL errada, Wi-Fi), tenta de novo
    # em vez de deixar a thread morrer com o servidor no ar e sem vídeo
    while True:
        try:
            run_yolo_stream(model)
            log.warning("Leitura da câmera terminou (falha, %d s sem quadro ou fim do vídeo); "
                        "reabrindo em %d s", ESPERA_QUADRO_S, CAMERA_RETRY_SECONDS)
        except Exception as e:
            log.error("Erro no stream da câmera (%s): %s. Nova tentativa em %d s",
                      config['camera_index'], e, CAMERA_RETRY_SECONDS)
        time.sleep(CAMERA_RETRY_SECONDS)

def run_yolo_stream(model):
    """Roda o YOLO sobre a câmera até a leitura terminar ou falhar"""
    log.info("Abrindo câmera: %s", config['camera_index'])
    leitor = LeitorCamera(config['camera_index'], config['camera'], ao_mudar_foco=foco_mudou)
    log.info(descrever(leitor.relatorio))
    if capturador is not None:
        capturador.camera_aberta(leitor.relatorio)
    state.leitor = leitor
    try:
        laco_yolo(model, leitor)
    finally:
        state.leitor = None
        leitor.fechar()

def laco_yolo(model, leitor):
    """Um quadro por vez: o mais recente da câmera (os intermediários são pulados)"""
    imgsz = config['camera']['imgsz']
    # Câmera (re)aberta: trilhas e IDs recomeçam (persist=False no primeiro quadro)
    disparos = DisparosPorTrilha()
    persistir = False
    frame_count = 0
    # FPS medido em janelas de 1 s (a média desde o início escondia quedas)
    fps_frames = 0
    fps_start = time.time()

    while True:
        frame = leitor.proximo()
        if frame is None:
            return
        result = model.track(frame, persist=persistir, tracker=RASTREADOR,
                             conf=min(CONF_MINIMA_MODELO, config['confidence']),
                             imgsz=imgsz, verbose=False)[0]
        persistir = True
        frame_count += 1
        if frame_count == 1:
            log.info("Stream YOLO iniciado!")

        # Calcula FPS
        fps_frames += 1
        elapsed = time.time() - fps_start
        if elapsed >= 1.0:
            state.fps = round(fps_frames / elapsed)
            fps_frames = 0
            fps_start = time.time()

        H, W = result.orig_shape
        
        # Processa detecções
        detections = []
        if result.boxes is not None and result.boxes.cls is not None:
            boxes = result.boxes
            # config['confidence'] lida a cada quadro: o slider vale sem reiniciar
            detections = deteccoes_do_quadro(
                result.names,
                boxes.cls.cpu().numpy().astype(int),
                boxes.conf.cpu().numpy(),
                boxes.xyxy.cpu().numpy(),
                config['confidence'],
                None if boxes.id is None else boxes.id.cpu().numpy(),
            )
        if detections:
            log.debug("Quadro %d: %s", frame_count, ", ".join(
                f"#{d['id']} {d['class']} ({d['material']}) {d['confidence']:.2f}" for d in detections))

        # Dispara o servo uma vez por objeto, quando a trilha dele cruza a faixa
        now = time.time()
        disparo = disparos.quadro(detections, H, config, now, state.processing)
        if disparo:
            log.info("Disparando: #%d → %s → %d° (votos: %s)", disparo['id'], disparo['material'],
                     disparo['angulo'], ", ".join(f"{m} {v:.1f}" for m, v in
                                                  sorted(disparo['votos'].items(), key=lambda x: -x[1])))
            send_angle(state.serial_port, disparo['angulo'])
            state.processing = True
            state.processing_started_at = now
        while disparos.perdidas_ocupado:
            log.warning("Objeto #%d cruzou a faixa com o servo ocupado e não foi separado",
                        disparos.perdidas_ocupado.pop(0))

        state.current_detections = detections
        state.ultimo_quadro = (frame, detections, time.monotonic())

        # Captura para a anotação (T4): roda com ou sem cliente conectado
        if capturador is not None:
            try:
                capturador.quadro(frame, time.monotonic(), datetime.now(timezone.utc),
                                  state.motor.ligado_desde,
                                  {"detections": detections, "fps": state.fps})
            except Exception:
                log.exception("Captura: erro ao avaliar o quadro")
        
        # Finaliza processamento (o motor fica como o usuário deixou)
        if state.processing:
            elapsed_proc = time.time() - state.processing_started_at
            if elapsed_proc >= config['servo_actuation_seconds']:
                state.processing = False
        
        # Sem clientes, não há por que codificar o quadro
        if not (SERVER_LOOP and SERVER_LOOP.is_running() and state.websocket_clients):
            continue

        # Quadro vai limpo: as caixas são desenhadas pelo frontend a partir de 'detections'
        # Converte frame para base64
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Prepara dados para WebSocket
        frame_data = {
            'frame': frame_b64,
            'detections': detections,
            'fps': state.fps,
            'motor_running': state.motor.ligado,
            # None em modo demonstração (sem serial ou após falha de escrita)
            'serial_port': config['serial_port'] if state.serial_port else None,
            # Captura (T4): automática ligada? e quadros gravados nesta execução
            'captura_automatica': capturador.automatica if capturador else False,
            'capturas_gravadas': capturador.gravados if capturador else 0,
            # Foco da câmera {auto, valor}; None se a fonte não tem (vídeo, URL)
            'foco': leitor.foco,
        }
        
        # Envia para WebSocket (asyncio)
        try:
            SERVER_LOOP.call_soon_threadsafe(broadcast_frame, json.dumps(frame_data))
        except RuntimeError:
            # Loop encerrando. O pool de conexões do frontend fará nova tentativa.
            pass

# ==== Main ====
def _booleano(valor):
    """Converte o valor de --debug ("true"/"false", "1"/"0", "sim"/"não")"""
    v = valor.strip().lower()
    if v in ("true", "1", "sim", "s", "yes", "y", "on"):
        return True
    if v in ("false", "0", "não", "nao", "n", "no", "off"):
        return False
    raise argparse.ArgumentTypeError(f"esperado true ou false, recebido '{valor}'")


def ler_argumentos():
    parser = argparse.ArgumentParser(description="EcoVision: YOLO + ESP32 + WebSocket")
    parser.add_argument(
        "--debug", type=_booleano, nargs="?", const=True, default=False, metavar="true|false",
        help="mostra cada comando enviado ao ESP32 e as detecções de cada quadro "
             "(padrão: false; --debug sozinho equivale a --debug=true)",
    )
    parser.add_argument(
        "--capturar", type=_booleano, nargs="?", const=True, default=None, metavar="true|false",
        help="grava quadros da esteira para a anotação (T4; backend/PLANO-CAPTURA.md); "
             "padrão: captura.ativa do config.json",
    )
    return parser.parse_args()


async def main():
    """Inicia WebSocket server e thread YOLO"""
    log.info("EcoVision - Sistema de Reciclagem com IA")
    log.info("Configuração: %s", CONFIG_FILE)
    log.info("Porta Serial: %s", config['serial_port'])
    log.info("Modelo YOLO: %s", config['model_path'])
    log.info("WebSocket: ws://localhost:8765")
    
    global SERVER_LOOP
    SERVER_LOOP = asyncio.get_running_loop()

    # Serial (com reconexão) e YOLO, cada um na sua thread
    Thread(target=manter_serial, name="serial", daemon=True).start()
    yolo_thread = Thread(target=process_yolo_stream, name="yolo", daemon=True)
    yolo_thread.start()
    
    # Inicia WebSocket server
    async with websockets.serve(websocket_handler, "localhost", 8765):
        log.info("WebSocket server rodando!")
        await asyncio.Future()  # Roda forever

def iniciar_captura(ativa):
    """
    Cria o capturador. A automática começa ligada com --capturar=true ou
    captura.ativa; o Monitor a liga e desliga, e grava quadros à mão. A pasta
    da sessão só é criada na primeira captura.
    """
    cfg = config['captura']
    automatica = cfg['ativa'] if ativa is None else ativa
    pasta = Path(cfg['pasta'])
    if not pasta.is_absolute():
        pasta = BACKEND_DIR / pasta
    if automatica:
        log.info("Captura automática ligada: por objeto novo, %.1f s depois de entrar, a cada %.1f s no mínimo, em %s",
                 cfg["atraso_s"], cfg["intervalo_s"], pasta)
    else:
        log.info("Captura automática desligada (liga pelo Monitor); manual em %s", pasta)
    return Capturador(pasta, cfg, {"camera_index": config['camera_index'],
                                   "model_path": config['model_path'],
                                   "confidence": config['confidence']}, automatica=automatica)


if __name__ == "__main__":
    args = ler_argumentos()
    if args.debug:
        log.setLevel(logging.DEBUG)
    capturador = iniciar_captura(args.capturar)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Encerrando EcoVision...")
        encerrando = True
        if capturador is not None:
            capturador.fechar()
        ser = state.serial_port
        if ser:
            state.serial_port = None  # encerra a thread de leitura
            motor_off(ser)
            ser.close()
