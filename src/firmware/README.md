# Firmware ESP32 - EcoVision

## Upload do Firmware

### 1. Instalar Arduino IDE

- Download: https://www.arduino.cc/en/software
- Instale a versão mais recente

### 2. Configurar ESP32 no Arduino IDE

1. Abra Arduino IDE
2. Vá em **File → Preferences**
3. Em "Additional Boards Manager URLs", adicione:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Vá em **Tools → Board → Boards Manager**
5. Procure por "esp32" e instale "ESP32 by Espressif Systems"

### 3. Instalar Biblioteca Servo

1. Vá em **Sketch → Include Library → Manage Libraries**
2. Procure por "Servo" 
3. Instale "Servo by Michael Margolis" (ou use a biblioteca ESP32 Servo)

### 4. Upload

1. Abra `esp32_ecovision.ino` no Arduino IDE
2. Conecte o ESP32 via USB
3. Selecione a placa: **Tools → Board → ESP32 Dev Module**
4. Selecione a porta: **Tools → Port → COMx** (Windows) ou **/dev/ttyUSBx** (Linux)
5. Clique em **Upload** (seta →)

### 5. Verificar

1. Abra o Serial Monitor: **Tools → Serial Monitor**
2. Configure para **115200 baud**
3. Você deve ver: `EcoVision ESP32 Ready!`

## Diagrama de Conexão

```
ESP32 DevKit
┌──────────────┐
│              │
│  GPIO 18 ────┼─→ Servo (Signal - Laranja)
│              │
│  GPIO 19 ────┼─→ Relé (IN - Azul)
│              │
│  5V      ────┼─→ Servo (VCC - Vermelho)
│              │   Relé (VCC)
│              │
│  GND     ────┼─→ Servo (GND - Marrom)
│              │   Relé (GND)
└──────────────┘

Relé → Motor da Esteira
       COM: Fase (AC)
       NO: Motor

Servo → Direcionador de Materiais
        Ângulo 0-180° controla posição
```

## Comandos Serial

| Comando | Descrição |
|---------|-----------|
| `MOTOR ON` | Liga o motor da esteira |
| `MOTOR OFF` | Desliga o motor da esteira |
| `50` | Move servo para 50° (mantém 5s, retorna para 180°) |
| `90` | Move servo para 90° |
| `130` | Move servo para 130° |

## Ajustes

### Alterar pinos

Edite no início do código:

```cpp
const int SERVO_PIN = 18;  // Seu pino do servo
const int MOTOR_PIN = 19;  // Seu pino do relé
```

### Alterar tempo de atuação

```cpp
const int SERVO_HOLD_TIME = 5000;  // 5000ms = 5 segundos
```

### Alterar posição padrão

```cpp
const int SERVO_DEFAULT_POS = 180;  // 180° = posição neutra
```

## Troubleshooting

### "Serial port not found"
- Instale drivers CH340/CP2102 do fabricante do ESP32
- No Windows: Device Manager → Ports (COM & LPT)
- No Linux: `ls /dev/ttyUSB*` ou `ls /dev/ttyACM*`

### "Upload failed"
- Mantenha o botão BOOT pressionado durante o upload
- Tente outra porta USB
- Reduz a velocidade de upload: **Tools → Upload Speed → 115200**

### Servo não se move
- Verifique alimentação (servo precisa de 5V/1A+)
- Use fonte externa se ESP32 não fornecer corrente suficiente
- Teste com um exemplo básico de servo primeiro

### Motor não liga
- Verifique conexões do relé
- Use multímetro para testar se GPIO 19 vai para HIGH
- Certifique-se que o relé é 3.3V ou 5V compatível
