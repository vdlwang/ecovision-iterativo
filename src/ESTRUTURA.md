# 📂 Estrutura do Projeto EcoVision

## Arquivos Essenciais

```
ecovision/
│
├── 📄 README.md              ⭐ LEIA PRIMEIRO - Documentação completa
├── 📄 QUICKSTART.md          ⚡ Instalação rápida em 5 minutos
├── 📄 .gitignore             🔒 Arquivos ignorados pelo Git
├── 📄 package.json           📦 Dependências Node.js
├── 📄 vite.config.ts         ⚙️ Configuração Vite
├── 📄 index.html             🌐 HTML base
├── 📄 App.tsx                🎯 App principal React
│
├── 🐍 backend/
│   ├── ecovision_local.py    ⭐ Backend Python (YOLO + WebSocket + Serial)
│   ├── requirements.txt      📦 Dependências Python
│   └── test_connection.py    🔌 Testa conexão serial
│
├── ⚛️ components/
│   ├── LoginScreen.tsx       🔐 Tela de login
│   ├── Sidebar.tsx           📋 Barra lateral
│   ├── MonitorPanel.tsx      📊 Dashboard principal
│   ├── ConfigGatesPanel.tsx  🎚️ Config. cancelas
│   ├── ConfigModelPanel.tsx  ⚙️ Config. modelo
│   ├── ErrorBoundary.tsx     🛡️ Tratamento de erros
│   ├── ToastProvider.tsx     🔔 Notificações
│   └── ui/                   🎨 Componentes shadcn
│
├── 🤖 firmware/
│   └── esp32_ecovision.ino   📡 Firmware ESP32 (Arduino)
│
├── 🎨 styles/
│   └── globals.css           🎨 Estilos globais
│
├── 🏃 Scripts de Execução
│   ├── run.bat               ▶️ Roda tudo (Windows)
│   └── run.sh                ▶️ Roda tudo (Linux/Mac)
│
└── 📁 yolo_models/           🧠 Modelos YOLO (você adiciona)
    └── taco/
        └── yolov8s.pt        ⚠️ COLOQUE SEU MODELO AQUI
```

## Pastas Opcionais (podem ser ignoradas)

```
├── 📁 diagrams/              📐 Diagramas UML (documentação)
├── 📁 guidelines/            📝 Diretrizes do projeto
├── 📁 models/                📦 Modelos alternativos
├── 📁 supabase/              ☁️ Backend alternativo (não usado)
└── 📁 utils/                 🔧 Utilitários diversos
```

## Arquivos que VOCÊ precisa adicionar

1. **Modelo YOLO treinado:**
   ```
   yolo_models/taco/yolov8s.pt
   ```
   ⚠️ Obrigatório para detecção funcionar

2. **config.json** (opcional):
   ```json
   {
     "serial_port": "COM8",
     "baud_rate": 115200,
     "camera_index": 2,
     "confidence": 0.4,
     "model_path": "../yolo_models/taco/150ep_best.pt"
   }
   ```
   💡 Pode configurar via interface web

## Fluxo de Trabalho

### Primeira Vez (Setup)

1. **Instalar dependências:**
   ```bash
   # Python
   cd backend
   pip install -r requirements.txt
   
   # Node
   cd ..
   npm install
   ```

2. **Adicionar modelo YOLO:**
   - Coloque `.pt` em `yolo_models/taco/`

3. **Upload firmware ESP32:**
   - Abra `firmware/esp32_ecovision.ino`
   - Upload via Arduino IDE

### Uso Diário

**Opção 1 - Automático:**
```bash
# Windows
run.bat

# Linux/Mac
./run.sh
```

**Opção 2 - Manual:**
```bash
# Terminal 1
cd backend
python ecovision_local.py

# Terminal 2
npm run dev
```

### Desenvolvimento

```bash
# Editar componentes
components/*.tsx

# Editar backend
backend/ecovision_local.py

# Editar estilos
styles/globals.css
```

## Portas Usadas

- **8765** - WebSocket (Python ↔ React)
- **5173** - Frontend React (Vite dev server)
- **COM8** - Serial (Python ↔ ESP32) - configurável

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| **Frontend** | React 18 + TypeScript + Vite |
| **Backend** | Python 3.8+ |
| **IA** | YOLO v8 (Ultralytics) |
| **Visão** | OpenCV |
| **Hardware** | ESP32 + Arduino |
| **Comunicação** | WebSocket + Serial |
| **UI** | Tailwind CSS + shadcn/ui |

## Tamanho dos Arquivos

| Item | Tamanho Aprox. |
|------|----------------|
| Frontend (node_modules) | ~200 MB |
| Backend (venv) | ~500 MB |
| Modelo YOLO (yolov8s.pt) | ~22 MB |
| Código fonte | ~5 MB |

## Checklist de Instalação

- [ ] Python 3.8+ instalado
- [ ] Node.js 16+ instalado
- [ ] Arduino IDE instalado
- [ ] ESP32 conectado via USB
- [ ] Webcam conectada
- [ ] Modelo YOLO em `yolo_models/taco/`
- [ ] Dependências Python instaladas
- [ ] Dependências Node instaladas
- [ ] Firmware ESP32 uploaded
- [ ] Porta serial configurada

## Próximos Passos

1. ✅ Leia o **README.md** completo
2. ⚡ Siga o **QUICKSTART.md** para setup rápido
3. 🚀 Execute `run.bat` ou `run.sh`
4. 🌐 Acesse http://localhost:5173
5. 🎉 Use o sistema!

---

**Dúvidas?** Consulte o **README.md** principal para documentação completa.
