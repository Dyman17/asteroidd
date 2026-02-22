#include "config.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

// Глобальные переменные
Servo servoBase, servoShoulder, servoElbow, servoGripper;
bool wifi_connected = false;
unsigned long last_scan_time = 0;
String last_decision = "NONE";

// Структура для хранения расстояний
struct Distances {
  float left;
  float center;
  float right;
};

// Структура для позиций манипулятора
struct ManipulatorPosition {
  int base;
  int shoulder;
  int elbow;
  int gripper;
};

// Предопределенные позиции
const ManipulatorPosition positions[] = {
  {90, 90, 90, 90},   // POSITION_HOME
  {90, 60, 120, 90},  // POSITION_DETECT
  {90, 45, 90, 45},   // POSITION_GRAB
  {90, 120, 60, 180}  // POSITION_RELEASE
};

void setup() {
  Serial.begin(115200);
  Serial.println("\n🤖 AI Smart Grabber - ESP32-Servo");
  
  // Инициализация пинов
  setupPins();
  
  // Инициализация сервоприводов
  setupServos();
  
  // Подключение к Wi-Fi
  setupWiFi();
  
  // Перемещение в домашнюю позицию
  moveToPosition(POSITION_HOME);
  
  Serial.println("✅ Система готова к работе");
  Serial.println("🔍 Начинаю сканирование...");
}

void loop() {
  unsigned long current_time = millis();
  
  // Сканирование с заданным интервалом
  if (current_time - last_scan_time >= SCAN_INTERVAL) {
    last_scan_time = current_time;
    
    Distances distances = measureDistances();
    
    #if DEBUG_MODE
    Serial.printf("📏 Расстояния: L=%.1fcm, C=%.1fcm, R=%.1fcm\n", 
                  distances.left, distances.center, distances.right);
    #endif
    
    // Проверка на наличие объекта
    if (hasObject(distances)) {
      handleObjectDetection(distances);
    }
  }
  
  delay(10);
}

void setupPins() {
  // Настройка пинов ультразвуковых датчиков
  pinMode(TRIG_PIN_LEFT, OUTPUT);
  pinMode(ECHO_PIN_LEFT, INPUT);
  pinMode(TRIG_PIN_CENTER, OUTPUT);
  pinMode(ECHO_PIN_CENTER, INPUT);
  pinMode(TRIG_PIN_RIGHT, OUTPUT);
  pinMode(ECHO_PIN_RIGHT, INPUT);
  
  Serial.println("✅ Пины инициализированы");
}

void setupServos() {
  // Разрешение ESP32 для сервоприводов
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  
  // Присоединение сервоприводов
  servoBase.attach(SERVO_BASE_PIN);
  servoShoulder.attach(SERVO_SHOULDER_PIN);
  servoElbow.attach(SERVO_ELBOW_PIN);
  servoGripper.attach(SERVO_GRIPPER_PIN);
  
  // Установка частоты
  servoBase.setPeriodHertz(SERVO_FREQUENCY);
  servoShoulder.setPeriodHertz(SERVO_FREQUENCY);
  servoElbow.setPeriodHertz(SERVO_FREQUENCY);
  servoGripper.setPeriodHertz(SERVO_FREQUENCY);
  
  Serial.println("✅ Сервоприводы инициализированы");
}

void setupWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  Serial.print("🔌 Подключение к Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("✅ Wi-Fi подключен, IP адрес: ");
  Serial.println(WiFi.localIP());
  
  wifi_connected = true;
}

float measureDistance(int trigPin, int echoPin) {
  // Отправка импульса
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Измерение длительности ответа
  long duration = pulseIn(echoPin, HIGH, 30000); // Таймаут 30мс
  
  // Расчет расстояния (звук ~343 м/с)
  float distance = duration * 0.0343 / 2;
  
  // Ограничение диапазона
  if (distance < MIN_DISTANCE) distance = MIN_DISTANCE;
  if (distance > MAX_DISTANCE) distance = MAX_DISTANCE;
  
  return distance;
}

Distances measureDistances() {
  Distances d;
  d.left = measureDistance(TRIG_PIN_LEFT, ECHO_PIN_LEFT);
  d.center = measureDistance(TRIG_PIN_CENTER, ECHO_PIN_CENTER);
  d.right = measureDistance(TRIG_PIN_RIGHT, ECHO_PIN_RIGHT);
  return d;
}

bool hasObject(Distances distances) {
  return distances.left <= DETECTION_DISTANCE || 
         distances.center <= DETECTION_DISTANCE || 
         distances.right <= DETECTION_DISTANCE;
}

