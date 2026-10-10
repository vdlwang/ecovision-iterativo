"""
Teste local sem YOLO: envia detecções falsas para o middleware.
Rode o middleware_gui.py antes e depois:
python sender_test.py
"""
import random
import time
from middleware_client import send_detection

MATERIAIS = [
    "glass bottle",
    "normal paper",
    "corrugated carton",
    "metal drink can",
    "plastic bottle cap",
    "plastic bottle",
]

if __name__ == "__main__":
    for _ in range(100):
        label = random.choice(MATERIAIS)
        conf = random.uniform(0.4, 0.98)
        print(f"enviando: {label} {conf:.2f}")
        send_detection(label, conf)
        time.sleep(0.5)
