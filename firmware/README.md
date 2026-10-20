# Firmware ESP32 - EcoVision

Projeto PlatformIO (`platformio.ini`, placa `esp32dev`, framework Arduino, biblioteca `ESP32Servo`). O código está em `src/main.cpp`. Visão geral do sistema no [README principal](../README.md); o lado Python da serial está em [`backend/README.md`](../backend/README.md).

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
| GPIO 2  | LED da placa: aceso = motor ligado; pisca enquanto o servo segura a posição |

## Funcionamento

Três tarefas FreeRTOS:

- `serialTask`: única leitora da serial; interpreta os comandos.
- `motorControl`: com o motor ligado, aplica PWM 255 no IN1 (velocidade fixa, um sentido).
- `servoControl`: consome uma fila de até 8 ângulos; move o servo, mantém 5 s e volta para 175°.

No boot, o motor começa **desligado** até receber `MOTOR ON`, e o servo vai para a posição de repouso (175°).

## Comandos Serial (115200 baud, terminados em `\n`)

| Comando | Resposta | Efeito |
|---------|----------|--------|
| `MOTOR ON` | `OK MOTOR ON` | Liga a esteira |
| `MOTOR OFF` | `OK MOTOR OFF` | Desliga a esteira |
| `SERVO <n>` | `Servo movido para <n> graus` | Enfileira o ângulo `n` |
| `<n>` (0–180) | `Servo movido para <n> graus` | Igual a `SERVO <n>` |
| `PING` | `PONG` | Testa a comunicação, sem mover nada |

A resposta `Servo movido` sai quando o servo começa o movimento. Se ele estiver ocupado com um ângulo anterior, isso pode levar até 5 s por item na fila.

Erros: `ERR: comando invalido.` para texto não reconhecido, `ERR: angulo invalido (0..180).` para `SERVO` com argumento fora da faixa ou não numérico, `ERR: fila do servo cheia.` quando já há 8 ângulos esperando. Em todos os casos, o servo não se move.

## Troubleshooting

### "Serial port not found"
- Instale drivers CH340/CP2102 do fabricante do ESP32
- No Windows: Device Manager → Ports (COM & LPT)
- No Linux: `ls /dev/ttyUSB*` ou `ls /dev/ttyACM*`

### "Upload failed"
- Mantenha o botão BOOT pressionado durante o upload
- Tente outra porta USB
- Reduza a velocidade de upload: `upload_speed = 115200` em `platformio.ini`

### Comandos não funcionam
- Abra o monitor serial (`pio device monitor -b 115200`) e confira se aparece `ESP32 pronto.` ao resetar
- Teste os comandos com `python backend/testes_serial.py`
- Feche o monitor serial antes de rodar o backend: só um programa pode usar a porta

### Servo não se move
- Verifique alimentação (servo precisa de 5V/1A+)
- Use fonte externa se ESP32 não fornecer corrente suficiente, com GND comum
- Confira se o sinal está no GPIO 32

### Motor não liga
- Confirme que `MOTOR ON` foi enviado (o motor começa desligado) e que a resposta `OK MOTOR ON` chegou
- Verifique a alimentação da L298N e o jumper ENA
- Use multímetro para testar se o GPIO 22 tem sinal
