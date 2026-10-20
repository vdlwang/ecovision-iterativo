#include <Arduino.h>
#include <ESP32Servo.h>

#define LED_PIN   2
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

// ======== ÚNICA leitora da Serial ========
void serialTask(void *pvParameters) {
  String line;
  Serial.println("Comandos: <angulo 0..180> | SERVO <angulo> | MOTOR ON | MOTOR OFF");
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
            Serial.println("OK MOTOR ON");
          } else if (up == "MOTOR OFF") {
            motors_enabled = false;
            // garante OFF imediato
            analogWrite(PINO_IN1, 0);
            analogWrite(PINO_IN2, 0);
            Serial.println("OK MOTOR OFF");
          } else if (up.startsWith("SERVO ")) {
            int sp = up.indexOf(' ');
            int ang = up.substring(sp + 1).toInt();
            xQueueSend(qServoAngles, &ang, 0);
          } else {
            // tenta como número puro
            int ang = up.toInt();
            if (ang >= 0 && ang <= 180) {
              xQueueSend(qServoAngles, &ang, 0);
            } else {
              Serial.println("ERR: comando invalido.");
            }
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
      delay(5000);        // mantém posição por 5s
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

  Serial.begin(115200);
  Serial.println("ESP32 pronto.");

  qServoAngles = xQueueCreate(8, sizeof(int));

  xTaskCreate(motorControl, "Motor Control Task", 2048, NULL, 1, NULL);
  xTaskCreate(servoControl, "Servo Control Task", 2048, NULL, 1, NULL);
  xTaskCreate(serialTask,   "Serial Task",        4096, NULL, 2, NULL);
}

void loop() {}