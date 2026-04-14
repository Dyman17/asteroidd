#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <WiFiClientSecure.h>

// ===== WIFI =====
const char* ssid = "Dyman";
const char* password = "Dastan2020+";
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
  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return -1;
  return duration * 0.034 / 2;
}

// ===== SERVER CHECK =====
bool serverAllows() {
  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClientSecure client;
  client.setInsecure();  // For self-signed or test certificates

  HTTPClient http;
  http.begin(client, SERVER_URL);
  http.setTimeout(3000);

  int code = http.GET();
  if (code != 200) {
    http.end();
    return false;
  }

  String response = http.getString();
  http.end();

  response.trim();
  Serial.print("🧠 Server says: ");
  Serial.println(response);

  return response == "ALLOW";
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
  long left   = readDistance(TRIG_LEFT, ECHO_LEFT);
  delay(40);
  long center = readDistance(TRIG_CENTER, ECHO_CENTER);
  delay(40);
  long right  = readDistance(TRIG_RIGHT, ECHO_RIGHT);
  delay(40);

  Serial.printf("📏 L:%ld C:%ld R:%ld\n", left, center, right);

  int threshold = 15;
  bool detected = false;

  if (left > 0 && left < threshold) {
    moveSmooth(bigServo, 90, 180, 2);
    detected = true;
  }
  else if (center > 0 && center < threshold) {
    moveSmooth(bigServo, 90, 0, 2);
    detected = true;
  }
  else if (right > 0 && right < threshold) {
    moveSmooth(bigServo, 90, 90, 2);
    detected = true;
  }

  if (!detected) return;

  // ===== AI DECISION =====
  if (serverAllows()) {
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