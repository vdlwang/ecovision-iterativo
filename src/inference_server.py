"""
EcoVision - Servidor de Inferência com Ultralytics YOLO
Detecta materiais recicláveis em tempo real: papel, metal, plástico, vidro

Requisitos: pip install -r requirements.txt
"""

import os
import io
import time
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from ultralytics import YOLO

# ==================== CONFIGURAÇÃO ====================

app = FastAPI(
    title="EcoVision Inference API",
    description="API de inferência para detecção de materiais recicláveis",
    version="1.0.0"
)

# CORS para permitir acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mapeamento de classes COCO para materiais recicláveis
# Ajustar conforme o modelo treinado
CLASS_TO_MATERIAL = {
    # Papel/Papelão
    "book": "papel",
    "newspaper": "papel",
    "cardboard": "papel",
    
    # Metal
    "can": "metal",
    "fork": "metal",
    "knife": "metal",
    "spoon": "metal",
    
    # Plástico
    "bottle": "plastico",
    "cup": "plastico",
    "plastic_bag": "plastico",
    
    # Vidro
    "wine glass": "vidro",
    "glass": "vidro",
    "jar": "vidro",
}

# Modelos disponíveis
MODELS_PATH = "./models"
AVAILABLE_MODELS = {
    "YOLOv8n": "yolov8n.pt",  # Mais rápido, menos preciso
    "YOLOv8s": "yolov8s.pt",  # Balanceado
    "YOLOv8m": "yolov8m.pt",  # Mais preciso, mais lento
}

# Modelo atual carregado
current_model: Optional[YOLO] = None
current_model_version: str = "YOLOv8n"

# ==================== MODELOS DE DADOS ====================

class InferenceRequest(BaseModel):
    """Request para inferência com imagem base64"""
    image_base64: str
    model_version: Optional[str] = "YOLOv8n"
    min_confidence: Optional[float] = 0.5

class BoundingBox(BaseModel):
    """Bounding box de uma detecção"""
    x: float
    y: float
    width: float
    height: float

class Detection(BaseModel):
    """Detecção individual"""
    class_name: str
    material: str
    confidence: float
    bounding_box: BoundingBox

class InferenceResponse(BaseModel):
    """Response da inferência"""
    success: bool
    detections: List[Detection]
    processing_time_ms: int
    model_version: str
    timestamp: str
    image_shape: Tuple[int, int, int]

class ModelInfo(BaseModel):
    """Informações do modelo"""
    available_models: List[str]
    current_model: str
    model_path: str

# ==================== FUNÇÕES AUXILIARES ====================

def load_model(model_version: str = "YOLOv8n") -> YOLO:
    """
    Carrega o modelo YOLO especificado
    
    Args:
        model_version: Versão do modelo (YOLOv8n, YOLOv8s, YOLOv8m)
    
    Returns:
        Modelo YOLO carregado
    """
    global current_model, current_model_version
    
    if model_version not in AVAILABLE_MODELS:
        raise ValueError(f"Modelo {model_version} não disponível. Use: {list(AVAILABLE_MODELS.keys())}")
    
    model_filename = AVAILABLE_MODELS[model_version]
    model_path = os.path.join(MODELS_PATH, model_filename)
    
    # Se o modelo não existe, baixar automaticamente
    if not os.path.exists(model_path):
        os.makedirs(MODELS_PATH, exist_ok=True)
        print(f"📥 Baixando modelo {model_version}...")
        model = YOLO(model_filename)  # Ultralytics baixa automaticamente
        model.save(model_path)
    else:
        print(f"📦 Carregando modelo existente: {model_path}")
        model = YOLO(model_path)
    
    current_model = model
    current_model_version = model_version
    
    print(f"✅ Modelo {model_version} carregado com sucesso!")
    return model

def base64_to_image(base64_string: str) -> np.ndarray:
    """
    Converte string base64 para imagem numpy array
    
    Args:
        base64_string: String base64 da imagem
    
    Returns:
        Imagem como numpy array (BGR)
    """
    # Remove prefixo data:image se existir
    if "base64," in base64_string:
        base64_string = base64_string.split("base64,")[1]
    
    # Decodifica base64
    img_data = base64.b64decode(base64_string)
    
    # Converte para imagem PIL
    img_pil = Image.open(io.BytesIO(img_data))
    
    # Converte para numpy array (RGB)
    img_rgb = np.array(img_pil)
    
    # Converte RGB para BGR (formato OpenCV)
    if len(img_rgb.shape) == 3 and img_rgb.shape[2] == 3:
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    else:
        img_bgr = img_rgb
    
    return img_bgr

def map_class_to_material(class_name: str) -> str:
    """
    Mapeia classe detectada para material reciclável
    
    Args:
        class_name: Nome da classe detectada pelo YOLO
    
    Returns:
        Material correspondente (papel, metal, plastico, vidro)
    """
    class_lower = class_name.lower()
    
    # Busca exata
    if class_lower in CLASS_TO_MATERIAL:
        return CLASS_TO_MATERIAL[class_lower]
    
    # Busca por palavras-chave
    if any(key in class_lower for key in ["paper", "book", "cardboard"]):
        return "papel"
    if any(key in class_lower for key in ["metal", "can", "fork", "knife", "spoon"]):
        return "metal"
    if any(key in class_lower for key in ["plastic", "bottle", "cup", "bag"]):
        return "plastico"
    if any(key in class_lower for key in ["glass", "jar", "wine"]):
        return "vidro"
    
    # Default: classifica como plástico (mais comum)
    return "plastico"

