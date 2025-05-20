from ultralytics import YOLO

INFER_SOURCE = "../images/20250323_174353.jpg"
MODEL_SOURCE = "../yolo_models/taco/yolov8s_100epochs-best.pt"
USE_WEBCAM = False

model = YOLO(MODEL_SOURCE)

if USE_WEBCAM:
    results = model(source = 0, save = True, conf=0.4, show = True)
else:
    results = model(source = INFER_SOURCE, save = True)

print(results)
