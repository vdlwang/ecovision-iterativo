# EcoVision - Sistema Inteligente de Reciclagem

> **Origem:** este repositório dá continuidade ao EcoVision, TCC de Engenharia de Computação (Poli-USP, 2025) de **Vitor Santos** e **Nathan Santos**, com correções e melhorias. O ponto de partida é a versão final do TCC (`vitor-scosta/Ecovision@d6f5181`), que está na raiz. A versão preliminar (`vitor-scosta/tcc-testes`) fica em [`legado/`](legado/). O histórico de ambas foi preservado.

Sistema de controle para esteira rolante de centro de reciclagem. Uma webcam filma a esteira, um modelo YOLOv8 identifica o material (plástico, metal, vidro ou papel) e um ESP32 move um único servo para desviar o objeto para a saída correta.

## Arquitetura

```
┌─────────────┐          ┌──────────────┐          ┌─────────────┐
│   Webcam    │──USB────▶│   Python     │──Serial─▶│   ESP32     │
│   (câmera)  │          │   Backend    │          │             │
└─────────────┘          │              │          └─────────────┘
                         │  - YOLO v8   │               │
┌─────────────┐          │  - WebSocket │               │
│   React     │◀─────────│  - OpenCV    │               ▼
│  Frontend   │ ws://    └──────────────┘          ┌─────────────┐
└─────────────┘                                    │ Servo+Motor │
                                                   └─────────────┘
```

O backend lê a câmera, roda o YOLO e, quando o centro de um objeto cruza uma faixa horizontal do quadro (ROI), envia ao ESP32 o ângulo configurado para aquele material. Ao mesmo tempo, transmite os quadros e as detecções ao frontend por WebSocket.

| Parte | Pasta | Documentação |
|-------|-------|--------------|
| Backend (Python: YOLO + WebSocket + serial) | `backend/` | [`backend/README.md`](backend/README.md) |
| Frontend (React + Vite) | `frontend/` | [`frontend/README.md`](frontend/README.md) |
| Firmware (ESP32, PlatformIO) | `firmware/` | [`firmware/README.md`](firmware/README.md) |
| Pesos do YOLO | `yolo_models/taco/` | [`yolo_models/README.md`](yolo_models/README.md) |
| Diagramas (PlantUML) | `docs/diagrams/` | |
| Versão preliminar do TCC (scripts, datasets, middleware, maquete) | `legado/` | [`legado/README.md`](legado/README.md) |
| Problemas da versão preliminar e observações sobre a monografia | | [`PROBLEMAS.md`](PROBLEMAS.md) |

## Requisitos

- **Python 3.10+**
- **Node.js 18+** e npm
- **PlatformIO** (CLI ou extensão do VS Code), para gravar o firmware
- **Hardware:** webcam, ESP32 DevKit, servo MG996R, ponte H L298N e os motores DC da esteira

## Instalação

```bash
git clone https://github.com/vdlwang/ecovision-iterativo.git
cd ecovision-iterativo

# Backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Firmware (com o ESP32 conectado)
cd firmware && pio run -t upload && cd ..
```

## Execução

Ajuste `serial_port` em `backend/config.json` (`COM8` por padrão; no Linux, algo como `/dev/ttyUSB0`). O arquivo não é versionado: é criado com os valores padrão na primeira execução do backend. Os demais campos estão em [`backend/README.md`](backend/README.md).

```bash
./run.sh                                  # Windows: run.bat
```

Ou manualmente, em dois terminais:

```bash
python backend/ecovision_local_modf.py    # backend: WebSocket em ws://localhost:8765
cd frontend && npm run dev                # interface em http://localhost:5173
```

Sem a porta serial disponível, o backend continua em modo demonstração (detecta e transmite, mas não aciona nada).

Para testar só a comunicação com o ESP32: `python backend/testes_serial.py`.

## Limitações conhecidas

- **O seletor de modelo da interface carrega pesos errados:** "Small" carrega o `yolov8s.pt`, que é o modelo COCO (não detecta lixo); "Nano" e "Medium" carregam os pesos TACO sem fine-tuning; "Large" e "XLarge" não existem. Para usar o modelo do projeto, mantenha `model_path` em `../yolo_models/taco/best.pt`.
- **O slider de confiança não tem efeito** com o backend rodando; a confiança só muda ao reiniciar.
- **O acionamento não acompanha a posição do objeto:** a esteira não para, e o servo fica 5 s em posição. Objetos que chegam nesse intervalo são ignorados.
- **A serial não tem trava:** a thread do YOLO e o handler do WebSocket escrevem na mesma porta sem lock, e a leitura da resposta bloqueia o loop do WebSocket.
- **O login é simulado:** não há autenticação real.

## Licença

MIT, conforme declarado pelos autores originais.
