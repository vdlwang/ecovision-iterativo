# 🚀 Quick Start - EcoVision

## Instalação Rápida (5 minutos)

### 1. Backend Python

```bash
# Instalar dependências
cd backend
pip install -r requirements.txt

# Colocar modelo YOLO treinado em:
# yolo_models/taco/yolov8s.pt
```

### 2. Frontend React

```bash
# Voltar para raiz
cd ..

# Instalar dependências
npm install
```

### 3. Firmware ESP32

1. Abra `firmware/esp32_ecovision.ino` no Arduino IDE
2. Conecte ESP32 via USB
3. Selecione placa e porta
4. Faça upload

### 4. Configurar Porta Serial

Edite `config.json`:
```json
{
  "serial_port": "COM7",
  "camera_index": 0
}
```

### 5. Rodar

**Opção A - Script Automático:**
```bash
# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh
```

**Opção B - Manual:**
```bash
# Terminal 1 - Backend
cd backend
python ecovision_local.py

# Terminal 2 - Frontend
npm run dev
```

### 6. Acessar

Abra navegador em: **http://localhost:5173**

Login: Use **Modo Demo**

Pronto! ✅
