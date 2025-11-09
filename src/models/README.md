# Modelos YOLO para EcoVision

Esta pasta deve conter os modelos treinados do YOLO para detecção de materiais recicláveis.

## ⚡ NOVIDADE: Inferência no Navegador com ONNX

O EcoVision agora suporta **inferência diretamente no navegador** usando ONNX Runtime Web! Isso elimina a necessidade de um servidor Python separado e oferece:

- ✅ Processamento **local e privado** (dados não saem do navegador)
- ✅ **Latência ultra-baixa** (sem necessidade de rede)
- ✅ **Funciona offline** após carregar o modelo
- ✅ **Sem custos de servidor** para inferência

### ⚙️ Início Rápido com ONNX

O sistema está configurado para usar ONNX no navegador por padrão. Para funcionar:

1. **Tenha um modelo YOLO treinado** (arquivo `.pt`)
2. **Converta para ONNX** (veja instruções abaixo)
3. **Coloque o arquivo `.onnx` nesta pasta** `/models/`
4. **Pronto!** O sistema detectará automaticamente

### Como Converter Modelo YOLO para ONNX

```python
from ultralytics import YOLO

# Carregar seu modelo treinado
model = YOLO('models/yolov8n.pt')

# Exportar para ONNX
model.export(format='onnx', simplify=True, dynamic=False, imgsz=640)

# Isso criará: models/yolov8n.onnx
```

**Ou use o script de conversão fornecido:**
```bash
# Ver convert_to_onnx.py na raiz do projeto
python convert_to_onnx.py
```

### Colocar Modelo ONNX na Pasta /models

Após exportar, coloque o arquivo `.onnx` na pasta `/models`:
```bash
cp models/yolov8n.onnx /path/to/ecovision/models/yolov8n.onnx
```

O sistema detectará automaticamente o modelo ONNX e usará inferência no navegador!

### 🔄 Sistema Híbrido

O EcoVision usa um sistema híbrido inteligente:

1. **Primeira opção:** ONNX no navegador (se modelo `.onnx` disponível)
2. **Fallback:** Servidor Python (se `inference_server.py` rodando)
3. **Fallback final:** Mock detections (para desenvolvimento)

**Recomendado:** Use ONNX para melhor performance e experiência do usuário.

---

## Modelos Necessários

Você pode usar tanto modelos `.pt` (para servidor Python) quanto `.onnx` (para navegador).

### Formato ONNX (Recomendado - Navegador)
- **yolov8n.onnx** - Modelo Nano ONNX (~12MB)
  - Executa diretamente no navegador
  - FPS: 30-60 FPS (varia com hardware do cliente)
  - Sem necessidade de servidor Python

### Formato PyTorch (Servidor Python)
Coloque os seguintes arquivos `.pt` nesta pasta:

1. **yolov8n.pt** - Modelo Nano (mais rápido, ~6MB)
   - Ideal para: Processamento em tempo real
   - FPS esperado: 60-120 FPS
   - Precisão: Boa

2. **yolov8s.pt** - Modelo Small (~22MB)
   - Ideal para: Balanceamento entre velocidade e precisão
   - FPS esperado: 40-80 FPS
   - Precisão: Muito boa

3. **yolov8m.pt** - Modelo Medium (~52MB)
   - Ideal para: Máxima precisão
   - FPS esperado: 20-40 FPS
   - Precisão: Excelente

## Classes Detectadas

Os modelos devem ser treinados para detectar 4 classes:

| Classe ID | Nome      | Cor      | Código Hex |
|-----------|-----------|----------|------------|
| 0         | papel     | Azul     | #163b6f    |
| 1         | metal     | Verde    | #196626    |
| 2         | plastico  | Vermelho | #dc1f2e    |
| 3         | vidro     | Amarelo  | #d2b91f    |

## Como Treinar os Modelos

### 1. Prepare seu dataset

Estrutura recomendada:
```
recycling_dataset/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
└── data.yaml
```

### 2. Arquivo data.yaml

```yaml
path: ./recycling_dataset
train: images/train
val: images/val
test: images/test

nc: 4  # número de classes
names: ['papel', 'metal', 'plastico', 'vidro']
```

### 3. Treinamento

```python
from ultralytics import YOLO

# Treinar YOLOv8n (nano)
model = YOLO('yolov8n.pt')
results = model.train(
    data='recycling_dataset/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='ecovision_n'
)

# Treinar YOLOv8s (small)
model = YOLO('yolov8s.pt')
results = model.train(
    data='recycling_dataset/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='ecovision_s'
)

# Treinar YOLOv8m (medium)
model = YOLO('yolov8m.pt')
results = model.train(
    data='recycling_dataset/data.yaml',
    epochs=100,
    imgsz=640,
    batch=8,
    name='ecovision_m'
)
```

### 4. Validação

