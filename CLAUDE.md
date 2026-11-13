# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

EcoVision (a.k.a. CyberReciclagem): the 2025 undergraduate thesis (TCC, Engenharia de Computação, Poli-USP) of Vitor Santos and Nathan Santos, a recycling conveyor belt. A YOLO model detects waste on the belt from a webcam, and an ESP32 drives one servo (MG996R) and the belt motors (L298N + 4 DC motors) to sort it into 4 materials: plastic, metal, glass, paper. The authors have graduated. This repo, maintained by Victor Wang, continues the project: new fixes and features go here, on top of the thesis's final version. Code, comments and identifiers are in Portuguese. Match that when editing.

The repo merges two histories from the thesis: its final version (`vitor-scosta/Ecovision`), which is the root and the base for all new work, and its preliminary version (`vitor-scosta/tcc-testes`) under `legado/`, kept only as reference. "Iterativo" in the repo name refers to the current work iterating on the thesis, not to `legado/`. Both upstreams are frozen. `origin` is `vdlwang/ecovision-iterativo`, a standalone repo (not a fork). `vdlwang/ecovision-fork` is the retired old fork, kept for reference. Never push to or open PRs against `vitor-scosta/tcc-testes`: it happened once by mistake (PR #3, reverted in #4).

There is no linter or TypeScript type-check (no `tsconfig.json`; Vite only transpiles), and the only tests are pytest unit tests for `anotacao/` (`anotar.py`, `avaliar.py`, `saida.py`, `visualizar.py`, `revisar.py`; they don't load the model). The available checks are:

```bash
cd frontend && npm run build               # bundles the frontend; catches import/syntax errors
python -m py_compile backend/*.py
cd firmware && pio run                     # compile only, no upload
python -m pytest anotacao/tests            # needs anotacao/requirements.txt (pyyaml, pillow, pytest)
```

## Running things

```bash
pip install -r backend/requirements.txt   # ultralytics, opencv-python, pyserial, websockets
cd frontend && npm install                 # deps pinned + package-lock; unpinned "*" deps broke clean installs before

python backend/ecovision_local_modf.py     # official backend: WebSocket on localhost:8765 + webcam + serial
cd frontend && npm run dev                 # Vite on http://localhost:5173
./run.sh   (or run.bat)                    # both of the above in separate terminals

python backend/test_connection.py          # checks camera and serial port
python backend/testes_serial.py            # interactive REPL to the ESP32
cd firmware && pio run -t upload           # PlatformIO firmware
```

`backend/config.json` holds serial port (default `COM8`, the team developed on Windows; use `/dev/ttyUSB0` on Linux), camera index, `model_path`, confidence, ROI, `class_to_angle`, timings. It is gitignored (local per machine); when missing, `load_config()` writes the defaults, which hold the thesis values. The frontend overwrites it on "Salvar" (including a stray `"type": "save_config"` key). A relative `model_path` is resolved from `backend/`. With no serial port the backend keeps running in demo mode.

## Architecture

**Backend.** The official backend is `backend/ecovision_local_modf.py`, which `run.sh`/`run.bat` launch. It is a single file of functions; only `SystemState` is a class, despite the class diagram in `docs/diagrams/` showing `YOLOPipeline`/`SerialController`/`WebSocketHandler`. A thread runs `model(source=camera, stream=True)` and maps each TACO class name to a material via `taco_to_material`. When a box center falls inside the horizontal ROI band (`roi_y_min`..`roi_y_max`), it sends that material's angle at once, then ignores detections for `servo_actuation_seconds`. The minimum gap between triggers is the hardcoded `DETECTION_COOLDOWN = 1.5`; the config's `detection_cooldown` is ignored. The belt is **not** stopped on detection. Every frame is broadcast over WebSocket as base64 JPEG, together with the detections. The file also prints debug lines for every frame. `ecovision_local.py` is the previous variant, which queues materials and uses `detection_cooldown`. Both files share most of their code, so a fix usually belongs in both, or the old one should be deleted.

**WebSocket protocol** (JSON): client → server `{"command": "MOTOR ON"|"MOTOR OFF"|"<angle>"}`, `{"type": "config", "confidence"}`, `{"type": "save_config", ...}`. Server → client `{frame, detections[{class, material, confidence, bbox}], fps, motor_running}`.

**Frontend** (`frontend/`): React 18 + Vite, exported from Figma. Components import versioned specifiers (`lucide-react@0.487.0`, `sonner@2.0.3`), resolved by the aliases in `frontend/vite.config.ts`; keep them. `frontend/src/index.css` is precompiled Tailwind. Login is a mock (localStorage flag). Panels: `MonitorPanel`, `ConfigGatesPanel` (angles per material), `ConfigModelPanel`, all sharing one socket through `hooks/useStableWebSocket.ts`.

**Firmware** (`firmware/src/main.cpp`, PlatformIO, `ESP32Servo`): servo on GPIO32, L298N IN1=22 / IN2=23, 115200 baud. Commands: `MOTOR ON`, `MOTOR OFF`, `SERVO <n>`, bare `<n>`. Angles go into an 8-slot FreeRTOS queue; each is held 5 s and the servo returns to 175°. Motor is fixed PWM 255 on IN1, starts off.

**Models** (`yolo_models/taco/`): `best.pt` is the default (YOLOv8s fine-tuned from `150ep_best.pt` on the team's photos; 61 classes = 60 TACO + `Background`). `50ep_best`, `97ep_best`, `150ep_best` are earlier fine-tunes. `yolov8n.pt`/`yolov8s.pt`/`yolov8m.pt` are the original TACO weights (60 classes, no fine-tuning), byte-identical to `legado/yolo_models/taco/yolov8{n,s,m}_100epochs-best.pt`. (Docs claimed `yolov8s.pt` was the COCO checkpoint until 2026-11-13; it is not.) Training scripts and the train/val split are not in the repo.

## Known pitfalls

These are also listed for users in `README.md` ("Limitações conhecidas") and `frontend/README.md`. Update those when fixing one.


- `ConfigModelPanel`'s model selector sets `model_path` to `../yolo_models/taco/<yolov8n|s|m|l|x>.pt`. `n`/`s`/`m` are TACO weights without fine-tuning, and `l`/`x` don't exist. `best.pt` is not offered.
- `ConfigGatesPanel` uses key `vidro` while the backend maps glass to `glass`, so glass is never actuated once the config is saved from the UI.
- The backend does not handle `get_config` (the panels request it), so the UI shows hardcoded defaults.
- `conf` is fixed when the YOLO stream starts; changing confidence at runtime has no effect.
- Serial is used from both the YOLO thread and the asyncio handler without a lock, and `read_reply` blocks the event loop.
- In the firmware, any non-numeric command (e.g. `PING`) parses as 0 and moves the servo to 0°.
- The queue and fixed 5 s hold are not tied to object position on a moving belt, so actuation drifts.

## Documentation layout

The root `README.md` stays short (overview, install, run, limitations) and links to `PROBLEMAS.md`, `OBJETIVO.md` (the full target system: belt images → three annotators → 3oo3 vote → human review → train/test bases → YOLO fine-tuning, with decisions and a task list T1..T14; the current scope is T1 and then the multi-annotator pipeline of its section 6: T5 importar.py, a generic detector interface, avaliar.py over saved proposals, more annotators, the vote) and to per-directory READMEs: `backend/README.md` (config.json fields, WebSocket protocol, test scripts), `frontend/README.md` (UI usage), `firmware/README.md` (pinout, serial commands), `yolo_models/README.md` (what each weight file is, with metrics read from the checkpoints), `anotacao/README.md` (assisted annotation: state lives in a SQLite database, `<saida>/anotacoes.sqlite` (phase 3b, schema and all access in `saida.py`: classes, lotes, imagens with voto/motivo, execucoes, propostas, revisoes; proposals and reviews are never overwritten, the current one is the highest id; `labels/`, `revisadas.txt` and `data.yaml` are generated from it, `anotar.py --exportar` regenerates them; every write is a `BEGIN IMMEDIATE` transaction; older output dirs with `imagens.csv` are refused; the Colab notebook works on a local copy and backs it up to Drive); `importar.py` copies a batch (lote) into the shared `images/` store and registers it with its train/test set and region of interest; `anotar.py` runs an annotator over imported pending images from its `ANOTADORES` registry (detectors subclass `Detector` and implement only `carregar()`/`pontuar()`; Grounding DINO and OWLv2, open-vocabulary, with the prompts (a string or a list per class) in `classes.yaml`; and `yolo`, the team's `best.pt`, matched to the classes by name. These three are the voting trio, decision 17) and writes proposals (every box from `--piso` 0.05 with its class; the read thresholds `confianca`/`confianca_classe` are stored in the run's parameters and applied by readers via `saida.separar()`) to the database, never to `labels/`; `--aceitar` records proposals as an unchanged review; output `anotacoes/` is gitignored; `revisar.py` serves `revisar.html` plus a JSON API on 127.0.0.1; pending images can be edited (change class, remove, add a box by clicking one of the annotator's stored candidates, undo/redo, save, discard) and each review is a new row in the database (drawing/moving boxes by hand is deferred, decision 12; reopening is phase 5); the page sends the `proposta_id` it showed and gets 409 if a newer proposal exists; `visualizar.py` stays as the static `file://` page; `avaliar.py` scores saved proposals (no model run; validation images are imported and annotated like any batch, matched to the team labels in `legado/database` by original name) for coverage per read threshold, class per confidence band, detection and click-to-box, plus `--comparar` (joint class error of two annotators) and `--voto` (strict NooN vote per image, and consensus per box), after applying `correcoes_rotulos.yaml` (the team labelled all glass as `Glass bottle`; corrections are by .txt line, legado/ stays untouched); `anotar_colab.ipynb` runs it on Colab; `PLANO-REVISAO.md` plans T1, the generic annotation framework and the review/edit page). Put details in the matching one.

## legado/

The thesis's preliminary version, kept as reference (don't develop here), with its own README. Its issue list (2026-10-08, including notes on the thesis text) is the root `PROBLEMAS.md`; items the final version fixes are marked there. Highlights:

- `legado/scripts/` (run from inside that dir; relative `../yolo_models` paths): `model_2.py` (webcam → YOLO → serial, stops the belt on each detection), `val.py` (benchmarks yolov8 n/s/m on the 4 scenarios), `infer.py`, `testes_serial.py`. Same serial protocol as the current firmware, but substring class mapping that misses cans and paper.
- `legado/interface/reciclagem_middleware_v1/`: obsolete Tk middleware + `esp32_cancela.ino` speaking an incompatible `PULSE:<gate>,<ms>` protocol.
- `legado/database/tcc-<0|45><CF|SF>/`: the team's photos, 4 capture scenarios (camera angle 0°/45°, com/sem flash) of the same scenes taken seconds apart; only the `validation` split is committed. `data.yaml` `path:` is an absolute Windows path.
- `legado/Maquete Final/`: SketchUp/CAD models of the belt.
