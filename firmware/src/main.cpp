#include <Arduino.h>
#include <ESP32Servo.h>

#define LED_PIN   2   // LED da placa: aceso = motor ligado; pisca enquanto o servo segura a posição
#define PINO_IN1  22
#define PINO_IN2  23
#define SERVO_PIN 32

Servo motor;

// ---- FILA p/ SERVO ----
QueueHandle_t qServoAngles = NULL;

// ---- FLAG GLOBAL: LIGA/DESLIGA MOTORES ----
volatile bool motors_enabled = false; // começa desligado

// ======== TASK MOTOR (agora respeita motors_enabled) ========
void motorControl(void *pvParameters) {
  while (1) {
    // Se motores OFF: “coast” (ambos LOW), pequena espera e continua
    if (!motors_enabled) {
      analogWrite(PINO_IN1, 0);
      analogWrite(PINO_IN2, 0);
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }

    analogWrite(PINO_IN1, 255);
    vTaskDelay(pdMS_TO_TICKS(100));
  }
}

// Enfileira o ângulo se o texto for um inteiro de 0 a 180 (sem isso, toInt()
// devolve 0 para qualquer texto e o servo iria para 0°)
bool enfileiraAngulo(const String &texto) {
  if (texto.length() == 0 || texto.length() > 3) return false;
  for (unsigned int i = 0; i < texto.length(); i++) {
    if (!isDigit(texto[i])) return false;
  }
  int ang = texto.toInt();
  if (ang > 180) return false;
  if (xQueueSend(qServoAngles, &ang, 0) != pdTRUE) {
    Serial.println("ERR: fila do servo cheia.");
  }
  return true;
}

// ======== ÚNICA leitora da Serial ========
void serialTask(void *pvParameters) {
  String line;
  Serial.println("Comandos: <angulo 0..180> | SERVO <angulo> | MOTOR ON | MOTOR OFF | PING");
  for (;;) {
    while (Serial.available() > 0) {
      char c = (char)Serial.read();
      if (c == '\r') continue;
      if (c == '\n') {
        line.trim();
        if (line.length() > 0) {
          String up = line; up.toUpperCase();

          if (up == "MOTOR ON") {
            motors_enabled = true;
            digitalWrite(LED_PIN, HIGH);
            Serial.println("OK MOTOR ON");
          } else if (up == "MOTOR OFF") {
            motors_enabled = false;
            // garante OFF imediato
            analogWrite(PINO_IN1, 0);
            analogWrite(PINO_IN2, 0);
            digitalWrite(LED_PIN, LOW);
            Serial.println("OK MOTOR OFF");
          } else if (up == "PING") {
            Serial.println("PONG");
          } else if (up.startsWith("SERVO ")) {
            String arg = up.substring(6);
            arg.trim();
            if (!enfileiraAngulo(arg)) Serial.println("ERR: angulo invalido (0..180).");
          } else if (!enfileiraAngulo(up)) {
            // número puro é o mesmo que SERVO <n>
            Serial.println("ERR: comando invalido.");
          }
        }
        line = "";
      } else {
        if (line.length() < 64) line += c;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

// ======== TASK do SERVO (consome fila) ========
void servoControl(void *pvParameters) {
  int angle = 0;
  while (1) {
    if (xQueueReceive(qServoAngles, &angle, portMAX_DELAY) == pdTRUE) {
      if (angle < 0) angle = 0;
      if (angle > 180) angle = 175;
      motor.write(angle);
      Serial.printf("Servo movido para %d graus\n", angle);
      // mantém posição por 5 s com o LED piscando
      bool aceso = false;
      for (int i = 0; i < 25; i++) {
        aceso = !aceso;
        digitalWrite(LED_PIN, aceso ? HIGH : LOW);
        vTaskDelay(pdMS_TO_TICKS(200));
      }
      digitalWrite(LED_PIN, motors_enabled ? HIGH : LOW);
      motor.write(175);   // retorna para 175
    }
  }
}

void setup() {
  pinMode(PINO_IN1, OUTPUT);
  pinMode(PINO_IN2, OUTPUT);
  pinMode(LED_PIN, OUTPUT);

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  motor.setPeriodHertz(50);
  motor.attach(SERVO_PIN, 500, 2400);
  motor.write(175);   // posição de repouso, a mesma para onde o servo volta
  digitalWrite(LED_PIN, LOW);

  Serial.begin(115200);
  Serial.println("ESP32 pronto.");

  qServoAngles = xQueueCreate(8, sizeof(int));

  xTaskCreate(motorControl, "Motor Control Task", 2048, NULL, 1, NULL);
  xTaskCreate(servoControl, "Servo Control Task", 2048, NULL, 1, NULL);
  xTaskCreate(serialTask,   "Serial Task",        4096, NULL, 2, NULL);
}

void loop() {}