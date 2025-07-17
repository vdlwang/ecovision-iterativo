from ultralytics import YOLO
from pathlib import Path
import csv

# Caminho base do script
script_dir = Path(__file__).resolve().parent
modelo_path = script_dir.parent / "yolo_models" / "taco" / "yolov8s_100epochs-best.pt"

# Cenários a avaliar
# cenarios = ["tcc-0CF"]  
cenarios = ["tcc-0CF", "tcc-0SF", "tcc-45CF", "tcc-45SF"]

# Carrega o modelo YOLOv8
model = YOLO(modelo_path)
nomes_classes = model.names  # dicionário index: nome

todos_resultados = []

label_map = {
    6: "glass bottle",
    33: "normal paper",
    17: "corrugated carton",
    12: "metal drink can",
    7: "plastic bottle cap",
    5: "plastic bottle"
}

for nome_cenario in cenarios:
    print(f"\n🔍 Avaliando cenário: {nome_cenario}")

    dataset_dir = script_dir.parent / "database" / nome_cenario / "YOLO_dataset"
    yaml_path = dataset_dir / "data.yaml"

    if not yaml_path.exists():
        print(f"data.yaml não encontrado em: {yaml_path}")
        continue

    # Validação no cenário
    metrics = model.val(
        data=str(yaml_path),
        imgsz=640,
        conf=0.001,
        save=True,
        save_json=True,
        verbose=True
    )

    # Guarda os resultados
    resultado = {
        "cenario": nome_cenario,
        "mAP@0.5": round(metrics.box.map50, 4),
        "mAP@0.5:0.95": round(metrics.box.map, 4),
        "mean_precision": round(metrics.box.mp, 4),
        "precisao_por_classe": [round(p, 4) for p in metrics.box.p],
        "revocacao_por_classe": [round(r, 4) for r in metrics.box.r],
    }

    resultado["nomes_classes"] = [label_map[i] for i in [6, 33, 17, 12, 7, 5]]

    todos_resultados.append(resultado)

# Mostra os resultados no terminal
print("\nRESULTADOS FINAIS:")
for r in todos_resultados:
    print(f"\n📁 {r['cenario']}")
    print(f" - mAP@0.5:            {r['mAP@0.5']}")
    print(f" - mAP@0.5:0.95:       {r['mAP@0.5:0.95']}")
    print(f" - Precision média:    {r['mean_precision']}")
    print(f" - Precisão por classe:")
    for nome, prec in zip(r["nomes_classes"], r["precisao_por_classe"]):
        print(f"   • {nome:25s} → {prec}")
    print(f" - Revocação por classe:")
    for nome, recall in zip(r["nomes_classes"], r["revocacao_por_classe"]):
        print(f"   • {nome:25s} → {recall}")