```python
# Validar modelo
model = YOLO('runs/detect/ecovision_n/weights/best.pt')
metrics = model.val()

print(f"mAP50: {metrics.box.map50}")
print(f"mAP50-95: {metrics.box.map}")
```

### 5. Copiar para pasta /models/

Após o treinamento, copie os melhores modelos:
```bash
cp runs/detect/ecovision_n/weights/best.pt models/yolov8n.pt
cp runs/detect/ecovision_s/weights/best.pt models/yolov8s.pt
cp runs/detect/ecovision_m/weights/best.pt models/yolov8m.pt
```

## Dicas de Treinamento

### Aumentação de Dados (Data Augmentation)
- Rotação: ±15°
- Zoom: 0.8-1.2x
- Flip horizontal: Sim
- Blur: Leve
- Brilho/Contraste: ±20%
- Ruído: Leve

### Hiperparâmetros Recomendados
```python
model.train(
    data='data.yaml',
    epochs=100,
    patience=50,      # Early stopping
    batch=16,
    imgsz=640,
    lr0=0.01,         # Learning rate inicial
    lrf=0.01,         # Learning rate final
    momentum=0.937,
    weight_decay=0.0005,
    warmup_epochs=3,
    warmup_momentum=0.8,
    hsv_h=0.015,      # Augmentation - hue
    hsv_s=0.7,        # Augmentation - saturation
    hsv_v=0.4,        # Augmentation - value
    degrees=0.0,      # Augmentation - rotation
    translate=0.1,    # Augmentation - translation
    scale=0.5,        # Augmentation - scale
    flipud=0.0,       # Flip vertical
    fliplr=0.5,       # Flip horizontal
    mosaic=1.0,       # Mosaic augmentation
)
```

## Testando os Modelos

### Teste Básico
```python
from ultralytics import YOLO

# Carregar modelo
model = YOLO('models/yolov8n.pt')

# Fazer predição
results = model('test_image.jpg', conf=0.85)

# Ver resultados
for r in results:
    print(f"Detecções: {len(r.boxes)}")
    for box in r.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        print(f"  - Classe {cls}: {conf*100:.1f}%")
```

### Benchmark de Performance
```python
import time
from ultralytics import YOLO
import cv2

model = YOLO('models/yolov8n.pt')
cap = cv2.VideoCapture(0)

fps_list = []
for _ in range(100):
    ret, frame = cap.read()
    start = time.time()
    results = model(frame, conf=0.85, verbose=False)
    end = time.time()
    fps = 1 / (end - start)
    fps_list.append(fps)

print(f"FPS médio: {sum(fps_list)/len(fps_list):.1f}")
cap.release()
```

## Métricas Esperadas

### Boas Métricas (após treinamento adequado)
- **mAP50:** > 0.85 (85%)
- **mAP50-95:** > 0.60 (60%)
- **Precisão:** > 0.80 (80%)
- **Recall:** > 0.75 (75%)
- **FPS (yolov8n):** > 60
- **FPS (yolov8s):** > 40
- **FPS (yolov8m):** > 20

### Sinais de Problemas
- mAP50 < 0.70: Dataset pequeno ou pouco diverso
- Precisão baixa: Muitos falsos positivos
- Recall baixo: Muitos falsos negativos
- FPS muito baixo: Hardware inadequado ou modelo muito grande

## Melhorando a Performance

### Se a precisão estiver baixa:
1. Colete mais dados (recomendado: 1000+ imagens por classe)
2. Balanceie o dataset (mesma quantidade para cada classe)
3. Melhore a qualidade das anotações
4. Aumente o número de épocas
5. Use um modelo maior (s ou m ao invés de n)

### Se a velocidade estiver baixa:
1. Use modelo menor (n ao invés de s ou m)
2. Reduza imgsz (512 ou 416 ao invés de 640)
3. Use GPU (CUDA)
4. Reduza conf (menos verificações)

### Se houver overfitting:
1. Adicione mais augmentation
2. Use dropout/regularização
3. Reduza o número de épocas
4. Colete mais dados de validação

## Observações Importantes

⚠️ **ATENÇÃO:**
- Os modelos NÃO estão incluídos neste repositório
- Você DEVE treinar seus próprios modelos com seu dataset
- O treinamento pode levar horas/dias dependendo do hardware
- GPU é ALTAMENTE recomendada para treinamento
- Para inferência, CPU pode ser suficiente com modelo nano

📝 **NOTA:**
- Modelos pré-treinados do COCO podem ser usados como base
- Fine-tuning geralmente é mais rápido que treinar do zero
- Considere usar transfer learning para melhores resultados

🎯 **DICA:**
- Comece com yolov8n para testes rápidos
- Use yolov8s para produção balanceada
- Use yolov8m apenas se precisar de máxima precisão

---

Última atualização: 08 de Novembro de 2025
