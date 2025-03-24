from ultralytics import YOLO

# run yolo11n on test-images

model = YOLO("yolo11n.pt")
results = model(source = "test-images/*", save = True)

print(results)
