# 📁 Modelos YOLO - EcoVision

Coloque seus modelos YOLO treinados nesta pasta.

---

## 🚀 Início Rápido

### Para usar ONNX no navegador (Recomendado):

```bash
# 1. Converta seu modelo treinado
python convert_to_onnx.py --weights best.pt --output models/

# 2. Coloque o arquivo .onnx aqui
# models/yolov8n.onnx

# 3. Pronto! O sistema detectará automaticamente
```

### Para usar servidor Python:

```bash
# 1. Coloque modelo .pt aqui
# models/yolov8n.pt

# 2. Inicie servidor
python inference_server.py
```

---

## 📦 Modelos Suportados

| Arquivo | Tamanho | FPS | Precisão | Uso |
|---------|---------|-----|----------|-----|
| **yolov8n.onnx** | ~12MB | Alto | Boa | Navegador (Recomendado) |
| **yolov8n.pt** | ~6MB | Muito Alto | Boa | Servidor Python |
| **yolov8s.pt** | ~22MB | Alto | Muito Boa | Servidor Python |
| **yolov8m.pt** | ~52MB | Médio | Excelente | Servidor Python |

---

## 🎯 Classes Detectadas

O modelo deve detectar 4 classes:

| ID | Material | Cor |
|----|----------|-----|
| 0 | papel | Azul (#163b6f) |
| 1 | metal | Verde (#196626) |
| 2 | plastico | Vermelho (#dc1f2e) |
| 3 | vidro | Amarelo (#d2b91f) |

---

## 🔄 Converter YOLO → ONNX

```python
from ultralytics import YOLO

# Carregar modelo treinado
model = YOLO('best.pt')

# Exportar para ONNX
model.export(format='onnx', simplify=True, dynamic=False, imgsz=640)
```

---

## ⚠️ Importante

- Modelos **não estão incluídos** no repositório
- Você deve **treinar seus próprios modelos** com seu dataset
- Para dataset e treinamento, consulte documentação YOLOv8 Ultralytics

---

**Última atualização:** Novembro 2025
