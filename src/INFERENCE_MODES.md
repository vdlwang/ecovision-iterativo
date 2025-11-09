# EcoVision - Modos de Inferência

O EcoVision suporta **dois modos** de inferência para detecção de materiais recicláveis:

## 🚀 Modo 1: Inferência no Navegador (ONNX) - RECOMENDADO

### Como Funciona
- Usa **ONNX Runtime Web** para executar o modelo YOLO diretamente no navegador
- Todo o processamento acontece no **dispositivo do usuário**
- Não requer servidor Python separado

### Vantagens
- ✅ **Privacidade Total**: Imagens não saem do navegador
- ✅ **Latência Ultra-Baixa**: Sem overhead de rede
- ✅ **Funciona Offline**: Após carregar o modelo inicial
- ✅ **Escalável**: Não sobrecarrega o servidor
- ✅ **Sem Custos Adicionais**: Processamento no cliente
- ✅ **Configuração Simples**: Apenas copie o arquivo .onnx

### Desvantagens
- ⚠️ Performance varia com o hardware do cliente
- ⚠️ Requer navegador moderno com WebAssembly
- ⚠️ Download inicial do modelo (~12MB para YOLOv8n)

### Configuração

#### Passo 1: Converter Modelo PyTorch para ONNX
```python
from ultralytics import YOLO

# Carregar modelo treinado
model = YOLO('models/yolov8n.pt')

# Exportar para ONNX (otimizado para web)
model.export(
    format='onnx',
    simplify=True,      # Simplifica grafo para performance
    dynamic=False,      # Input fixo 640x640
    imgsz=640,          # Tamanho de entrada
    opset=12            # ONNX opset version
)

# Arquivo gerado: yolov8n.onnx
```

#### Passo 2: Colocar Modelo na Pasta /models
```bash
cp yolov8n.onnx /path/to/ecovision/models/yolov8n.onnx
```

#### Passo 3: Sistema Detecta Automaticamente
- Ao iniciar, o EcoVision tenta carregar `/models/yolov8n.onnx`
- Se encontrar, ativa automaticamente o modo ONNX
- Indicador visual mostra "Modo: Inferência Local (ONNX)"

### Requisitos de Hardware (Cliente)
- **Mínimo**: CPU dual-core, 4GB RAM, navegador moderno
- **Recomendado**: CPU quad-core+, 8GB RAM+
- **Performance esperada**: 
  - Desktop moderno: 40-60 FPS
  - Laptop médio: 20-40 FPS
  - Dispositivos móveis: 10-30 FPS

---

## 🖥️ Modo 2: Inferência no Servidor (Python)

### Como Funciona
- Servidor Python local (`inference_server.py`) roda em `localhost:8000`
- Frontend envia frames via HTTP para o servidor
- Servidor processa com Ultralytics YOLO e retorna detecções

### Vantagens
- ✅ **Performance Consistente**: GPU dedicada no servidor
- ✅ **Modelos Maiores**: Pode usar YOLOv8m ou v8l
- ✅ **Controle Total**: Ajustes finos no servidor
- ✅ **Debugging**: Logs detalhados no servidor

### Desvantagens
- ⚠️ **Latência de Rede**: ~50-200ms adicional
- ⚠️ **Requer Servidor**: Infraestrutura adicional
- ⚠️ **Privacidade**: Imagens transitam pela rede
- ⚠️ **Escalabilidade**: Servidor pode sobrecarregar
- ⚠️ **Custos**: Hardware/cloud para servidor

### Configuração

#### Passo 1: Instalar Dependências Python
```bash
pip install -r requirements.txt
```

#### Passo 2: Colocar Modelos PyTorch
```bash
cp best.pt models/yolov8n.pt
```

#### Passo 3: Iniciar Servidor
```bash
# Windows
run_dev.bat

# Linux/Mac
chmod +x run_dev.sh
./run_dev.sh
```

#### Passo 4: Verificar Conexão
- Servidor deve estar rodando em `http://localhost:8000`
- Teste: `curl http://localhost:8000/health`

### Requisitos de Hardware (Servidor)
- **CPU**: Quad-core+ (para YOLOv8n)
- **RAM**: 8GB mínimo
- **GPU** (Opcional): NVIDIA CUDA para aceleração
  - Com GPU: 100-200+ FPS
  - Sem GPU: 10-30 FPS

---

## 🔄 Fallback Automático

