from ultralytics import YOLO

model = YOLO("yolo11n.pt")

results = model(0, save = True, conf=0.8, show = True)