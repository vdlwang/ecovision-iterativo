#!/usr/bin/env python3
"""
EcoVision - Script de Teste de Instalação
Verifica se todos os componentes estão instalados corretamente
"""

import sys
import os

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_python_version():
    print("🐍 Verificando versão do Python...")
    version = sys.version_info
    print(f"   Versão: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 8:
        print("   ✅ Versão compatível!")
        return True
    else:
        print("   ❌ Python 3.8+ necessário!")
        return False

def check_module(module_name, import_name=None):
    import_name = import_name or module_name
    try:
        mod = __import__(import_name)
        version = getattr(mod, '__version__', 'N/A')
        print(f"   ✅ {module_name}: {version}")
        return True
    except ImportError:
        print(f"   ❌ {module_name}: NÃO INSTALADO")
        return False

def check_cuda():
    print("\n🎮 Verificando suporte CUDA (GPU)...")
    try:
        import torch
        has_cuda = torch.cuda.is_available()
        
        if has_cuda:
            device_name = torch.cuda.get_device_name(0)
            print(f"   ✅ CUDA disponível!")
            print(f"   GPU: {device_name}")
            print(f"   CUDA Version: {torch.version.cuda}")
        else:
            print("   ⚠️  CUDA não disponível (GPU não detectada)")
            print("   Inferência será feita na CPU (mais lento)")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro ao verificar CUDA: {e}")
        return False

def check_webcam():
    print("\n📹 Verificando acesso à webcam...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                h, w, c = frame.shape
                print(f"   ✅ Webcam detectada!")
                print(f"   Resolução: {w}x{h}")
                cap.release()
                return True
            else:
                print("   ⚠️  Webcam detectada mas não conseguiu capturar frame")
                cap.release()
                return False
        else:
            print("   ❌ Nenhuma webcam detectada")
            print("   Conecte uma webcam USB ou use câmera integrada")
            return False
    except Exception as e:
        print(f"   ❌ Erro ao acessar webcam: {e}")
        return False

def check_model_files():
    print("\n🤖 Verificando modelos YOLO...")
    models_dir = "./models"
    
    if not os.path.exists(models_dir):
        print(f"   ⚠️  Pasta {models_dir} não encontrada")
        print(f"   Criando pasta...")
        os.makedirs(models_dir, exist_ok=True)
    
    models = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"]
    found = []
    
    for model in models:
        path = os.path.join(models_dir, model)
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024 * 1024)  # MB
            print(f"   ✅ {model}: {size:.1f} MB")
            found.append(model)
        else:
            print(f"   ⚠️  {model}: Não encontrado")
    
    if len(found) == 0:
        print("\n   ℹ️  Nenhum modelo encontrado")
        print("   Os modelos serão baixados automaticamente na primeira execução")
    
    return True

def test_inference():
    print("\n🧪 Testando inferência com imagem de exemplo...")
    try:
        from ultralytics import YOLO
        import numpy as np
        
        # Cria imagem de teste (pura azul)
        img = np.zeros((640, 640, 3), dtype=np.uint8)
        img[:, :] = (255, 0, 0)  # Azul
        
        print("   Carregando modelo YOLOv8n...")
        model = YOLO('yolov8n.pt')
        
        print("   Executando inferência...")
        results = model.predict(img, verbose=False)
        
        print(f"   ✅ Inferência executada com sucesso!")
        print(f"   Detecções: {len(results[0].boxes)}")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro na inferência: {e}")
        return False

def main():
    print_header("EcoVision - Verificação de Instalação")
    
    results = {}
    
    # Verificar Python
    results['python'] = check_python_version()
    
    # Verificar módulos
    print("\n📦 Verificando dependências...")
    modules = [
        ('FastAPI', 'fastapi'),
        ('Uvicorn', 'uvicorn'),
        ('Ultralytics', 'ultralytics'),
        ('OpenCV', 'cv2'),
        ('Pillow', 'PIL'),
        ('PyTorch', 'torch'),
        ('NumPy', 'numpy'),
        ('Pydantic', 'pydantic'),
    ]
    
    all_modules = True
    for name, import_name in modules:
        if not check_module(name, import_name):
            all_modules = False
    
    results['modules'] = all_modules
    
    # Verificar CUDA
    results['cuda'] = check_cuda()
    
    # Verificar webcam
    results['webcam'] = check_webcam()
    
    # Verificar modelos
    results['models'] = check_model_files()
    
    # Teste de inferência
    if results['modules']:
        results['inference'] = test_inference()
    else:
        print("\n⚠️  Pulando teste de inferência (dependências não instaladas)")
        results['inference'] = False
    
    # Resumo
    print_header("Resumo da Verificação")
    
    status = []
    status.append(("Python 3.8+", results['python']))
    status.append(("Dependências", results['modules']))
    status.append(("CUDA/GPU", results.get('cuda', False)))
    status.append(("Webcam", results['webcam']))
    status.append(("Modelos YOLO", results['models']))
    status.append(("Teste Inferência", results.get('inference', False)))
    
    for item, ok in status:
        symbol = "✅" if ok else "❌"
        print(f"{symbol} {item}")
    
    # Recomendações
    print("\n" + "="*60)
    
    if all(results.values()):
        print("🎉 PARABÉNS! Tudo está configurado corretamente!")
        print("\nPróximos passos:")
        print("  1. Execute: python inference_server.py")
        print("  2. Acesse: http://localhost:8000/docs")
        print("  3. Teste a API de inferência")
    else:
        print("⚠️  Algumas verificações falharam.")
        print("\nPara corrigir:")
        
        if not results['modules']:
            print("  • Instale dependências: pip install -r requirements.txt")
        
        if not results['webcam']:
            print("  • Conecte uma webcam ou verifique permissões")
        
        if not results.get('cuda', True):
            print("  • (Opcional) Instale CUDA para acelerar inferência")
            print("    https://developer.nvidia.com/cuda-downloads")
    
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Verificação interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
