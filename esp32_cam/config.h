#ifndef CONFIG_H
#define CONFIG_H

// Wi-Fi настройки
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Настройки камеры
#define CAMERA_MODEL_AI_THINKER
#define CAMERA_LED_GPIO 4

// Настройки сервера
#define SERVER_PORT 80
#define MAX_CLIENTS 4

// Настройки изображения
#define FRAME_SIZE FRAMESIZE_SVGA  // 800x600
#define JPEG_QUALITY 10            // 1-31, lower is better
#define BRIGHTNESS 0               // -2 to 2
#define CONTRAST 0                  // -2 to 2
#define SATURATION 0               // -2 to 2

// Пины для AI-THINKER модели
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

#endif // CONFIG_H
