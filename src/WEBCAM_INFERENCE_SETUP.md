# 🎥 EcoVision - Guia Completo de Configuração de Webcam e Inferência YOLO

Este guia irá te ajudar a configurar completamente a captura de webcam/câmera e o servidor de inferência com Ultralytics YOLO para detecção de materiais recicláveis em tempo real.

## 📋 Índice

1. [Visão Geral da Arquitetura](#-visão-geral-da-arquitetura)
2. [Pré-requisitos](#-pré-requisitos)
3. [Instalação do Servidor de Inferência Python](#-instalação-do-servidor-de-inferência-python)
4. [Configuração dos Modelos YOLO](#-configuração-dos-modelos-yolo)
5. [Configuração do Backend Supabase](#-configuração-do-backend-supabase)
6. [Testando a Integração](#-testando-a-integração)
7. [Uso Local (Desenvolvimento)](#-uso-local-desenvolvimento)
8. [Deploy em Produção](#-deploy-em-produção)
9. [Troubleshooting](#-troubleshooting)
10. [API Reference](#-api-reference)

---

## 🏗️ Visão Geral da Arquitetura

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│                 │      │                  │      │                     │
│  Frontend React │─────▶│  Backend Hono    │─────▶│  Servidor Python    │
│  (Webcam)       │      │  (Supabase Edge) │      │  (FastAPI+YOLO)     │
│                 │      │                  │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
        │                         │                          │
        │                         │                          │
        ▼                         ▼                          ▼
 Captura frames          Autentica usuário         Processa com
 da webcam em            Salva no PostgreSQL       Ultralytics YOLO
 base64 (2s)             Retorna detecções         Retorna bounding boxes
```

### Fluxo de Dados:

1. **Frontend** captura frames da webcam a cada 2 segundos
2. Converte frame para **base64**
3. Envia para **Backend** com token de autenticação
4. **Backend** repassa para **Servidor Python**
5. **Servidor Python** processa com modelo YOLO
6. Retorna detecções (material, confiança, bounding box)
7. **Backend** salva no banco PostgreSQL
8. **Frontend** renderiza bounding boxes e atualiza estatísticas

---

## ✅ Pré-requisitos

### Sistema Operacional
- Windows 10/11, macOS 10.15+, ou Linux (Ubuntu 20.04+)

### Software Necessário

#### 1. Python 3.8 - 3.11
```bash
# Verificar versão do Python
python --version
# ou
python3 --version

# Deve retornar: Python 3.8.x, 3.9.x, 3.10.x ou 3.11.x
```

**Instalação:**
- **Windows**: https://www.python.org/downloads/
- **macOS**: `brew install python@3.11`
- **Linux**: `sudo apt install python3.11 python3.11-venv`

#### 2. pip (gerenciador de pacotes Python)
```bash
# Verificar versão do pip
pip --version
# ou
pip3 --version
```

#### 3. Node.js 18+ (para o frontend)
```bash
node --version  # Deve ser v18.x ou superior
npm --version
```

#### 4. Git
```bash
git --version
```

### Hardware Recomendado

#### Mínimo:
- **CPU**: Intel i5 / AMD Ryzen 5 ou superior
- **RAM**: 8GB
- **Webcam**: Qualquer webcam USB ou integrada
- **GPU**: Não é obrigatória, mas recomendada

#### Recomendado:
- **CPU**: Intel i7 / AMD Ryzen 7 ou superior
- **RAM**: 16GB
- **Webcam**: 1080p (Full HD)
- **GPU**: NVIDIA GPU com CUDA (para inferência rápida)
  - GTX 1060 6GB ou superior
  - RTX 2060 ou superior (ideal)

---

## 🐍 Instalação do Servidor de Inferência Python

### Passo 1: Clone o Repositório

```bash
# Clone o repositório (ou navegue até a pasta do projeto)
cd /caminho/para/ecovision
```

### Passo 2: Crie um Ambiente Virtual Python

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**Você deve ver `(venv)` no início do prompt do terminal.**

### Passo 3: Instale as Dependências

```bash
# Atualizar pip
pip install --upgrade pip

# Instalar dependências do requirements.txt
pip install -r requirements.txt
```

**O que será instalado:**
- `fastapi` - Framework web para API
- `uvicorn` - Servidor ASGI
- `ultralytics` - Framework YOLO v8
- `opencv-python` - Processamento de imagem
- `Pillow` - Manipulação de imagem
- `torch` - PyTorch (backend de ML)
- `torchvision` - Visão computacional

⏱️ **Tempo estimado**: 5-15 minutos (dependendo da conexão)

### Passo 4: Verificar Instalação

```bash
python -c "import ultralytics; print(ultralytics.__version__)"
# Deve imprimir: 8.0.230 (ou similar)

python -c "import torch; print('CUDA disponível:', torch.cuda.is_available())"
# Imprime True se tiver GPU NVIDIA com CUDA, False caso contrário
```

---

## 🤖 Configuração dos Modelos YOLO

### Opção 1: Usar Modelos Pré-treinados COCO (Mais Rápido)

Os modelos YOLO v8 serão **baixados automaticamente** na primeira execução.

**Modelos disponíveis:**
- `YOLOv8n` (nano) - Mais rápido, menos preciso (~6 MB)
- `YOLOv8s` (small) - Balanceado (~22 MB)
- `YOLOv8m` (medium) - Mais preciso, mais lento (~52 MB)

**Classes COCO mapeadas para materiais:**
```python
# Papel/Papelão
"book", "newspaper", "cardboard" → papel

# Metal
"can", "fork", "knife", "spoon" → metal

# Plástico
"bottle", "cup", "plastic_bag" → plastico

# Vidro
"wine glass", "glass", "jar" → vidro
```

### Opção 2: Usar Modelos Customizados (.pt)

Se você tem modelos treinados especificamente para reciclagem:

#### 2.1. Criar pasta de modelos

```bash
mkdir -p models
```

#### 2.2. Adicionar seus arquivos .pt

Coloque seus modelos na pasta `/models`:

```
models/
├── yolov8n.pt      # Modelo nano customizado
├── yolov8s.pt      # Modelo small customizado
├── yolov8m.pt      # Modelo medium customizado
└── README.md
```

#### 2.3. Atualizar mapeamento de classes (se necessário)

Edite `/inference_server.py`, linha 29-50:

```python
CLASS_TO_MATERIAL = {
    # Suas classes customizadas
    "papel": "papel",
    "papelao": "papel",
    "lata": "metal",
    "aluminio": "metal",
    "pet": "plastico",
    "plastico_duro": "plastico",
    "vidro_transparente": "vidro",
    "vidro_colorido": "vidro",
    # ... adicione suas classes
}
```

### Download Manual de Modelos

Se preferir baixar manualmente:

```bash
# YOLOv8n (6.2 MB)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# YOLOv8s (21.5 MB)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt

# YOLOv8m (49.7 MB)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt

# Mover para pasta models
mv yolov8*.pt models/
```

---

## 🚀 Configuração do Backend Supabase

### Passo 1: Configurar Variável de Ambiente

O backend precisa saber onde está o servidor Python de inferência.

#### Desenvolvimento Local:

Crie arquivo `.env` na raiz:

```bash
INFERENCE_SERVER_URL=http://localhost:8000
```

#### Produção (Supabase):

```bash
# Via CLI do Supabase
supabase secrets set INFERENCE_SERVER_URL=https://seu-servidor-python.com

# Ou via Dashboard Supabase:
# 1. Vá para Project Settings > Edge Functions
# 2. Adicione variável: INFERENCE_SERVER_URL
```

### Passo 2: Verificar Tabelas do Banco

O banco já foi configurado com as tabelas necessárias através da migração `001_create_ecovision_tables.sql`:

```sql
-- Tabelas criadas:
✓ profiles
✓ user_sessions
✓ inferences
✓ system_config
✓ statistics
✓ system_logs
```

Para verificar:

```bash
# Via Supabase CLI
supabase db pull

# Ou via SQL Editor no Dashboard
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';
```

---

## 🧪 Testando a Integração

### Teste 1: Servidor Python Standalone

#### 1.1. Inicie o servidor

```bash
# Ative o ambiente virtual (se não estiver ativo)
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate  # Windows

# Inicie o servidor
python inference_server.py
```

**Saída esperada:**
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
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 1.2. Teste de health check

Em **outro terminal**:

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

#### 1.3. Teste de inferência com imagem

```bash
# Baixe uma imagem de teste
curl -o test.jpg https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=640

# Teste inferência
curl -X POST http://localhost:8000/inference/file \
  -F "file=@test.jpg" \
  -F "model_version=YOLOv8n" \
  -F "min_confidence=0.5"
```

**Resposta esperada:**
```json
{
  "success": true,
  "detections": [
    {
      "class_name": "bottle",
      "material": "plastico",
      "confidence": 87.5,
      "bounding_box": {
        "x": 120.5,
        "y": 80.3,
        "width": 150.2,
        "height": 300.8
      }
    }
  ],
  "processing_time_ms": 145,
  "model_version": "YOLOv8n",
  "timestamp": "2025-11-09T12:35:10.123Z",
  "image_shape": [640, 480, 3]
}
```

### Teste 2: Integração Frontend → Backend → Python

#### 2.1. Inicie os servidores

**Terminal 1** - Servidor Python:
```bash
python inference_server.py
```

**Terminal 2** - Frontend (Figma Make ou desenvolvimento local):
```bash
npm run dev
```

**Terminal 3** - Backend Supabase (se local):
```bash
supabase functions serve
```

#### 2.2. Teste no navegador

1. Abra a aplicação: `http://localhost:5173` (ou URL do Figma Make)
2. Faça login com Google
3. Vá para a aba **Monitor**
4. Clique em **Iniciar Sistema**
5. Permita acesso à webcam quando solicitado
6. Observe o console do navegador (F12):

```javascript
[CÂMERA] 1 câmera(s) detectada(s): ["Integrated Webcam"]
[CÂMERA] Stream iniciada - Câmera: Integrated Webcam
[INFERÊNCIA] Enviando frame para modelo YOLOv8n (confiança mínima: 85%)
[INFERÊNCIA] 2 detecção(ões) em 152ms: plastico (92.3%), papel (88.1%)
[BD] Detecção registrada para usuário abc123
```

7. Observe o console do servidor Python:

```
INFO:     127.0.0.1:54321 - "POST /inference HTTP/1.1" 200 OK
✅ Inferência processada: 2 detecções em 152ms
```

### Teste 3: Verificar Dados no Banco

```sql
-- Via Supabase SQL Editor
SELECT * FROM inferences ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM user_sessions ORDER BY started_at DESC LIMIT 5;
SELECT * FROM statistics ORDER BY date DESC LIMIT 7;
```

---

## 💻 Uso Local (Desenvolvimento)

### Configuração Completa de Desenvolvimento

#### 1. Estrutura de pastas

```
ecovision/
├── venv/                    # Ambiente virtual Python
├── models/                  # Modelos YOLO (.pt)
├── inference_server.py      # Servidor de inferência
├── requirements.txt         # Dependências Python
├── .env                     # Variáveis de ambiente
├── src/                     # Frontend React
│   ├── App.tsx
│   ├── components/
│   └── ...
└── supabase/                # Backend
    ├── functions/
    └── migrations/
```

#### 2. Arquivo .env completo

```bash
# Servidor de Inferência
INFERENCE_SERVER_URL=http://localhost:8000

# Supabase (copie do dashboard)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Opcional: Google OAuth
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
```

#### 3. Scripts úteis

Crie arquivo `package.json` com scripts:

```json
{
  "scripts": {
    "dev": "vite",
    "dev:python": "python inference_server.py",
    "dev:all": "concurrently \"npm run dev\" \"npm run dev:python\"",
    "test:inference": "curl http://localhost:8000/health"
  }
}
```

#### 4. Executar tudo simultaneamente

```bash
# Instalar concurrently (se não tiver)
npm install -D concurrently

# Executar frontend + servidor Python
npm run dev:all
```

---

## 🌐 Deploy em Produção

### Opção 1: Servidor Python no Render/Railway

#### Render.com (Recomendado - Free tier disponível)

1. **Criar `render.yaml`:**

```yaml
services:
  - type: web
    name: ecovision-inference
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python inference_server.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

2. **Deploy:**
   - Conecte repositório ao Render
   - Selecione branch
   - Deploy automático

3. **Obter URL:**
   - Copie URL: `https://ecovision-inference.onrender.com`

4. **Configurar no Supabase:**

```bash
supabase secrets set INFERENCE_SERVER_URL=https://ecovision-inference.onrender.com
```

### Opção 2: Servidor Python no Heroku

```bash
# Login no Heroku
heroku login

# Criar app
heroku create ecovision-inference

# Deploy
git push heroku main

# Obter URL
heroku info -s | grep web_url

# Configurar no Supabase
supabase secrets set INFERENCE_SERVER_URL=https://ecovision-inference.herokuapp.com
```

### Opção 3: VPS (DigitalOcean, AWS EC2, etc)

```bash
# Conectar ao servidor
ssh user@seu-servidor.com

# Instalar Python e dependências
sudo apt update
sudo apt install python3.11 python3.11-venv nginx

# Clonar repositório
git clone https://github.com/seu-usuario/ecovision.git
cd ecovision

# Configurar ambiente virtual
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Criar serviço systemd
sudo nano /etc/systemd/system/ecovision.service
```

**Conteúdo do arquivo:**
```ini
[Unit]
Description=EcoVision Inference Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ecovision
Environment="PATH=/home/ubuntu/ecovision/venv/bin"
ExecStart=/home/ubuntu/ecovision/venv/bin/python inference_server.py

[Install]
WantedBy=multi-user.target
```

```bash
# Iniciar serviço
sudo systemctl enable ecovision
sudo systemctl start ecovision
sudo systemctl status ecovision

# Configurar Nginx como proxy reverso
sudo nano /etc/nginx/sites-available/ecovision
```

**Configuração Nginx:**
```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Ativar configuração
sudo ln -s /etc/nginx/sites-available/ecovision /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Configurar HTTPS (Opcional mas Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado SSL
sudo certbot --nginx -d seu-dominio.com
```

---

## 🐛 Troubleshooting

### Problema 1: "ModuleNotFoundError: No module named 'ultralytics'"

**Solução:**
```bash
# Verificar se ambiente virtual está ativo
which python  # Deve mostrar caminho com 'venv'

# Se não estiver ativo
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstalar dependências
pip install -r requirements.txt
```

### Problema 2: "torch.cuda.is_available() retorna False" (GPU não detectada)

**Solução:**

```bash
# Verificar instalação CUDA
nvidia-smi

# Se CUDA não instalado:
# 1. Instalar CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
# 2. Reinstalar PyTorch com suporte CUDA:

pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Problema 3: "Webcam não detectada no navegador"

**Soluções:**

1. **Verificar permissões:**
   - Chrome: `chrome://settings/content/camera`
   - Firefox: `about:preferences#privacy`
   - Permitir acesso para o domínio

2. **HTTPS obrigatório:**
   - Webcam só funciona em HTTPS (exceto localhost)
   - Use ngrok para desenvolvimento: `ngrok http 3000`

3. **Testar webcam:**
   ```javascript
   // Cole no console do navegador (F12)
   navigator.mediaDevices.enumerateDevices()
     .then(devices => console.log(devices.filter(d => d.kind === 'videoinput')))
   ```

### Problema 4: "CORS Error" ao chamar servidor Python

**Solução:**

Verifique se CORS está configurado no `inference_server.py`:

```python
# Linha 45-52
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Problema 5: "Servidor Python lento (>5s por inferência)"

**Soluções:**

1. **Usar GPU:**
   ```bash
   python -c "import torch; print('CUDA:', torch.cuda.is_available())"
   # Se False, instalar CUDA
   ```

2. **Usar modelo mais leve:**
   - Trocar de `YOLOv8m` para `YOLOv8n`
   - No frontend, selecionar "YOLOv8n" em Modelo

3. **Reduzir resolução da webcam:**
   ```typescript
   // Em CameraFeed.tsx, linha 88-91
   video: {
     deviceId: selectedDevice ? { exact: selectedDevice } : undefined,
     width: { ideal: 640 },   // Reduzir de 1920
     height: { ideal: 480 }   // Reduzir de 1080
   }
   ```

4. **Aumentar intervalo de captura:**
   ```typescript
   // Em CameraFeed.tsx, linha 201
   }, 5000); // Aumentar de 2000ms para 5000ms (5 segundos)
   ```

### Problema 6: "Banco de dados não salva detecções"

**Diagnóstico:**

```bash
# Verificar logs do backend
supabase functions logs make-server-ea835390

# Verificar tabela inferences
psql $DATABASE_URL -c "SELECT COUNT(*) FROM inferences;"
```

**Solução:**

1. **Verificar autenticação:**
   ```javascript
   // Console do navegador
   const token = await supabase.auth.getSession()
   console.log('Token:', token)
   ```

2. **Verificar permissões RLS:**
   ```sql
   -- Desabilitar temporariamente para testar
   ALTER TABLE inferences DISABLE ROW LEVEL SECURITY;
   
   -- Reabilitar depois com políticas corretas
   ALTER TABLE inferences ENABLE ROW LEVEL SECURITY;
   ```

### Problema 7: "Dashboard não mostra dados"

**Solução:**

1. **Verificar endpoint de estatísticas:**
   ```bash
   curl -H "Authorization: Bearer SEU_TOKEN" \
     https://seu-projeto.supabase.co/functions/v1/make-server-ea835390/stats
   ```

2. **Verificar dados no banco:**
   ```sql
   SELECT COUNT(*) FROM inferences;
   SELECT material_detected, COUNT(*) 
   FROM inferences 
   GROUP BY material_detected;
   ```

3. **Forçar atualização:**
   - Clicar no botão "Atualizar" no Dashboard
   - Ou fazer logout/login

---

## 📚 API Reference

### Servidor Python - Endpoints

#### GET /health
Health check do servidor

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "current_model": "YOLOv8n",
  "timestamp": "2025-11-09T12:34:56Z"
}
```

#### GET /models
Lista modelos disponíveis

**Response:**
```json
{
  "available_models": ["YOLOv8n", "YOLOv8s", "YOLOv8m"],
  "current_model": "YOLOv8n",
  "model_path": "./models/yolov8n.pt"
}
```

#### POST /models/load
Carrega um modelo específico

**Request:**
```json
{
  "model_version": "YOLOv8s"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Modelo YOLOv8s carregado com sucesso",
  "current_model": "YOLOv8s"
}
```

#### POST /inference
Processa imagem base64

**Request:**
```json
{
  "image_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "model_version": "YOLOv8n",
  "min_confidence": 0.85
}
```

**Response:**
```json
{
  "success": true,
  "detections": [
    {
      "class_name": "bottle",
      "material": "plastico",
      "confidence": 92.3,
      "bounding_box": {
        "x": 120.5,
        "y": 80.3,
        "width": 150.2,
        "height": 300.8
      }
    }
  ],
  "processing_time_ms": 145,
  "model_version": "YOLOv8n",
  "timestamp": "2025-11-09T12:34:56Z",
  "image_shape": [1920, 1080, 3]
}
```

#### POST /inference/file
Processa arquivo de imagem

**Request (multipart/form-data):**
- `file`: Arquivo de imagem (jpg, png, etc)
- `model_version`: "YOLOv8n" | "YOLOv8s" | "YOLOv8m"
- `min_confidence`: 0.0 - 1.0

**Response:** Mesmo formato de `/inference`

### Backend Supabase - Endpoints

#### POST /make-server-ea835390/config
Salva configuração do sistema

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "gateConfigs": {
    "1": "papel",
    "2": "plastico",
    "3": "metal"
  },
  "minAccuracy": 85,
  "modelVersion": "YOLOv8n"
}
```

#### GET /make-server-ea835390/config
Obtém configuração ativa

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "config": {
    "gate_1_material": "papel",
    "gate_2_material": "plastico",
    "gate_3_material": "metal",
    "min_confidence": 85,
    "model_version": "YOLOv8n"
  }
}
```

#### POST /make-server-ea835390/inference
Processa inferência (proxy para servidor Python)

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "image_base64": "...",
  "model_version": "YOLOv8n",
  "min_confidence": 85
}
```

**Response:**
```json
{
  "success": true,
  "detections": [...],
  "processing_time_ms": 145,
  "saved_to_database": true
}
```

#### GET /make-server-ea835390/stats
Obtém estatísticas do usuário

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total": 1234,
    "byMaterial": {
      "papel": 345,
      "metal": 123,
      "plastico": 567,
      "vidro": 199
    },
    "byGate": {
      "1": 345,
      "2": 567,
      "3": 322
    },
    "avgConfidence": 87.5,
    "recentDetections": [...],
    "totalSessions": 12
  }
}
```

---

## 🎯 Próximos Passos

Após configuração completa:

1. **Otimizar Performance:**
   - Treinar modelo customizado para reciclagem
   - Usar GPU para inferência mais rápida
   - Implementar cache de frames

2. **Melhorar Precisão:**
   - Coletar dataset de imagens de reciclagem
   - Fine-tuning do YOLO com Roboflow
   - Aumentar dataset com augmentation

3. **Adicionar Features:**
   - Upload de imagens/vídeos
   - Histórico de detecções
   - Relatórios PDF
   - Notificações em tempo real

4. **Integração ESP32:**
   - Conectar via Serial/USB
   - Enviar comandos para cancelas
   - Ler sensores de peso

---

## 📞 Suporte

**Problemas não resolvidos?**

1. Verifique logs:
   ```bash
   # Servidor Python
   tail -f inference_server.log
   
   # Backend Supabase
   supabase functions logs
   
   # Console do navegador
   F12 > Console
   ```

2. Execute diagnóstico:
   ```bash
   # Criar script de diagnóstico
   python -c "
   import sys
   import torch
   import cv2
   import ultralytics
   
   print('Python:', sys.version)
   print('PyTorch:', torch.__version__)
   print('CUDA:', torch.cuda.is_available())
   print('OpenCV:', cv2.__version__)
   print('Ultralytics:', ultralytics.__version__)
   "
   ```

3. Consulte documentação:
   - Ultralytics: https://docs.ultralytics.com
   - FastAPI: https://fastapi.tiangolo.com
   - Supabase: https://supabase.com/docs

---

## 📄 Licença

MIT License - EcoVision 2025

---

**✅ Checklist de Configuração Completa:**

- [ ] Python 3.8-3.11 instalado
- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas (`requirements.txt`)
- [ ] Modelos YOLO baixados/configurados
- [ ] Servidor Python iniciado (`http://localhost:8000/health` responde)
- [ ] Variável `INFERENCE_SERVER_URL` configurada no backend
- [ ] Tabelas do banco criadas (migração executada)
- [ ] Frontend conectando com webcam
- [ ] Inferências salvando no banco
- [ ] Dashboard mostrando estatísticas

**Parabéns! 🎉 Seu EcoVision está 100% funcional!**
