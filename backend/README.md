# Backend - EcoVision

Processo Python que junta câmera, YOLO, WebSocket e serial. Visão geral do sistema no [README principal](../README.md).

## Execução

```bash
pip install -r requirements.txt
python ecovision_local_modf.py      # pode ser chamado de qualquer pasta
```

- **`ecovision_local_modf.py`** é o backend oficial (é o que `run.sh` e `run.bat` sobem). Quando um objeto entra na ROI, envia o ângulo na hora e ignora novas detecções até passar `servo_actuation_seconds`. O intervalo mínimo entre disparos é fixo no código (`DETECTION_COOLDOWN = 1.5` s, em `deteccao.py`).
- **`deteccao.py`** guarda a lógica que não depende de câmera nem de serial: a tabela `taco_to_material`, o filtro das caixas pela confiança (`deteccoes_do_quadro`) e a decisão de disparar o servo (`angulo_a_disparar`).
- A variante anterior, `ecovision_local.py`, enfileirava os materiais detectados e os enviava um a um, usando `detection_cooldown`. Foi removida; está na tag `tese-final` (`git show tese-final:backend/ecovision_local.py`).

O WebSocket escuta em `ws://localhost:8765`. Se a porta serial não abrir, o backend segue em modo demonstração: detecta e transmite, mas não aciona o ESP32.

## `config.json`

Lido na inicialização a partir de `backend/config.json`. Se o arquivo não existir, é criado com os valores padrão definidos em `load_config()`. É configuração local da máquina e está no `.gitignore`. O frontend também grava neste arquivo ao clicar em "Salvar". O `config.example.json` traz os mesmos valores padrão, como referência para editar à mão (por exemplo, `cp config.example.json config.json`).

| Campo | Uso |
|-------|-----|
| `serial_port`, `baud_rate` | Porta do ESP32 (`COM8` / `/dev/ttyUSB0`) e velocidade (115200) |
| `camera_index` | Índice da webcam no OpenCV, ou URL de um stream (ex.: `http://<ip>:8080/video` do app IP Webcam; a página `.html` do app não serve) |
| `model_path` | Pesos do YOLO. Caminho relativo é resolvido a partir de `backend/`. Padrão: `../yolo_models/taco/best.pt` (veja [`yolo_models/README.md`](../yolo_models/README.md)) |
| `confidence` | Confiança mínima das detecções. O YOLO roda com `CONF_MINIMA_MODELO` (0.1) e o filtro é feito a cada quadro, então vale na hora (valores abaixo de 0.1 só depois de reiniciar) |
| `roi_y_min`, `roi_y_max` | Faixa horizontal do quadro (fração da altura) em que o centro do objeto dispara o servo |
| `class_to_angle` | Ângulo do servo por material: chaves `plastic`, `metal`, `glass`, `paper` |
| `servo_actuation_seconds` | Tempo em que o sistema fica ocupado após cada disparo |
| `detection_cooldown` | Ignorado (era usado pela variante removida `ecovision_local.py`); o intervalo é `DETECTION_COOLDOWN` no código |

`serial_port`, `baud_rate`, `camera_index` e `model_path` só passam a valer depois de reiniciar o backend. `confidence`, `class_to_angle` e a ROI valem na hora.

Cada classe TACO detectada é convertida em material pela tabela `taco_to_material` de `deteccao.py` (por exemplo, `drink can` → `metal`, `corrugated carton` → `paper`). Classes fora dos quatro grupos viram `other` e não acionam o servo.

## Protocolo WebSocket (JSON)

Do frontend para o backend:

| Mensagem | Efeito |
|----------|--------|
| `{"command": "MOTOR ON"}` / `{"command": "MOTOR OFF"}` | Liga ou desliga a esteira |
| `{"command": "<ângulo>"}` | Move o servo direto (botão "Testar") |
| `{"type": "config", "confidence": <n>}` | Atualiza a confiança em memória |
| `{"type": "get_config"}` | Pede a configuração atual (os painéis enviam ao conectar) |
| `{"type": "save_config", ...}` | Mescla os campos no `config.json` e salva (a chave `type` não é gravada) |

Do backend para o frontend:

- Um por quadro: `{"frame": <jpeg base64>, "detections": [{"class", "material", "confidence", "bbox"}], "fps", "motor_running", "serial_port"}`. `serial_port` é `null` em modo demonstração.
- Resposta a `get_config`, só para quem pediu: `{"type": "config", ...campos do config.json}`.

## Scripts de teste

```bash
python test_connection.py    # bibliotecas instaladas, câmera 0, portas seriais disponíveis e porta 8765 livre
python testes_serial.py      # REPL para mandar comandos ao ESP32 (porta e baud do config.json)
```

Os comandos aceitos estão em [`firmware/README.md`](../firmware/README.md). Com firmware anterior à continuação (tag `tese-final`), evite `PING`: ele é lido como 0 e move o servo para 0°.

## Troubleshooting

**"Could not open camera" / "Erro no stream da câmera":** o backend continua no ar e tenta reabrir a câmera a cada 5 s (`CAMERA_RETRY_SECONDS`). Tente outro `camera_index` (1, 2...). Com câmera de celular, use a URL do stream de vídeo (ex.: `http://<ip>:8080/video`), não a da página do app. No Linux, o usuário precisa estar no grupo `video` (`sudo usermod -a -G video $USER`).

**Porta serial não abre:**
- Confira a porta com `python test_connection.py`.
- Windows: instale o driver CH340/CP2102 do ESP32.
- Linux: adicione o usuário ao grupo `dialout` (`sudo usermod -a -G dialout $USER`) ou, temporariamente, `sudo chmod 666 /dev/ttyUSB0`.
- Feche o monitor serial do PlatformIO ou da Arduino IDE, que mantém a porta ocupada.
