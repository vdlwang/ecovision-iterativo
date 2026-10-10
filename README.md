# 🌿 EcoVision - Sistema Inteligente de Reciclagem

> **Origem:** TCC de Engenharia de Computação (Poli-USP, 2025) de **Vitor Santos** e **Nathan Santos**. Este repositório une a versão final (`vitor-scosta/Ecovision@d6f5181`, na raiz) e a versão iterativa (`vitor-scosta/tcc-testes`, em [`legado/`](legado/)), com o histórico de ambas preservado.

Sistema de controle para esteira rolante de centro de reciclagem integrado com IA que identifica e separa automaticamente materiais (papel/papelão, metal, plástico e vidro) através de um servomotor único.

![EcoVision](https://img.shields.io/badge/YOLO-v8-green) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![React](https://img.shields.io/badge/React-18+-cyan) ![ESP32](https://img.shields.io/badge/ESP32-Arduino-orange)

---

## 📋 Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Arquitetura](#arquitetura)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Configuração](#configuração)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Sobre o Projeto

O EcoVision é um sistema completo que combina:

- **Inferência Local**: YOLO v8 rodando localmente via Ultralytics
- **Interface Web**: Dashboard React para monitoramento e configuração
- **Hardware**: ESP32 controlando servo e motor da esteira
- **Comunicação**: WebSocket (Python ↔ React) + Serial (Python ↔ ESP32)

### Funcionalidades

✅ Detecção em tempo real de 4 tipos de materiais  
✅ Separação automática via servo controlado  
✅ Interface web responsiva com autenticação  
✅ Configuração de ângulos das cancelas  
✅ Ajuste de confiança do modelo  
✅ Controle do motor da esteira  
✅ Visualização de detecções com bounding boxes  

---

## 🏗️ Arquitetura

```
┌─────────────┐          ┌──────────────┐          ┌─────────────┐
│   Webcam    │──USB────▶│   Python     │──Serial─▶│   ESP32     │
│   (câmera)  │          │   Backend    │          │  (Arduino)  │
└─────────────┘          │              │          └─────────────┘
                         │  - YOLO v8   │               │
┌─────────────┐          │  - WebSocket │               │
│   React     │◀─────────│  - OpenCV    │               ▼
│  Frontend   │ ws://    └──────────────┘          ┌─────────────┐
└─────────────┘                                    │ Servo+Motor │
                                                   └─────────────┘
```

**Fluxo de Dados:**
1. Webcam captura frame
2. YOLO detecta material
3. Python envia comando serial para ESP32
4. ESP32 move servo para ângulo configurado
5. Material é direcionado para cancela correta
6. Frontend recebe frames + detecções via WebSocket

---

## 📦 Requisitos

### Hardware

- **Computador**: Windows/Linux/Mac com webcam
- **ESP32 DevKit**: Qualquer modelo com GPIO
- **Servo Motor**: 9g ou similar (0-180°)
- **Motor DC**: Para esteira rolante
- **Cabos**: USB para ESP32, jumpers para conexões

### Software

#### Python (Backend)
- Python 3.8 ou superior
- pip (gerenciador de pacotes)

#### Node.js (Frontend)
- Node.js 16+ e npm

#### Arduino IDE
- Arduino IDE 2.0+ ou PlatformIO
- Biblioteca ESP32

---

## 🚀 Instalação

### 1️⃣ Clone o Repositório

```bash
git clone https://github.com/seu-usuario/ecovision.git
cd ecovision
```

### 2️⃣ Backend Python

#### Instalar Dependências

```bash
# Criar ambiente virtual (recomendado)
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install ultralytics opencv-python pyserial websockets
```

#### Modelo YOLO

Os pesos já estão em `yolo_models/taco/`. O padrão (`model_path` em `backend/config.json`) é `best.pt`, o YOLOv8s com fine-tuning nas imagens do projeto. Caminhos relativos em `model_path` são resolvidos a partir de `backend/`.

### 3️⃣ Frontend React

```bash
cd frontend
npm install
```

### 4️⃣ Firmware ESP32

O firmware é um projeto PlatformIO em `firmware/` (`firmware/src/main.cpp`). Veja [`firmware/README.md`](firmware/README.md) para pinagem e comandos.

```bash
cd firmware
pio run -t upload
```

---

## 🎮 Como Usar

### Passo 1: Configurar Porta Serial

Edite `backend/config.json` (se existir) ou configure via interface:

```json
{
  "serial_port": "COM8",
  "baud_rate": 115200,
  "camera_index": 0,
  "confidence": 0.45,
  "model_path": "../yolo_models/taco/best.pt"
}
```

**Descobrir porta serial:**
- **Windows**: Gerenciador de Dispositivos > Portas COM (COMx)
- **Linux**: `ls /dev/ttyUSB*` ou `ls /dev/ttyACM*`
- **Mac**: `ls /dev/tty.usb*`

### Passo 2: Iniciar Backend Python

```bash
# Ativar ambiente virtual (se criou)
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Rodar backend
python backend/ecovision_local_modf.py
```

**Saída esperada:**
```
[INFO] Carregando modelo YOLO: yolov8s.pt
[INFO] Modelo carregado com sucesso
[INFO] Conectando porta serial: COM8
[INFO] Serial conectada: COM8 @ 115200 baud
[INFO] Abrindo câmera (índice 0)...
[INFO] Câmera aberta: 640x480
[INFO] WebSocket iniciado em: ws://localhost:8765
[INFO] Aguardando conexões...
```

### Passo 3: Iniciar Frontend React

**Em outro terminal:**

```bash
cd frontend
npm run dev
```

**Saída esperada:**
```
VITE v5.x.x  ready in 500 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### Passo 4: Acessar Interface

1. Abra navegador em `http://localhost:5173`
2. Faça login:
   - **Google** (simulado)
   - **Modo Demo** (sem autenticação)

### Passo 5: Usar o Sistema

**Monitor:**
- Visualize detecções em tempo real
- Controle motor da esteira (Ligar/Parar)
- Veja FPS e status da conexão

**Cancelas de Separação:**
- Configure ângulo do servo para cada material
- Teste cada configuração individualmente
- Salve configurações

**Configuração do Modelo:**
- Escolha modelo YOLO (nano/small/medium/large/xlarge)
- Ajuste confiança mínima (0-100%)
- Configure porta serial e câmera
- Teste conexão

---

## 📁 Estrutura do Projeto

```
.
├── backend/
│   ├── ecovision_local.py       # Backend: YOLO + WebSocket + Serial (usado por run.sh/run.bat)
│   ├── ecovision_local_modf.py  # Variante: dispara na hora, sem fila
│   ├── config.json              # Configuração (gravada também pela interface)
│   ├── requirements.txt
│   ├── test_connection.py       # Testa câmera e serial
│   └── testes_serial.py         # REPL serial para o ESP32
├── frontend/                    # React + Vite
│   ├── index.html
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── components/          # Painéis + componentes shadcn (ui/)
│       └── hooks/useStableWebSocket.ts
├── firmware/                    # ESP32 (PlatformIO)
│   ├── platformio.ini
│   └── src/main.cpp
├── yolo_models/taco/            # Pesos YOLO (best.pt = padrão)
├── docs/diagrams/               # Diagramas PlantUML e renderizações
├── legado/                      # Versão iterativa do TCC (scripts, datasets, middleware, maquete)
├── run.sh / run.bat             # Sobe backend e frontend
└── README.md
```

---

## ⚙️ Configuração

### Configuração via Interface Web

1. Acesse **Configuração do Modelo**
2. Ajuste parâmetros:
   - Tipo de modelo YOLO
   - Confiança mínima
   - Porta serial ESP32
   - Baud rate
   - Índice da câmera
3. Clique em **Salvar Configuração**
4. **Reinicie o backend Python**

### Mapeamento Material → Servo

1. Acesse **Cancelas de Separação**
2. Configure ângulo para cada material:
   - **Plástico**: ex. 50°
   - **Metal**: ex. 90°
   - **Papelão**: ex. 130°
   - **Papel**: ex. 130°
3. Use botão **Testar** para verificar
4. Clique em **Salvar Configuração**
5. **Reinicie o backend Python**

### Diagrama de Conexão Hardware

Pinagem de `firmware/src/main.cpp`:

```
ESP32 DevKit           Servo MG996R       L298N (ponte H)      Motores DC da esteira
┌───────────┐         ┌──────────┐       ┌──────────┐         ┌──────────┐
│  GPIO 32  ├────────▶│  Signal  │       │          │         │          │
│  GPIO 22  ├────────────────────────────▶  IN1     ├────────▶│  OUT1/2  │
│  GPIO 23  ├────────────────────────────▶  IN2     │         │          │
│    GND    ├────────▶│  GND     │◀──────┤  GND     │         │          │
└───────────┘         └──────────┘       └──────────┘         └──────────┘
```

**Importante:**
- Servo requer alimentação estável e externa (5V/1A+), com GND comum ao ESP32
- O firmware aciona só o IN1 com PWM fixo (255): a esteira gira num único sentido e velocidade

---

## 🐛 Troubleshooting

### Backend não inicia

**Erro: "No module named 'ultralytics'"**
```bash
pip install ultralytics opencv-python pyserial websockets
```

**Erro: "Could not open camera"**
- Verifique se câmera está conectada
- Tente outro índice: `camera_index: 1` ou `2`
- No Linux: `sudo usermod -a -G video $USER`

**Erro: "Could not open serial port"**
- Verifique porta correta no Device Manager
- Windows: Instale driver CH340 (ESP32 clone)
- Linux: `sudo chmod 666 /dev/ttyUSB0`
- Feche Arduino IDE (mantém porta aberta)

### Frontend não conecta

**Erro: "Backend Offline"**
- Verifique se backend Python está rodando
- Backend usa porta 8765 (ws://localhost:8765)
- Verifique firewall

**Erro: "Cannot GET /"**
- Rode `npm run dev` (não apenas `npm start`)

### ESP32 não responde

**Comandos não funcionam:**
- Verifique firmware foi uploaded
- Abra Serial Monitor (115200 baud)
- Veja se ESP32 está recebendo comandos
- Verifique conexões GPIO

**Servo não move:**
- Verifique alimentação (5V suficiente)
- Teste servo com código básico
- Verifique se o sinal está no GPIO 32

---

## 🎓 Comandos Rápidos

### Backend
```bash
# Ativar venv
venv\Scripts\activate              # Windows
source venv/bin/activate           # Linux/Mac

# Rodar
python backend/ecovision_local.py

# Testar conexão
python backend/test_connection.py  # Se existir
```

### Frontend
```bash
cd frontend

# Desenvolvimento
npm run dev

# Build produção
npm run build

# Preview build
npm run preview
```

### Teclas de Atalho (Backend Terminal)
- `O` - Ligar motor
- `P` - Parar motor
- `Q` - Sair

---

## 📊 Performance

| Modelo | FPS (CPU) | FPS (GPU) | Precisão |
|--------|-----------|-----------|----------|
| Nano   | 15-20     | 60+       | ⭐⭐⭐     |
| Small  | 10-15     | 45+       | ⭐⭐⭐⭐   |
| Medium | 5-10      | 30+       | ⭐⭐⭐⭐   |
| Large  | 2-5       | 20+       | ⭐⭐⭐⭐⭐ |

**Recomendação:** YOLOv8 Small para melhor custo-benefício

---

## 🔧 Desenvolvimento

### Instalar Dependências Dev

```bash
# Python
pip install black flake8 pytest

# Node
npm install --save-dev @types/react @types/node
```

### Estrutura de Código

- **Backend**: `backend/ecovision_local.py` - Tudo em um arquivo
- **Frontend**: Componentes modulares em `frontend/src/components`
- **Config**: `backend/config.json` (opcional, pode usar interface)

---

## 📝 Licença

MIT License - use livremente para projetos pessoais ou comerciais

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'Add nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra Pull Request

---

## 📧 Suporte

- **Issues**: Abra issue no GitHub
- **Email**: seu-email@exemplo.com
- **Docs**: [Link para documentação adicional]

---

## 🌟 Features Futuras

- [ ] Suporte para múltiplas câmeras
- [ ] Estatísticas de reciclagem
- [ ] Integração com banco de dados
- [ ] App mobile (React Native)
- [ ] Modo offline completo
- [ ] Exportar relatórios PDF

---

**Desenvolvido com ❤️ para um mundo mais sustentável 🌍♻️**
