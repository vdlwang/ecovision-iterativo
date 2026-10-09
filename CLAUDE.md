# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CyberReciclagem: the undergraduate thesis (TCC, Engenharia de Computação, Poli-USP) for a recycling conveyor belt. A YOLO model detects waste on the belt from a webcam, and an ESP32 drives servos, gates and the belt motor to sort it. Code, comments and identifiers are in Portuguese. Match that when editing.

There is no build system, test suite, linter or `requirements.txt`, although the middleware README mentions one. Dependencies are installed by hand: `ultralytics`, `pyserial`, `pandas` + `openpyxl` (for `val.py`), and Tkinter (`python3-tk` on Linux).

## Running things

The scripts in `scripts/` use relative paths like `../yolo_models/...`, so run them from inside `scripts/`:

```bash
cd scripts
python infer.py              # single-image or webcam inference (toggle USE_WEBCAM)
python val.py                # benchmark yolov8{n,s,m} on all 4 scenarios → avaliacao_modelos_resultados_2.xlsx
python test-yolo-format.py   # validate one model on one dataset (tcc-0SF)
python testes_serial.py      # interactive REPL to send commands to the ESP32
python model_2.py            # full pipeline: webcam → YOLO → serial (conveyor + servo)
make clean                   # (from repo root) delete scripts/runs/* (Ultralytics outputs)
```

Middleware (run from `interface/reciclagem_middleware_v1/`):

```bash
python middleware_gui.py                  # Tk GUI: TCP server on 127.0.0.1:8765 + serial to ESP32
python sender_test.py                     # fake detections, no YOLO needed
python example_integration_ultralytics.py # real YOLO → middleware
```

Most scripts hardcode `PORT = "COM5"` and Windows-style paths (`r"..\yolo_models\..."`, and `C:\Users\...` image paths in `model.py`/`final_model.py`), because the team develops on Windows. On Linux, change the port to `/dev/ttyUSB0` or similar and use forward slashes. `model_2.py` only reads keyboard shortcuts through `msvcrt` (Windows) and skips them elsewhere.

## Architecture

This repo does not contain the final system described in the thesis: the React/WebSocket dashboard, the backend classes `YOLOPipeline`/`SerialController`/`SystemState`, the fine-tuned YOLOv8s weights, and the servo/motor ESP32 firmware. The real hardware is 1 servo (MG996R) + L298N + 4 DC motors, which matches the `scripts/` protocol, not `esp32_cancela.ino`. Known issues are in `PROBLEMAS.md`.

**Models** (`yolo_models/taco/*.pt`) are YOLOv8 n/s/m trained on the TACO dataset. They have 61 classes, and the class list is in any `database/*/YOLO_dataset/data.yaml`. The project only uses 6 TACO class IDs: `5` plastic bottle, `6` glass bottle, `7` plastic bottle cap, `12` drink can, `17` corrugated carton, `33` normal paper. `val.py`, `example_integration_ultralytics.py` and `middleware_gui.py` (`MATERIAIS`) all repeat this mapping, so keep the copies in sync. `yolov8s` is the default model.

**Datasets** (`database/tcc-<scenario>/`) are the team's own photos in 4 capture scenarios: `0`/`45` is the camera angle in degrees, and `CF`/`SF` is *com/sem flash* (with/without flash). Images in the 4 scenarios were taken seconds apart, so they show the same scenes. Each scenario has a `COCO_dataset/` export and a `YOLO_dataset/`, but only the `validation` split is committed. The `path:` field in each `data.yaml` is an absolute Windows path from a teammate's machine. Ultralytics resolves `val:` relative to it, so fix or override `path` before running `val.py` locally. `scripts/convert-to-yolo-format.py` converts the COCO exports. `images/` holds loose test photos.

**Two separate control paths. Their serial protocols are not compatible:**

1. **Direct scripts** (`scripts/model.py`, `model_2.py`, `final_model.py`, `testes_serial.py`) talk to an ESP32 firmware that is *not in this repo*. Commands are newline-terminated: a bare angle like `50`, or `SERVO <0-180>`, `MOTOR ON`, `MOTOR OFF`, `PING`. Classes map to servo angles by substring match on the TACO name (`plastic`→50, `metal`→90, `cardboard`/`glass`→130). `model_2.py` is the most complete version. It counts an object only when its box center crosses a horizontal ROI band (`ROI_Y_MIN`..`ROI_Y_MAX` of frame height), queues it, stops the belt, actuates the servo, waits `SERVO_ACTUATION_SECONDS`, then restarts the belt.

2. **Middleware** (`interface/reciclagem_middleware_v1/`) splits the work into two processes. The inference script sends one JSON line per detection, `{"label", "confidence", "ts"}`, over localhost TCP using `middleware_client.send_detection`. That call fails silently if the GUI isn't running. `middleware_gui.py` maps each of the 6 materials to at most one of 3 gates, applies a per-gate confidence threshold and cooldown, and sends `PULSE:<gate>,<ms>` over serial. The firmware for this path is `esp32_cancela/esp32_cancela.ino`. It also accepts `OPEN:<gate>` and `CLOSE:<gate>`, uses pins 16/17/18, and runs at 115200 baud.

`interface/canva/interface.html` is a static Tailwind mockup of a control panel. Its JS only simulates state and is not connected to the Python code.

`Maquete Final/` holds SketchUp/CAD models of the physical belt. `scripts/runs/` and `datasets/` are gitignored.
