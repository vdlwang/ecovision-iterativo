from ultralytics import YOLO
from ultralytics.data.converter import convert_coco
from pathlib import Path
import tempfile
import yaml

# Carrega o modelo
model = YOLO('../yolo_models/taco/yolov8s_100epochs-best.pt')

yaml_path = './YOLO_dataset/data.yaml'

# Rodar tesste
results = model.val(
    data=yaml_path,
    split='val',
    verbose=True
)

# Mostrar métricas principais
print(f"Resultados para base 1:")
print(f" - mAP@0.5:      {results.box.map50:.4f}")
print(f" - mAP@0.5:0.95: {results.box.map:.4f}")
print(f" - Precisão média (mean precision): {results.box.mp:.4f}")
print(f" - Precisão por classe: {results.box.p}")
print(f" - Revocação por classe:    {results.box.r}")