def process_detections(results) -> List[Detection]:
    """
    Processa resultados do YOLO e converte para lista de detecções
    
    Args:
        results: Resultados do YOLO
    
    Returns:
        Lista de detecções formatadas
    """
    detections = []
    
    for result in results:
        boxes = result.boxes
        
        for i in range(len(boxes)):
            # Coordenadas do bounding box
            xyxy = boxes.xyxy[i].cpu().numpy()
            x1, y1, x2, y2 = xyxy
            
            # Confiança e classe
            conf = float(boxes.conf[i].cpu().numpy())
            cls_id = int(boxes.cls[i].cpu().numpy())
            class_name = result.names[cls_id]
            
            # Mapeia para material
            material = map_class_to_material(class_name)
            
            # Cria detecção
            detection = Detection(
                class_name=class_name,
                material=material,
                confidence=round(conf * 100, 2),  # Converte para percentual
                bounding_box=BoundingBox(
                    x=float(x1),
                    y=float(y1),
                    width=float(x2 - x1),
                    height=float(y2 - y1)
                )
            )
            
            detections.append(detection)
    
    return detections

# ==================== ENDPOINTS ====================

@app.on_event("startup")
async def startup_event():
    """Carrega modelo padrão ao iniciar"""
    print("🚀 Iniciando EcoVision Inference Server...")
    try:
        load_model("YOLOv8n")
        print("✅ Servidor pronto!")
    except Exception as e:
        print(f"⚠️  Erro ao carregar modelo: {e}")
        print("ℹ️  O modelo será carregado na primeira requisição")

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "message": "EcoVision Inference Server is running",
        "version": "1.0.0",
        "current_model": current_model_version
    }

@app.get("/health")
async def health():
    """Health check detalhado"""
    return {
        "status": "healthy",
        "model_loaded": current_model is not None,
        "current_model": current_model_version,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/models")
async def get_models() -> ModelInfo:
    """Lista modelos disponíveis"""
    return ModelInfo(
        available_models=list(AVAILABLE_MODELS.keys()),
        current_model=current_model_version,
        model_path=os.path.join(MODELS_PATH, AVAILABLE_MODELS.get(current_model_version, ""))
    )

@app.post("/models/load")
async def load_model_endpoint(model_version: str):
    """Carrega um modelo específico"""
    try:
        load_model(model_version)
        return {
            "success": True,
            "message": f"Modelo {model_version} carregado com sucesso",
            "current_model": current_model_version
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/inference", response_model=InferenceResponse)
async def inference(request: InferenceRequest):
    """
    Realiza inferência em uma imagem base64
    
    Args:
        request: Request com imagem base64 e configurações
    
    Returns:
        Detecções encontradas na imagem
    """
    try:
        start_time = time.time()
        
        # Carrega modelo se necessário
        if current_model is None or current_model_version != request.model_version:
            load_model(request.model_version)
        
        # Converte base64 para imagem
        img = base64_to_image(request.image_base64)
        
        # Realiza inferência
        results = current_model.predict(
            img,
            conf=request.min_confidence,
            verbose=False
        )
        
        # Processa detecções
        detections = process_detections(results)
        
        # Calcula tempo de processamento
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return InferenceResponse(
            success=True,
            detections=detections,
            processing_time_ms=processing_time_ms,
            model_version=current_model_version,
            timestamp=datetime.now().isoformat(),
            image_shape=img.shape
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na inferência: {str(e)}"
        )

@app.post("/inference/file")
async def inference_file(
    file: UploadFile = File(...),
    model_version: str = Form("YOLOv8n"),
    min_confidence: float = Form(0.5)
):
    """
    Realiza inferência em arquivo de imagem
    
    Args:
        file: Arquivo de imagem (jpg, png, etc)
        model_version: Versão do modelo
        min_confidence: Confiança mínima
    
    Returns:
        Detecções encontradas na imagem
    """
    try:
        # Lê arquivo
        contents = await file.read()
        
        # Converte para base64
        base64_string = base64.b64encode(contents).decode('utf-8')
        
        # Chama endpoint de inferência
        request = InferenceRequest(
            image_base64=base64_string,
            model_version=model_version,
            min_confidence=min_confidence
        )
        
        return await inference(request)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar arquivo: {str(e)}"
        )

# ==================== MAIN ====================

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════╗
    ║   EcoVision Inference Server              ║
    ║   Detecção de Materiais Recicláveis       ║
    ║   Powered by Ultralytics YOLO             ║
    ╚═══════════════════════════════════════════╝
    """)
    
    # Porta padrão: 8000
    # Acessível em: http://localhost:8000
    # Documentação: http://localhost:8000/docs
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
