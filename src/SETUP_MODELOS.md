# 🚀 Setup dos Modelos YOLO - EcoVision

## ⚠️ PROBLEMA ATUAL

Você tem os modelos `.pt` treinados no GitHub, mas o sistema **não consegue fazer inferências** porque precisa dos modelos em formato `.onnx` para rodar no navegador.

---

## ✅ SOLUÇÃO RÁPIDA (3 Passos)

### **Passo 1: Baixe seus modelos do GitHub**

```bash
# Clone ou baixe os modelos .pt do seu repositório
# Exemplo (ajuste para seu repo):
cd /caminho/para/ecovision/models
wget https://github.com/seu-usuario/seu-repo/raw/main/models/yolov8n.pt
# ou copie manualmente se já tiver local
```

### **Passo 2: Converta para ONNX**

```bash
# Na raiz do projeto EcoVision
python convert_to_onnx.py --weights models/yolov8n.pt --output models/

# Isso criará: models/yolov8n.onnx
```

**Parâmetros opcionais:**
```bash
# Se quiser especificar nome diferente:
python convert_to_onnx.py --weights models/best.pt --output models/yolov8n.onnx

# Se quiser tamanho de entrada específico (padrão 640):
python convert_to_onnx.py --weights models/yolov8n.pt --imgsz 640 --output models/
```

### **Passo 3: Teste no navegador**

```bash
# Inicie o sistema
./run_dev.sh   # Linux/Mac
# ou
run_dev.bat    # Windows

# Acesse http://localhost:5000
# Faça login → Vá para aba "Monitor" → Clique "Iniciar Sistema"
```

O sistema detectará automaticamente o arquivo `/models/yolov8n.onnx` e começará a fazer inferências locais!

---

## 📊 VERIFICAÇÃO

### ✅ Modelo ONNX funcionando:
```
Console do navegador (F12) mostrará:
[ONNX] Carregando modelo: /models/yolov8n.onnx...
[ONNX] ✅ Modelo carregado com sucesso
[INFERÊNCIA ONNX] Processando frame localmente...
[INFERÊNCIA ONNX] 2 detecção(ões) em 45.2ms: plastico (92.3%), papel (88.1%)
```

### ❌ Modelo não encontrado:
```
Console mostrará:
[ONNX] ❌ Erro ao carregar modelo
[ONNX] ℹ️ O modelo ONNX não está disponível. Sistema funcionará em modo servidor/mock
[INFERÊNCIA MOCK] Detecção simulada...
```

---

## 🔧 CONVERSÃO DETALHADA

### Script de Conversão (`convert_to_onnx.py`)

```python
from ultralytics import YOLO
import argparse

def convert_model(weights_path, output_path=None, imgsz=640):
    """
    Converte modelo YOLOv8 .pt para .onnx
    
    Args:
        weights_path: Caminho para arquivo .pt
        output_path: Caminho de saída (opcional)
        imgsz: Tamanho da imagem de entrada
    """
    print(f"📦 Carregando modelo: {weights_path}")
    model = YOLO(weights_path)
    
    print(f"🔄 Convertendo para ONNX (imgsz={imgsz})...")
    model.export(
        format='onnx',
        imgsz=imgsz,
        simplify=True,      # Simplifica o grafo ONNX
        dynamic=False,      # Tamanho fixo para melhor performance
        opset=12            # ONNX opset version
    )
    
    # Se output_path especificado, move o arquivo
    if output_path:
        import os
        import shutil
        
        # Arquivo gerado automaticamente
        generated_file = weights_path.replace('.pt', '.onnx')
        
        if os.path.exists(generated_file):
            # Se output_path é diretório, mantém nome original
            if os.path.isdir(output_path):
                basename = os.path.basename(generated_file)
                final_path = os.path.join(output_path, basename)
            else:
                final_path = output_path
            
            shutil.move(generated_file, final_path)
            print(f"✅ Modelo ONNX salvo em: {final_path}")
        else:
            print(f"❌ Erro: arquivo {generated_file} não foi gerado")
    else:
        print(f"✅ Modelo ONNX gerado: {weights_path.replace('.pt', '.onnx')}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converte YOLOv8 .pt para .onnx')
    parser.add_argument('--weights', type=str, required=True, help='Caminho para .pt')
    parser.add_argument('--output', type=str, help='Caminho/diretório de saída')
    parser.add_argument('--imgsz', type=int, default=640, help='Tamanho da imagem')
    
    args = parser.parse_args()
    convert_model(args.weights, args.output, args.imgsz)
```

