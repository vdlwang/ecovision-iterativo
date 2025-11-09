#!/usr/bin/env python3
"""
EcoVision - Conversor de Modelo YOLO para ONNX
Converte modelos PyTorch (.pt) para ONNX (.onnx) otimizado para navegador
"""

import argparse
import sys
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ Erro: ultralytics não está instalado")
    print("📦 Instale com: pip install ultralytics")
    sys.exit(1)


def convert_model(input_path: str, output_name: str = None, simplify: bool = True):
    """
    Converte modelo YOLO para formato ONNX
    
    Args:
        input_path: Caminho para arquivo .pt (ex: 'best.pt', 'yolov8n.pt')
        output_name: Nome do arquivo de saída (opcional)
        simplify: Se True, simplifica o grafo ONNX para melhor performance
    """
    input_file = Path(input_path)
    
    # Valida entrada
    if not input_file.exists():
        print(f"❌ Erro: Arquivo não encontrado: {input_path}")
        return False
    
    if not input_file.suffix == '.pt':
        print(f"❌ Erro: Arquivo deve ser .pt, recebido: {input_file.suffix}")
        return False
    
    print(f"📁 Carregando modelo: {input_path}")
    
    try:
        # Carrega modelo
        model = YOLO(str(input_file))
        
        print("🔄 Convertendo para ONNX...")
        print(f"   - Formato: ONNX")
        print(f"   - Simplify: {simplify}")
        print(f"   - Input size: 640x640")
        print(f"   - Dynamic: False (otimizado para web)")
        
        # Exporta para ONNX
        export_path = model.export(
            format='onnx',
            simplify=simplify,
            dynamic=False,
            imgsz=640,
            opset=12
        )
        
        # Renomeia se necessário
        export_file = Path(export_path)
        if output_name:
            output_file = export_file.parent / output_name
            export_file.rename(output_file)
            final_path = output_file
        else:
            final_path = export_file
        
        # Exibe informações
        file_size_mb = final_path.stat().st_size / (1024 * 1024)
        
        print("\n✅ Conversão concluída com sucesso!")
        print(f"📁 Arquivo gerado: {final_path}")
        print(f"📊 Tamanho: {file_size_mb:.2f} MB")
        print("\n📋 Próximos passos:")
        print(f"   1. Copie o arquivo para a pasta models/:")
        print(f"      cp {final_path} models/yolov8n.onnx")
        print(f"   2. Inicie a aplicação:")
        print(f"      npm run dev")
        print(f"   3. O sistema detectará o modelo ONNX automaticamente!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro durante conversão: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Converte modelo YOLO (.pt) para ONNX (.onnx) otimizado para web',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Converter modelo treinado
  python convert_to_onnx.py best.pt
  
  # Converter com nome específico
  python convert_to_onnx.py runs/detect/train/weights/best.pt --output yolov8n.onnx
  
  # Converter sem simplificação
  python convert_to_onnx.py best.pt --no-simplify
  
  # Ajuda
  python convert_to_onnx.py --help
        """
    )
    
    parser.add_argument(
        'input',
        help='Caminho para o arquivo .pt de entrada'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Nome do arquivo de saída (ex: yolov8n.onnx)',
        default=None
    )
    
    parser.add_argument(
        '--no-simplify',
        action='store_true',
        help='Não simplificar o grafo ONNX (pode reduzir performance)'
    )
    
    args = parser.parse_args()
    
    # Banner
    print("=" * 60)
    print("🌿 EcoVision - Conversor YOLO → ONNX")
    print("=" * 60)
    print()
    
    # Executa conversão
    success = convert_model(
        input_path=args.input,
        output_name=args.output,
        simplify=not args.no_simplify
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
