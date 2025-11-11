from ultralytics import YOLO
import serial
import time

# Ajuste a porta conforme o seu sistema:
# Exemplo: "COM5" no Windows ou "/dev/ttyUSB0" no Linux/Mac
PORT = "COM5"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(10)  # tempo para o ESP32 reiniciar ao abrir a porta

MODEL_SOURCE = "../yolo_models/taco/yolov8s_100epochs-best.pt"
USE_WEBCAM = True

MODEL_SOURCE = r"..\yolo_models\taco\yolov8s_100epochs-best.pt"
IMG = r"C:\Users\natha\OneDrive\Notebook\Documents\USP\TCC\Modelos\tcc-testes\images\20250323_184434.jpg"

model = YOLO(MODEL_SOURCE)
results = model(source=IMG, save=True, conf=0.4, show=True, stream=True)

# results = model(source=0, save=True, conf=0.4, show=True, stream=True)


print(results)

for result in results:
    names = result.names
    detected_classes = result.boxes.cls.cpu().numpy().astype(int)
    for cls_id in detected_classes:
        # print(names[cls_id])
        if "plastic" in names[cls_id].lower():
            print("plastic")
            angle = 50
            ser.write((str(angle) + "\n").encode())
        elif "metal" in names[cls_id].lower():
            print("metal")
            angle = 90
            ser.write((str(angle) + "\n").encode())
        elif "cardboard" in names[cls_id].lower():
            print("cardboard")
            angle = 130
            ser.write((str(angle) + "\n").encode())
        elif "glass" in names[cls_id].lower():
            print("glass")
        
        response = ser.readline().decode().strip()
        if response:
            print("ESP32:", response)
            time.sleep(5) # Aguarda 5 segundos para o ESP32 processar
        
