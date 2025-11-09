# 🚀 EcoVision - Quick Start

Guia rápido para colocar o EcoVision rodando em **menos de 10 minutos**.

## ⚡ Início Rápido (TL;DR)

```bash
# 1. Clone e entre na pasta
cd ecovision

# 2. Crie ambiente virtual Python
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# ou: venv\Scripts\activate  # Windows

# 3. Instale dependências Python
pip install -r requirements.txt

# 4. Teste instalação
python test_setup.py

# 5. Inicie servidor de inferência
python inference_server.py

# 6. Em outro terminal, inicie frontend
npm run dev
```

Abra http://localhost:5173 e faça login!

---

## 📋 Pré-requisitos Mínimos

- ✅ **Python 3.8+** ([download](https://www.python.org/downloads/))
- ✅ **Node.js 18+** ([download](https://nodejs.org/))
- ✅ **Webcam** (integrada ou USB)
- ✅ **8GB RAM**
- ⚠️ **GPU NVIDIA** (opcional, mas recomendado para velocidade)

---

## 🎯 Passo a Passo Detalhado

### 1️⃣ Verificar Instalações

```bash
# Verificar Python
python3 --version
# Esperado: Python 3.8.x ou superior

# Verificar Node.js
node --version
# Esperado: v18.x.x ou superior

# Verificar pip
pip3 --version
```

Se algum comando falhar, instale o software necessário.

### 2️⃣ Configurar Ambiente Python

#### macOS/Linux:
```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate

# Você deve ver (venv) no início do prompt
```

#### Windows:
```cmd
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
venv\Scripts\activate

# Você deve ver (venv) no início do prompt
```

### 3️⃣ Instalar Dependências

```bash
# Atualizar pip
pip install --upgrade pip

# Instalar dependências (pode levar 5-10 min)
pip install -r requirements.txt
```

**O que está sendo instalado:**
- FastAPI (servidor web)
- Ultralytics YOLO (IA de detecção)
- OpenCV (processamento de imagem)
- PyTorch (backend de ML)

### 4️⃣ Testar Instalação

```bash
python test_setup.py
```

**Saída esperada:**
```
============================================================
  EcoVision - Verificação de Instalação
============================================================

🐍 Verificando versão do Python...
   Versão: 3.11.0
   ✅ Versão compatível!

📦 Verificando dependências...
   ✅ FastAPI: 0.104.1
   ✅ Uvicorn: 0.24.0
   ✅ Ultralytics: 8.0.230
   ✅ OpenCV: 4.8.1
   ✅ PyTorch: 2.1.0
   ...

🎮 Verificando suporte CUDA (GPU)...
   ✅ CUDA disponível!
   GPU: NVIDIA GeForce RTX 3060

📹 Verificando acesso à webcam...
   ✅ Webcam detectada!
   Resolução: 1920x1080

🎉 PARABÉNS! Tudo está configurado corretamente!
```

### 5️⃣ Iniciar Servidor de Inferência

#### Opção A: Script automático (recomendado)

**macOS/Linux:**
```bash
chmod +x run_dev.sh
./run_dev.sh
```

**Windows:**
```cmd
run_dev.bat
```

#### Opção B: Manual

```bash
python inference_server.py
```

**Você deve ver:**
```
    ╔═══════════════════════════════════════════╗
    ║   EcoVision Inference Server              ║
    ║   Detecção de Materiais Recicláveis       ║
    ║   Powered by Ultralytics YOLO             ║
    ╚═══════════════════════════════════════════╝

🚀 Iniciando EcoVision Inference Server...
📥 Baixando modelo YOLOv8n...
✅ Modelo YOLOv8n carregado com sucesso!
✅ Servidor pronto!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 6️⃣ Testar Servidor Python

**Em outro terminal:**

```bash
curl http://localhost:8000/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "current_model": "YOLOv8n",
  "timestamp": "2025-11-09T12:34:56.789Z"
}
```

✅ Se recebeu essa resposta, o servidor está funcionando!

### 7️⃣ Configurar Backend Supabase

O backend já está deployado! Você só precisa configurar a variável de ambiente:

```bash
# Criar arquivo .env na raiz
echo "INFERENCE_SERVER_URL=http://localhost:8000" > .env
```

### 8️⃣ Iniciar Frontend

**Em outro terminal:**

```bash
# Instalar dependências (primeira vez)
npm install

# Iniciar servidor de desenvolvimento
npm run dev
```

**Você deve ver:**
```
  VITE v4.x.x  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### 9️⃣ Acessar Aplicação

1. Abra navegador em: **http://localhost:5173**
2. Clique em **"Entrar com Google"**
3. Faça login com sua conta Google
4. Você será redirecionado para o **Monitor**

### 🔟 Testar Detecção

1. Vá para aba **"Monitor"**
2. Permita acesso à webcam quando solicitado
3. Clique em **"Iniciar Sistema"**
4. Coloque objetos recicláveis na frente da câmera:
   - 📄 Papel/livro
   - 🥫 Lata
   - 🍾 Garrafa plástica
   - 🍷 Copo de vidro
5. Observe as detecções aparecerem em tempo real!

**Console do navegador (F12):**
```
[CÂMERA] 1 câmera(s) detectada(s): ["Integrated Webcam"]
[INFERÊNCIA] Enviando frame para modelo YOLOv8n (confiança mínima: 85%)
[INFERÊNCIA] 2 detecção(ões) em 152ms: plastico (92.3%), papel (88.1%)
```

---

## 🎨 Próximos Passos

### ✅ Sistema Funcionando!

Agora você pode:

1. **Configurar Cancelas**
   - Vá para aba "Cancelas"
   - Configure quais materiais cada cancela deve separar

2. **Ajustar Modelo**
   - Vá para aba "Modelo"
   - Ajuste confiança mínima (85% recomendado)
   - Teste diferentes modelos (n, s, m)

3. **Ver Estatísticas**
   - Vá para aba "Dashboard"
   - Veja detecções em tempo real
   - Analise gráficos de performance

### 📚 Documentação Completa

- [WEBCAM_INFERENCE_SETUP.md](./WEBCAM_INFERENCE_SETUP.md) - Guia completo de configuração
- [API.md](./API.md) - Documentação da API
- [models/README.md](./models/README.md) - Como treinar modelos customizados

---

## ❓ Problemas Comuns

### "ModuleNotFoundError: No module named 'ultralytics'"

**Solução:**
```bash
# Verificar se ambiente virtual está ativo
which python  # Deve mostrar caminho com 'venv'

# Ativar ambiente virtual
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstalar
pip install -r requirements.txt
```

### "Webcam não detectada"

**Soluções:**
1. Verificar permissões do navegador
2. Usar HTTPS ou localhost
3. Testar com: `python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`

### "Servidor Python não inicia"

**Soluções:**
1. Verificar se porta 8000 está livre: `lsof -i :8000`
2. Verificar logs: `cat logs/inference.log`
3. Reinstalar dependências: `pip install -r requirements.txt --force-reinstall`

### "Dashboard não mostra dados"

**Soluções:**
1. Verificar se fez login
2. Fazer pelo menos uma detecção primeiro
3. Clicar em "Atualizar" no dashboard
4. Verificar console (F12) por erros

---

## 🆘 Ajuda

Se ainda tiver problemas:

1. **Verificar logs:**
   ```bash
   # Servidor Python
   tail -f logs/inference.log
   
   # Console do navegador
   F12 > Console
   ```

2. **Executar diagnóstico:**
   ```bash
   python test_setup.py
   ```

3. **Consultar documentação completa:**
   - [WEBCAM_INFERENCE_SETUP.md](./WEBCAM_INFERENCE_SETUP.md)
   - [Troubleshooting](./WEBCAM_INFERENCE_SETUP.md#-troubleshooting)

---

## 🎉 Sucesso!

Se chegou até aqui, parabéns! Seu EcoVision está funcionando!

**Checklist final:**
- [x] Servidor Python rodando (http://localhost:8000)
- [x] Frontend rodando (http://localhost:5173)
- [x] Login funcionando
- [x] Webcam detectada
- [x] Detecções aparecendo
- [x] Dados salvando no banco
- [x] Dashboard mostrando estatísticas

**Próximo nível:**
- Treinar modelo customizado ([models/README.md](./models/README.md))
- Deploy em produção ([WEBCAM_INFERENCE_SETUP.md#-deploy-em-produção](./WEBCAM_INFERENCE_SETUP.md#-deploy-em-produção))
- Integrar ESP32 para controle físico de cancelas

---

**Desenvolvido com ❤️ para reciclagem inteligente**
