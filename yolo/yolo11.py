from ultralytics import YOLO

model = YOLO("./yolo/yolo11n.pt")

results = model(source=0, conf=0.8, show=True, save=False)