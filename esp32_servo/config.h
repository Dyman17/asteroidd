#ifndef CONFIG_H
#define CONFIG_H

// Wi-Fi настройки
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Настройки AI сервера
#define AI_SERVER_HOST "192.168.1.10"  // IP адрес ноутбука с AI сервером
#define AI_SERVER_PORT 8000
#define ESP32_CAM_URL "http://192.168.1.100/capture"  // IP адрес ESP32-CAM

// Ультразвуковые датчики
#define TRIG_PIN_LEFT   5
#define ECHO_PIN_LEFT   18
#define TRIG_PIN_CENTER 19
#define ECHO_PIN_CENTER 21
#define TRIG_PIN_RIGHT  22
#define ECHO_PIN_RIGHT  23

// Серво-приводы манипулятора
#define SERVO_BASE_PIN      12  // Основание (поворот)
#define SERVO_SHOULDER_PIN  13  // Плечо
#define SERVO_ELBOW_PIN     14  // Локоть
#define SERVO_GRIPPER_PIN   15  // Захват

// Настройки расстояний (в см)
#define DETECTION_DISTANCE 15    // Расстояние для срабатывания
#define MIN_DISTANCE 2           // Минимальное расстояние
#define MAX_DISTANCE 400        // Максимальное расстояние

// Настройки сервоприводов
#define SERVO_MIN_PULSE 500     // Минимальная длина импульса (мкс)
#define SERVO_MAX_PULSE 2500    // Максимальная длина импульса (мкс)
#define SERVO_FREQUENCY 50      // Частота (Гц)

// Позиции манипулятора
#define POSITION_HOME      0    // Домашняя позиция
#define POSITION_DETECT    1    // Позиция для детекции
#define POSITION_GRAB      2    // Позиция захвата
#define POSITION_RELEASE   3    // Позиция выпуска

// Тайминги (в мс)
#define SCAN_INTERVAL      100  // Интервал сканирования
#define REQUEST_TIMEOUT    5000 // Таймаут запроса к серверу
#define MOVE_DELAY         500  // Задержка между движениями
#define GRAB_DELAY         1000 // Задержка захвата

// Отладка
#define DEBUG_MODE true        // Включить отладочные сообщения

#endif // CONFIG_H
