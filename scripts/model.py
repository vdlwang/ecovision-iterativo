from ultralytics import YOLO
import serial, time
from pathlib import Path

# ==== Config ====
PORT = "COM5"
BAUD = 115200
MODEL_SOURCE = r"..\yolo_models\taco\yolov8s_100epochs-best.pt"
IMG = r"C:\Users\natha\OneDrive\Notebook\Documents\USP\TCC\Modelos\tcc-testes\images\20250323_184434.jpg"
CONF = 0.4
USE_STREAM = True  # stream=True retorna um gerador

# Mapeamento classe -> ângulo
CLASS_TO_ANGLE = {
    "plastic": 50,     # ajuste conforme seu servo
    "metal": 90,
    "cardboard": 130,
    "glass": 130,      # exemplo: mande o mesmo ângulo do cardboard ou outro
}

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
    time.sleep(5.0)  # dá tempo pro reset do ESP32
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Liga motor antes de começar (opcional)
    send_line(ser, "MOTOR ON")
    resp = read_reply(ser)
    if resp: print("ESP32:", resp)

    # --- YOLO ---
    model = YOLO(MODEL_SOURCE)

    # Se for uma imagem única, você pode tirar o stream=True
    results = model(source=IMG, save=True, conf=CONF, show=True, stream=USE_STREAM)

    # Para evitar spam: memorize último ângulo enviado
    last_angle_sent = None

    def maybe_send_angle(angle):
        nonlocal last_angle_sent
        if angle is None:
            return
        if angle != last_angle_sent:
            send_line(ser, str(angle))         # também aceitaria "SERVO 90"
            r = read_reply(ser)
            if r: print("ESP32:", r)
            last_angle_sent = angle
            # se sua firmware mantém 5s e volta para 180°, aguarde um pouco:
            time.sleep(0.2)  # ajuste se necessário

    # --- Loop de inferência ---
    # results é um gerador quando stream=True
    for result in results:
        names = result.names
        detected = result.boxes.cls.cpu().numpy().astype(int)

        # Escolha uma estratégia: primeiro match, ou prioridade
        angle_to_send = None
        for cls_id in detected:
            name = names[cls_id].lower()
            for key, ang in CLASS_TO_ANGLE.items():
                if key in name:
                    angle_to_send = ang
                    break
            if angle_to_send is not None:
                break

        maybe_send_angle(angle_to_send)

    # --- Encerramento ---
    time.sleep(5)
    send_line(ser, "MOTOR OFF")
    resp = read_reply(ser)
    if resp: print("ESP32:", resp)

    ser.close()

if __name__ == "__main__":
    main()
