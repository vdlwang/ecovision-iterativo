# Middleware IA ↔ ESP32 — Esteira de Reciclagem

Este pacote contém:
- `middleware_gui.py` — GUI que recebe detecções da IA via TCP, mapeia 6 materiais para até 3 cancelas e envia comandos seriais ao ESP32.
- `middleware_client.py` — helper para seu script de inferência enviar `{label, confidence}` via TCP.
- `example_integration_ultralytics.py` — exemplo simples usando Ultralytics YOLO.
- `sender_test.py` — teste local sem YOLO (gera detecções aleatórias).
- `esp32_cancela/esp32_cancela.ino` — firmware para o ESP32.

## Requisitos (PC)
- Python 3.9+
- `pip install -r requirements.txt`
- Tkinter já vem com Python em Windows/macOS; no Linux pode ser necessário instalar `python3-tk` via gerenciador de pacotes.

## Como rodar
1) Conecte seu ESP32 (115200 baud).
2) Suba a GUI:
```bash
python middleware_gui.py
```
Selecione a porta serial do ESP32, conecte, mapeie **1 material por cancela**, ajuste **confiança mínima (%)** e **pulso (ms)**.

3) Teste sem IA (opcional):
```bash
python sender_test.py
```
Você verá logs na GUI e, se conectado, comandos enviados ao ESP32.

4) Integre com a IA (Ultralytics, exemplo):
```bash
python example_integration_ultralytics.py
```
Adapte o caminho do modelo `.pt` e a fonte (`source=0` para webcam).

## Por que usar TCP entre IA e GUI?
- **Processos separados**: a IA pode travar/reiniciar sem derrubar a GUI/Serial.
- **Simplicidade e portabilidade**: `localhost` TCP funciona no Windows/macOS/Linux sem dependências extras.
- **Flexível**: no futuro, é fácil distribuir (IA em outro PC/Jetson) sem mudar a GUI.
- **Alternativas**: ver comentários no final do `README`.

## Protocolos
- IA → GUI: uma linha JSON por detecção:
```
{"label": "glass bottle", "confidence": 0.87}
```
- GUI → ESP32 (Serial): comandos de texto, por exemplo:
```
PULSE:1,500
```
