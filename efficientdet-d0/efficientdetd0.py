import torch
import cv2
import numpy as np
from effdet import create_model
from torchvision import transforms

# COCO class labels
COCO_CLASSES = [
    "N/A", "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", 
    "traffic light", "fire hydrant", "N/A", "stop sign", "parking meter", "bench", "bird", "cat", "dog", 
    "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "N/A", "backpack", "umbrella", 
    "N/A", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", 
    "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "N/A", "wine glass", "cup", 
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", 
    "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed", "N/A", "dining table", "N/A", "toilet", 
    "N/A", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", 
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# Criar o modelo EfficientDet-D0 pré-treinado
model = create_model('tf_efficientdet_d0', pretrained=True)
model.eval()

# Transformação para a imagem
transform = transforms.Compose([
    transforms.ToTensor()
])

# Abrir a webcam
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Redimensionar e converter para tensor
    img_resized = cv2.resize(frame, (512, 512))  # Dimensão esperada pelo EfficientDet-D0
    img_tensor = transform(img_resized).unsqueeze(0)

    # Fazer a previsão
    with torch.no_grad():
        outputs = model(img_tensor)  # EfficientDet retorna uma lista de dicionários

    # Processar os resultados (ajustando a indexação correta)
    if len(outputs) > 0 and isinstance(outputs, list):  # Verifica se há detecções
        outputs = outputs[0]  # Pegamos o primeiro item da lista

        boxes = outputs['boxes'].cpu().numpy().astype(int)
        scores = outputs['scores'].cpu().numpy()
        labels = outputs['labels'].cpu().numpy()

        for i in range(len(scores)):
            if scores[i] > 0.2:  # Definir um limiar de confiança
                box = boxes[i]
                label = int(labels[i])

                # Obter o nome da classe a partir do índice
                label_name = COCO_CLASSES[label]

                # Desenhar a caixa de detecção e o rótulo
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
                cv2.putText(frame, f"{label_name}: {scores[i]:.2f}", (box[0], box[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Mostrar o frame
    cv2.imshow("EfficientDet Webcam", frame)

    # Sair com tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
