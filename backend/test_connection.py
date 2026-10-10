"""
Script de teste para verificar conexões do sistema
"""

import sys

def test_imports():
    """Testa se todas as bibliotecas estão instaladas"""
    print("=" * 50)
    print("Testando importações...")
    print("=" * 50)
    
    try:
        import cv2
        print("✓ OpenCV instalado:", cv2.__version__)
    except ImportError:
        print("✗ OpenCV não instalado. Execute: pip install opencv-python")
        return False
    
    try:
        import serial
        print("✓ PySerial instalado:", serial.__version__)
    except ImportError:
        print("✗ PySerial não instalado. Execute: pip install pyserial")
        return False
    
    try:
        import websockets
        print("✓ WebSockets instalado:", websockets.__version__)
    except ImportError:
        print("✗ WebSockets não instalado. Execute: pip install websockets")
        return False
    
    try:
        from ultralytics import YOLO
        print("✓ Ultralytics YOLO instalado")
    except ImportError:
        print("✗ Ultralytics não instalado. Execute: pip install ultralytics")
        return False
    
    print()
    return True

def test_camera():
    """Testa se a câmera está acessível"""
    print("=" * 50)
    print("Testando câmera...")
    print("=" * 50)
    
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("✗ Câmera não encontrada no índice 0")
            print("  Tente ajustar 'camera_index' no config.json")
            return False
        
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            print(f"✓ Câmera funcionando: {w}x{h}")
            cap.release()
            return True
        else:
            print("✗ Erro ao capturar frame da câmera")
            cap.release()
            return False
    except Exception as e:
        print(f"✗ Erro ao testar câmera: {e}")
        return False

def test_serial():
    """Lista portas seriais disponíveis"""
    print("=" * 50)
    print("Testando conexão serial...")
    print("=" * 50)
    
    try:
        import serial.tools.list_ports
        
        ports = list(serial.tools.list_ports.comports())
        
        if not ports:
            print("✗ Nenhuma porta serial encontrada")
            print("  Conecte o ESP32 via USB")
            return False
        
        print("✓ Portas seriais disponíveis:")
        for port in ports:
            print(f"  - {port.device}: {port.description}")
        
        print("\nAtualize 'serial_port' no config.json com a porta correta")
        return True
    except Exception as e:
        print(f"✗ Erro ao listar portas: {e}")
        return False

def test_websocket():
    """Testa se a porta WebSocket está livre"""
    print("=" * 50)
    print("Testando porta WebSocket...")
    print("=" * 50)
    
    try:
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8765))
        sock.close()
        
        if result == 0:
            print("✗ Porta 8765 já está em uso")
            print("  Feche o backend anterior ou altere a porta")
            return False
        else:
            print("✓ Porta 8765 disponível")
            return True
    except Exception as e:
        print(f"✗ Erro ao testar porta: {e}")
        return False

def main():
    print("\n" + "=" * 50)
    print("EcoVision - Teste de Conexões")
    print("=" * 50 + "\n")
    
    results = []
    
    results.append(("Bibliotecas", test_imports()))
    results.append(("Câmera", test_camera()))
    results.append(("Serial", test_serial()))
    results.append(("WebSocket", test_websocket()))
    
    print("\n" + "=" * 50)
    print("RESUMO")
    print("=" * 50)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    all_passed = all(r for _, r in results)
    
    if all_passed:
        print("\n✓ Todos os testes passaram! O sistema está pronto.")
        print("\nExecute: python ecovision_local.py")
    else:
        print("\n✗ Alguns testes falharam. Corrija os problemas acima.")
    
    print("=" * 50 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
