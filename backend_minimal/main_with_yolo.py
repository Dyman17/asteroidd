from fastapi import FastAPI
import requests
import cv2
import numpy as np
from ultralytics import YOLO
import os

app = FastAPI()

# ===== CONFIG =====
CAMERA_URL = "http://172.20.10.9/capture"
TIMEOUT = 3

# Пути к моделям
YOLO_MODEL = "yolov8n.pt"  # стандартная модель
ASTEROID_MODEL = "asteroid_detector.pt"  # ваша обученная модель

ALLOW_CLASSES = [
    "bottle",
    "can", 
    "cup",
    "book",
    "cell phone",
    "asteroid",
    "space_rock",
    "meteor"
]

# ===== YOLO MODELS =====
try:
    # Загружаем стандартную YOLO модель
    yolo_model = YOLO(YOLO_MODEL)
    print(f"✅ Стандартная YOLO модель загружена: {YOLO_MODEL}")
except Exception as e:
    print(f"❌ Ошибка загрузки YOLO: {e}")
    yolo_model = None

try:
    # Загружаем вашу модель астероидов
    asteroid_model = YOLO(ASTEROID_MODEL) if os.path.exists(ASTEROID_MODEL) else None
    if asteroid_model:
        print(f"✅ Модель астероидов загружена: {ASTEROID_MODEL}")
    else:
        print(f"⚠️ Модель астероидов не найдена: {ASTEROID_MODEL}")
        print("💡 Обучите модель: python train_asteroids.py")
except Exception as e:
    print(f"❌ Ошибка загрузки модели астероидов: {e}")
    asteroid_model = None

# ===== DETECTION FUNCTIONS =====
def detect_with_yolo(image):
    """Детекция стандартной YOLO моделью"""
    if not yolo_model:
        return []
    
    try:
        results = yolo_model(image, conf=0.5)
        detected_classes = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    class_name = yolo_model.names[class_id]
                    confidence = float(box.conf[0])
                    
                    if confidence > 0.5:  # порог уверенности
                        detected_classes.append(class_name)
        
        return detected_classes
    except Exception as e:
        print(f"❌ Ошибка YOLO детекции: {e}")
        return []

def detect_with_asteroid_model(image):
    """Детекция моделью астероидов"""
    if not asteroid_model:
        return []
    
    try:
        results = asteroid_model(image, conf=0.3)  # более низкий порог для астероидов
        detected_classes = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    class_name = asteroid_model.names[class_id]
                    confidence = float(box.conf[0])
                    
                    if confidence > 0.3:
                        detected_classes.append(class_name)
        
        return detected_classes
    except Exception as e:
        print(f"❌ Ошибка детекции астероидов: {e}")
        return []

def combined_detection(image):
    """Комбинированная детекция обеими моделями"""
    yolo_classes = detect_with_yolo(image)
    asteroid_classes = detect_with_asteroid_model(image)
    
    # Объединяем результаты
    all_classes = yolo_classes + asteroid_classes
    
    print(f"🔍 YOLO нашел: {yolo_classes}")
    print(f"🌑 Астероиды: {asteroid_classes}")
    print(f"🎯 Всего: {all_classes}")
    
    return all_classes

# ===== UTILS =====
def get_camera_frame():
    try:
        r = requests.get(CAMERA_URL, timeout=TIMEOUT)
        if r.status_code != 200:
            return None

        img_array = np.frombuffer(r.content, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        print(f"❌ Ошибка получения кадра: {e}")
        return None

# ===== ROUTES =====
@app.get("/")
def status():
    return {
        "status": "running",
        "camera": CAMERA_URL,
        "server_ip": "172.20.10.2",
        "yolo_loaded": yolo_model is not None,
        "asteroid_model_loaded": asteroid_model is not None
    }

@app.get("/check")
def check_object():
    try:
        frame = get_camera_frame()
        if frame is None:
            return "DENY"

        detected = combined_detection(frame)

        for cls in detected:
            if cls in ALLOW_CLASSES:
                return "ALLOW"

        return "DENY"

    except Exception as e:
        print("❌ ERROR:", e)
        return "DENY"

@app.get("/test")
def test():
    frame = get_camera_frame()
    if frame is None:
        return {
            "camera": "fail",
            "yolo_detected": False,
            "asteroid_detected": False,
            "final_result": "DENY"
        }

    yolo_classes = detect_with_yolo(frame)
    asteroid_classes = detect_with_asteroid_model(frame)
    all_classes = yolo_classes + asteroid_classes

    return {
        "camera": "ok",
        "yolo_detected": len(yolo_classes) > 0,
        "yolo_classes": yolo_classes,
        "asteroid_detected": len(asteroid_classes) > 0,
        "asteroid_classes": asteroid_classes,
        "all_classes": all_classes,
        "final_result": "ALLOW" if any(c in ALLOW_CLASSES for c in all_classes) else "DENY"
    }

@app.get("/models")
def get_models_info():
    """Информация о загруженных моделях"""
    return {
        "yolo_model": {
            "loaded": yolo_model is not None,
            "path": YOLO_MODEL,
            "classes": list(yolo_model.names.values()) if yolo_model else []
        },
        "asteroid_model": {
            "loaded": asteroid_model is not None,
            "path": ASTEROID_MODEL,
            "classes": list(asteroid_model.names.values()) if asteroid_model else []
        }
    }
