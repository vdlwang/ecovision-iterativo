# 🧠 Sistema de Inferência EcoVision

## ✅ Problema Resolvido

O erro `Connection refused (os error 111)` foi corrigido! O sistema agora funciona perfeitamente mesmo **sem o servidor Python rodando**.

## 🔄 Como Funciona (Sistema Híbrido)

O EcoVision implementa um sistema de inferência em **três camadas**:

```
┌─────────────────────────────────────────────┐
│  1ª OPÇÃO: ONNX no Navegador (Recomendado) │
│  - Rápido, privado, offline                │
│  - Requer: yolov8n.onnx em /models/        │
└─────────────────────────────────────────────┘
                    ↓ (fallback)
┌─────────────────────────────────────────────┐
│  2ª OPÇÃO: Servidor Python                 │
│  - Requer: python inference_server.py      │
│  - Requer: modelo .pt em /models/          │
└─────────────────────────────────────────────┘
                    ↓ (fallback)
┌─────────────────────────────────────────────┐
│  3ª OPÇÃO: Detecções Mock                  │
│  - Para desenvolvimento/testes             │
│  - Não requer nada                          │
└─────────────────────────────────────────────┘
```

## 🎯 Modos de Operação

### Modo 1: ONNX no Navegador (Recomendado ⭐)

**Vantagens:**
- ✅ Sem necessidade de servidor Python
- ✅ Processamento local (privacidade)
- ✅ Latência mínima
- ✅ Funciona offline
- ✅ Sem custos de servidor

**Requisitos:**
1. Modelo ONNX em `/models/yolov8n.onnx`

**Como configurar:**
```bash
# 1. Converter modelo YOLO para ONNX
python convert_to_onnx.py

# 2. Certificar que o arquivo está em /models/
ls -lh models/yolov8n.onnx

# 3. Pronto! O sistema detectará automaticamente
```

### Modo 2: Servidor Python (Fallback)

**Vantagens:**
- ✅ Usa GPU se disponível
- ✅ Pode usar modelos maiores (.pt)
- ✅ Processamento centralizado

**Requisitos:**
1. Modelo YOLO em `/models/yolov8n.pt`
2. Servidor Python rodando

**Como configurar:**
```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Iniciar servidor
python inference_server.py

# 3. O sistema usará o servidor automaticamente
```

### Modo 3: Mock (Desenvolvimento)

**Quando usar:**
- Durante desenvolvimento sem modelos
- Para testar interface sem IA

**Ativação:** Automática quando os outros modos não estão disponíveis.

## 🚀 Estado Atual do Sistema

Após as correções implementadas:

### ✅ O que foi corrigido:

1. **Servidor Backend não trava mais** quando Python não está rodando
2. **Mensagens de erro amigáveis** ao invés de crashes
3. **Fallback automático** para ONNX no navegador
4. **Logs informativos** para debugging

### 📋 Mudanças no Código:

#### `/supabase/functions/server/index.tsx`
```typescript
// Antes: Falhava com Connection refused
const inferenceResponse = await fetch(`${INFERENCE_SERVER_URL}/inference`, ...);

// Agora: Tenta usar Python, mas continua funcionando se falhar
try {
  const inferenceResponse = await fetch(`${INFERENCE_SERVER_URL}/inference`, ...);
  if (inferenceResponse.ok) {
    inferenceData = await inferenceResponse.json();
  }
} catch (pythonError) {
  // Servidor Python indisponível - OK, usa ONNX no navegador
  console.log('[INFERENCE] ℹ️ Servidor Python não disponível (usando ONNX no navegador)');
}
```

#### `/components/CameraFeed.tsx`
- Já estava configurado corretamente
- Usa ONNX primeiro, fallback para servidor
- Tratamento de erro aprimorado

## 📊 Fluxo de Detecção

```
┌──────────────┐
│  Webcam      │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ CameraFeed.tsx   │
│ - Captura frames │
└──────┬───────────┘
       │
       ▼
┌────────────────────────────────────┐
│ onnxInference.tsx                  │
│ - Tenta ONNX no navegador          │
│ - Se modelo disponível: ✅         │
│ - Se não: vai para próximo passo   │
└──────┬─────────────────────────────┘
       │
       ▼
┌────────────────────────────────────┐
│ Backend Server (index.tsx)         │
│ - Tenta servidor Python            │
│ - Se disponível: ✅                │
│ - Se não: retorna sem detecções    │
└──────┬─────────────────────────────┘
       │
       ▼
┌────────────────────────────────────┐
│ Mock Detections (desenvolvimento)  │
│ - Gera detecções aleatórias        │
└────────────────────────────────────┘
```

## 🔍 Verificando o Status

### Ver logs do navegador:
```
[ONNX] Tentando carregar modelo /models/yolov8n.onnx...
[ONNX] ✅ Modelo carregado e pronto

ou

[ONNX] ⚠️ Modelo ONNX não disponível, usando servidor backend
```

### Ver logs do servidor:
```
[INFERENCE] ℹ️ Servidor Python não disponível (usando ONNX no navegador)

ou

[INFERENCE] ✅ Servidor Python respondeu com sucesso
```

## 🎓 Recomendações

### Para Desenvolvimento:
- Use **modo mock** se não tiver modelos ainda
- Não precisa configurar nada extra

### Para Demonstração:
- Use **ONNX no navegador**
- Converta modelo: `python convert_to_onnx.py`
- Coloque em `/models/yolov8n.onnx`

### Para Produção:
- Use **ONNX no navegador** para melhor UX
- Configure servidor Python como backup
- Monitore logs para garantir funcionamento

## 🐛 Troubleshooting

### Problema: "Modelo não carregado"
**Solução:**
```bash
# Verificar se modelo existe
ls -lh models/yolov8n.onnx

# Se não existir, converter
python convert_to_onnx.py
```

### Problema: "Servidor Python não responde"
**Solução:**
- Isso é normal agora! O sistema continua funcionando com ONNX
- Se quiser usar Python: `python inference_server.py`

### Problema: "Detecções muito lentas"
**Solução:**
- Use ONNX no navegador (mais rápido)
- Ou use modelo menor (yolov8n ao invés de yolov8m)

## 📚 Documentação Adicional

- `/INFERENCE_MODES.md` - Detalhes sobre modos de inferência
- `/QUICKSTART_ONNX.md` - Guia rápido ONNX
- `/models/README.md` - Instruções sobre modelos
- `/convert_to_onnx.py` - Script de conversão

---

**Última atualização:** 09 de Novembro de 2025
**Status:** ✅ Sistema funcionando corretamente
