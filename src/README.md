# EcoVision 🌱

Sistema de reciclagem inteligente com IA que detecta e separa automaticamente materiais recicláveis usando YOLO + ESP32.

## 🎯 Características

- **Detecção em Tempo Real**: YOLO (Ultralytics) rodando localmente na webcam
- **Separação Automática**: Servo único controlado via ESP32 direciona materiais para cancelas específicas
- **Interface Web**: Monitor em tempo real com configuração de ângulos do servo
- **Zero Cloud**: Tudo roda localmente (Python + React)

## 📦 Materiais Detectados

| Material | Ícone | Ângulo Padrão |
|----------|-------|---------------|
| Plástico | ♻️ | 50° |
| Metal | 🔩 | 90° |
| Papelão | 📦 | 130° |
| Papel | 📄 | 130° |

## 🚀 Quick Start (5 minutos)

### 1. Instalar Dependências

```bash
# Backend Python
cd backend
pip install -r requirements.txt

# Frontend React (já configurado pelo Figma Make)
```

### 2. Testar Conexões

Antes de executar, teste se tudo está configurado:

```bash
cd backend
python test_connection.py
```

Este script verifica:
- ✓ Bibliotecas instaladas
- ✓ Câmera acessível
- ✓ Portas seriais disponíveis
- ✓ Porta WebSocket livre

### 3. Configurar

Edite `config.json`:

```json
{
  "serial_port": "COM7",        // Sua porta serial (Windows: COMx, Linux: /dev/ttyUSBx)
  "model_path": "../yolo_models/taco/yolov8s.pt",  // Caminho do seu modelo .pt
  "confidence": 0.4,
  "class_to_angle": {
    "plastic": 50,
    "metal": 90,
    "corrugated carton": 130,
    "paper": 130
  }
}
```

### 4. Executar

**Opção 1: Scripts Automáticos**

Windows:
```bash
run.bat
```

Linux/Mac:
```bash
chmod +x run.sh
./run.sh
```

**Opção 2: Manual**

Terminal 1 (Backend):
```bash
cd backend
python ecovision_local.py
```

Terminal 2 (Frontend):
```bash
# O frontend já está rodando no Figma Make
# Acesse: http://localhost:XXXX
```

### 5. Conectar Hardware

1. **ESP32**: Faça upload do firmware (veja `/firmware/README.md`)
2. **Webcam**: Conecte e ajuste `camera_index` no `config.json` se necessário
3. **Servo**: Conecte ao ESP32 conforme diagrama

## 🎛️ Interface

### Monitor
- Feed da câmera com bounding boxes em tempo real
- Controle da esteira (Ligar/Parar motor)
- Ajuste de confiança mínima do YOLO
- Status do sistema (Câmera, YOLO, ESP32)

### Configuração
- Mapear cada material a um ângulo do servo (0-180°)
- Testar posições do servo individualmente
- Configurar porta serial e ROI (Região de Interesse)

## 🔧 Arquitetura

```
┌─────────────┐
│   Webcam    │ → Captura frames (30 FPS)
└──────┬──────┘
       │
       ↓
┌─────────────────────────┐
│  YOLO (Ultralytics)     │ → Detecção de materiais
│  - YOLOv8               │
│  - Confiança: 40%       │
│  - ROI: 45-55% altura   │
└──────┬──────────────────┘
       │
       ↓
┌─────────────────────────┐
│  Python Backend         │ → Lógica de controle
│  - WebSocket (8765)     │ → Envia frames para frontend
│  - Serial (115200 baud) │ → Envia comandos para ESP32
└──────┬──────────────────┘
       │
       ↓
┌─────────────────────────┐
│  ESP32 + Servo          │ → Atuação física
│  - Recebe ângulo (0-180°)
│  - Move servo por 5s    │
│  - Retorna à posição 180°
└─────────────────────────┘
       │
       ↓
   [Cancelas de Separação]
   📄  🔩  ♻️  📦
```

## ⚙️ Configuração Avançada

