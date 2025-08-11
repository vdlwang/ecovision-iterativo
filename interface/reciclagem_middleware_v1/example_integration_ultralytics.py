"""
Exemplo de integração com Ultralytics YOLO.
Ajuste caminho do modelo (.pt) e a fonte de vídeo/câmera.

pip install ultralytics
python example_integration_ultralytics.py
"""

from ultralytics import YOLO
from middleware_client import send_detection
from pathlib import Path

interface_dir = Path(__file__).resolve().parent
BASE_DIR = interface_dir.parents[1]

modelos = {
    "yolov8s": BASE_DIR / "yolo_models" / "taco" / "yolov8s_100epochs-best.pt",
    "yolov8n": BASE_DIR / "yolo_models" / "taco" / "yolov8n_100epochs-best.pt",
    "yolov8m": BASE_DIR / "yolo_models" / "taco" / "yolov8m_100epochs-best.pt"
}

# IDs/classes de interesse (ajuste se necessário)
ALVOS = {
    6: "glass bottle",
    33: "normal paper",
    17: "corrugated carton",
    12: "metal drink can",
    7: "plastic bottle cap",
    5: "plastic bottle",
}

def main():
    model = YOLO(modelos["yolov8s"])  # seu .pt
    # Exemplo com câmera: source=0; para vídeo use path do arquivo
    for r in model.predict(source=0, stream=True, conf=0.25, imgsz=640):
        if not hasattr(r, "boxes") or r.boxes is None or len(r.boxes) == 0:
            continue
        best = None
        for b in r.boxes:
            cls_id = int(b.cls[0].item())
            if cls_id not in ALVOS:
                continue
            conf = float(b.conf[0].item())
            name = ALVOS.get(cls_id, model.names.get(cls_id, str(cls_id)))
            if best is None or conf > best[1]:
                best = (name, conf)
        if best:
            # Envia apenas a melhor detecção do frame (opcional)
            send_detection(best[0], best[1])

if __name__ == "__main__":
    main()
