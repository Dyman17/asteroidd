# 📚 API документация AI Smart Grabber

## 🌐 AI Server API

### Базовый URL
```
http://localhost:8000
```

### Методы аутентификации
API не требует аутентификации (работает в локальной сети).

---

## 📊 Эндпоинты

### 1. Статус сервера

**GET** `/status`

Получение текущего статуса AI сервера.

**Ответ:**
```json
{
  "status": "healthy",
  "server_time": "2024-01-15T10:30:00.000Z",
  "model_loaded": true,
  "uptime": 3600.5
}
```

**Поля:**
- `status` - "healthy" если модель загружена, "error" в противном случае
- `server_time` - текущее время сервера
- `model_loaded` - загружена ли YOLO модель
- `uptime` - время работы в секундах

---

### 2. Анализ изображения

**POST** `/analyze`

Анализ загруженного изображения.

**Запрос:**
- Content-Type: `multipart/form-data`
- Поле: `file` (изображение)

**Ответ:**
```json
{
  "decision": "ALLOW",
  "detections": [
    {
      "class_name": "bottle",
      "confidence": 0.85,
      "bbox": [100, 150, 200, 300]
    }
  ],
  "processing_time": 0.125,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Поля ответа:**
- `decision` - "ALLOW" или "DENY"
- `detections` - массив обнаруженных объектов
- `processing_time` - время обработки в секундах
- `timestamp` - время анализа

**Ошибки:**
- `400` - файл не является изображением
- `500` - ошибка обработки изображения
- `503` - модель не загружена

---

### 3. Анализ с ESP32-CAM

**POST** `/analyze_from_camera`

Получение и анализ изображения с ESP32-CAM.

**Ответ:**
```json
{
  "decision": "DENY",
  "detections": [
    {
      "class_name": "person",
      "confidence": 0.92,
      "bbox": [50, 80, 400, 600]
    }
  ],
  "processing_time": 0.234,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Ошибки:**
- `502` - ошибка подключения к ESP32-CAM
- `500` - ошибка обработки изображения
- `503` - модель не загружена

---

### 4. Управление классами объектов

#### GET `/classes`

Получение списка разрешенных классов.

**Ответ:**
```json
{
  "allowed_classes": [
    "bottle",
    "can",
    "cup",
    "book",
    "cell phone",
    "asteroid",
    "space_rock",
    "meteor"
  ],
  "total": 8
}
```

#### POST `/classes/add`

Добавление нового разрешенного класса.

**Запрос:**
```json
{
  "class_name": "laptop"
}
```

**Ответ:**
```json
{
  "message": "Класс 'laptop' добавлен в разрешенные",
  "allowed_classes": ["bottle", "can", "cup", "book", "cell phone", "laptop"]
}
```

#### DELETE `/classes/{class_name}`

Удаление разрешенного класса.

**Параметры:**
- `class_name` - имя класса для удаления

**Ответ:**
```json
{
  "message": "Класс 'laptop' удален из разрешенных",
  "allowed_classes": ["bottle", "can", "cup", "book", "cell phone"]
}
```

---

## 📷 ESP32-CAM API

### Базовый URL
```
http://IP_АДРЕС_ESP32_CAM
```

### Эндпоинты

#### 1. Захват изображения

**GET** `/capture`

Получение JPEG изображения с камеры.

**Ответ:**
- Content-Type: `image/jpeg`
- Content-Length: размер изображения
- Access-Control-Allow-Origin: `*`

**Пример использования:**
```bash
curl -o image.jpg http://192.168.1.100/capture
```

#### 2. Статус устройства

**GET** `/status`

Получение статуса ESP32-CAM.

**Ответ:**
```json
{
  "status": "ok",
  "camera_initialized": true,
  "wifi_connected": true,
  "ip_address": "192.168.1.100",
  "free_heap": 234567,
  "uptime": 7200
}
```

#### 3. Главная страница

**GET** `/`

Веб-интерфейс для управления камерой.

Возвращает HTML страницу с:
- Статусом устройства
- Предпросмотром камеры
- Кнопками управления

#### 4. Перезагрузка

**POST** `/restart`

Перезагрузка ESP32-CAM.

**Ответ:**
```
Перезагрузка через 3 секунды...
```

---

## 🔧 Примеры использования

### Python клиент для анализа

```python
import requests

def analyze_image(image_path, server_url="http://localhost:8000"):
    """Анализ локального изображения"""
    with open(image_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{server_url}/analyze", files=files)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Решение: {result['decision']}")
        print(f"Найдено объектов: {len(result['detections'])}")
        return result
    else:
        print(f"Ошибка: {response.status_code}")
        return None

def analyze_from_camera(server_url="http://localhost:8000"):
    """Анализ изображения с ESP32-CAM"""
    response = requests.post(f"{server_url}/analyze_from_camera")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code}")
        return None
```

### JavaScript клиент

```javascript
// Анализ изображения с камеры
async function analyzeFromCamera() {
    try {
        const response = await fetch('http://localhost:8000/analyze_from_camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        console.log('Решение:', result.decision);
        console.log('Детекции:', result.detections);
        
        return result;
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

// Получение изображения с ESP32-CAM
async function captureImage(esp32Url) {
    try {
        const response = await fetch(`${esp32Url}/capture`);
        const blob = await response.blob();
        
        // Создание URL для изображения
        const imageUrl = URL.createObjectURL(blob);
        
        // Отображение изображения
        const img = document.createElement('img');
        img.src = imageUrl;
        document.body.appendChild(img);
        
        return imageUrl;
    } catch (error) {
        console.error('Ошибка захвата:', error);
    }
}
```

### curl примеры

```bash
# Проверка статуса AI сервера
curl http://localhost:8000/status

# Анализ изображения с камеры
curl -X POST http://localhost:8000/analyze_from_camera

# Анализ локального файла
curl -X POST -F "file=@test_image.jpg" http://localhost:8000/analyze

# Получение разрешенных классов
curl http://localhost:8000/classes

# Добавление нового класса
curl -X POST -H "Content-Type: application/json" \
     -d '{"class_name":"laptop"}' \
     http://localhost:8000/classes/add

# Захват изображения с ESP32-CAM
curl http://192.168.1.100/capture > captured_image.jpg
```

---

## 📊 Модели данных

### DetectionResult
```json
{
  "class_name": "string",
  "confidence": "float",
  "bbox": [int, int, int, int]
}
```

### AnalysisResponse
```json
{
  "decision": "string",  // "ALLOW" | "DENY"
  "detections": [DetectionResult],
  "processing_time": "float",
  "timestamp": "datetime"
}
```

### StatusResponse
```json
{
  "status": "string",
  "server_time": "datetime",
  "model_loaded": "boolean",
  "uptime": "float"
}
```

---

## ⚠️ Ограничения

1. **Размер изображения**: максимальный размер файла 10MB
2. **Форматы**: поддерживаются JPEG, PNG, BMP
3. **Таймауты**: 
   - Анализ изображения: 30 секунд
   - Подключение к ESP32-CAM: 5 секунд
4. **Конкурентные запросы**: максимально 10 одновременных анализов

---

## 🔍 Отладка

### Логи сервера
Сервер выводит подробные логи в консоль:
- Загрузка модели
- Обработка запросов
- Ошибки подключения
- Время обработки

### Тестирование эндпоинтов
Используйте Swagger UI: `http://localhost:8000/docs`

### Мониторинг производительности
```bash
# Проверка нагрузки на CPU
htop

# Мониторинг памяти
free -h

# Проверка сетевых соединений
netstat -an | grep :8000
```

---

## 🚀 Производительность

### Среднее время обработки:
- YOLO детекция: 50-200ms (зависит от размера изображения)
- HTTP запрос: 10-50ms
- Общее время: 100-300ms

### Рекомендации:
- Используйте изображения размером 640x640 для оптимальной производительности
- Настройте `CONF_THRESHOLD` для баланса точности и скорости
- Используйте статические IP адреса для стабильной работы сети
