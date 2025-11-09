# 🔧 Guia de Resolução de Problemas - EcoVision

## ✅ Problemas Corrigidos - Versão Atual

### 1. ❌ ERRO: ONNX - Failed to fetch WASM module

**Status:** ✅ **CORRIGIDO**

**Sintoma:**
```
[ONNX] ❌ Erro ao carregar modelo: Error: no available backend found. 
ERR: [wasm] TypeError: Failed to fetch dynamically imported module
```

**Solução implementada:**
- Sistema usa múltiplos CDNs (unpkg.com e jsdelivr.net) com fallback automático
- Desabilitado SIMD e multi-threading para máxima compatibilidade
- Fallback silencioso para modo servidor/mock se ONNX falhar
- Sistema continua funcionando normalmente mesmo sem ONNX

**Nenhuma ação necessária do usuário!**

---

### 2. ❌ ERRO: JWT Inválido (401) no Dashboard

**Status:** ✅ **CORRIGIDO**

**Sintoma:**
```
[DASHBOARD] Erro HTTP: 401
[PERFIL] Erro HTTP: 401
{"code":401,"message":"Invalid JWT"}
```

**Solução implementada:**
- Dashboard e Perfil agora detectam modo demo automaticamente
- Não fazem requisições ao servidor quando token é inválido
- Exibem avisos claros sobre limitações do modo demo
- Sistema continua funcional com interface completa

**Quando acontece:**
- Usuário está em Modo Demo (sem OAuth configurado)
- Token OAuth expirou

