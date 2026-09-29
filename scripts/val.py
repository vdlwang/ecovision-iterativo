from ultralytics import YOLO
from pathlib import Path
import pandas as pd

# Caminho base
script_dir = Path(__file__).resolve().parent
modelos = {
    "yolov8s": script_dir.parent / "yolo_models" / "taco" / "yolov8s_100epochs-best.pt",
    "yolov8n": script_dir.parent / "yolo_models" / "taco" / "yolov8n_100epochs-best.pt",
    "yolov8m": script_dir.parent / "yolo_models" / "taco" / "yolov8m_100epochs-best.pt"
}
cenarios = ["tcc-0CF", "tcc-0SF", "tcc-45CF", "tcc-45SF"]

label_map = {
    6: "glass bottle",
    33: "normal paper",
    17: "corrugated carton",
    12: "metal drink can",
    7: "plastic bottle cap",
    5: "plastic bottle"
}
id_interesse = [6, 33, 17, 12, 7, 5]
todos_resultados = []

for nome_modelo, path_modelo in modelos.items():
    print(f"\nAvaliando modelo: {nome_modelo}")

    model = YOLO(path_modelo)

    for nome_cenario in cenarios:
        print(f"\nAvaliando cenário: {nome_cenario}")

        dataset_dir = script_dir.parent / "database" / nome_cenario / "YOLO_dataset"
        yaml_path = dataset_dir / "data.yaml"

        if not yaml_path.exists():
            print(f"data.yaml não encontrado em: {yaml_path}")
            continue

        metrics = model.val(
            data=str(yaml_path),
            imgsz=640,
            conf=0.001,
            # save=True,
            # save_json=True,
            verbose=False
        )

        resultado = {
            "modelo": nome_modelo,
            "cenario": nome_cenario,
            "mAP@0.5": round(metrics.box.map50, 4),
            "mAP@0.5:0.95": round(metrics.box.map, 4),
            "mean_precision": round(metrics.box.mp, 4)
        }

        for idx, class_id in enumerate(id_interesse):
            classe = label_map[class_id]
            resultado[f"prec_{classe}"] = round(metrics.box.p[idx], 4)
            resultado[f"rec_{classe}"] = round(metrics.box.r[idx], 4)

        todos_resultados.append(resultado)

# Exporta para Excel
df_resultados = pd.DataFrame(todos_resultados)
excel_path = script_dir / "avaliacao_modelos_resultados_2.xlsx"
df_resultados.to_excel(excel_path, index=False)

# Mostra no terminal
print("\nRESULTADOS FINAIS:")
for r in todos_resultados:
    print(f"\n{r['modelo']} - {r['cenario']}")
    print(f" - mAP@0.5:      {r['mAP@0.5']}")
    print(f" - mAP@0.5:0.95: {r['mAP@0.5:0.95']}")
    print(f" - Precision média: {r['mean_precision']}")
    print(" - Precisão por classe:")
    for class_id in id_interesse:
        classe = label_map[class_id]
        print(f"   • {classe:25s} → {r[f'prec_{classe}']}")
    print(" - Revocação por classe:")
    for class_id in id_interesse:
        classe = label_map[class_id]
        print(f"   • {classe:25s} → {r[f'rec_{classe}']}")

print(f"\nResultados exportados para: {excel_path}")
