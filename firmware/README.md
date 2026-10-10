# Firmware ESP32 - EcoVision

Projeto PlatformIO (`platformio.ini`, placa `esp32dev`, framework Arduino, biblioteca `ESP32Servo`). O código está em `src/main.cpp`.

## Upload

Com a extensão PlatformIO do VS Code, ou pela CLI:

```bash
cd firmware
pio run -t upload          # compila e grava
pio device monitor -b 115200
```

## Pinagem

| Pino ESP32 | Ligação |
|------------|---------|
| GPIO 32 | Sinal do servo (MG996R) |
| GPIO 22 | IN1 da ponte H L298N (PWM) |
| GPIO 23 | IN2 da ponte H L298N |
| GPIO 2  | LED (configurado, não usado) |

## Funcionamento

Três tarefas FreeRTOS:

- `serialTask`: única leitora da serial; interpreta os comandos.
- `motorControl`: com o motor ligado, aplica PWM 255 no IN1 (velocidade fixa, um sentido).
- `servoControl`: consome uma fila de até 8 ângulos; move o servo, mantém 5 s e volta para 175°.

O motor começa **desligado** até receber `MOTOR ON`.

## Comandos Serial (115200 baud, terminados em `\n`)

| Comando | Resposta | Efeito |
|---------|----------|--------|
| `MOTOR ON` | `OK MOTOR ON` | Liga a esteira |
| `MOTOR OFF` | `OK MOTOR OFF` | Desliga a esteira |
| `SERVO <n>` | `Servo movido para <n> graus` | Enfileira o ângulo `n` |
| `<n>` (0–180) | `Servo movido para <n> graus` | Igual a `SERVO <n>` |

## Troubleshooting

### "Serial port not found"
- Instale drivers CH340/CP2102 do fabricante do ESP32
- No Windows: Device Manager → Ports (COM & LPT)
- No Linux: `ls /dev/ttyUSB*` ou `ls /dev/ttyACM*`

### "Upload failed"
- Mantenha o botão BOOT pressionado durante o upload
- Tente outra porta USB
- Reduza a velocidade de upload: `upload_speed = 115200` em `platformio.ini`

### Servo não se move
- Verifique alimentação (servo precisa de 5V/1A+)
- Use fonte externa se ESP32 não fornecer corrente suficiente
- Teste com um exemplo básico de servo primeiro

### Motor não liga
- Confirme que `MOTOR ON` foi enviado (o motor começa desligado) e que a resposta `OK MOTOR ON` chegou
- Verifique a alimentação da L298N e o jumper ENA
- Use multímetro para testar se o GPIO 22 tem sinal
