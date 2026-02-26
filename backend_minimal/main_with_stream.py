from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, HTMLResponse
import requests
import cv2
import numpy as np
import io
import base64
from PIL import Image

app = FastAPI()

# ===== CONFIG =====
CAMERA_URL = "http://172.20.10.9/capture"
TIMEOUT = 3

ALLOW_CLASSES = [
    "bottle",      # Бутылка (мусор)
    "can",         # Жестяная банка (мусор)
    "cup",         # Чашка/кружка (мусор)
    "book",        # Книга (мусор)
    "cell phone",  # Телефон (ценный мусор)
    "plastic_bag", # Пакет (мусор)
    "wrapper",     # Обертка (мусор)
    "container",   # Контейнер (мусор)
    "newspaper",   # Газета (мусор)
    "cardboard",   # Картон (мусор)
]

DENY_CLASSES = [
    "asteroid",    # Астероид (запрещено)
    "space_rock",  # Космический камень (запрещено)
    "meteor",      # Метеорит (запрещено)
    "person",      # Человек (запрещено - безопасность)
    "hand",        # Рука человека (запрещено)
    "cat", "dog", "horse", "cow",  # Животные (запрещено)
]

# Глобальные переменные для стрима
last_frame = None
last_detection = ""
last_decision = ""

# ===== MOCK YOLO (быстрая заглушка) =====
def yolo_detect(image):
    """
    Быстрая заглушка для тестирования
    Возвращает случайные объекты для проверки логики
    """
    import random

    # Генерируем случайное число для логирования
    rand_val = random.random()
    print(f"Случайное значение: {rand_val:.3f}")

    # 40% шанс найти мусор (разрешенные объекты)
    if rand_val < 0.4:
        trash_items = ["bottle", "can", "cup", "book", "cell phone", "plastic_bag"]
        found = random.choice(trash_items)
        print(f"Мок-детекция: найден мусор - {found}")
        return [found]

    # 20% шанс найти человека/руку (запрещено)
    elif rand_val < 0.6:
        person_items = ["person", "hand"]
        found = random.choice(person_items)
        print(f"Мок-детекция: найден человек/рука - {found}")
        return [found]

    # 15% шанс найти астероид (запрещено)
    elif rand_val < 0.75:
        print("Мок-детекция: найден астероид (ЗАПРЕЩЕНО)")
        return ["asteroid"]

    # 25% ничего не найдено
    else:
        print("Мок-детекция: ничего не найдено")
        return []

