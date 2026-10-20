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
from threading import Thread

# ==== Configuração ====
BACKEND_DIR = Path(__file__).parent
CONFIG_FILE = BACKEND_DIR / "config.json"

# Cooldown fixo entre detecções enviadas (em segundos)
DETECTION_COOLDOWN = 1.5

# Espera antes de reabrir a câmera depois de uma falha (em segundos)
CAMERA_RETRY_SECONDS = 5

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

# ==== Mapeamento TACO -> material genérico ====
PLASTIC = "plastic"
METAL   = "metal"
GLASS   = "glass"
PAPER   = "paper"
OTHER   = "other"  # opcional

# Dicionário: nome da classe TACO (lowercase) -> grupo de material
taco_to_material = {
    # --- Metal ---
    "aluminium foil": METAL,
    "battery": METAL,
    "aluminium blister pack": METAL,
    "metal bottle cap": METAL,
    "food can": METAL,
    "aerosol": METAL,
    "drink can": METAL,
    "metal lid": METAL,
    "scrap metal": METAL,
    "pop tab": METAL,

    # --- Glass ---
    "glass bottle": GLASS,
    "broken glass": GLASS,
    "glass cup": GLASS,
    "glass jar": GLASS,

    # --- Paper / papel ---
    "toilet tube": PAPER,
    "other carton": PAPER,
    "egg carton": PAPER,
    "drink carton": PAPER,          # Tetrapak: aqui tratado como papel
    "corrugated carton": PAPER,
    "meal carton": PAPER,
    "pizza box": PAPER,
    "paper cup": PAPER,
    "magazine paper": PAPER,
    "tissues": PAPER,
    "wrapping paper": PAPER,
    "normal paper": PAPER,
    "paper bag": PAPER,
    "plastified paper bag": PAPER,
    "paper straw": PAPER,

    # --- Plastic / plástico ---
    "other plastic bottle": PLASTIC,
    "clear plastic bottle": PLASTIC,
    "plastic bottle cap": PLASTIC,
    "disposable plastic cup": PLASTIC,
    "foam cup": PLASTIC,             # isopor
    "other plastic cup": PLASTIC,
    "plastic lid": PLASTIC,
    "other plastic": PLASTIC,
    "plastic film": PLASTIC,
    "six pack rings": PLASTIC,
    "garbage bag": PLASTIC,
    "other plastic wrapper": PLASTIC,
    "single-use carrier bag": PLASTIC,
    "polypropylene bag": PLASTIC,
    "crisp packet": PLASTIC,         # embalagem metalizada
    "spread tub": PLASTIC,
    "tupperware": PLASTIC,
    "disposable food container": PLASTIC,
    "foam food container": PLASTIC,
    "other plastic container": PLASTIC,
    "plastic glooves": PLASTIC,
    "plastic gloves": PLASTIC,       # por segurança
    "plastic utensils": PLASTIC,
    "squeezable tube": PLASTIC,
    "plastic straw": PLASTIC,
    "styrofoam piece": PLASTIC,
    "rope & strings": PLASTIC,       # assumindo corda sintética

    # --- Outros / não mapeados nos 4 grupos ---
    "food waste": OTHER,
    "shoe": OTHER,
    "unlabeled litter": OTHER,
    "cigarette": OTHER,
}

def map_taco_to_material(class_name: str) -> str:
    """
    Recebe o nome da classe TACO (como vem do YOLO) e
    devolve 'plastic', 'metal', 'glass', 'paper' ou 'other'.
    """
    key = class_name.strip().lower()
    return taco_to_material.get(key, OTHER)

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
def send_line(ser, msg):
    """Envia comando via serial"""
    if ser is None:
        print(f"[DEMO] Serial indisponível; comando ignorado: {msg.strip()}")
        return False
    try:
        if not msg.endswith("\n"):
            msg += "\n"
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