### ROI (Região de Interesse)
Ajuste `roi_y_min` e `roi_y_max` no `config.json` para definir a faixa vertical onde objetos são detectados:

```json
{
  "roi_y_min": 0.45,  // 45% da altura do frame
  "roi_y_max": 0.55   // 55% da altura do frame
}
```

Isso reduz falsos positivos detectando apenas quando o objeto cruza o centro da tela.

### Cooldown de Detecção
Evita múltiplas detecções do mesmo objeto:

```json
{
  "detection_cooldown": 1.0  // 1 segundo entre detecções
}
```

### Tempo de Atuação
Tempo que o servo permanece na posição antes de retornar:

```json
{
  "servo_actuation_seconds": 5.0  // 5 segundos
}
```

## 🔌 Firmware ESP32

Exemplo mínimo (use Arduino IDE):

```cpp
#include <Servo.h>

Servo myServo;
const int SERVO_PIN = 18;
const int MOTOR_PIN = 19;

void setup() {
  Serial.begin(115200);
  myServo.attach(SERVO_PIN);
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, HIGH); // Motor ligado
  myServo.write(180); // Posição inicial
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd == "MOTOR ON") {
      digitalWrite(MOTOR_PIN, HIGH);
      Serial.println("OK: Motor ON");
    }
    else if (cmd == "MOTOR OFF") {
      digitalWrite(MOTOR_PIN, LOW);
      Serial.println("OK: Motor OFF");
    }
    else {
      int angle = cmd.toInt();
      if (angle >= 0 && angle <= 180) {
        myServo.write(angle);
        delay(5000); // Mantém 5s
        myServo.write(180); // Retorna
        Serial.println("OK: Servo " + String(angle));
      }
    }
  }
}
```

## 🐛 Troubleshooting

### "WebSocket connection failed"
- **Backend não está rodando**: Execute `python backend/ecovision_local.py`
- **Porta incorreta**: Verifique se está usando `ws://localhost:8765`
- **Firewall bloqueando**: Adicione exceção para porta 8765
- **Teste a porta**: Execute `python backend/test_connection.py`

### "Serial port not found"
- Verifique se o ESP32 está conectado
- Ajuste `serial_port` no `config.json` (Windows: `COM3`, Linux: `/dev/ttyUSB0`)
- No Linux, adicione permissões: `sudo usermod -a -G dialout $USER`

### "Modelo YOLO não encontrado"
- Coloque seu modelo `.pt` treinado em `../yolo_models/taco/`
- Ou use um modelo pré-treinado: `yolov8s.pt` (será baixado automaticamente)
- Ajuste `model_path` no `config.json`

### "WebSocket não conecta"
- Certifique-se que o backend Python está rodando
- Verifique o console: deve mostrar `WebSocket server rodando!`
- Porta padrão: `ws://localhost:8765`

### "Câmera não abre"
- Ajuste `camera_index` no `config.json` (tente 0, 1, 2...)
- No Linux: instale `sudo apt-get install v4l-utils`
- Liste câmeras: `v4l2-ctl --list-devices`

## 📁 Estrutura do Projeto

```
ecovision/
├── backend/
│   ├── ecovision_local.py    # Backend principal
│   └── requirements.txt      # Dependências Python
├── components/               # Componentes React
│   ├── Sidebar.tsx
│   ├── MonitorPanel.tsx
│   └── ConfigPanel.tsx
├── config.json              # Configuração central
├── README.md                # Este arquivo
└── App.tsx                  # Frontend principal
```

## 🤝 Contribuindo

1. Ajuste os ângulos do servo para seu setup específico
2. Treine seu próprio modelo YOLO com seu dataset
3. Ajuste ROI conforme a altura da sua esteira

## 📝 Licença

MIT License - Use livremente para projetos de reciclagem!

## 🎓 Créditos

- **YOLO**: [Ultralytics](https://github.com/ultralytics/ultralytics)
- **Dataset TACO**: [TACO Dataset](http://tacodataset.org/)
- **Framework**: React + Python + ESP32