void handleObjectDetection(Distances distances) {
  Serial.println("🎯 Объект обнаружен! Запрашиваю решение у AI сервера...");
  
  // Перемещение в позицию детекции
  moveToPosition(POSITION_DETECT);
  delay(MOVE_DELAY);
  
  // Запрос решения у AI сервера
  String decision = requestAIDecision();
  
  if (decision == "ALLOW") {
    Serial.println("✅ Разрешено: выполняю захват объекта");
    performGrabSequence(distances);
  } else if (decision == "DENY") {
    Serial.println("❌ Запрещено: игнорирую объект");
    last_decision = "DENY";
  } else {
    Serial.println("⚠️ Ошибка: не получено решение от сервера");
    last_decision = "ERROR";
  }
  
  // Возврат в домашнюю позицию
  delay(MOVE_DELAY);
  moveToPosition(POSITION_HOME);
}

String requestAIDecision() {
  if (!wifi_connected) {
    Serial.println("❌ Wi-Fi не подключен");
    return "ERROR";
  }
  
  HTTPClient http;
  String url = String("http://") + AI_SERVER_HOST + ":" + AI_SERVER_PORT + "/analyze_from_camera";
  
  #if DEBUG_MODE
  Serial.printf("🌐 Запрос к AI серверу: %s\n", url.c_str());
  #endif
  
  http.begin(url);
  http.setTimeout(REQUEST_TIMEOUT);
  
  int httpCode = http.GET();
  String response = "";
  
  if (httpCode == HTTP_CODE_OK) {
    response = http.getString();
    
    // Парсинг JSON ответа
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      String decision = doc["decision"];
      last_decision = decision;
      
      #if DEBUG_MODE
      Serial.printf("🧠 AI решение: %s\n", decision.c_str());
      #endif
      
      http.end();
      return decision;
    } else {
      Serial.printf("❌ Ошибка парсинга JSON: %s\n", error.c_str());
    }
  } else {
    Serial.printf("❌ HTTP ошибка: %d\n", httpCode);
  }
  
  http.end();
  return "ERROR";
}

void moveToPosition(int positionIndex) {
  if (positionIndex < 0 || positionIndex > 3) {
    Serial.println("❌ Неверный индекс позиции");
    return;
  }
  
  ManipulatorPosition pos = positions[positionIndex];
  
  #if DEBUG_MODE
  Serial.printf("🦾 Перемещение в позицию %d: B=%d, S=%d, E=%d, G=%d\n", 
                positionIndex, pos.base, pos.shoulder, pos.elbow, pos.gripper);
  #endif
  
  // Плавное перемещение сервоприводов
  servoBase.write(pos.base);
  delay(100);
  servoShoulder.write(pos.shoulder);
  delay(100);
  servoElbow.write(pos.elbow);
  delay(100);
  servoGripper.write(pos.gripper);
}

void performGrabSequence(Distances distances) {
  Serial.println("🦾 Выполняю последовательность захвата");
  
  // Определение направления к объекту
  int direction = 0; // 0 - центр, -1 - лево, 1 - право
  if (distances.left < distances.center && distances.left < distances.right) {
    direction = -1;
  } else if (distances.right < distances.center && distances.right < distances.left) {
    direction = 1;
  }
  
  // Поворот к объекту
  int baseAngle = 90 + (direction * 30); // Поворот на 30 градусов
  servoBase.write(baseAngle);
  delay(MOVE_DELAY);
  
  // Опускание к объекту
  moveToPosition(POSITION_GRAB);
  delay(MOVE_DELAY);
  
  // Закрытие захвата
  Serial.println("🤏 Закрываю захват");
  for (int angle = 90; angle >= 45; angle -= 5) {
    servoGripper.write(angle);
    delay(50);
  }
  delay(GRAB_DELAY);
  
  // Подъем объекта
  moveToPosition(POSITION_DETECT);
  delay(MOVE_DELAY);
  
  // Перемещение в зону выпуска
  moveToPosition(POSITION_RELEASE);
  delay(MOVE_DELAY);
  
  // Открытие захвата
  Serial.println("✋ Открываю захват");
  for (int angle = 180; angle >= 90; angle -= 5) {
    servoGripper.write(angle);
    delay(50);
  }
  delay(GRAB_DELAY);
  
  Serial.println("✅ Последовательность захвата завершена");
}

// Функции для отладки и контроля
void printSystemStatus() {
  Serial.println("\n📊 Статус системы:");
  Serial.printf("Wi-Fi: %s\n", wifi_connected ? "Подключен" : "Отключен");
  Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());
  Serial.printf("Последнее решение: %s\n", last_decision.c_str());
  Serial.printf("Свободная память: %d байт\n", ESP.getFreeHeap());
  
  Distances d = measureDistances();
  Serial.printf("Текущие расстояния: L=%.1fcm, C=%.1fcm, R=%.1fcm\n", 
                d.left, d.center, d.right);
  Serial.println();
}
