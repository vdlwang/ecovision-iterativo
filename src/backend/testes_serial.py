import serial
import time

# Ajuste a porta conforme o seu sistema:
PORT = "COM5"     # ex.: "COM5" (Windows) ou "/dev/ttyUSB0" (Linux/Mac)
BAUD = 115200

def send_line(ser, msg):
    if not msg.endswith("\n"):
        msg += "\n"
    ser.write(msg.encode("utf-8"))
    ser.flush()

def read_reply(ser, timeout=2.0):
    """Lê uma linha de resposta dentro do timeout (segundos)."""
    end = time.time() + timeout
    while time.time() < end:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            return line
    return None

def print_help():
    print(
        "Comandos:\n"
        "  60 | 90 | 120           -> posiciona o servo\n"
        "  SERVO <angulo>          -> posiciona o servo (0..180)\n"
        "  MOTOR ON                -> liga motor\n"
        "  MOTOR OFF               -> desliga motor\n"
        "  PING                    -> teste de comunicação\n"
        "  help                    -> mostra esta ajuda\n"
        "  sair / quit / exit      -> encerra\n"
    )

def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)  # tempo para o ESP32 reiniciar ao abrir a porta
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    print("Conectado em", PORT)
    print_help()

    while True:
        try:
            cmd = input("cmd> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando...")
            break

        if not cmd:
            continue

        lower = cmd.lower()
        if lower in ("sair", "quit", "exit", "q"):
            break
        if lower == "help":
            print_help()
            continue

        # Aceita MOTOR ON/OFF, PING, SERVO X, ou número puro (ângulo)
        to_send = None
        if lower in ("motor on", "motor off", "ping"):
            to_send = cmd.upper()
        elif lower.startswith("servo "):
            # SERVO <angulo>
            try:
                ang = int(lower.split()[1])
                if 0 <= ang <= 180:
                    to_send = f"SERVO {ang}"
                else:
                    print("Ângulo inválido: use 0..180.")
                    continue
            except Exception:
                print("Uso: SERVO <angulo>")
                continue
        else:
            # tenta número puro (ângulo)
            try:
                ang = int(cmd)
                if 0 <= ang <= 180:
                    to_send = str(ang)
                else:
                    print("Ângulo inválido: use 0..180.")
                    continue
            except ValueError:
                print("Comando inválido. Digite 'help' para ver as opções.")
                continue

        # Envia e lê resposta
        send_line(ser, to_send)
        resp = read_reply(ser, timeout=2.5)
        if resp:
            print("ESP32:", resp)
        else:
            print("Sem resposta do ESP32.")

    ser.close()
    print("Serial fechada.")

if __name__ == "__main__":
    main()
