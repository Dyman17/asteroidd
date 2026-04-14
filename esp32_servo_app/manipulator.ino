#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <WiFiClientSecure.h>

// ===== GLOBAL TLS CLIENT =====
WiFiClientSecure client;
HTTPClient httpClient;

// ===== WIFI =====
const char* ssid = "Test";
const char* password = "Test1234";
const char* SERVER_URL = "https://asteroidd-server.onrender.com/esp_servo/check?device_id=esp32-servo-test";

// ===== ULTRASONIC =====
#define TRIG_LEFT   5
#define ECHO_LEFT   18
#define TRIG_CENTER 4
#define ECHO_CENTER 19
#define TRIG_RIGHT  26
#define ECHO_RIGHT  33

// ===== SERVOS =====
#define BIG_SERVO     25
#define SMALL_SERVO_1 13
#define SMALL_SERVO_2 27

Servo bigServo;
Servo smallServo1;
Servo smallServo2;

// ===== COOLDOWN =====
unsigned long lastAIRequest = 0;
const int AI_COOLDOWN = 2000;  // 2 seconds between AI requests

// ===== SERVO HELPERS =====
void moveSmooth(Servo &servo, int startAngle, int endAngle, int speedDelay) {
  int step = (endAngle > startAngle) ? 1 : -1;
  for (int pos = startAngle; pos != endAngle; pos += step) {
    servo.write(pos);
    delay(speedDelay);
  }
  servo.write(endAngle);
}

void moveTwoSmooth(Servo &s1, Servo &s2,
                   int s1Start, int s1End,
                   int s2Start, int s2End,
                   int speedDelay) {

  int step1 = (s1End > s1Start) ? 1 : -1;
  int step2 = (s2End > s2Start) ? 1 : -1;

  int a1 = s1Start;
  int a2 = s2Start;

  while (a1 != s1End || a2 != s2End) {
    if (a1 != s1End) a1 += step1;
    if (a2 != s2End) a2 += step2;
    s1.write(a1);
    s2.write(a2);
    delay(speedDelay);
  }
}

// ===== DISTANCE =====
long readDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 10000);
  if (duration == 0) return -1;
  return duration * 0.034 / 2;
}

// ===== SERVER CHECK =====
bool serverAllows() {
  if (WiFi.status() != WL_CONNECTED) return false;

  client.setInsecure();  // For self-signed or test certificates

  httpClient.begin(client, SERVER_URL);
  httpClient.setTimeout(3000);

  int code = httpClient.GET();
  if (code != 200) {
    httpClient.end();
    return false;
  }

  String response = httpClient.getString();
  httpClient.end();

  response.trim();
  Serial.print("🧠 Server says: ");
  Serial.println(response);

  return response == "ALLOW";
}

// ===== SEND EVENT =====
String sendEvent() {
  if (WiFi.status() != WL_CONNECTED) return "DENY";

  client.setInsecure();

  String url = "https://asteroidd-server.onrender.com/esp_servo/event?device_id=esp32-servo-test";
  httpClient.begin(client, url);
  httpClient.setTimeout(10000);  // Longer timeout for AI processing
  int code = httpClient.GET();
  if (code != 200) {
    httpClient.end();
    return "DENY";
  }

  String response = httpClient.getString();
  httpClient.end();
  response.trim();
  Serial.print("🧠 Event response: ");
  Serial.println(response);
  return response;
}

// ===== SETUP =====
void setup() {
  Serial.begin(115200);

  pinMode(TRIG_LEFT, OUTPUT);
  pinMode(ECHO_LEFT, INPUT);
  pinMode(TRIG_CENTER, OUTPUT);
  pinMode(ECHO_CENTER, INPUT);
  pinMode(TRIG_RIGHT, OUTPUT);
  pinMode(ECHO_RIGHT, INPUT);

  bigServo.attach(BIG_SERVO);
  smallServo1.attach(SMALL_SERVO_1);
  smallServo2.attach(SMALL_SERVO_2);

  bigServo.write(90);
  smallServo1.write(45);
  smallServo2.write(90);

  // ===== WIFI CONNECT =====
  WiFi.begin(ssid, password);
  Serial.print("📡 Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ WiFi connected");
  Serial.print("🦾 ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

// ===== LOOP =====
void loop() {
  // ===== WIFI CHECK =====
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi lost, reconnecting...");
    WiFi.reconnect();
    delay(1000);
    return;
  }

  long left   = readDistance(TRIG_LEFT, ECHO_LEFT);
  delay(40);
  long center = readDistance(TRIG_CENTER, ECHO_CENTER);
  delay(40);
  long right  = readDistance(TRIG_RIGHT, ECHO_RIGHT);
  delay(40);

  Serial.printf("📏 L:%ld C:%ld R:%ld\n", left, center, right);

  int threshold = 15;
  int detectCount = 0;
  int direction = -1; // 0: left, 1: center, 2: right

  if (left > 0 && left < threshold) {
    detectCount++;
    if (direction == -1) direction = 0;
  }
  if (center > 0 && center < threshold) {
    detectCount++;
    if (direction == -1) direction = 1;
  }
  if (right > 0 && right < threshold) {
    detectCount++;
    if (direction == -1) direction = 2;
  }

  if (detectCount < 2) return;

  // Move servo based on direction
  if (direction == 0) moveSmooth(bigServo, 90, 180, 2);
  else if (direction == 1) moveSmooth(bigServo, 90, 0, 2);
  else if (direction == 2) moveSmooth(bigServo, 90, 90, 2);

  // ===== AI COOLDOWN CHECK =====
  if (millis() - lastAIRequest < AI_COOLDOWN) {
    Serial.println("⏳ AI cooldown active, skipping request");
    return;
  }
  lastAIRequest = millis();

  // ===== SEND EVENT AND GET DECISION =====
  String decision = sendEvent();

  if (decision == "ALLOW") {
    Serial.println("✅ ALLOW → GRAB");

    // ===== GRAB =====
    moveTwoSmooth(smallServo1, smallServo2, 45, 84, 90, 39, 2);
    delay(600);
    moveTwoSmooth(smallServo1, smallServo2, 84, 45, 39, 90, 2);
    moveSmooth(bigServo, bigServo.read(), 90, 2);
    delay(1000);
  } else {
    Serial.println("❌ DENY → ignore");
    moveSmooth(bigServo, bigServo.read(), 90, 2);
    delay(500);
    return;
  }
}
