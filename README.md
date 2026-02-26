# 🤖 AI Smart Grabber

**«Интеллектуальная система манипуляции с детекцией астероидов»**

AI Smart Grabber — система роботизированной манипуляции с использованием ESP32-CAM и YOLO для детекции объектов. Проект создан для автоматического захвата и сортировки объектов, включая астероиды и космические объекты.

## 🎯 Возможности

- **Детекция**: астероиды, космические объекты, бытовые предметы
- **Манипуляция**: автоматический захват и перемещение
- **Реальное время**: мгновенная обработка через FastAPI
- **Источники**: ESP32-CAM + YOLO AI + сервоприводы

## 🏗 Архитектура

```
📷 ESP32-CAM → FastAPI Backend → YOLO AI → ESP32-Servo
```

## � Быстрый старт

### 1. Запуск AI сервера
```bash
cd ai_server && pip install -r requirements.txt
python main.py
```

### 2. Прошивка ESP32-CAM
- Настройте Wi-Fi в `esp32_cam/esp32cam.ino`
- Прошейте устройство

### 3. Прошивка ESP32-Servo
- Настройте IP адреса в `esp32_servo/manipulator.ino`
- Прошейте устройство

## 📁 Структура

```
├── ai_server/        # FastAPI сервер с YOLO
├── esp32_cam/        # Прошивка ESP32-CAM
├── esp32_servo/      # Прошивка ESP32-Servo
├── docs/             # Документация
└── requirements.txt  # Зависимости Python
```

## 📊 API

- `POST /analyze` - анализ загруженного изображения
- `POST /analyze/esp32` - анализ с ESP32-CAM
- `GET /status` - статус сервера
- `GET /allowed-classes` - разрешенные классы объектов
- `POST /allowed-classes` - обновление классов

## 🌐 Ссылки

- **GitHub**: [github.com/Dyman17/asteroidd](https://github.com/Dyman17/asteroidd)
- **Документация**: [Google Docs](https://docs.google.com/document/d/1-TK_TiXlVmHxVKi7C-XYBaTW_SIBIqns/edit?usp=sharing&ouid=116860278482411569103&rtpof=true&sd=true)
- **Презентация**: [Google Slides](https://docs.google.com/document/d/1-TK_TiXlVmHxVKi7C-XYBaTW_SIBIqns/edit?usp=sharing&ouid=116860278482411569103&rtpof=true&sd=true)
- **Видео**: [Google Drive](https://drive.google.com/file/d/12Rnz7P5-263DtvEsZlyrEBy-qIDxIwQh/view?usp=drive_link)

## 🧠 Классы объектов

### ALLOW_CLASSES:
- `asteroid` - астероиды
- `space_rock` - космические камни
- `meteor` - метеоры
- `bottle` - бутылки
- `can` - банки
- `cup` - чашки
- `book` - книги
- `cell phone` - телефоны

---

<div align="center">

**🤖 AI Smart Grabber - Умная манипуляция для космоса и Земли!**

[![GitHub](https://img.shields.io/badge/📦-GitHub-black?style=flat-square)](https://github.com/Dyman17/asteroidd)
[![Python](https://img.shields.io/badge/🐍-Python-blue?style=flat-square)](https://www.python.org/)
[![YOLO](https://img.shields.io/badge/🎯-YOLO-orange?style=flat-square)](https://ultralytics.com/)

</div>
