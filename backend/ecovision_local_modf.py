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
import asyncio
import websockets
from pathlib import Path
from threading import Thread, Lock

from deteccao import deteccoes_do_quadro, angulo_a_disparar

# ==== Configuração ====
BACKEND_DIR = Path(__file__).parent
CONFIG_FILE = BACKEND_DIR / "config.json"

# Espera antes de reabrir a câmera depois de uma falha (em segundos)
CAMERA_RETRY_SECONDS = 5

# O conf passado ao YOLO fica fixo enquanto o stream roda; por isso o modelo
# roda com este piso e o filtro por config['confidence'] é feito a cada quadro
CONF_MINIMA_MODELO = 0.1

def load_config():
    """Carrega configuração do arquivo JSON"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Configuração padrão
    default_config = {
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
        "servo_actuation_seconds": 5.0
        # detection_cooldown agora é fixo no código (DETECTION_COOLDOWN)
    }
    
    # Salva configuração padrão
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2)
    
    return default_config

config = load_config()

# ==== Estado Global ====
class SystemState:
    def __init__(self):
        self.motor_running = True
        self.processing = False
        self.processing_started_at = 0.0
        # timestamp da última detecção enviada ao ESP32
        self.last_detection_ts = 0.0
        self.current_detections = []
        self.fps = 0
        self.serial_port = None
        self.websocket_clients = set()

state = SystemState()
SERVER_LOOP: asyncio.AbstractEventLoop | None = None

# ==== Serial (ESP32) ====
# A thread do YOLO (ângulos) e o handler do WebSocket (motor, teste de ângulo)
# escrevem na mesma porta; a trava impede que duas linhas se misturem
serial_lock = Lock()

def send_line(ser, msg):
    """Envia comando via serial"""
    if ser is None:
        print(f"[DEMO] Serial indisponível; comando ignorado: {msg.strip()}")
        return False
    try:
        if not msg.endswith("\n"):
            msg += "\n"
        with serial_lock:
            ser.write(msg.encode("utf-8"))
            ser.flush()
        return True
    except Exception as exc:
        # Quando a serial está ocupada ou inacessível no Windows o pyserial
        # levanta PermissionError("WriteFile failed..."). Neste caso
        # desativamos a serial para evitar quedas no WebSocket e seguimos em
        # modo demonstração.
        print(f"[DEMO] Falha ao enviar para serial ({exc}); desativando serial")
        state.serial_port = None
        return False

def read_serial_loop(ser):
    """Thread que registra tudo o que o ESP32 envia.

    Ninguém espera resposta depois de mandar um comando: o firmware só
    responde a um ângulo quando ele sai da fila (até 5 s por item), então a
    resposta lida logo após um comando podia ser a de outro.
    """
    while state.serial_port is ser:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
        except Exception as exc:
            if state.serial_port is ser:
                print(f"[DEMO] Falha ao ler da serial ({exc}); desativando serial")
                state.serial_port = None
            return
        if line:
            print(f"ESP32: {line}")

def motor_on(ser):
    """Liga o motor da esteira"""
    send_line(ser, "MOTOR ON")

def motor_off(ser):
    """Desliga o motor da esteira"""
    send_line(ser, "MOTOR OFF")

def send_angle(ser, angle):
    """Envia ângulo para o servo"""
    send_line(ser, str(angle))

# ==== WebSocket Server ====
async def websocket_handler(websocket):
    """Gerencia conexões WebSocket (compatível com websockets≥12)."""
    try:
        state.websocket_clients.add(websocket)
        print(f"Cliente WebSocket conectado. Total: {len(state.websocket_clients)}")
        async for message in websocket:
            try:
                data = json.loads(message)
                
                # Comandos do frontend
                if 'command' in data:
                    cmd = data['command']
                    if cmd == 'MOTOR ON':
                        motor_on(state.serial_port)
                        state.motor_running = True
                    elif cmd == 'MOTOR OFF':
                        motor_off(state.serial_port)
                        state.motor_running = False
                    elif cmd.isdigit():
                        # Comando de ângulo direto
                        send_angle(state.serial_port, int(cmd))
                
                # Atualização de configuração
                elif data.get('type') == 'config':
                    if 'confidence' in data:
                        config['confidence'] = data['confidence']
                        print(f"Confiança atualizada: {config['confidence']}")
                
                # Envia a configuração atual (os painéis pedem ao conectar)
                elif data.get('type') == 'get_config':
                    await websocket.send(json.dumps({**config, 'type': 'config'}))

                # Salvar configuração
                elif data.get('type') == 'save_config':
                    config.update({k: v for k, v in data.items() if k != 'type'})
                    config.pop('type', None)  # chave gravada por versões anteriores
                    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2)
                    print("Configuração salva em config.json")
                
            except Exception as e:
                print(f"Erro ao processar mensagem WebSocket: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        state.websocket_clients.discard(websocket)
        envios_pendentes.pop(websocket, None)
        print(f"Cliente WebSocket desconectado. Total: {len(state.websocket_clients)}")

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
def process_yolo_stream():
    """Thread principal: YOLO + Serial + WebSocket broadcast"""
    # Conectar serial
    try:
        ser = serial.Serial(config['serial_port'], config['baud_rate'], timeout=1)
        time.sleep(2.5)  # Aguarda reset do ESP32
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        state.serial_port = ser
        print(f"Serial conectada: {config['serial_port']}")
        Thread(target=read_serial_loop, args=(ser,), daemon=True).start()
        
        # Liga motor inicial
        motor_on(ser)
        state.motor_running = True
    except Exception as e:
        print(f"Erro ao conectar serial: {e}")
        print("Continuando sem serial (modo demonstração)")
        state.serial_port = None
    
    # Carregar YOLO
    print(f"Carregando modelo YOLO: {config['model_path']}")
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
            print(f"Stream da câmera terminou; reabrindo em {CAMERA_RETRY_SECONDS} s")
        except Exception as e:
            print(f"Erro no stream da câmera ({config['camera_index']}): {e}")
            print(f"Nova tentativa em {CAMERA_RETRY_SECONDS} s")
        time.sleep(CAMERA_RETRY_SECONDS)

def run_yolo_stream(model):
    """Roda o YOLO sobre a câmera até o stream terminar ou falhar"""
    results_gen = model(
        source=config['camera_index'],
        conf=min(CONF_MINIMA_MODELO, config['confidence']),
        show=False,  # Não mostra janela OpenCV
        stream=True,
        verbose=False
    )
    
    print(f"Abrindo câmera: {config['camera_index']}")
    
    frame_count = 0
    # FPS medido em janelas de 1 s (a média desde o início escondia quedas)
    fps_frames = 0
    fps_start = time.time()
    
    for result in results_gen:
        frame_count += 1
        if frame_count == 1:
            print("Stream YOLO iniciado!")
        
        # Calcula FPS
        fps_frames += 1
        elapsed = time.time() - fps_start
        if elapsed >= 1.0:
            state.fps = round(fps_frames / elapsed)
            fps_frames = 0
            fps_start = time.time()
        
        # Extrai frame original
        frame = result.orig_img
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
            )
        
        # Dispara o servo para a primeira detecção que cumpre as condições
        now = time.time()
        for det in detections:
            angle = angulo_a_disparar(det, H, config, state.processing,
                                      now - state.last_detection_ts)
            if angle is None:
                continue
            print(f"→ Disparando imediatamente: {det['class']} → {det['material']} → {angle}°")
            send_angle(state.serial_port, angle)
            
            state.processing = True
            state.processing_started_at = now
            state.last_detection_ts = now
        
        state.current_detections = detections
        
        # Finaliza processamento (o motor fica como o usuário deixou)
        if state.processing:
            elapsed_proc = time.time() - state.processing_started_at
            if elapsed_proc >= config['servo_actuation_seconds']:
                state.processing = False
        
        # Sem clientes, não há por que desenhar e codificar o quadro
        if not (SERVER_LOOP and SERVER_LOOP.is_running() and state.websocket_clients):
            continue
        
        # Desenha bounding boxes no frame
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            label_material = det.get('material', '?')
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (34, 197, 94), 2)
            label = f"{det['class']} ({label_material}) {det['confidence']*100:.1f}%"
            cv2.putText(frame, label, (int(x1), int(y1)-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (34, 197, 94), 2)
        
        # Converte frame para base64
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Prepara dados para WebSocket
        frame_data = {
            'frame': frame_b64,
            'detections': detections,
            'fps': state.fps,
            'motor_running': state.motor_running,
            # None em modo demonstração (sem serial ou após falha de escrita)
            'serial_port': config['serial_port'] if state.serial_port else None
        }
        
        # Envia para WebSocket (asyncio)
        try:
            SERVER_LOOP.call_soon_threadsafe(broadcast_frame, json.dumps(frame_data))
        except RuntimeError:
            # Loop encerrando. O pool de conexões do frontend fará nova tentativa.
            pass

# ==== Main ====
async def main():
    """Inicia WebSocket server e thread YOLO"""
    print("=" * 50)
    print("EcoVision - Sistema de Reciclagem com IA")
    print("=" * 50)
    print(f"Configuração: {CONFIG_FILE}")
    print(f"Porta Serial: {config['serial_port']}")
    print(f"Modelo YOLO: {config['model_path']}")
    print(f"WebSocket: ws://localhost:8765")
    print("=" * 50)
    
    global SERVER_LOOP
    SERVER_LOOP = asyncio.get_running_loop()

    # Inicia thread YOLO
    yolo_thread = Thread(target=process_yolo_stream, daemon=True)
    yolo_thread.start()
    
    # Inicia WebSocket server
    async with websockets.serve(websocket_handler, "localhost", 8765):
        print("✓ WebSocket server rodando!")
        await asyncio.Future()  # Roda forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nEncerrando EcoVision...")
        ser = state.serial_port
        if ser:
            state.serial_port = None  # encerra a thread de leitura
            motor_off(ser)
            ser.close()
