#ifndef CONFIG_H
#define CONFIG_H

// Wi-Fi
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Cloud relay
#define CLOUD_HOST "your-cloud-host.com"
#define CLOUD_CHECK_PATH "/esp_servo/check"
#define CLOUD_PING_PATH "/esp_servo/ping"
#define DEVICE_ID "esp32-cam-1"
#define PING_INTERVAL_MS 30000

// Ultrasonic sensors
#define TRIG_PIN_LEFT   5
#define ECHO_PIN_LEFT   18
#define TRIG_PIN_CENTER 19
#define ECHO_PIN_CENTER 21
#define TRIG_PIN_RIGHT  22
#define ECHO_PIN_RIGHT  23

// Servos
#define SERVO_BASE_PIN      12
#define SERVO_SHOULDER_PIN  13
#define SERVO_ELBOW_PIN     14
#define SERVO_GRIPPER_PIN   15

// Distances (cm)
#define DETECTION_DISTANCE 15
#define MIN_DISTANCE 2
#define MAX_DISTANCE 400

// Servo settings
#define SERVO_MIN_PULSE 500
#define SERVO_MAX_PULSE 2500
#define SERVO_FREQUENCY 50

// Positions
#define POSITION_HOME      0
#define POSITION_DETECT    1
#define POSITION_GRAB      2
#define POSITION_RELEASE   3

// Timing (ms)
#define SCAN_INTERVAL      100
#define REQUEST_TIMEOUT    5000
#define MOVE_DELAY         500
#define GRAB_DELAY         1000

// TLS
#define USE_TLS_INSECURE 1

// Debug
#define DEBUG_MODE true

#endif // CONFIG_H
