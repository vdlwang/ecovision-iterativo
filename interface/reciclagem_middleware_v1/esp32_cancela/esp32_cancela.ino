// ESP32 — Acionamento de 3 cancelas via comandos seriais de texto
// Protocolo esperado (terminado em \n):
//   PULSE:<gate>,<ms>   ex.: PULSE:1,500  (Cancela 1 por 500 ms)
//   OPEN:<gate>         ex.: OPEN:2
//   CLOSE:<gate>        ex.: CLOSE:3

#include <Arduino.h>

// Ajuste os pinos conforme seu circuito
const int GATE_PINS[4] = { -1, 16, 17, 18 }; // índices 1..3 são válidos

String inbuf;

void setup() {
  Serial.begin(115200);
  delay(300);
  for (int i = 1; i <= 3; ++i) {
    pinMode(GATE_PINS[i], OUTPUT);
    digitalWrite(GATE_PINS[i], LOW);
  }
  Serial.println("ESP32 pronto");
}

void pulseGate(int gate, int ms) {
  if (gate < 1 || gate > 3) return;
  if (ms < 50) ms = 50; // mínimo de segurança
  digitalWrite(GATE_PINS[gate], HIGH);
  delay(ms);
  digitalWrite(GATE_PINS[gate], LOW);
}

void openGate(int gate) {
  if (gate < 1 || gate > 3) return;
  digitalWrite(GATE_PINS[gate], HIGH);
}

void closeGate(int gate) {
  if (gate < 1 || gate > 3) return;
  digitalWrite(GATE_PINS[gate], LOW);
}

void processLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line.startsWith("PULSE:")) {
    int c = line.indexOf(':');
    int comma = line.indexOf(',', c + 1);
    if (comma > 0) {
      int gate = line.substring(c + 1, comma).toInt();
      int ms = line.substring(comma + 1).toInt();
      pulseGate(gate, ms);
      Serial.printf("OK PULSE %d %d\n", gate, ms);
      return;
    }
  }
  if (line.startsWith("OPEN:")) {
    int gate = line.substring(5).toInt();
    openGate(gate);
    Serial.printf("OK OPEN %d\n", gate);
    return;
  }
  if (line.startsWith("CLOSE:")) {
    int gate = line.substring(6).toInt();
    closeGate(gate);
    Serial.printf("OK CLOSE %d\n", gate);
    return;
  }

  Serial.println("ERR comando");
}

void loop() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (inbuf.length() > 0) {
        processLine(inbuf);
        inbuf = "";
      }
    } else {
      inbuf += ch;
    }
  }
}
