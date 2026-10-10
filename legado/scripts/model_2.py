from ultralytics import YOLO
import serial, time, sys
from collections import deque
from pathlib import Path

# ==== Config ====
PORT = "COM5"
BAUD = 115200
MODEL_SOURCE = r"..\yolo_models\taco\yolov8s_100epochs-best.pt"
CONF = 0.4

# Webcam
CAM_INDEX = 0
SHOW = True  # show=True abre a janela com as detecções

# Servo por classe (ajuste conforme seu setup)
CLASS_TO_ANGLE = {
    "plastic": 50,
    "metal": 90,
    "cardboard": 130,
    "glass": 130,
}

# Região de Interesse (ROI): fração da altura (0..1)
# Ex.: banda central: [0.45, 0.55] da altura do frame
ROI_Y_MIN = 0.45
ROI_Y_MAX = 0.55

# Tempos
SERVO_ACTUATION_SECONDS = 5.0   # sua firmware já mantém 5s e retorna p/ 180; deixe igual
MOTOR_RESTART_DELAY = 0.5       # pequena folga antes de religar
DETECTION_COOLDOWN = 1.0        # 1s entre enfileirar o mesmo objeto (debounce)

# ====== Util ======
def send_line(ser, msg):
    if not msg.endswith("\n"):
        msg += "\n"
    ser.write(msg.encode("utf-8"))
    ser.flush()

def read_reply(ser, timeout=1.5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            return line
    return None

def main():
    # --- Serial ---
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2.5)  # reset do ESP32
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    def motor_on():
        send_line(ser, "MOTOR ON")
        r = read_reply(ser)
        if r: print("ESP32:", r)

    def motor_off():
        send_line(ser, "MOTOR OFF")
        r = read_reply(ser)
        if r: print("ESP32:", r)

    def send_angle(angle):
        send_line(ser, str(angle))  # também funcionaria "SERVO <ang>"
        r = read_reply(ser)
        if r: print("ESP32:", r)

    # Liga no início
    motor_on()
    motor_running = True

    # --- YOLO ---
    model = YOLO(MODEL_SOURCE)

    # Stream da webcam
    results_gen = model(
        source=CAM_INDEX,
        conf=CONF,
        show=SHOW,
        stream=True
    )

    # Fila de processamento (múltiplas detecções)
    queue = deque()

    # Debounce por classe (opcional)
    last_enqueue_ts = 0.0

    # Estado de processamento atual
    processing = False
    processing_started_at = 0.0

    print("Atalhos: (o)=ON  (p)=OFF  (q)=Sair")

    # Tentativa de leitura de teclado (Windows)
    try:
        import msvcrt
        have_kbd = True
    except ImportError:
        have_kbd = False

    for result in results_gen:
        # 1) Leitura de atalhos
        if have_kbd and msvcrt.kbhit():
            ch = msvcrt.getwch().lower()
            if ch == 'o':
                motor_on(); motor_running = True
            elif ch == 'p':
                motor_off(); motor_running = False
            elif ch == 'q':
                print("Saindo...")
                break

        # 2) Extrai detecções desse frame
        if result is None or result.boxes is None or result.boxes.cls is None:
            continue

        names = result.names
        boxes = result.boxes
        cls_ids = boxes.cls.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()
        xyxy = boxes.xyxy.cpu().numpy()  # (N,4) -> x1,y1,x2,y2

        # Tamanho do frame (p/ ROI). Ultralytics armazena em result.orig_shape
        H, W = result.orig_shape

        # 3) Escolhe as classes que importam e verifica cruzamento da ROI
        now = time.time()
        for i, cls_id in enumerate(cls_ids):
            class_name = names[cls_id].lower()
            if not any(key in class_name for key in CLASS_TO_ANGLE.keys()):
                continue

            x1, y1, x2, y2 = xyxy[i]
            cy = (y1 + y2) / 2.0
            cy_norm = cy / H  # 0..1

            # O objeto “conta” quando o centro cruza a banda ROI
            if ROI_Y_MIN <= cy_norm <= ROI_Y_MAX:
                # (debounce simples)
                if now - last_enqueue_ts >= DETECTION_COOLDOWN:
                    # Prioridade: pegue o primeiro mapeado na string (plastic/metal/cardboard/glass)
                    chosen_key = None
                    for key in CLASS_TO_ANGLE.keys():
                        if key in class_name:
                            chosen_key = key
                            break
                    if chosen_key:
                        queue.append(chosen_key)
                        last_enqueue_ts = now
                        print(f"Enfileirado: {chosen_key} (centro y={cy_norm:.2f})")

        # 4) Processamento da fila (uma peça por vez)
        if not processing and queue:
            target = queue.popleft()
            angle = CLASS_TO_ANGLE[target]

            # Para esteira se estiver ligada
            if motor_running:
                motor_off()
                motor_running = False
                time.sleep(0.05)

            # Aciona o servo
            print(f"Processando: {target} -> ang={angle}")
            send_angle(angle)

            # Marca início do ciclo de atuação (servo/esteira parada)
            processing = True
            processing_started_at = time.time()

        # 5) Finaliza ciclo após tempo do servo e religa a esteira
        if processing:
            if time.time() - processing_started_at >= SERVO_ACTUATION_SECONDS + MOTOR_RESTART_DELAY:
                if not motor_running:
                    motor_on()
                    motor_running = True
                processing = False

    # Encerramento
    if motor_running:
        motor_off()
    ser.close()

if __name__ == "__main__":
    main()
