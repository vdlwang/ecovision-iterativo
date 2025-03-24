from ultralytics import YOLO

# Load a COCO-pretrained YOLO11n model
model = YOLO("yolo11n.pt")

results = model(source = 0, save = True, conf=0.4, show = True)
