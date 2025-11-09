# 🚀 Início Rápido - Inferência ONNX no Navegador

Este guia mostra como configurar o EcoVision para usar **inferência local no navegador** em menos de 5 minutos.

## ✅ Pré-requisitos

- Python 3.8+ instalado
- Modelo YOLO treinado (arquivo `.pt`)
- Navegador moderno (Chrome, Edge, Firefox, Safari)

## 📋 Passos

### 1. Instalar Ultralytics (se ainda não tem)

```bash
pip install ultralytics
```

### 2. Converter Modelo para ONNX

Crie um arquivo `convert_to_onnx.py`:

```python
from ultralytics import YOLO

# Carregar seu modelo treinado
# Substitua 'best.pt' pelo caminho do seu modelo
model = YOLO('best.pt')

# Exportar para ONNX
print("🔄 Convertendo modelo para ONNX...")
model.export(
    format='onnx',
    simplify=True,
    dynamic=False,
    imgsz=640
)

print("✅ Conversão concluída!")
print("📁 Arquivo gerado: yolov8n.onnx")
```

Execute:
```bash
python convert_to_onnx.py
```

### 3. Copiar Modelo para Pasta /models

```bash
# Windows
copy yolov8n.onnx models\yolov8n.onnx

# Linux/Mac
cp yolov8n.onnx models/yolov8n.onnx
```

### 4. Iniciar Aplicação

```bash
# O EcoVision detectará automaticamente o modelo ONNX
npm run dev
# ou
yarn dev
```

### 5. Verificar Modo ONNX

1. Abra a aplicação no navegador
2. Faça login
3. Vá para o painel da câmera
4. Verifique o indicador: **"Modo: Inferência Local (ONNX)"**

---

## 🎯 Pronto!

Se tudo funcionou, você verá:

- ✅ Indicador verde: **"Modo: Inferência Local (ONNX) [Rápido]"**
- ✅ Detecções acontecendo localmente no navegador
- ✅ Sem necessidade de servidor Python rodando

---

## ❌ Troubleshooting

### "Modelo ONNX não disponível, usando servidor backend"

**Possíveis causas:**

1. **Arquivo não encontrado**
   ```bash
   # Verifique se o arquivo existe
   ls models/yolov8n.onnx
   ```

2. **Nome incorreto**
   - O arquivo DEVE se chamar exatamente `yolov8n.onnx`
   - Está na pasta `/models/` (na raiz do projeto)

3. **Arquivo corrompido**
   ```bash
   # Converta novamente
   python convert_to_onnx.py
   ```

### "Erro ao carregar modelo ONNX"

**Console do navegador mostra erro:**

```
[ONNX] ❌ Erro ao carregar modelo: ...
```

**Soluções:**

1. **Limpe cache do navegador**
   - Chrome: Ctrl+Shift+Del → Limpar cache
   - Recarregue a página (Ctrl+R)

2. **Verifique o console**
   - Abra DevTools (F12)
   - Veja mensagens de erro detalhadas
   - Procure por erros de CORS ou rede

3. **Teste em navegador diferente**
   - Alguns navegadores têm melhor suporte a WebAssembly

### Performance muito baixa (<10 FPS)

**Otimizações:**

1. **Feche outras abas/programas**
   - ONNX usa CPU, libere recursos

2. **Reduza tamanho da imagem**
   - Edite `onnxInference.tsx`
   - Mude `inputSize: 640` para `inputSize: 416`

3. **Use servidor Python com GPU**
   - Veja `INFERENCE_MODES.md` para comparação

---

## 📊 Verificação de Performance

Abra o console do navegador (F12) e procure por:

```
[ONNX] ✅ Inferência concluída: 2 detecção(ões) em 45.2ms
```

**Benchmarks esperados:**

| Hardware | FPS Típico | Latência |
|----------|------------|----------|
| Desktop moderno (i7/Ryzen 7) | 40-60 FPS | 16-25ms |
| Laptop médio (i5/Ryzen 5) | 20-40 FPS | 25-50ms |
| Laptop básico (Celeron/i3) | 10-20 FPS | 50-100ms |
| Tablet/Mobile | 5-15 FPS | 65-200ms |

---

## 🔄 Voltar para Servidor Python

Se preferir usar o servidor Python:

1. **Não copie** o arquivo `.onnx` para `/models/`
2. **Ou** renomeie: `mv yolov8n.onnx yolov8n.onnx.bak`
3. **Inicie** o servidor Python: `python inference_server.py`
4. **Sistema usará** automaticamente o servidor backend

---

## 📚 Próximos Passos

- 📖 Leia `INFERENCE_MODES.md` para comparação detalhada
- 🎯 Otimize seu modelo para melhor performance
- 🔧 Ajuste parâmetros de confiança no painel
- 📊 Monitore estatísticas de detecção

---

## 💡 Dicas

### Melhor Precisão
- Use YOLOv8s ou YOLOv8m (modelos maiores)
- Exporte para ONNX do mesmo jeito
- ⚠️ Reduzirá FPS (~50% mais lento)

### Melhor Velocidade  
- Use YOLOv8n (nano)
- Reduza `inputSize` para 416 ou 512
- ✅ Aumentará FPS (~50% mais rápido)

### Melhor Balanceamento
- Use YOLOv8s com `inputSize: 512`
- Bom compromisso entre precisão e velocidade

---

## 🆘 Suporte

Problemas? Verifique:
1. Console do navegador (F12) → Mensagens de erro
2. `INFERENCE_MODES.md` → Troubleshooting completo
3. `models/README.md` → Guia de conversão de modelos

---

Criado em: 09 de Novembro de 2025
