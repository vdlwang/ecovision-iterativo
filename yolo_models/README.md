# Pesos do YOLO

O backend carrega o arquivo definido em `model_path` de `backend/config.json` (padrão `../yolo_models/taco/best.pt`). Visão geral no [README principal](../README.md).

As métricas abaixo foram lidas dos próprios checkpoints (`train_metrics`, avaliadas no split de validação de cada treino).

| Arquivo | O que é | P | R | mAP50 |
|---------|---------|---|---|-------|
| **`taco/best.pt`** | **Padrão.** YOLOv8s com fine-tuning nas fotos do projeto, continuando o `150ep_best.pt` por mais 100 épocas (dez/2025) | 0,82 | 0,98 | 0,995 |
| `taco/150ep_best.pt` | Fine-tuning do YOLOv8s (`train4`, 200 épocas, batch 4) | 0,76 | 0,75 | 0,80 |
| `taco/97ep_best.pt` | Fine-tuning do YOLOv8s (`train3`, melhor época 85). Tem 64 MB porque guarda o estado do otimizador | 0,75 | 0,65 | 0,78 |
| `taco/50ep_best.pt` | Fine-tuning do YOLOv8s (`train2`, 50 épocas) | 0,81 | 0,65 | 0,71 |
| `taco/yolov8n.pt`, `taco/yolov8m.pt` | Pesos treinados só no TACO (2023), sem fine-tuning. São os mesmos arquivos `yolov8{n,m}_100epochs-best.pt` de `legado/yolo_models/taco/`, renomeados | | | |
| `taco/yolov8s.pt` | ⚠️ **YOLOv8s original do COCO (80 classes: pessoa, carro...)**, não do TACO. Não detecta lixo. O YOLOv8s treinado no TACO está em `legado/yolo_models/taco/yolov8s_100epochs-best.pt` | | | |

Os modelos com fine-tuning têm 61 classes: as 60 do TACO mais `Background`, com os mesmos IDs do TACO (`5` garrafa plástica transparente, `6` garrafa de vidro, `12` lata de bebida, `17` papelão ondulado, `33` papel comum...).

## Ressalvas

- O mAP50 de 0,995 do `best.pt` é otimista. As fotos do projeto mostram as mesmas cenas em 4 condições de captura, então treino e validação quase certamente compartilham cenas. Além disso, o `best.pt` continuou o treino sobre o mesmo split. Detalhes em [`legado/PROBLEMAS.md`](../legado/PROBLEMAS.md) (item T2).
- O script de treino, o `data.yaml` e a divisão treino/validação usados no fine-tuning não estão no repositório.
