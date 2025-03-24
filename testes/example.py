from ultralytics import YOLO

# model = YOLO("yolo11n.pt")
model = YOLO("runs/detect/train/weights/best.pt")

# results = model.train(data="coco8.yaml", epochs=10, imgsz=640)
# results = model(source = "example.jpeg", save = True)
results = model.val()

print(results)