# ===== UTILS =====
def get_camera_frame():
    global last_frame
    print("Запрос изображения с камеры...")
    try:
        r = requests.get(CAMERA_URL, timeout=TIMEOUT)
        if r.status_code != 200:
            print(f"[ERROR] Камера вернула статус: {r.status_code}")
            return None

        img_array = np.frombuffer(r.content, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if frame is None:
            print("[ERROR] Не удалось декодировать изображение")
            return None

        last_frame = frame.copy()
        print(f"Изображение получено: {frame.shape}")
        return frame
    except Exception as e:
        print(f"[ERROR] Ошибка получения кадра: {e}")
        return None

def draw_detection_info(frame, detections, decision):
    """Рисует информацию о детекции на кадре"""
    # Создаем копию для рисования
    annotated = frame.copy()
    
    # Добавляем текстовую информацию
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    
    # Фон для текста
    cv2.rectangle(annotated, (10, 10), (400, 120), (0, 0, 0), -1)
    
    # Статус камеры
    cv2.putText(annotated, f"Camera: {CAMERA_URL}", (15, 30), font, font_scale, (0, 255, 0), thickness)
    
    # Детекции
    det_text = f"Detected: {', '.join(detections) if detections else 'None'}"
    cv2.putText(annotated, det_text, (15, 55), font, font_scale, (0, 255, 255), thickness)
    
    # Решение
    color = (0, 255, 0) if decision == "ALLOW" else (0, 0, 255)
    cv2.putText(annotated, f"Decision: {decision}", (15, 85), font, font_scale, color, thickness)
    
    # Время
    import datetime
    time_text = datetime.datetime.now().strftime("%H:%M:%S")
    cv2.putText(annotated, f"Time: {time_text}", (15, 110), font, font_scale, (255, 255, 255), thickness)
    
    return annotated

def frame_to_bytes(frame):
    """Конвертирует кадр в байты для стрима"""
    ret, buffer = cv2.imencode('.jpg', frame)
    frame_bytes = buffer.tobytes()
    return frame_bytes

# ===== ROUTES =====
@app.get("/", response_class=HTMLResponse)
def home():
    """Главная страница с видеопотоком"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>🤖 AI Smart Grabber - Live Stream</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #1a1a1a; 
            color: white; 
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        .header { 
            text-align: center; 
            margin-bottom: 20px; 
        }
        .video-container { 
            display: flex; 
            gap: 20px; 
            margin-bottom: 20px; 
        }
        .video-box { 
            flex: 1; 
            background: #2a2a2a; 
            border-radius: 10px; 
            padding: 10px; 
        }
        .video-box h3 { 
            margin-top: 0; 
            color: #00ff00; 
        }
        img { 
            width: 100%; 
            height: auto; 
            border-radius: 5px; 
        }
        .controls { 
            background: #2a2a2a; 
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
        }
        button { 
            background: #007bff; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            margin: 5px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px; 
        }
        button:hover { 
            background: #0056b3; 
        }
        .status { 
            background: #2a2a2a; 
            padding: 15px; 
            border-radius: 10px; 
            margin-top: 20px; 
        }
        .status-item { 
            display: inline-block; 
            margin: 5px 10px; 
            padding: 5px 10px; 
            background: #3a3a3a; 
            border-radius: 5px; 
        }
        .allow { color: #00ff00; }
        .deny { color: #ff0000; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Smart Grabber - Live Stream</h1>
            <p>📷 Камера: """ + CAMERA_URL + """</p>
        </div>
        
        <div class="video-container">
            <div class="video-box">
                <h3>📹 Original Camera</h3>
                <img src="/camera_feed" alt="Original Camera" />
            </div>
            <div class="video-box">
                <h3>🧠 AI Detection</h3>
                <img src="/detection_feed" alt="AI Detection" />
            </div>
        </div>
        
        <div class="controls">
            <button onclick="checkObject()">🔍 Check Object</button>
            <button onclick="forceAllow()">✅ Force Allow</button>
            <button onclick="forceDeny()">❌ Force Deny</button>
            <button onclick="refreshStatus()">🔄 Refresh Status</button>
        </div>
        
        <div class="status" id="status">
            <h3>📊 Current Status</h3>
            <div id="status-content">Loading...</div>
        </div>
    </div>

    <script>
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    const statusHtml = `
                        <span class="status-item">🤖 Server: <span class="allow">${data.status}</span></span>
                        <span class="status-item">📷 Camera: <span class="allow">${data.camera}</span></span>
                        <span class="status-item">🌐 IP: <span class="allow">${data.server_ip}</span></span>
                        <span class="status-item">🧠 Mode: <span class="allow">${data.mode}</span></span>
                    `;
                    document.getElementById('status-content').innerHTML = statusHtml;
                })
                .catch(error => console.error('Error:', error));
        }
        
        function checkObject() {
            fetch('/check')
                .then(response => response.text())
                .then(decision => {
                    const colorClass = decision === 'ALLOW' ? 'allow' : 'deny';
                    showNotification(`Decision: ${decision}`, colorClass);
                });
        }
        
        function forceAllow() {
            fetch('/force_allow')
                .then(response => response.text())
                .then(decision => {
                    showNotification(`Force: ${decision}`, 'allow');
                });
        }
        
        function forceDeny() {
            fetch('/force_deny')
                .then(response => response.text())
                .then(decision => {
                    showNotification(`Force: ${decision}`, 'deny');
                });
        }
        
        function showNotification(message, type) {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed; top: 20px; right: 20px; 
                background: ${type === 'allow' ? '#00ff00' : '#ff0000'}; 
                color: white; padding: 10px 20px; 
                border-radius: 5px; z-index: 1000;
            `;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 3000);
        }
        
        // Автообновление статуса
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/camera_feed")
def camera_feed():
    """Видеопоток с камеры"""
    def generate():
        while True:
            frame = get_camera_frame()
            if frame is not None:
                frame_bytes = frame_to_bytes(frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Черный экран если камера недоступна
                black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame_bytes = frame_to_bytes(black_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            import time
            time.sleep(0.1)  # 10 FPS
    
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace;boundary=frame")

@app.get("/detection_feed")
def detection_feed():
    """Видеопоток с детекцией"""
    global last_detection, last_decision
    
    def generate():
        while True:
            frame = get_camera_frame()
            if frame is not None:
                # Выполняем детекцию
                detections = yolo_detect(frame)
                
                # Принимаем решение
                decision = "DENY"
                for cls in detections:
                    if cls in DENY_CLASSES:
                        decision = "DENY"
                        break
                else:
                    for cls in detections:
                        if cls in ALLOW_CLASSES:
                            decision = "ALLOW"
                            break
                
                last_detection = detections
                last_decision = decision
                
                # Рисуем информацию
                annotated = draw_detection_info(frame, detections, decision)
                frame_bytes = frame_to_bytes(annotated)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Черный экран с ошибкой
                black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(black_frame, "Camera Offline", (200, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                frame_bytes = frame_to_bytes(black_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            import time
            time.sleep(0.1)  # 10 FPS
    
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace;boundary=frame")

@app.get("/status")
def status():
    return {
        "status": "running",
        "camera": CAMERA_URL,
        "server_ip": "172.20.10.2",
        "mode": "trash_collector_with_stream",
        "last_detection": last_detection,
        "last_decision": last_decision
    }

@app.get("/check")
def check_object():
    global last_detection, last_decision
    try:
        frame = get_camera_frame()
        if frame is None:
            print("📷 Камера недоступна - DENY")
            return "DENY"

        detected = yolo_detect(frame)
        print(f"🔍 Мок-детекция нашла: {detected}")

        # Сначала проверяем запрещенные классы
        for cls in detected:
            if cls in DENY_CLASSES:
                print(f"🚫 НАЙДЕН ЗАПРЕЩЕННЫЙ ОБЪЕКТ: {cls} -> DENY")
                last_detection = detected
                last_decision = "DENY"
                return "DENY"
        
        # Потом проверяем разрешенные
        for cls in detected:
            if cls in ALLOW_CLASSES:
                print(f"✅ НАЙДЕН РАЗРЕШЕННЫЙ МУСОР: {cls} -> ALLOW")
                last_detection = detected
                last_decision = "ALLOW"
                return "ALLOW"

        print(f"❌ Неизвестные объекты: {detected} -> DENY")
        last_detection = detected
        last_decision = "DENY"
        return "DENY"

    except Exception as e:
        print(f"❌ ERROR в /check: {e}")
        return "DENY"

@app.get("/test")
def test():
    frame = get_camera_frame()
    if frame is None:
        return {
            "camera": "fail",
            "mock_detected": False,
            "final_result": "DENY"
        }

    detected = yolo_detect(frame)

    return {
        "camera": "ok",
        "mock_detected": len(detected) > 0,
        "detected_classes": detected,
        "final_result": "ALLOW" if any(c in ALLOW_CLASSES for c in detected) else "DENY"
    }

@app.get("/force_allow")
def force_allow():
    """Принудительно разрешить - для теста манипулятора"""
    global last_decision
    last_decision = "ALLOW"
    return "ALLOW"

@app.get("/force_deny")
def force_deny():
    """Принудительно запретить - для теста манипулятора"""
    global last_decision
    last_decision = "DENY"
    return "DENY"
