# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

EcoVision (a.k.a. CyberReciclagem): the 2025 undergraduate thesis (TCC, Engenharia de Computação, Poli-USP) of Vitor Santos and Nathan Santos, a recycling conveyor belt. A YOLO model detects waste on the belt from a webcam, and an ESP32 drives one servo (MG996R) and the belt motors (L298N + 4 DC motors) to sort it into 4 materials: plastic, metal, glass, paper. The authors have graduated. This repo, maintained by Victor Wang, continues the project: new fixes and features go here, on top of the thesis's final version. Code, comments and identifiers are in Portuguese. Match that when editing.

The repo merges two histories from the thesis: its final version (`vitor-scosta/Ecovision`), which is the root and the base for all new work, and its preliminary version (`vitor-scosta/tcc-testes`) under `legado/`, kept only as reference. "Iterativo" in the repo name refers to the current work iterating on the thesis, not to `legado/`. Both upstreams are frozen. `origin` is `vdlwang/ecovision-iterativo`, a standalone repo (not a fork). `vdlwang/ecovision-fork` is the retired old fork, kept for reference. Never push to or open PRs against `vitor-scosta/tcc-testes`: it happened once by mistake (PR #3, reverted in #4).

There is no test suite, linter or TypeScript type-check (no `tsconfig.json`; Vite only transpiles). The available checks are:

```bash
cd frontend && npm run build               # bundles the frontend; catches import/syntax errors
python -m py_compile backend/*.py
cd firmware && pio run                     # compile only, no upload
```

## Running things

```bash
pip install -r backend/requirements.txt   # ultralytics, opencv-python, pyserial, websockets
cd frontend && npm install                 # deps pinned + package-lock; unpinned "*" deps broke clean installs before

python backend/ecovision_local_modf.py     # official backend: WebSocket on localhost:8765 + webcam + serial
cd frontend && npm run dev                 # Vite on http://localhost:5173
./run.sh   (or run.bat)                    # both of the above in separate terminals

python backend/test_connection.py          # checks camera and serial port
python backend/testes_serial.py            # interactive REPL to the ESP32 (port from config.json)
cd firmware && pio run -t upload           # PlatformIO firmware
```

`backend/config.json` holds serial port (default `COM8`, the team developed on Windows; use `/dev/ttyUSB0` on Linux), camera index, `model_path`, confidence, ROI, `class_to_angle`, timings. It is gitignored (local per machine); when missing, `load_config()` writes the defaults, which hold the thesis values. The frontend overwrites it on "Salvar"; the backend drops the `type` key when saving. A relative `model_path` is resolved from `backend/`. With no serial port the backend keeps running in demo mode.

## Architecture

**Backend.** The official backend is `backend/ecovision_local_modf.py`, which `run.sh`/`run.bat` launch. It is a single file of functions; only `SystemState` is a class, despite the class diagram in `docs/diagrams/` showing `YOLOPipeline`/`SerialController`/`WebSocketHandler`. A thread runs `model(source=camera, stream=True)` and maps each TACO class name to a material via `taco_to_material`. When a box center falls inside the horizontal ROI band (`roi_y_min`..`roi_y_max`), it sends that material's angle at once, then ignores detections for `servo_actuation_seconds`. The minimum gap between triggers is the hardcoded `DETECTION_COOLDOWN = 1.5`; the config's `detection_cooldown` is ignored. The belt is **not** stopped on detection. Frames are broadcast over WebSocket as base64 JPEG with the detections; frames aren't encoded with no client connected, and `broadcast_frame` skips a client while its previous send is still pending (`envios_pendentes`), so a slow client drops frames without piling up sends or stalling the others. Serial writes go through `serial_lock` in `send_line`; nobody waits for replies, a `read_serial_loop` thread just logs every line from the ESP32 (the firmware answers an angle only when it leaves its queue, so replies can't be matched to commands). The previous variant `ecovision_local.py` (queues materials, uses `detection_cooldown`) was removed; see `git show tese-final:backend/ecovision_local.py`.

