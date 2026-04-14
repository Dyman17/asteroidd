#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// ================= WIFI =================
#define WIFI_SSID "Test"
#define WIFI_PASS "Test1234"

// ================= CLOUD =================
#define CLOUD_HOST "asteroidd-server.onrender.com"
#define DEVICE_ID "auto"

// ================= ENDPOINTS =================
#define PING_PATH "/esp_cam/ping"
#define PING_INTERVAL_MS 10000

// ================= SERVER =================
WebServer server(80);

bool camera_initialized = false;
unsigned long last_ping_time = 0;

// ================= CAMERA PINS (AI THINKER ESP32-CAM) =================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  Serial.println("\n🚀 ESP32-CAM START");

  setupCamera();
  setupWiFi();
  setupServer();

  delay(1500);
  sendPing();

  Serial.println("✅ READY");
  Serial.println(WiFi.localIP());
}

// ================= LOOP =================
void loop() {
  server.handleClient();

  if (millis() - last_ping_time > PING_INTERVAL_MS) {
    last_ping_time = millis();
    sendPing();
  }
}

// ================= CAMERA (FIXED FOR YOUR SENSOR) =================
void setupCamera() {
  camera_config_t config;

  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;

  // 🔥 ВАЖНО: НЕ JPEG (у тебя нет поддержки)
  config.pixel_format = PIXFORMAT_RGB565;

  config.frame_size = FRAMESIZE_QVGA;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);

  if (err != ESP_OK) {
    Serial.printf("❌ CAMERA FAIL: 0x%x\n", err);
    camera_initialized = false;
    return;
  }

  camera_initialized = true;
  Serial.println("📷 CAMERA OK (RGB565)");
}

// ================= WIFI =================
void setupWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("WiFi connecting");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi OK");
}

// ================= SERVER =================
void setupServer() {
  server.on("/", []() {
    server.send(200, "text/plain", "ESP32-CAM RGB565 ONLINE");
  });

  server.begin();
}

// ================= PING =================
void sendPing() {
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(20000);

  HTTPClient http;

  String url = String("https://") + CLOUD_HOST + PING_PATH +
               "?device_id=" + DEVICE_ID;

  Serial.println("\n🔵 PING:");
  Serial.println(url);  

  int code = -1;

  for (int i = 0; i < 3; i++) {
    http.begin(client, url);
    http.setTimeout(20000);
    http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
    http.setReuse(false);

    code = http.GET();

    if (code > 0) break;

    Serial.println("❌ retry " + String(i + 1));
    delay(500);
  }

  Serial.print("📡 HTTP CODE: ");
  Serial.println(code);

  if (code < 0) {
    Serial.println("ERROR: " + http.errorToString(code));
  }

  http.end();
}