def read_reply(ser, timeout=1.5):
    """Lê resposta do ESP32"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            return line
    return None

def motor_on(ser):
    """Liga o motor da esteira"""
    if send_line(ser, "MOTOR ON"):
        r = read_reply(ser)
        if r:
            print(f"ESP32: {r}")

def motor_off(ser):
    """Desliga o motor da esteira"""
    if send_line(ser, "MOTOR OFF"):
        r = read_reply(ser)
        if r:
            print(f"ESP32: {r}")

def send_angle(ser, angle):
    """Envia ângulo para o servo"""
    if send_line(ser, str(angle)):
        r = read_reply(ser)
        if r:
            print(f"ESP32: {r}")

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
        print(f"Cliente WebSocket desconectado. Total: {len(state.websocket_clients)}")

async def broadcast_frame(frame_data):
    """Envia frame para todos os clientes conectados"""
    if state.websocket_clients:
        message = json.dumps(frame_data)
        await asyncio.gather(
            *[client.send(message) for client in state.websocket_clients],
            return_exceptions=True
        )

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
        
        # Liga motor inicial
        motor_on(ser)
        state.motor_running = True
    except Exception as e:
        print(f"Erro ao conectar serial: {e}")
        print("Continuando sem serial (modo demonstração)")
        ser = None
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
            run_yolo_stream(model, ser)
            print(f"Stream da câmera terminou; reabrindo em {CAMERA_RETRY_SECONDS} s")
        except Exception as e:
            print(f"Erro no stream da câmera ({config['camera_index']}): {e}")
            print(f"Nova tentativa em {CAMERA_RETRY_SECONDS} s")
        time.sleep(CAMERA_RETRY_SECONDS)

def run_yolo_stream(model, ser):
    """Roda o YOLO sobre a câmera até o stream terminar ou falhar"""
    results_gen = model(
        source=config['camera_index'],
        conf=config['confidence'],
        show=False,  # Não mostra janela OpenCV
        stream=True,
        verbose=False
    )
    
    print(f"Abrindo câmera: {config['camera_index']}")
    
    frame_count = 0
    start_time = time.time()
    
    for result in results_gen:
        frame_count += 1
        if frame_count == 1:
            print("Stream YOLO iniciado!")
        
        # Calcula FPS
        elapsed = time.time() - start_time
        if elapsed > 0:
            state.fps = int(frame_count / elapsed)
        
        # Extrai frame original
        frame = result.orig_img
        H, W = result.orig_shape
        
        # Processa detecções
        detections = []
        if result.boxes is not None and result.boxes.cls is not None:
            names = result.names
            boxes = result.boxes
            cls_ids = boxes.cls.cpu().numpy().astype(int)
            confs = boxes.conf.cpu().numpy()
            xyxy = boxes.xyxy.cpu().numpy()
            
            now = time.time()
            
            for i, cls_id in enumerate(cls_ids):
                class_name_raw = names[cls_id]       # nome original
                class_name = class_name_raw.lower()  # em lowercase
                confidence = float(confs[i])
                x1, y1, x2, y2 = xyxy[i]
                
                # Descobre o material genérico a partir da classe TACO
                material = map_taco_to_material(class_name)
                
                # Adiciona à lista de detecções (incluindo material)
                detections.append({
                    'class': class_name,   # ou class_name_raw se preferir
                    'material': material,
                    'confidence': confidence,
                    'bbox': [float(x1), float(y1), float(x2), float(y2)]
                })
                
                # Verifica se esse material tem ângulo configurado
                if material not in config['class_to_angle']:
                    continue
                
                # Calcula centro Y normalizado
                cy = (y1 + y2) / 2.0
                cy_norm = cy / H
                
                # Verifica ROI
                if config['roi_y_min'] <= cy_norm <= config['roi_y_max']:
                    # Só dispara se:
                    # 1) não estamos processando um item agora
                    # 2) já passou o cooldown desde a última detecção enviada
                    if (not state.processing) and (now - state.last_detection_ts >= DETECTION_COOLDOWN):
                        chosen_key = material  # grupo genérico
                        angle = config['class_to_angle'][chosen_key]

                        print(f"→ Disparando imediatamente: {class_name_raw} → {chosen_key} → {angle}°")
                        send_angle(ser, angle)

                        state.processing = True
                        state.processing_started_at = now
                        state.last_detection_ts = now
        
        state.current_detections = detections
        
        # Finaliza processamento (o motor fica como o usuário deixou)
        if state.processing:
            elapsed_proc = time.time() - state.processing_started_at
            if elapsed_proc >= config['servo_actuation_seconds']:
                state.processing = False
        
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
            if SERVER_LOOP and SERVER_LOOP.is_running():
                asyncio.run_coroutine_threadsafe(broadcast_frame(frame_data), SERVER_LOOP)
        except Exception:
            # Ignora erros se não houver clientes ou se o loop ainda não estiver
            # pronto. O pool de conexões do frontend fará nova tentativa.
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
        if state.serial_port:
            motor_off(state.serial_port)
            state.serial_port.close()
