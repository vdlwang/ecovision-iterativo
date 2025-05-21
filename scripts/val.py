from ultralytics import YOLO

TACO_MODEL_SOURCE = "../yolo_models/taco/yolov8s_100epochs-best.pt"
COCO_MODEL_SOURCE = "../yolo_models/yolo11n.pt"

model = YOLO(COCO_MODEL_SOURCE)

results = model.val(data="../datasets/coco8/coco8.yaml")

print(results.box)
