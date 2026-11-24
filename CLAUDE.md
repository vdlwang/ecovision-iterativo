# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

EcoVision (a.k.a. CyberReciclagem): the 2025 undergraduate thesis (TCC, Engenharia de Computação, Poli-USP) of Vitor Santos and Nathan Santos, a recycling conveyor belt. A YOLO model detects waste on the belt from a webcam, and an ESP32 drives one servo (MG996R) and the belt motors (L298N + 4 DC motors) to sort it into 4 materials: plastic, metal, glass, paper. The authors have graduated. This repo, maintained by Victor Wang, continues the project: new fixes and features go here, on top of the thesis's final version. Code, comments and identifiers are in Portuguese. Match that when editing.

The repo merges two histories from the thesis: its final version (`vitor-scosta/Ecovision`), which is the root and the base for all new work, and its preliminary version (`vitor-scosta/tcc-testes`) under `legado/`, kept only as reference. "Iterativo" in the repo name refers to the current work iterating on the thesis, not to `legado/`. Both upstreams are frozen. `origin` is `vdlwang/ecovision-iterativo`, a standalone repo (not a fork). `vdlwang/ecovision-fork` is the retired old fork, kept for reference. Never push to or open PRs against `vitor-scosta/tcc-testes`: it happened once by mistake (PR #3, reverted in #4).

There is no linter or TypeScript type-check (no `tsconfig.json`; Vite only transpiles), and the only tests are pytest unit tests: `backend/tests` (`backend/deteccao.py`, plus `test_requirements.py`, which checks every backend requirement is pinned with `==` and matches the installed version) and `anotacao/tests` (`anotar.py`, `avaliar.py`, `saida.py`, `visualizar.py`, `revisar.py`, `votar.py`, `importar.py`, `pipeline.py`, `metricas.py`; they don't load the model). There are no hardware, camera or frontend tests. The available checks are:

```bash
cd frontend && npm run build               # bundles the frontend; catches import/syntax errors
python -m py_compile backend/*.py
python -m pytest backend/tests           # needs backend/requirements-dev.txt; the best.pt class-coverage test skips without ultralytics
cd firmware && pio run                     # compile only, no upload
python -m pytest anotacao/tests            # needs anotacao/requirements.txt (pyyaml, pillow, pytest)
```

## Running things

```bash
pip install -r backend/requirements.txt   # pinned (==), tested on Python 3.14; numpy 2.5 needs 3.12+. Bump all together
cd frontend && npm install                 # deps pinned + package-lock; unpinned "*" deps broke clean installs before

python backend/ecovision_local_modf.py     # official backend: WebSocket on localhost:8765 + webcam + serial
python backend/ecovision_local_modf.py --debug=true   # also logs each serial command and per-frame detections
python backend/ecovision_local_modf.py --capturar=true   # also saves belt frames for annotation (T4) to backend/capturas/
cd frontend && npm run dev                 # Vite on http://localhost:5173
./run.sh   (or run.bat)                    # both of the above in separate terminals; args go to the backend

python backend/test_connection.py          # checks camera and serial port
python backend/testes_serial.py            # interactive REPL to the ESP32 (port from config.json)
cd firmware && pio run -t upload           # PlatformIO firmware
```

`backend/config.json` holds serial port (default `COM8`, the team developed on Windows; use `/dev/ttyUSB0` on Linux), camera index, the `camera` block (resolution, format, exposure...), `model_path`, confidence, ROI, `class_to_angle`, timings. It is gitignored (local per machine); when missing, `load_config()` writes the defaults, which hold the thesis values. The frontend overwrites it on "Salvar"; the backend drops the `type` key when saving. A relative `model_path` is resolved from `backend/`. With no serial port the backend keeps running in demo mode.

## Architecture

**Backend.** The official backend is `backend/ecovision_local_modf.py`, which `run.sh`/`run.bat` launch. It is a file of functions (only `SystemState` is a class) plus `backend/deteccao.py`, which holds the logic with no camera/serial/YOLO imports: `taco_to_material`, `deteccoes_do_quadro` (box → detection with the tracker `id`, confidence filter) and `DisparosPorTrilha` (T15: fires once per track when its center is in or has crossed the ROI band, material voted by summed confidence over the track, busy for `servo_actuation_seconds`, warns when a track crosses while busy, re-ID inherits a fire); and `backend/motor.py` (`EstadoMotor`: `motor_running` is the last motor command actually sent, starts off, and goes off when the ESP32 prints `ESP32 pronto.` after a reset); and `backend/captura.py` (T4 capture for annotation, off by default, `--capturar`/`captura.ativa`: `deve_capturar` saves at most every `intervalo_s`; with the motor on, `atraso_s` (1 s) after a new object enters the empty belt, detected by `OcupacaoLona` from the difference to an empty-belt reference, deliberately not by YOLO (sampling bias, `OBJETIVO.md`); with it off only when the frame differs from the last saved; a `captura` thread writes `capturas/<session>/<UTC time>.jpg` with the capture time in EXIF plus `captura.jsonl`); and `backend/camera.py` (etapa 6a: opens the `VideoCapture` itself, V4L2 on Linux, DSHOW untested; applies the `camera` block of `config.json`, where `null` in exposure/white balance/focus re-enables auto on every open because V4L2 keeps the last value set; reads back and logs divergences; a `camera` thread keeps only the latest frame, which the YOLO thread passes to `model(frame, imgsz=...)`; `backend/ajustar_camera.py` is the calibration tool; for a URL with credentials it sets FFmpeg `auth_type=basic`, because the Android IP camera app used as a temporary camera answers 429 to unauthenticated requests, see `backend/README.md`). `load_config()` fills keys missing from `config.json` with `CONFIG_PADRAO`. This is despite the class diagram in `docs/diagrams/` showing `YOLOPipeline`/`SerialController`/`WebSocketHandler`. The YOLO thread runs the model on each latest frame and maps each TACO class name to a material. The YOLO thread runs `model.track(..., persist=True, tracker="bytetrack.yaml")` (needs `lap`), `persist=False` on the first frame after a camera (re)open; `DisparosPorTrilha` decides the servo angle. The config's `detection_cooldown` is ignored (the fixed `DETECTION_COOLDOWN` was removed by T15). The belt is **not** stopped on detection. YOLO runs with `conf=CONF_MINIMA_MODELO` (0.1) and boxes below `config['confidence']` are dropped per frame, so confidence changes apply live. Frames are broadcast over WebSocket as base64 JPEG with the detections, without boxes drawn (the `MonitorPanel` canvas draws boxes and labels from `detections`); frames aren't encoded with no client connected, and `broadcast_frame` skips a client while its previous send is still pending (`envios_pendentes`), so a slow client drops frames without piling up sends or stalling the others. A `serial` thread (`manter_serial`) opens the port and reopens it every `SERIAL_RETRY_SECONDS` (5) after a failure or when absent at start; `MOTOR ON` is sent only on the startup connection, never on a reconnect. Serial writes go through `serial_lock` in `send_line`; nobody waits for replies, `read_serial_loop` (run by that thread) just logs every line from the ESP32 (the firmware answers an angle only when it leaves its queue, so replies can't be matched to commands). Output goes through `logging` (logger `ecovision`, threads named `yolo`/`camera`/`serial`; INFO, or DEBUG with `--debug=true` parsed by argparse in `__main__`; libraries stay at WARNING), not `print`. The previous variant `ecovision_local.py` (queues materials, uses `detection_cooldown`) was removed; see `git show tese-final:backend/ecovision_local.py`.

**WebSocket protocol** (JSON): client → server `{"command": "MOTOR ON"|"MOTOR OFF"|"<angle>"}`, `{"type": "config", "confidence"}`, `{"type": "get_config"}`, `{"type": "save_config", ...}`, `{"type": "captura_automatica", "ativa"}` (toggles automatic capture in memory), `{"type": "capturar"}` (manual capture of the latest frame), `{"type": "foco"|"exposicao", "modo": "auto"|"travar"|"manual", "valor"}` (camera focus/exposure, applied by the `camera` thread between reads via `LeitorCamera.pedir`, persisted to `camera.foco`, or `camera.exposicao` + `camera.ganho`; locking exposure also re-sets the gain read before, because the C920 falls back to the last manual gain and goes dark). Server → client `{frame, detections[{class, material, confidence, bbox, id}], fps, motor_running, serial_port, captura_automatica, capturas_gravadas, foco, exposicao}` per frame (`serial_port` is `null` in demo mode), `{"type": "config", ...config}` in reply to `get_config` and `{"type": "captura_manual", ok, arquivo, erro}` in reply to `capturar` (both sent only to the requester). The `Capturador` always exists (`--capturar`/`captura.ativa` only set whether automatic starts on); the session folder is created on the first capture.

**Frontend** (`frontend/`): React 18 + Vite, exported from Figma. Components import versioned specifiers (`lucide-react@0.487.0`, `sonner@2.0.3`), resolved by the aliases in `frontend/vite.config.ts`; keep them. `frontend/src/index.css` is precompiled Tailwind. Login is a mock (localStorage flag). Panels: `MonitorPanel`, `ConfigGatesPanel` (angles per material), `ConfigModelPanel`, all sharing one socket (the Monitor's focus and exposure cards are `components/AjusteCamera.tsx`) through `hooks/useStableWebSocket.ts`, with the URL in `src/config.ts` (`BACKEND_WS_URL`) and the connection badge in `components/BadgeBackend.tsx`. The Monitor picks each detection's icon from `det.material` (sent by the backend), not from the class name.

**Firmware** (`firmware/src/main.cpp`, PlatformIO, `ESP32Servo`): servo on GPIO32, L298N IN1=22 / IN2=23, 115200 baud. Commands: `MOTOR ON`, `MOTOR OFF`, `SERVO <n>`, bare `<n>`, `PING` (→ `PONG`); anything else, or an angle outside 0..180, gets `ERR: ...` and does not move the servo. Angles go into an 8-slot FreeRTOS queue; each is held 5 s and the servo returns to 175° (also its boot position). Motor is fixed PWM 255 on IN1, starts off. The board LED (GPIO2) is on while the motor runs and blinks during each servo hold.

**Models** (`yolo_models/taco/`): `best.pt` is the default (YOLOv8s fine-tuned from `150ep_best.pt` on the team's photos; 61 classes = 60 TACO + `Background`). `50ep_best`, `97ep_best`, `150ep_best` are earlier fine-tunes. `yolov8n.pt`/`yolov8s.pt`/`yolov8m.pt` are the original TACO weights (60 classes, no fine-tuning), byte-identical to `legado/yolo_models/taco/yolov8{n,s,m}_100epochs-best.pt`. (Docs claimed `yolov8s.pt` was the COCO checkpoint until 2026-11-13; it is not.) Training scripts and the train/val split are not in the repo.

## Known pitfalls

These are also listed for users in `README.md` ("Limitações conhecidas") and `frontend/README.md`. Update those when fixing one.


- The queue and fixed 5 s hold are not tied to object position on a moving belt, so actuation drifts.
- Lighting is not controlled (decided 2026-11-18): the camera (Logitech C920, index 3) runs with auto exposure/gain/white balance (exposure and gain can be locked from the Monitor), so the image changes with what's on the belt and fps drops to 15 in low light; `captura.diferenca_quadros` equalizes mean brightness so auto exposure doesn't trigger motor-off captures. Fixed lighting + manual exposure is a future improvement (`backend/PLANO-CAPTURA.md`, 6b).

## Documentation layout

The root `README.md` stays short (overview, install, run, limitations) and links to `PROBLEMAS.md` (non-code issues), `CHANGELOG.md` (changes since tag `tese-final`, grouped by kind, citing commits; add an entry with each fix or behavior change), `OBJETIVO.md` (the full target system: belt images → three annotators → 3oo3 vote → human review → train/test bases → YOLO fine-tuning, with decisions and a task list T1..T15 with their status) and to per-directory READMEs: `backend/README.md` (config.json fields, WebSocket protocol, test scripts), `backend/PLANO-CAPTURA.md` (T4 belt capture plan: motor state, timer-spaced capture with EXIF capture time, importar.py `--janela` Δ check, camera settings later), `frontend/README.md` (UI usage), `firmware/README.md` (pinout, serial commands), `yolo_models/README.md` (what each weight file is, with metrics read from the checkpoints), `anotacao/README.md` (assisted annotation pipeline: importar → anotar → votar → revisar, SQLite state; the working details are in `anotacao/CLAUDE.md`, which loads when working there). Put details in the matching one.

## legado/

The thesis's preliminary version, kept as reference (don't develop here), with its own README. The root `PROBLEMAS.md` now keeps only issues outside the code that still apply (fine-tuning data leakage, dataset paths, camera-to-servo geometry, repo size); the original 2026-10-08 analysis of `legado/` and of the thesis text is in `git show 7007a0e:PROBLEMAS.md`. Highlights:

- `legado/scripts/` (run from inside that dir; relative `../yolo_models` paths): `model_2.py` (webcam → YOLO → serial, stops the belt on each detection), `val.py` (benchmarks yolov8 n/s/m on the 4 scenarios), `infer.py`, `testes_serial.py`. Same serial protocol as the current firmware, but substring class mapping that misses cans and paper.
- `legado/interface/reciclagem_middleware_v1/`: obsolete Tk middleware + `esp32_cancela.ino` speaking an incompatible `PULSE:<gate>,<ms>` protocol.
- `legado/database/tcc-<0|45><CF|SF>/`: the team's photos, 4 capture scenarios (camera angle 0°/45°, com/sem flash) of the same scenes taken seconds apart; only the `validation` split is committed. `data.yaml` `path:` is an absolute Windows path.
- `legado/Maquete Final/`: SketchUp/CAD models of the belt.
