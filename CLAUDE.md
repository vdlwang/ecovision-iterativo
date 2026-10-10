# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

EcoVision (a.k.a. CyberReciclagem): the 2025 undergraduate thesis (TCC, Engenharia de Computação, Poli-USP) of Vitor Santos and Nathan Santos, a recycling conveyor belt. A YOLO model detects waste on the belt from a webcam, and an ESP32 drives one servo (MG996R) and the belt motors (L298N + 4 DC motors) to sort it into 4 materials: plastic, metal, glass, paper. The authors have graduated; this repo is maintained by Victor Wang for fixes and improvements. Code, comments and identifiers are in Portuguese. Match that when editing.

The repo merges two histories: the final system (`vitor-scosta/Ecovision`) at the root, and the earlier iterative version (`vitor-scosta/tcc-testes`) under `legado/`. Neither upstream is reachable any more.

There is no test suite or linter.

## Running things

```bash
pip install -r backend/requirements.txt   # ultralytics, opencv-python, pyserial, websockets
cd frontend && npm install

python backend/ecovision_local.py          # WebSocket on localhost:8765 + webcam + serial
cd frontend && npm run dev                 # Vite on http://localhost:5173
./run.sh   (or run.bat)                    # both of the above in separate terminals

python backend/test_connection.py          # checks camera and serial port
python backend/testes_serial.py            # interactive REPL to the ESP32
cd firmware && pio run -t upload           # PlatformIO firmware
```

`backend/config.json` holds serial port (default `COM8`, the team developed on Windows; use `/dev/ttyUSB0` on Linux), camera index, `model_path`, confidence, ROI, `class_to_angle`, timings. The frontend overwrites it on "Salvar". A relative `model_path` is resolved from `backend/`. With no serial port the backend keeps running in demo mode.

## Architecture

**Backend** (`backend/ecovision_local.py`, a single file of functions; only `SystemState` is a class, despite the class diagram in `docs/diagrams/` showing `YOLOPipeline`/`SerialController`/`WebSocketHandler`): a thread runs `model(source=camera, stream=True)`, maps each TACO class name to a material via `taco_to_material`, and when a box center falls inside the horizontal ROI band (`roi_y_min`..`roi_y_max`) it enqueues the material (global `detection_cooldown`). The queue sends one angle at a time and waits `servo_actuation_seconds`. The belt is **not** stopped on detection. Every frame is JPEG/base64-broadcast over WebSocket with the detections. `ecovision_local_modf.py` is a variant that fires immediately and ignores detections while busy; the authors' last README edit points at it, while `run.sh`/`run.bat` launch `ecovision_local.py`.

**WebSocket protocol** (JSON): client → server `{"command": "MOTOR ON"|"MOTOR OFF"|"<angle>"}`, `{"type": "config", "confidence"}`, `{"type": "save_config", ...}`. Server → client `{frame, detections[{class, material, confidence, bbox}], fps, motor_running}`.

**Frontend** (`frontend/`): React 18 + Vite, exported from Figma. Components import versioned specifiers (`lucide-react@0.487.0`, `sonner@2.0.3`), resolved by the aliases in `frontend/vite.config.ts`; keep them. `frontend/src/index.css` is precompiled Tailwind. Login is a mock (localStorage flag). Panels: `MonitorPanel`, `ConfigGatesPanel` (angles per material), `ConfigModelPanel`, all sharing one socket through `hooks/useStableWebSocket.ts`.

**Firmware** (`firmware/src/main.cpp`, PlatformIO, `ESP32Servo`): servo on GPIO32, L298N IN1=22 / IN2=23, 115200 baud. Commands: `MOTOR ON`, `MOTOR OFF`, `SERVO <n>`, bare `<n>`. Angles go into an 8-slot FreeRTOS queue; each is held 5 s and the servo returns to 175°. Motor is fixed PWM 255 on IN1, starts off.

**Models** (`yolo_models/taco/`): `best.pt` is the default (YOLOv8s fine-tuned from `150ep_best.pt` on the team's photos; 61 classes = 60 TACO + `Background`). `50ep_best`, `97ep_best`, `150ep_best` are earlier fine-tunes. `yolov8n.pt`/`yolov8m.pt` are the original TACO weights renamed; `yolov8s.pt` is the stock **COCO** checkpoint (80 classes), not TACO. The original TACO YOLOv8s lives in `legado/yolo_models/taco/yolov8s_100epochs-best.pt`. Training scripts and the train/val split are not in the repo.

## Known pitfalls

- `ConfigGatesPanel` uses key `vidro` while the backend maps glass to `glass`, so glass is never actuated once the config is saved from the UI.
- The backend does not handle `get_config` (the panels request it), so the UI shows hardcoded defaults.
- `conf` is fixed when the YOLO stream starts; changing confidence at runtime has no effect.
- Serial is used from both the YOLO thread and the asyncio handler without a lock, and `read_reply` blocks the event loop.
- In the firmware, any non-numeric command (e.g. `PING`) parses as 0 and moves the servo to 0°.
- The queue and fixed 5 s hold are not tied to object position on a moving belt, so actuation drifts.

## legado/

The iterative version, with its own README and `PROBLEMAS.md` (issue list from 2026-10-08, including notes on the thesis text). Highlights:

- `legado/scripts/` (run from inside that dir; relative `../yolo_models` paths): `model_2.py` (webcam → YOLO → serial, stops the belt on each detection), `val.py` (benchmarks yolov8 n/s/m on the 4 scenarios), `infer.py`, `testes_serial.py`. Same serial protocol as the current firmware, but substring class mapping that misses cans and paper.
- `legado/interface/reciclagem_middleware_v1/`: obsolete Tk middleware + `esp32_cancela.ino` speaking an incompatible `PULSE:<gate>,<ms>` protocol.
- `legado/database/tcc-<0|45><CF|SF>/`: the team's photos, 4 capture scenarios (camera angle 0°/45°, com/sem flash) of the same scenes taken seconds apart; only the `validation` split is committed. `data.yaml` `path:` is an absolute Windows path.
- `legado/Maquete Final/`: SketchUp/CAD models of the belt.