O sistema possui **fallback inteligente**:

1. **Tenta ONNX primeiro** (se modelo está disponível)
2. **Se falhar**, automaticamente muda para servidor Python
3. **Se ambos falharem**, usa modo demo com detecções simuladas

### Indicadores Visuais

O painel da câmera mostra qual modo está ativo:

```
🟢 Modo: Inferência Local (ONNX)    [Rápido]
🟡 Modo: Servidor Backend (Python)  [Requer conexão]
🔴 Carregando modelo ONNX...
```

---

## 📊 Comparação Detalhada

| Aspecto | ONNX (Navegador) | Python (Servidor) |
|---------|------------------|-------------------|
| **Setup** | Simples (copiar .onnx) | Complexo (servidor Python) |
| **Latência** | 10-50ms | 50-200ms |
| **Performance** | Varia (cliente) | Consistente |
| **Privacidade** | ⭐⭐⭐⭐⭐ Total | ⭐⭐⭐ Rede local |
| **Escalabilidade** | ⭐⭐⭐⭐⭐ Infinita | ⭐⭐ Limitada |
| **Custo** | ⭐⭐⭐⭐⭐ Zero | ⭐⭐ Hardware/Cloud |
| **Offline** | ⭐⭐⭐⭐⭐ Sim | ❌ Não |
| **GPU** | ❌ Não disponível | ⭐⭐⭐⭐⭐ CUDA |
| **Modelos** | Nano/Small | Qualquer tamanho |

---

## 🎯 Recomendações

### Use ONNX (Navegador) Se:
- ✅ Prioriza privacidade
- ✅ Quer baixa latência
- ✅ Precisa funcionar offline
- ✅ Tem muitos usuários (escalabilidade)
- ✅ YOLOv8n é suficiente para seu caso

### Use Servidor Python Se:
- ✅ Tem GPU dedicada disponível
- ✅ Precisa de modelos maiores (v8m, v8l)
- ✅ Performance do cliente é muito variável
- ✅ Já tem infraestrutura de servidor
- ✅ Precisa de controle centralizado

### Use Ambos Se:
- ✅ Quer oferecer opção aos usuários
- ✅ Precisa de fallback robusto
- ✅ Diferentes cenários de uso

---

## 🔧 Troubleshooting

### ONNX Não Carrega
```
[ONNX] ⚠️ Modelo ONNX não disponível, usando servidor backend
```

**Soluções:**
1. Verifique se `/models/yolov8n.onnx` existe
2. Confirme que o arquivo não está corrompido
3. Teste a exportação novamente com `simplify=True`
4. Verifique console do navegador para erros detalhados

### Servidor Python Não Conecta
```
TypeError: error sending request for url (http://localhost:8000/inference): 
Connection refused (os error 111)
```

**Soluções:**
1. Inicie o servidor: `python inference_server.py`
2. Verifique se porta 8000 está livre
3. Confirme firewall não está bloqueando
4. Teste: `curl http://localhost:8000/health`

### Performance Baixa (ONNX)
- Recomende navegador moderno (Chrome, Edge)
- Sugira fechar outras abas/programas
- Considere reduzir FPS de captura
- Avalie usar servidor Python como alternativa

---

## 📝 Notas Técnicas

### Formato de Detecções
Ambos os modos retornam o mesmo formato:

```typescript
interface Detection {
  class_name: string;      // "Papel/Papelão", "Metal", etc.
  material: string;        // "papel", "metal", "plastico", "vidro"
  confidence: number;      // 0-100 (percentual)
  bounding_box: {
    x: number;            // Pixel X (canto superior esquerdo)
    y: number;            // Pixel Y
    width: number;        // Largura em pixels
    height: number;       // Altura em pixels
  }
}
```

### Otimizações ONNX
O serviço ONNX implementa:
- ✅ Pré-processamento otimizado (redimensionamento + normalização)
- ✅ Pós-processamento com NMS (Non-Maximum Suppression)
- ✅ Filtragem por confiança mínima
- ✅ Conversão de coordenadas (centro → canto)
- ✅ Cache de modelo (carrega uma vez)

### Limitações Conhecidas
- ONNX Runtime Web não suporta GPU no navegador (apenas WASM/CPU)
- Alguns navegadores antigos não suportam WebAssembly SIMD
- Modelos muito grandes (>100MB) podem causar problemas de memória

---

Última atualização: 09 de Novembro de 2025
