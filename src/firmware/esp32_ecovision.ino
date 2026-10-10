/**
 * EcoVision - Firmware ESP32
 * Controla servo único + motor da esteira via comandos serial
 * 
 * Comandos:
 * - "MOTOR ON"   → Liga motor da esteira
 * - "MOTOR OFF"  → Desliga motor da esteira
 * - "0-180"      → Move servo para ângulo (mantém 5s, retorna para 180°)
 */

#include <Servo.h>

// ==== Pinos ====
const int SERVO_PIN = 22;  // Servo de direcionamento
const int MOTOR_PIN = 23;  // Relé do motor da esteira

// ==== Configuração ====
const int SERVO_HOLD_TIME = 5000;  // 5 segundos mantendo posição
const int SERVO_DEFAULT_POS = 180; // Posição padrão (sem material)

Servo directionServo;
bool motorRunning = true;

void setup() {
  Serial.begin(115200);
  
  // Inicializa servo
  directionServo.attach(SERVO_PIN);
  directionServo.write(SERVO_DEFAULT_POS);
  
  // Inicializa motor (ativo por padrão)
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, HIGH);
  
  Serial.println("EcoVision ESP32 Ready!");
  Serial.println("Commands: MOTOR ON/OFF, 0-180");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // Comando: Ligar motor
    if (command == "MOTOR ON") {
      digitalWrite(MOTOR_PIN, HIGH);
      motorRunning = true;
      Serial.println("OK: Motor ON");
    }
    
    // Comando: Desligar motor
    else if (command == "MOTOR OFF") {
      digitalWrite(MOTOR_PIN, LOW);
      motorRunning = false;
      Serial.println("OK: Motor OFF");
    }
    
    // Comando: Ângulo do servo (0-180)
    else {
      int angle = command.toInt();
      
      if (angle >= 0 && angle <= 180) {
        // Move servo para posição
        directionServo.write(angle);
        Serial.print("OK: Servo moved to ");
        Serial.println(angle);
        
        // Mantém por 5 segundos
        delay(SERVO_HOLD_TIME);
        
        // Retorna à posição padrão
        directionServo.write(SERVO_DEFAULT_POS);
        Serial.println("OK: Servo returned to default");
      } else {
        Serial.println("ERROR: Invalid angle (0-180)");
      }
    }
  }
}
