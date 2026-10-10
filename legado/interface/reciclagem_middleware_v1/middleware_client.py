import json
import socket
import time

def send_detection(label: str, confidence: float, host: str = "127.0.0.1", port: int = 8765, timeout: float = 0.2):
    """Envia uma única detecção (linha JSON) para o middleware GUI.
    Uso típico: send_detection("glass bottle", 0.87)
    """
    payload = json.dumps({
        "label": str(label),
        "confidence": float(confidence),
        "ts": time.time(),
    }) + "\n"
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(payload.encode("utf-8"))
    except OSError:
        # Middleware pode não estar rodando — falha silenciosa para não quebrar a IA
        pass
