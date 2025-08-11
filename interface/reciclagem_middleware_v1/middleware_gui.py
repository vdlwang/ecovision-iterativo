import json
import queue
import socketserver
import threading
from datetime import datetime

import serial
import serial.tools.list_ports

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext

HOST = "127.0.0.1"
PORT = 8765  # Porta TCP para receber resultados da IA

# Materiais mapeáveis (ajuste se seus rótulos forem diferentes)
MATERIAIS = [
    "glass bottle",
    "normal paper",
    "corrugated carton",
    "metal drink can",
    "plastic bottle cap",
    "plastic bottle",
]

# Fila thread-safe para mensagens de detecção
_detection_queue = queue.Queue()

class DetectionTCPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        for raw in self.rfile:
            try:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                data = json.loads(line)
                # Esperado: {"label": str, "confidence": float}
                if "label" in data and "confidence" in data:
                    _detection_queue.put(data)
            except Exception:
                # Ignora linhas inválidas para robustez
                continue

class DetectionServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

class MiddlewareGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Middleware IA ↔ ESP32 — Esteira de Reciclagem")
        self.root.geometry("980x680")

        self.server = None
        self.server_thread = None
        self.ser = None  # serial.Serial ou None

        # Estado: seleção de material por cancela
        self.gate_material_vars = [tk.StringVar(value="— Nenhum —") for _ in range(3)]
        # Limite mínimo de confiança (%) por cancela
        self.threshold_vars = [tk.IntVar(value=60) for _ in range(3)]
        # Duração do pulso (ms) por cancela
        self.pulse_ms_vars = [tk.IntVar(value=500) for _ in range(3)]

        self.last_detection_var = tk.StringVar(value="—")
        self.server_status_var = tk.StringVar(value=f"Servidor TCP: iniciando em {HOST}:{PORT}…")
        self.serial_status_var = tk.StringVar(value="Serial: desconectado")

        # cooldown opcional por cancela (ms)
        self.cooldown_ms = 300
        self._last_pulse_ts = [0.0, 0.0, 0.0]

        self._build_ui()
        self._start_server()
        self._poll_queue()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------
    def _build_ui(self):
        pad = 8

        # Top: Conexão Serial
        frm_serial = ttk.LabelFrame(self.root, text="Conexão com ESP32 (Serial)")
        frm_serial.pack(fill=tk.X, padx=pad, pady=(pad, 4))

        ttk.Label(frm_serial, textvariable=self.serial_status_var).pack(side=tk.LEFT, padx=pad)

        self.port_combo = ttk.Combobox(frm_serial, width=24, state="readonly")
        self._refresh_ports()
        self.port_combo.pack(side=tk.LEFT, padx=pad)

        ttk.Button(frm_serial, text="Atualizar portas", command=self._refresh_ports).pack(side=tk.LEFT)
        ttk.Button(frm_serial, text="Conectar", command=self._connect_serial).pack(side=tk.LEFT, padx=(pad, 0))
        ttk.Button(frm_serial, text="Desconectar", command=self._disconnect_serial).pack(side=tk.LEFT)

        # Status do servidor
        frm_server = ttk.LabelFrame(self.root, text="Servidor de detecções (IA → GUI)")
        frm_server.pack(fill=tk.X, padx=pad, pady=4)
        ttk.Label(frm_server, textvariable=self.server_status_var).pack(side=tk.LEFT, padx=pad)

        # Mapeamento e parâmetros
        frm_map = ttk.LabelFrame(self.root, text="Mapeamento de Materiais → Cancelas & Parâmetros")
        frm_map.pack(fill=tk.X, padx=pad, pady=4)

        header = ["Cancela", "Material", "Confiança mínima (%)", "Pulso (ms)", "Teste"]
        for c, h in enumerate(header):
            ttk.Label(frm_map, text=h, font=("", 10, "bold")).grid(row=0, column=c, padx=6, pady=6)

        opcoes = ["— Nenhum —"] + MATERIAIS

        for i in range(3):
            r = i + 1
            ttk.Label(frm_map, text=f"Cancela {r}").grid(row=r, column=0, padx=6, pady=4, sticky="w")

            cb = ttk.Combobox(frm_map, values=opcoes, state="readonly", width=28, textvariable=self.gate_material_vars[i])
            cb.grid(row=r, column=1, padx=6, pady=4)
            cb.bind("<<ComboboxSelected>>", lambda e, idx=i: self._on_gate_selection_changed(idx))

            sp_thr = ttk.Spinbox(frm_map, from_=0, to=100, increment=1, width=6, textvariable=self.threshold_vars[i])
            sp_thr.grid(row=r, column=2, padx=6, pady=4)

            sp_ms = ttk.Spinbox(frm_map, from_=50, to=5000, increment=50, width=8, textvariable=self.pulse_ms_vars[i])
            sp_ms.grid(row=r, column=3, padx=6, pady=4)

            ttk.Button(frm_map, text="Testar", command=lambda idx=i: self._test_gate(idx)).grid(row=r, column=4, padx=6, pady=4)

        # Simulador de detecção
        frm_sim = ttk.LabelFrame(self.root, text="Simular detecção (para testes)")
        frm_sim.pack(fill=tk.X, padx=pad, pady=4)

        ttk.Label(frm_sim, text="Material:").pack(side=tk.LEFT, padx=(pad, 4))
        self.sim_mat = ttk.Combobox(frm_sim, values=MATERIAIS, state="readonly", width=28)
        self.sim_mat.current(0)
        self.sim_mat.pack(side=tk.LEFT, padx=(0, pad))

        ttk.Label(frm_sim, text="Confiança (%):").pack(side=tk.LEFT)
        self.sim_conf = ttk.Spinbox(frm_sim, from_=0, to=100, increment=1, width=6)
        self.sim_conf.delete(0, tk.END)
        self.sim_conf.insert(0, "85")
        self.sim_conf.pack(side=tk.LEFT, padx=(0, pad))

        ttk.Button(frm_sim, text="Enviar simulação", command=self._send_sim).pack(side=tk.LEFT)

        # Última detecção
        frm_last = ttk.LabelFrame(self.root, text="Última detecção recebida")
        frm_last.pack(fill=tk.X, padx=pad, pady=4)
        ttk.Label(frm_last, textvariable=self.last_detection_var, font=("", 10)).pack(side=tk.LEFT, padx=pad)

        # Log
        frm_log = ttk.LabelFrame(self.root, text="Log")
        frm_log.pack(fill=tk.BOTH, expand=True, padx=pad, pady=(4, pad))
        self.log_box = scrolledtext.ScrolledText(frm_log, height=18, wrap=tk.WORD)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)
        self._log("Pronto. Configure a serial e o mapeamento.")

    # ---------- Serial ----------
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["(nenhuma porta encontrada)"]
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)

    def _connect_serial(self):
        if self.ser and self.ser.is_open:
            messagebox.showinfo("Serial", "Já conectado.")
            return
        port = self.port_combo.get()
        if not port or port == "(nenhuma porta encontrada)":
            messagebox.showwarning("Serial", "Selecione uma porta válida.")
            return
        try:
            self.ser = serial.Serial(port=port, baudrate=115200, timeout=0.1)
            self.serial_status_var.set(f"Serial: conectado em {port} @115200")
            self._log(f"[SERIAL] Conectado em {port} @115200")
        except Exception as e:
            self.ser = None
            self.serial_status_var.set("Serial: erro ao conectar")
            messagebox.showerror("Serial", f"Falha ao conectar: {e}")

    def _disconnect_serial(self):
        try:
            if self.ser:
                port = self.ser.port
                self.ser.close()
                self._log(f"[SERIAL] Desconectado de {port}")
        except Exception:
            pass
        finally:
            self.ser = None
            self.serial_status_var.set("Serial: desconectado")

    # ---------- Servidor TCP ----------
    def _start_server(self):
        try:
            self.server = DetectionServer((HOST, PORT), DetectionTCPHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.server_status_var.set(f"Servidor TCP: ouvindo em {HOST}:{PORT}")
            self._log(f"[TCP] Servidor ouvindo em {HOST}:{PORT}")
        except OSError as e:
            self.server = None
            self.server_status_var.set(f"Servidor TCP: falhou ({e})")
            self._log(f"[TCP] ERRO ao iniciar servidor: {e}")

    def _stop_server(self):
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
        except Exception:
            pass
        self.server = None

    # ---------- Processamento ----------
    def _poll_queue(self):
        try:
            while True:
                data = _detection_queue.get_nowait()
                self._handle_detection(data)
        except queue.Empty:
            pass
        # Repetir a checagem periodicamente
        self.root.after(50, self._poll_queue)

    def _handle_detection(self, data):
        label = str(data.get("label", "")).strip()
        conf = float(data.get("confidence", 0.0))
        self.last_detection_var.set(f"label='{label}', confiança={conf:.3f}")

        gate_idx = self._gate_for_label(label)
        if gate_idx is None:
            self._log(f"[IA] {label} ({conf:.2f}) → não mapeado, ignorado.")
            return

        thr = self.threshold_vars[gate_idx].get() / 100.0
        if conf < thr:
            self._log(f"[IA] {label} ({conf:.2f}) < limite {thr:.2f} (Cancela {gate_idx+1}), ignorado.")
            return

        # cooldown simples por cancela
        from time import monotonic
        now = monotonic() * 1000.0
        if now - self._last_pulse_ts[gate_idx] < self.cooldown_ms:
            self._log(f"[IA] {label} ({conf:.2f}) OK, mas em cooldown (Cancela {gate_idx+1}).")
            return
        self._last_pulse_ts[gate_idx] = now

        pulse_ms = int(self.pulse_ms_vars[gate_idx].get())
        self._trigger_gate(gate_idx, pulse_ms, reason=f"{label} ({conf:.2f}) ≥ {thr:.2f}")

    def _gate_for_label(self, label):
        # Retorna índice 0..2 da cancela associada ao material, ou None
        for i, var in enumerate(self.gate_material_vars):
            if var.get() == label:
                return i
        return None

    def _trigger_gate(self, gate_idx, pulse_ms, reason=""):
        msg = f"PULSE:{gate_idx+1},{pulse_ms}\n"
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(msg.encode("utf-8"))
                self._log(f"[CMD] → ESP32: {msg.strip()}  | {reason}")
            except Exception as e:
                self._log(f"[CMD] FALHA ao enviar: {e}")
        else:
            self._log(f"[CMD] (não enviado — serial desconectado): {msg.strip()}  | {reason}")

    # ---------- Callbacks ----------
    def _on_gate_selection_changed(self, changed_idx):
        sel = self.gate_material_vars[changed_idx].get()
        if sel == "— Nenhum —":
            return
        # Evitar duplicidade: se já estiver em outra cancela, tira de lá
        for i, var in enumerate(self.gate_material_vars):
            if i != changed_idx and var.get() == sel:
                var.set("— Nenhum —")
                self._log(f"[MAP] '{sel}' movido para Cancela {changed_idx+1} (removido da Cancela {i+1}).")

    def _test_gate(self, idx):
        pulse_ms = int(self.pulse_ms_vars[idx].get())
        self._trigger_gate(idx, pulse_ms, reason="Teste manual")

    def _send_sim(self):
        label = self.sim_mat.get()
        try:
            conf = float(self.sim_conf.get()) / 100.0
        except Exception:
            conf = 0.0
        data = {"label": label, "confidence": conf}
        self._handle_detection(data)

    # ---------- Util ----------
    def _log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{ts}] {text}\n")
        self.log_box.see(tk.END)

    def _on_close(self):
        self._stop_server()
        self._disconnect_serial()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MiddlewareGUI(root)
    root.mainloop()