**Como resolver (opcional):**
- Configure Google OAuth seguindo [documentação Supabase](https://supabase.com/docs/guides/auth/social-login/auth-google)
- Ou continue usando modo demo com funcionalidade completa (apenas estatísticas históricas ficam desabilitadas)

---

### 3. ❌ ERRO: Permissão de Câmera Negada

**Status:** ✅ **MELHORADO**

**Sintoma:**
```
[CÂMERA] ❌ Erro ao iniciar câmera: NotAllowedError Permission denied
```

**Soluções implementadas:**
- Mensagens de erro detalhadas e específicas para cada tipo de erro
- Instruções passo-a-passo para resolver
- Botão "Tentar Novamente" sempre visível
- Detecção de múltiplos cenários de erro

**Como o usuário resolve:**

1. **Permissão Bloqueada** (NotAllowedError):
   - Clique no ícone 🔒 ou 📹 na barra de endereço
   - Selecione "Permitir" para câmera
   - Clique "Tentar Novamente"

2. **Câmera não encontrada** (NotFoundError):
   - Verifique se webcam está conectada
   - Teste a câmera em outro app
   - Conecte webcam externa se necessário

3. **Câmera em uso** (NotReadableError):
   - Feche Zoom, Teams, Skype
   - Feche outras abas usando câmera
   - Clique "Tentar Novamente"

4. **Contexto não seguro** (NotSupportedError):
   - Use http://localhost:5000 em desenvolvimento
   - Use HTTPS em produção

---

### 4. ❌ ERRO: Connection refused (os error 111)

**Status:** ✅ **RESOLVIDO ANTERIORMENTE**

**O que era:** Servidor backend tentava conectar ao servidor Python local.

**Solução implementada:**
- Sistema usa ONNX no navegador por padrão
- Servidor Python é opcional (fallback)
- Aplicação continua funcionando mesmo sem Python

**Nenhuma ação necessária do usuário!**

---

## 📋 Checklist de Funcionamento

### Verificação Rápida

```bash
# 1. Sistema básico funciona?
✅ Interface carrega
✅ Login funciona (Google OAuth ou Demo Mode)
✅ Câmera pode ser iniciada
✅ Sistema não trava

# 2. Inferência funciona?
□ Modelo ONNX presente (/models/yolov8n.onnx)
□ OU servidor Python rodando
□ OU modo mock ativo (para desenvolvimento)
```

---

## 🎯 Cenários Comuns

### Cenário 1: Desenvolvimento sem Modelos

**Sintoma:**
- Interface funciona
- Câmera funciona
- Detecções aparecem aleatoriamente (mock)

**Isso é normal?** ✅ **SIM!**

**Explicação:**
O sistema está em "modo desenvolvimento" usando detecções simuladas para você testar a interface.

**Para ativar IA real:**
```bash
# Opção A: ONNX no navegador (recomendado)
python convert_to_onnx.py
# Coloque o modelo em /models/yolov8n.onnx

# Opção B: Servidor Python
python inference_server.py
```

---

### Cenário 2: ONNX Carregado

**Sintoma:**
- Badge mostra: "Modo: Inferência Local (ONNX)"
- Badge verde: "✨ Rápido & Privado"
- Detecções rápidas e precisas

**Isso é normal?** ✅ **SIM! Melhor cenário!**

**Você está usando:**
- Inferência no navegador
- Processamento local
- Máxima privacidade
- Mínima latência

**Tudo funcionando perfeitamente! 🎉**

---

### Cenário 3: Servidor Python Ativo

**Sintoma:**
- Badge mostra: "Modo: Servidor Backend (Python)"
- Console mostra: "[INFERENCE] ✅ Servidor Python respondeu com sucesso"
- Detecções funcionam

**Isso é normal?** ✅ **SIM!**

**Você está usando:**
- Servidor Python local
- Modelo .pt (PyTorch)
- Pode usar GPU se disponível

**Funcionando corretamente!**

---

### Cenário 4: Nenhum Modelo (Mock)

**Sintoma:**
- Badge mostra: "Modo: Servidor Backend / Mock"
- Badge amarelo: "⚠️ Requer modelo"
- Info azul: "Sistema funcionando em modo de desenvolvimento"
- Detecções aparecem aleatoriamente

**Isso é normal?** ✅ **SIM para desenvolvimento!**

**O que fazer:**
1. **Para desenvolvimento:** Nada, continue testando a UI
2. **Para produção:** Configure ONNX ou servidor Python

---

## 🚨 Problemas Reais

### Problema: Câmera não inicia

**Sintomas:**
- Botão "Iniciar Câmera" não funciona
- Erro de permissão
- Tela preta

**Soluções:**

1. **Verificar permissões do navegador:**
```
Chrome: Configurações > Privacidade > Configurações do site > Câmera
Firefox: Preferências > Privacidade > Permissões > Câmera
```

2. **Verificar se outra aplicação está usando a câmera:**
```bash
# Feche outras aplicações que usam câmera:
- Zoom, Teams, Skype
- OBS, StreamLabs
- Outras abas do navegador
```

3. **Testar câmera no navegador:**
```
Abra: chrome://settings/content/camera
Teste a câmera
```

4. **HTTPS necessário:**
```
⚠️ Navegadores modernos requerem HTTPS para câmera
✅ localhost é permitido em HTTP
❌ IP local (192.168.x.x) requer HTTPS
```

---

### Problema: Login não funciona

**Sintomas:**
- Botão Google não responde
- Erro de autenticação
- Token inválido

**Soluções:**

1. **Usar Demo Mode:**
```typescript
// Sempre funciona, sem configuração
Clique em "Entrar em Modo Demo"
```

2. **Configurar Google OAuth:**
```
Siga: https://supabase.com/docs/guides/auth/social-login/auth-google

Passos:
1. Criar projeto no Google Cloud Console
2. Configurar OAuth 2.0
3. Adicionar credenciais no Supabase
4. Configurar redirect URLs
```

3. **Verificar Supabase:**
```bash
# Verificar se variáveis de ambiente existem
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY
```

---

### Problema: Detecções não aparecem

**Sintomas:**
- Câmera funciona
- Sistema rodando
- Nenhuma detecção aparece

**Diagnóstico:**

1. **Verificar logs do navegador (F12):**
```javascript
// Procure por:
[ONNX] ✅ Modelo carregado e pronto
// ou
[INFERENCE] ✅ Servidor Python respondeu com sucesso
// ou
[INFERÊNCIA MOCK] Detecção simulada
```

2. **Verificar qual modo está ativo:**
```
Badge no feed da câmera mostra o modo atual
```

3. **Soluções por modo:**

**Se modo ONNX:**
```bash
# Verificar modelo existe
ls -lh models/yolov8n.onnx

# Se não existe
python convert_to_onnx.py
```

**Se modo Servidor:**
```bash
# Verificar servidor rodando
curl http://localhost:8000/health

# Se não responde
python inference_server.py
```

**Se modo Mock:**
```
Detecções mock aparecem aleatoriamente (30% chance)
Isso é normal para desenvolvimento
```

---

### Problema: Detecções muito lentas

**Sintomas:**
- Delay de vários segundos
- FPS muito baixo
- Interface travando

**Soluções:**

1. **Usar ONNX ao invés de Servidor:**
```bash
python convert_to_onnx.py
# ONNX é muito mais rápido no navegador
```

2. **Usar modelo menor:**
```python
# Ao invés de yolov8m.pt (médio)
# Use yolov8n.pt (nano)
```

3. **Verificar hardware:**
```
Chrome DevTools > Performance
Verificar uso de CPU/Memória
```

4. **Ajustar intervalo de inferência:**
```typescript
// Em CameraFeed.tsx
const interval = setInterval(async () => {
  // Aumentar de 100ms para 500ms se necessário
}, 500);
```

---

### Problema: Detecções imprecisas

**Sintomas:**
- Muitos falsos positivos
- Material errado detectado
- Confiança muito baixa

**Soluções:**

1. **Ajustar threshold de confiança:**
```
Interface > Precisão Mínima
Aumentar de 85% para 90-95%
```

2. **Melhorar iluminação:**
```
- Luz adequada no ambiente
- Evitar contraluz
- Iluminação uniforme
```

3. **Treinar modelo melhor:**
```bash
# Dataset maior e mais diverso
# Mais épocas de treinamento
# Data augmentation adequado
```

4. **Usar modelo maior:**
```python
# yolov8n.pt → yolov8s.pt → yolov8m.pt
# Maior = mais preciso (mas mais lento)
```

---

## 🔍 Logs e Debug

### Habilitar logs detalhados

**Navegador (Console F12):**
```javascript
// Filtros úteis:
[ONNX]       - Inferência ONNX
[INFERENCE]  - Servidor backend
[CÂMERA]     - Câmera e stream
[AUTH]       - Autenticação
```

**Servidor:**
```bash
# Ver logs do Supabase Edge Function
# No console do Supabase: Functions > server > Logs
```

**Python (se usando):**
```bash
# Modo verbose
python inference_server.py --verbose
```

### Comandos úteis de debug

```bash
# 1. Verificar estrutura de arquivos
tree -L 2

# 2. Verificar modelos
ls -lh models/

# 3. Verificar porta do servidor Python
netstat -an | grep 8000

# 4. Testar servidor Python
curl -X POST http://localhost:8000/inference \
  -H "Content-Type: application/json" \
  -d '{"image_base64":"test","model_version":"YOLOv8n","min_confidence":0.85}'

# 5. Verificar dependências Python
pip list | grep -E "ultralytics|onnx|torch"
```

---

## 📞 Onde Buscar Ajuda

### Documentação do Sistema

1. `/SISTEMA_INFERENCIA.md` - Como funciona a inferência
2. `/INFERENCE_MODES.md` - Modos de operação
3. `/QUICKSTART_ONNX.md` - Guia rápido ONNX
4. `/models/README.md` - Modelos e treinamento
5. `/diagrams/README.md` - Arquitetura do sistema

### Verificação de Status

```bash
# Script de teste completo (se existir)
python test_setup.py

# Verificar saúde do servidor
curl http://localhost:8000/health
```

### Logs Importantes

**Sucesso com ONNX:**
```
[ONNX] Tentando carregar modelo /models/yolov8n.onnx...
[ONNX] ✅ Modelo carregado com sucesso
[ONNX] ✅ Inferência concluída: 1 detecção(ões) em 45.2ms
```

**Sucesso com Python:**
```
[INFERENCE] Tentando servidor Python em http://localhost:8000...
[INFERENCE] ✅ Servidor Python respondeu com sucesso
```

**Modo desenvolvimento (OK):**
```
[ONNX] ⚠️ Modelo ONNX não disponível, usando servidor backend
[INFERENCE] ℹ️ Servidor Python não disponível (usando ONNX no navegador)
[INFERÊNCIA MOCK] Detecção simulada: plastico (85.3%)
```

---

## ✨ Dicas de Performance

### Melhor Performance

1. **Use ONNX no navegador** (mais rápido)
2. **Use modelo nano (yolov8n)** (mais rápido)
3. **Boa iluminação** (menos ruído)
4. **Navegador moderno** (Chrome 90+, Firefox 88+)

### Melhor Precisão

1. **Use modelo médio (yolov8m)** (mais preciso)
2. **Servidor Python com GPU** (se disponível)
3. **Confiança mínima alta** (90%+)
4. **Bom dataset de treinamento**

### Balanceamento

1. **Use modelo small (yolov8s)**
2. **ONNX no navegador**
3. **Confiança mínima 85-90%**
4. **Iluminação controlada**

---

**Última atualização:** 09 de Novembro de 2025
**Versão do Sistema:** 5.0 (ONNX + Servidor Híbrido)
