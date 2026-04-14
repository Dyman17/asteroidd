#include "config.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <WiFiClientSecure.h>

Servo servoBase, servoShoulder, servoElbow, servoGripper;
bool wifi_connected = false;
unsigned long last_scan_time = 0;
unsigned long last_ping_time = 0;
String last_decision = "NONE";

struct Distances {
  float left;
  float center;
  float right;
};

struct ManipulatorPosition {
  int base;
  int shoulder;
  int elbow;
  int gripper;
};

const ManipulatorPosition positions[] = {
  {90, 90, 90, 90},
  {90, 60, 120, 90},
  {90, 45, 90, 45},
  {90, 120, 60, 180}
};

void setupPins();
void setupServos();
void setupWiFi();
float measureDistance(int trigPin, int echoPin);
Distances measureDistances();
bool hasObject(Distances distances);
void handleObjectDetection(Distances distances);
String requestAIDecision();
void moveToPosition(int positionIndex);
void performGrabSequence(Distances distances);
void sendPing();

void setup() {
  Serial.begin(115200);
  setupPins();
  setupServos();
  setupWiFi();
  moveToPosition(POSITION_HOME);
  sendPing();
}

void loop() {
  unsigned long current_time = millis();
  if (current_time - last_scan_time >= SCAN_INTERVAL) {
    last_scan_time = current_time;
    Distances distances = measureDistances();
    if (hasObject(distances)) {
      handleObjectDetection(distances);
    }
  }
  if (current_time - last_ping_time >= PING_INTERVAL_MS) {
    last_ping_time = current_time;
    sendPing();
  }
  delay(10);
}

void setupPins() {
  pinMode(TRIG_PIN_LEFT, OUTPUT);
  pinMode(ECHO_PIN_LEFT, INPUT);
  pinMode(TRIG_PIN_CENTER, OUTPUT);
  pinMode(ECHO_PIN_CENTER, INPUT);
  pinMode(TRIG_PIN_RIGHT, OUTPUT);
  pinMode(ECHO_PIN_RIGHT, INPUT);
}

void setupServos() {
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  servoBase.attach(SERVO_BASE_PIN);
  servoShoulder.attach(SERVO_SHOULDER_PIN);
  servoElbow.attach(SERVO_ELBOW_PIN);
  servoGripper.attach(SERVO_GRIPPER_PIN);

  servoBase.setPeriodHertz(SERVO_FREQUENCY);
  servoShoulder.setPeriodHertz(SERVO_FREQUENCY);
  servoElbow.setPeriodHertz(SERVO_FREQUENCY);
  servoGripper.setPeriodHertz(SERVO_FREQUENCY);
}

void setupWiFi() {
  WiFi.begin("Nuks", "Dastan2020+");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  wifi_connected = true;
}

float measureDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);
  float distance = duration * 0.0343 / 2;

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
  moveToPosition(POSITION_DETECT);
  delay(MOVE_DELAY);

  String decision = requestAIDecision();
  if (decision == "ALLOW") {
    performGrabSequence(distances);
  } else if (decision == "DENY") {
    last_decision = "DENY";
  } else {
    last_decision = "ERROR";
  }

  delay(MOVE_DELAY);
  moveToPosition(POSITION_HOME);
}

void sendPing() {
  if (!wifi_connected) return;

  WiFiClientSecure client;
#if USE_TLS_INSECURE
  client.setInsecure();
#endif
  HTTPClient http;
  String url = String("https://") + CLOUD_HOST + CLOUD_PING_PATH + "?device_id=" + DEVICE_ID;
  http.begin(client, url);
  http.setTimeout(REQUEST_TIMEOUT);
  http.GET();
  http.end();
}

String requestAIDecision() {
  if (!wifi_connected) {
    return "ERROR";
  }

  WiFiClientSecure client;
#if USE_TLS_INSECURE
  client.setInsecure();
#endif

  HTTPClient http;
  String url = String("https://") + CLOUD_HOST + CLOUD_CHECK_PATH + "?device_id=" + DEVICE_ID;
  http.begin(client, url);
  http.setTimeout(REQUEST_TIMEOUT);
  int httpCode = http.GET();

  if (httpCode == HTTP_CODE_OK) {
    String decision = http.getString();
    decision.trim();
    last_decision = decision;
    http.end();
    return decision;
  }

  http.end();
  return "ERROR";
}

void moveToPosition(int positionIndex) {
  if (positionIndex < 0 || positionIndex > 3) return;

  ManipulatorPosition pos = positions[positionIndex];
  servoBase.write(pos.base);
  delay(100);
  servoShoulder.write(pos.shoulder);
  delay(100);
  servoElbow.write(pos.elbow);
  delay(100);
  servoGripper.write(pos.gripper);
}

void performGrabSequence(Distances distances) {
  int direction = 0;
  if (distances.left < distances.center && distances.left < distances.right) {
    direction = -1;
  } else if (distances.right < distances.center && distances.right < distances.left) {
    direction = 1;
  }

  int baseAngle = 90 + (direction * 30);
  servoBase.write(baseAngle);
  delay(MOVE_DELAY);

  moveToPosition(POSITION_GRAB);
  delay(MOVE_DELAY);

  for (int angle = 90; angle >= 45; angle -= 5) {
    servoGripper.write(angle);
    delay(50);
  }
  delay(GRAB_DELAY);

  moveToPosition(POSITION_DETECT);
  delay(MOVE_DELAY);

  moveToPosition(POSITION_RELEASE);
  delay(MOVE_DELAY);

  for (int angle = 180; angle >= 90; angle -= 5) {
    servoGripper.write(angle);
    delay(50);
  }
  delay(GRAB_DELAY);
}
