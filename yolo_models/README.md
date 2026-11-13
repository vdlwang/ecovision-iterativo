# Pesos do YOLO

O backend carrega o arquivo definido em `model_path` de `backend/config.json` (padrão `../yolo_models/taco/best.pt`). Visão geral no [README principal](../README.md).

As métricas abaixo foram lidas dos próprios checkpoints (`train_metrics`, avaliadas no split de validação de cada treino).

| Arquivo | O que é | P | R | mAP50 |
|---------|---------|---|---|-------|
| **`taco/best.pt`** | **Padrão.** YOLOv8s com fine-tuning nas fotos do projeto, continuando o `150ep_best.pt` por mais 100 épocas (dez/2025) | 0,82 | 0,98 | 0,995 |
| `taco/150ep_best.pt` | Fine-tuning do YOLOv8s (`train4`, 200 épocas, batch 4) | 0,76 | 0,75 | 0,80 |
| `taco/97ep_best.pt` | Fine-tuning do YOLOv8s (`train3`, melhor época 85). Tem 64 MB porque guarda o estado do otimizador | 0,75 | 0,65 | 0,78 |
| `taco/50ep_best.pt` | Fine-tuning do YOLOv8s (`train2`, 50 épocas) | 0,81 | 0,65 | 0,71 |
| `taco/yolov8n.pt`, `taco/yolov8s.pt`, `taco/yolov8m.pt` | Pesos treinados só no TACO (2023, 60 classes), sem fine-tuning. São os mesmos arquivos (idênticos byte a byte) `yolov8{n,s,m}_100epochs-best.pt` de `legado/yolo_models/taco/`, renomeados. Até 2026-11-13 este README dizia que o `yolov8s.pt` era o COCO; não é. Os fine-tunings partiram de um `./modelos/yolov8s.pt` (`train_args` dos checkpoints), provavelmente este, mas o checkpoint não guarda qual | | | |

Os modelos com fine-tuning têm 61 classes: as 60 do TACO mais `Background`, com os mesmos IDs do TACO (`5` garrafa plástica transparente, `6` garrafa de vidro, `12` lata de bebida, `17` papelão ondulado, `33` papel comum...).

## Ressalvas

- O mAP50 de 0,995 do `best.pt` é otimista. As fotos do projeto mostram as mesmas cenas em 4 condições de captura, então treino e validação quase certamente compartilham cenas. O `best.pt` continuou o treino do `150ep` com um `./data.yaml` de mesmo nome, mas o conteúdo não está no repositório (ver o último item). Detalhes em [`PROBLEMAS.md`](../PROBLEMAS.md) (item T2).
- O script de treino, o `data.yaml` e a divisão treino/validação usados no fine-tuning não estão no repositório.
- Nas 88 fotos de validação de `legado/database` (2026-11-13, `anotacao/avaliar.py`), o `50ep`, o `97ep` e o `150ep` acham 99% dos objetos e dão a todo vidro o rótulo original da equipe (`Glass bottle`): memorizaram essas fotos ou as mesmas cenas. O `best.pt` acha só 43% em 0,20, quase o mesmo que o `yolov8s.pt` só do TACO, então deve ter treinado noutra base. Números no `OBJETIVO.md`, seção 5.
