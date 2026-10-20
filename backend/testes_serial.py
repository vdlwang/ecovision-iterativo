import json
import serial
import time
from pathlib import Path

# Porta e baud vêm do mesmo config.json do backend (serial_port, baud_rate)
CONFIG_FILE = Path(__file__).parent / "config.json"
DEFAULT_PORT = "COM8"
DEFAULT_BAUD = 115200

def load_serial_config():
    """Lê serial_port e baud_rate do config.json, com padrões se ele não existir"""
    if not CONFIG_FILE.exists():
        print(f"{CONFIG_FILE} não encontrado; usando {DEFAULT_PORT}. "
              "Rode o backend uma vez para criá-lo e ajuste serial_port.")
        return DEFAULT_PORT, DEFAULT_BAUD
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config.get('serial_port', DEFAULT_PORT), config.get('baud_rate', DEFAULT_BAUD)

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
        "  <angulo>                -> posiciona o servo (0..180; ex.: 50, 110, 130, 150)\n"
        "  SERVO <angulo>          -> posiciona o servo (0..180)\n"
        "  MOTOR ON                -> liga motor\n"
        "  MOTOR OFF               -> desliga motor\n"
        "  PING                    -> teste de comunicação (responde PONG; firmware antigo move o servo a 0°)\n"
        "  help                    -> mostra esta ajuda\n"
        "  sair / quit / exit      -> encerra\n"
    )

def main():
    port, baud = load_serial_config()
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2)  # tempo para o ESP32 reiniciar ao abrir a porta
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    print("Conectado em", port)
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