**WebSocket protocol** (JSON): client → server `{"command": "MOTOR ON"|"MOTOR OFF"|"<angle>"}`, `{"type": "config", "confidence"}`, `{"type": "get_config"}`, `{"type": "save_config", ...}`. Server → client `{frame, detections[{class, material, confidence, bbox}], fps, motor_running, serial_port}` per frame (`serial_port` is `null` in demo mode), and `{"type": "config", ...config}` in reply to `get_config` (sent only to the requester).

**Frontend** (`frontend/`): React 18 + Vite, exported from Figma. Components import versioned specifiers (`lucide-react@0.487.0`, `sonner@2.0.3`), resolved by the aliases in `frontend/vite.config.ts`; keep them. `frontend/src/index.css` is precompiled Tailwind. Login is a mock (localStorage flag). Panels: `MonitorPanel`, `ConfigGatesPanel` (angles per material), `ConfigModelPanel`, all sharing one socket through `hooks/useStableWebSocket.ts`.

**Firmware** (`firmware/src/main.cpp`, PlatformIO, `ESP32Servo`): servo on GPIO32, L298N IN1=22 / IN2=23, 115200 baud. Commands: `MOTOR ON`, `MOTOR OFF`, `SERVO <n>`, bare `<n>`, `PING` (→ `PONG`); anything else, or an angle outside 0..180, gets `ERR: ...` and does not move the servo. Angles go into an 8-slot FreeRTOS queue; each is held 5 s and the servo returns to 175° (also its boot position). Motor is fixed PWM 255 on IN1, starts off. The board LED (GPIO2) is on while the motor runs and blinks during each servo hold.

**Models** (`yolo_models/taco/`): `best.pt` is the default (YOLOv8s fine-tuned from `150ep_best.pt` on the team's photos; 61 classes = 60 TACO + `Background`). `50ep_best`, `97ep_best`, `150ep_best` are earlier fine-tunes. `yolov8n.pt`/`yolov8m.pt` are the original TACO weights renamed; `yolov8s.pt` is the stock **COCO** checkpoint (80 classes), not TACO. The original TACO YOLOv8s lives in `legado/yolo_models/taco/yolov8s_100epochs-best.pt`. Training scripts and the train/val split are not in the repo.

## Known pitfalls

These are also listed for users in `README.md` ("Limitações conhecidas") and `frontend/README.md`. Update those when fixing one.


- `conf` is fixed when the YOLO stream starts; changing confidence at runtime has no effect.
- The queue and fixed 5 s hold are not tied to object position on a moving belt, so actuation drifts.

## Documentation layout

The root `README.md` stays short (overview, install, run, limitations) and links to `PROBLEMAS.md` (non-code issues) and to per-directory READMEs: `backend/README.md` (config.json fields, WebSocket protocol, test scripts), `frontend/README.md` (UI usage), `firmware/README.md` (pinout, serial commands), `yolo_models/README.md` (what each weight file is, with metrics read from the checkpoints). Put details in the matching one.

## legado/

The thesis's preliminary version, kept as reference (don't develop here), with its own README. The root `PROBLEMAS.md` now keeps only issues outside the code that still apply (fine-tuning data leakage, dataset paths, camera-to-servo geometry, repo size); the original 2026-10-08 analysis of `legado/` and of the thesis text is in `git show 7007a0e:PROBLEMAS.md`. Highlights:

- `legado/scripts/` (run from inside that dir; relative `../yolo_models` paths): `model_2.py` (webcam → YOLO → serial, stops the belt on each detection), `val.py` (benchmarks yolov8 n/s/m on the 4 scenarios), `infer.py`, `testes_serial.py`. Same serial protocol as the current firmware, but substring class mapping that misses cans and paper.
- `legado/interface/reciclagem_middleware_v1/`: obsolete Tk middleware + `esp32_cancela.ino` speaking an incompatible `PULSE:<gate>,<ms>` protocol.
- `legado/database/tcc-<0|45><CF|SF>/`: the team's photos, 4 capture scenarios (camera angle 0°/45°, com/sem flash) of the same scenes taken seconds apart; only the `validation` split is committed. `data.yaml` `path:` is an absolute Windows path.
- `legado/Maquete Final/`: SketchUp/CAD models of the belt.