### Conversão em Lote

Se você tem múltiplos modelos (nano, small, medium):

```bash
# Script bash para converter todos
for model in models/*.pt; do
    echo "Convertendo $model..."
    python convert_to_onnx.py --weights "$model" --output models/
done
```

---

## 🐍 ALTERNATIVA: Servidor Python

Se não quiser converter para ONNX, pode usar o servidor Python:

### 1. Coloque os modelos .pt em `/models/`

```bash
cp /caminho/dos/modelos/yolov8n.pt models/
cp /caminho/dos/modelos/yolov8s.pt models/
cp /caminho/dos/modelos/yolov8m.pt models/
```

### 2. Inicie o servidor Python

```bash
# Terminal 1: Servidor de inferência
python inference_server.py

# Saída esperada:
# [INFO] Carregando modelo: models/yolov8n.pt
# [INFO] Modelo carregado com sucesso
# [INFO] Servidor rodando em http://0.0.0.0:8000
```

### 3. Inicie o frontend

```bash
# Terminal 2: Frontend
./run_dev.sh
```

O sistema detectará que o servidor Python está rodando e usará ele para inferência.

---

## 🎯 QUAL OPÇÃO ESCOLHER?

| Opção | Vantagens | Desvantagens |
|-------|-----------|--------------|
| **ONNX no Navegador** | • Mais rápido (local)<br>• Sem necessidade de servidor Python<br>• Privacidade total<br>• Funciona offline | • Precisa converter .pt → .onnx<br>• ~12MB para download inicial |
| **Servidor Python** | • Usa modelos .pt nativos<br>• Suporta GPU (CUDA)<br>• Sem conversão necessária | • Requer servidor rodando<br>• Latência de rede<br>• Mais complexo deployment |

**🏆 RECOMENDADO:** Use **ONNX no navegador** para melhor experiência.

---

## ❓ PROBLEMAS COMUNS

### Problema: "Modelo não encontrado"

**Solução:**
```bash
# Verifique se o arquivo existe
ls -la models/

# Deve mostrar:
# yolov8n.onnx  (ou yolov8n.pt)

# Se não existir, baixe/copie do GitHub
```

### Problema: "Erro ao converter para ONNX"

**Solução:**
```bash
# Instale/atualize ultralytics
pip install --upgrade ultralytics onnx

# Tente novamente
python convert_to_onnx.py --weights models/yolov8n.pt --output models/
```

### Problema: "Detecções simuladas (mock)"

Significa que nem ONNX nem servidor Python estão funcionando.

**Solução:**
1. Verifique console do navegador (F12)
2. Se ver `[ONNX] ❌ Erro ao carregar modelo`, converta o modelo
3. Se ver `[INFERÊNCIA SERVIDOR] Erro`, inicie o servidor Python

---

## 📝 CHECKLIST FINAL

- [ ] Modelos .pt baixados do GitHub e colocados em `/models/`
- [ ] Modelos convertidos para .onnx (`python convert_to_onnx.py`)
- [ ] Arquivo `/models/yolov8n.onnx` existe
- [ ] Sistema iniciado (`./run_dev.sh`)
- [ ] Login feito (OAuth ou Demo)
- [ ] Aba "Monitor" aberta
- [ ] Câmera permitida
- [ ] Botão "Iniciar Sistema" clicado
- [ ] Console mostra `[ONNX] ✅ Modelo carregado`
- [ ] Detecções aparecem com bounding boxes! 🎉

---

## 🆘 SUPORTE

Se ainda não funcionar:

1. Abra o console do navegador (F12)
2. Copie as mensagens de erro
3. Verifique se há mensagens `[ONNX]`, `[INFERÊNCIA]` ou `[CÂMERA]`
4. Compartilhe os logs para diagnóstico

---

**Desenvolvido com 💚 para EcoVision**
