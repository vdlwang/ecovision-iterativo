"""
Servidor de Inferência EcoVision
Processa frames da câmera usando modelos YOLO da Ultralytics

INSTRUÇÕES DE USO:
1. Instale as dependências: pip install ultralytics flask flask-cors opencv-python pillow
2. Coloque os modelos .pt na pasta /models/ com os nomes:
   - yolov8n.pt (nano - mais rápido)
   - yolov8s.pt (small - balanceado)
   - yolov8m.pt (medium - mais preciso)
3. Execute: python inference_server.py
4. O servidor ficará disponível em http://localhost:5000

TREINAMENTO DOS MODELOS:
- Os modelos devem ser treinados para detectar 4 classes:
  - 0: papel
  - 1: metal
  - 2: plastico
  - 3: vidro
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import numpy as np
import base64
from PIL import Image
import io
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permite requisições do frontend

# Dicionário de modelos carregados
models = {}
MODEL_DIR = "./models"

# Mapeamento de classes (ajuste conforme seu treinamento)
CLASS_NAMES = {
    0: "papel",
    1: "metal", 
    2: "plastico",
    3: "vidro"
}

def load_model(model_name):
    """Carrega um modelo YOLO se ainda não estiver carregado"""
    if model_name not in models:
        model_path = os.path.join(MODEL_DIR, f"{model_name}.pt")
        
        if not os.path.exists(model_path):
            print(f"[ERRO] Modelo não encontrado: {model_path}")
            print(f"[INFO] Coloque o arquivo {model_name}.pt na pasta {MODEL_DIR}/")
            return None
        
        try:
            print(f"[MODELO] Carregando {model_path}...")
            models[model_name] = YOLO(model_path)
            print(f"[MODELO] {model_name} carregado com sucesso!")
            return models[model_name]
        except Exception as e:
            print(f"[ERRO] Falha ao carregar modelo {model_name}: {str(e)}")
            return None
    
    return models[model_name]

def decode_image(base64_string):
    """Decodifica uma imagem base64 para formato numpy array"""
    try:
        # Remove o prefixo data:image/jpeg;base64, se presente
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decodifica base64
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        
        # Converte para numpy array (formato BGR para OpenCV)
        image_np = np.array(image)
        if len(image_np.shape) == 2:  # Grayscale
            image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
        elif image_np.shape[2] == 4:  # RGBA
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2BGR)
        elif image_np.shape[2] == 3:  # RGB
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        return image_np
    except Exception as e:
        print(f"[ERRO] Falha ao decodificar imagem: {str(e)}")
        return None

@app.route('/api/inference', methods=['POST'])
def infer():
    """
    Endpoint principal de inferência
    
    Recebe:
    {
        "image": "base64_encoded_image",
        "model": "yolov8n|yolov8s|yolov8m",
        "confidence": 0.85
    }
    
    Retorna:
    {
        "detections": [
            {
                "class": "papel",
                "confidence": 0.92,
                "bbox": [x, y, width, height]  # Coordenadas normalizadas (0-1)
            },
            ...
        ]
    }
    """
    try:
        data = request.json
        
        # Valida entrada
        if not data or 'image' not in data:
            return jsonify({"error": "Imagem não fornecida"}), 400
        
        model_name = data.get('model', 'yolov8n').lower()
        confidence_threshold = float(data.get('confidence', 0.85))
        
        print(f"\n[INFERÊNCIA] {datetime.now().strftime('%H:%M:%S')} - Modelo: {model_name}, Confiança: {confidence_threshold}")
        
        # Carrega modelo
        model = load_model(model_name)
        if model is None:
            return jsonify({"error": f"Modelo {model_name} não disponível"}), 500
        
        # Decodifica imagem
        image = decode_image(data['image'])
        if image is None:
            return jsonify({"error": "Falha ao processar imagem"}), 400
        
        # Executa inferência
        results = model(image, conf=confidence_threshold, verbose=False)
        
        # Processa resultados
        detections = []
        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                # Extrai informações
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                # Normaliza coordenadas (0-1)
                img_height, img_width = image.shape[:2]
                bbox_normalized = [
                    x1 / img_width,
                    y1 / img_height,
                    (x2 - x1) / img_width,
                    (y2 - y1) / img_height
                ]
                
                # Obtém nome da classe
                class_name = CLASS_NAMES.get(cls_id, f"unknown_{cls_id}")
                
                detection = {
                    "class": class_name,
                    "confidence": confidence,
                    "bbox": bbox_normalized
                }
                
                detections.append(detection)
                print(f"[DETECÇÃO] {class_name}: {confidence*100:.1f}% - bbox: [{bbox_normalized[0]:.2f}, {bbox_normalized[1]:.2f}, {bbox_normalized[2]:.2f}, {bbox_normalized[3]:.2f}]")
        
        if not detections:
            print(f"[INFO] Nenhuma detecção acima de {confidence_threshold*100:.1f}%")
        
        return jsonify({"detections": detections})
    
    except Exception as e:
        print(f"[ERRO] Erro durante inferência: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/models', methods=['GET'])
def list_models():
    """Lista modelos disponíveis"""
    available_models = []
    
    for model_name in ['yolov8n', 'yolov8s', 'yolov8m']:
        model_path = os.path.join(MODEL_DIR, f"{model_name}.pt")
        if os.path.exists(model_path):
            available_models.append({
                "name": model_name,
                "path": model_path,
                "loaded": model_name in models
            })
    
    return jsonify({"models": available_models})

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "server": "EcoVision Inference Server",
        "models_loaded": len(models)
    })

if __name__ == '__main__':
    # Cria diretório de modelos se não existir
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    print("="*60)
    print("EcoVision - Servidor de Inferência com Ultralytics YOLO")
    print("="*60)
    print(f"\n[INFO] Diretório de modelos: {os.path.abspath(MODEL_DIR)}")
    print("[INFO] Coloque seus modelos .pt neste diretório:")
    print("  - yolov8n.pt (nano - mais rápido)")
    print("  - yolov8s.pt (small - balanceado)")
    print("  - yolov8m.pt (medium - mais preciso)")
    print("\n[INFO] Iniciando servidor na porta 5000...")
    print("[INFO] Endpoint de inferência: http://localhost:5000/api/inference")
    print("[INFO] Para usar com o frontend, certifique-se de que está rodando\n")
    
    # Inicia servidor Flask
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
