"""
Estado do motor da esteira como o backend o conhece, sem serial nem câmera
(testável sem hardware, como deteccao.py).

O ESP32 não confirma os comandos de motor, então o estado é o do último
comando que de fato saiu pela serial. Ele começa desligado (o firmware liga
com o motor parado) e volta a desligado quando o ESP32 reinicia: o firmware
anuncia o boot com MENSAGEM_BOOT, e um reset (queda de tensão com o servo,
por exemplo) desliga o motor sem aviso ao backend.
"""

MENSAGEM_BOOT = "ESP32 pronto."


class EstadoMotor:
    def __init__(self):
        self.ligado = False
        # instante (time.monotonic) em que o motor ligou; None se desligado
        self.ligado_desde = None

    def comando(self, ligar, enviado, agora):
        """Registra um comando MOTOR ON/OFF; só muda o estado se ele foi enviado."""
        if not enviado:
            return
        if ligar and not self.ligado:
            self.ligado_desde = agora
        elif not ligar:
            self.ligado_desde = None
        self.ligado = ligar

    def linha_recebida(self, linha):
        """Trata uma linha lida do ESP32. Devolve True se era o aviso de boot."""
        if linha.strip() != MENSAGEM_BOOT:
            return False
        self.ligado = False
        self.ligado_desde = None
        return True
