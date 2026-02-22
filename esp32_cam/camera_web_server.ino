#include "config.h"
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

WebServer server(SERVER_PORT);

// Глобальные переменные
camera_config_t config;
bool camera_initialized = false;

void setup() {
  Serial.begin(115200);
  Serial.println("\n🚀 AI Smart Grabber - ESP32-CAM");
  
  // Инициализация камеры
  setupCamera();
  
  // Подключение к Wi-Fi
  setupWiFi();
  
  // Настройка веб-сервера
  setupServer();
  
  Serial.println("✅ Сервер запущен");
  Serial.print("📷 Камера доступна по адресу: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/capture");
}

void loop() {
  server.handleClient();
  delay(10);
}

void setupCamera() {
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
  config.pixel_format = PIXFORMAT_JPEG;
  
  // Инициализация с низким разрешением для начала
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  // Инициализация камеры
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Ошибка инициализации камеры: 0x%x\n", err);
    return;
  }

  // Настройка параметров камеры
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_brightness(s, BRIGHTNESS);
    s->set_contrast(s, CONTRAST);
    s->set_saturation(s, SATURATION);
    s->set_special_effect(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 0);
    s->set_ae_level(s, 0);
    s->set_aec_value(s, 300);
    s->set_gain_ctrl(s, 1);
    s->set_agc_gain(s, 0);
    s->set_gainceiling(s, (gainceiling_t)0);
    s->set_bpc(s, 0);
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
    s->set_lenc(s, 1);
    s->set_hmirror(s, 0);
    s->set_vflip(s, 0);
    s->set_dcw(s, 1);
    s->set_colorbar(s, 0);
    
    // Установка финального разрешения и качества
    s->set_framesize(s, FRAME_SIZE);
    s->set_quality(s, JPEG_QUALITY);
  }

  camera_initialized = true;
  Serial.println("✅ Камера инициализирована");
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
}

void setupServer() {
  // Основной эндпоинт для захвата изображения
  server.on("/capture", HTTP_GET, handleCapture);
  
  // Эндпоинт для получения статуса
  server.on("/status", HTTP_GET, handleStatus);
  
  // Эндпоинт для перезагрузки
  server.on("/restart", HTTP_POST, handleRestart);
  
  // Главная страница с информацией
  server.on("/", HTTP_GET, handleRoot);
  
  server.begin();
}

void handleCapture() {
  if (!camera_initialized) {
    server.send(500, "text/plain", "Камера не инициализирована");
    return;
  }

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "Ошибка захвата изображения");
    return;
  }

  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "image/jpeg", fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
  
  Serial.println("📸 Изображение захвачено и отправлено");
}

void handleStatus() {
  String json = "{";
  json += "\"status\":\"ok\",";
  json += "\"camera_initialized\":" + String(camera_initialized ? "true" : "false") + ",";
  json += "\"wifi_connected\":" + String(WiFi.status() == WL_CONNECTED ? "true" : "false") + ",";
  json += "\"ip_address\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
  json += "\"uptime\":" + String(millis());
  json += "}";
  
  server.send(200, "application/json", json);
}

void handleRestart() {
  server.send(200, "text/plain", "Перезагрузка через 3 секунды...");
  delay(3000);
  ESP.restart();
}

void handleRoot() {
  String html = R"(
<!DOCTYPE html>
<html>
<head>
    <title>AI Smart Grabber - ESP32-CAM</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .endpoint { background: #e8f4fd; padding: 10px; margin: 10px 0; border-radius: 3px; }
        .endpoint code { background: #333; color: #fff; padding: 2px 5px; border-radius: 3px; }
        img { max-width: 100%; height: auto; margin: 20px 0; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Smart Grabber - ESP32-CAM</h1>
        
        <div class="status">
            <h2>📊 Статус устройства</h2>
            <p><strong>IP адрес:</strong> )" + WiFi.localIP().toString() + R"(</p>
            <p><strong>Свободная память:</strong> )" + String(ESP.getFreeHeap()) + R"( байт</p>
            <p><strong>Время работы:</strong> )" + String(millis() / 1000) + R"( сек</p>
        </div>

        <h2>📸 Доступные эндпоинты</h2>
        
        <div class="endpoint">
            <h3>Захват изображения</h3>
            <code>GET /capture</code>
            <p>Возвращает JPEG изображение с камеры</p>
        </div>

        <div class="endpoint">
            <h3>Статус системы</h3>
            <code>GET /status</code>
            <p>Возвращает JSON с текущим статусом устройства</p>
        </div>

        <div class="endpoint">
            <h3>Перезагрузка</h3>
            <code>POST /restart</code>
            <p>Перезагружает устройство</p>
        </div>

        <h2>🖼️ Предпросмотр камеры</h2>
        <button onclick="captureImage()">📸 Захватить изображение</button>
        <div id="preview"></div>

        <script>
            function captureImage() {
                const preview = document.getElementById('preview');
                preview.innerHTML = '<p>Загрузка...</p>';
                
                fetch('/capture')
                    .then(response => response.blob())
                    .then(blob => {
                        const url = URL.createObjectURL(blob);
                        preview.innerHTML = '<img src="' + url + '" alt="Camera capture">';
                    })
                    .catch(error => {
                        preview.innerHTML = '<p style="color: red;">Ошибка: ' + error.message + '</p>';
                    });
            }
            
            // Автоматическое обновление статуса
            setInterval(() => {
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        // Можно обновить статус на странице
                    })
                    .catch(console.error);
            }, 5000);
        </script>
    </div>
</body>
</html>
  )";
  
  server.send(200, "text/html", html);
}
