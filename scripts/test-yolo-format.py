from ultralytics import YOLO
from pathlib import Path

# Caminho base do projeto (base onde está o data.yaml)
script_dir = Path(__file__).resolve().parent
dataset_dir = script_dir.parent / "database" / "tcc-0SF" / "YOLO_dataset"
yaml_path = dataset_dir / "data.yaml"

# Carrega o modelo
model = YOLO(script_dir.parent / "yolo_models" / "taco" / "yolov8s_100epochs-best.pt")

# Rodar teste
results = model.val(
    data=str(yaml_path),
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

# print(results.box)