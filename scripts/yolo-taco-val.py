from ultralytics import YOLO

model = YOLO("runs/detect/train/yolov8s_100epochs/weights/best.pt")
results = model.val(data="45-SF")
# results = model.val(data="../datasets/TACO/data/")

print(results)
