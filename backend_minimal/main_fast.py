from fastapi import FastAPI
import requests
import cv2
import numpy as np

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

# ===== MOCK YOLO (быстрая заглушка) =====
def yolo_detect(image):
    """
    Быстрая заглушка для тестирования
    Возвращает случайные объекты для проверки логики
    """
    import random
    
    # Генерируем случайное число для логирования
    rand_val = random.random()
    print(f"🎲 Случайное значение: {rand_val:.3f}")
    
    # 40% шанс найти мусор (разрешенные объекты)
    if rand_val < 0.4:
        trash_items = ["bottle", "can", "cup", "book", "cell phone", "plastic_bag"]
        found = random.choice(trash_items)
        print(f"🗑️ Мок-детекция: найден мусор - {found}")
        return [found]
    
    # 20% шанс найти человека/руку (запрещено)
    elif rand_val < 0.6:
        person_items = ["person", "hand"]
        found = random.choice(person_items)
        print(f"🚫 Мок-детекция: найден человек/рука - {found}")
        return [found]
    
    # 15% шанс найти астероид (запрещено)
    elif rand_val < 0.75:
        print("� Мок-детекция: найден астероид (ЗАПРЕЩЕНО)")
        return ["asteroid"]
    
    # 25% ничего не найдено
    else:
        print("👻 Мок-детекция: ничего не найдено")
        return []

# ===== UTILS =====
def get_camera_frame():
    print("📷 Запрос изображения с камеры...")
    try:
        r = requests.get(CAMERA_URL, timeout=TIMEOUT)
        if r.status_code != 200:
            print(f"❌ Камера вернула статус: {r.status_code}")
            return None

        img_array = np.frombuffer(r.content, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            print("❌ Не удалось декодировать изображение")
            return None
            
        print(f"✅ Изображение получено: {frame.shape}")
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
        "mode": "mock_detection"
    }

@app.get("/check")
def check_object():
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
                return "DENY"
        
        # Потом проверяем разрешенные
        for cls in detected:
            if cls in ALLOW_CLASSES:
                print(f"✅ НАЙДЕН РАЗРЕШЕННЫЙ МУСОР: {cls} -> ALLOW")
                return "ALLOW"

        print(f"❌ Неизвестные объекты: {detected} -> DENY")
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
    return "ALLOW"

@app.get("/force_deny")
def force_deny():
    """Принудительно запретить - для теста манипулятора"""
    return "DENY"

@app.get("/mock_settings")
def get_mock_settings():
    """Настройки мок-детекции"""
    return {
        "mode": "trash_collector_mock",
        "logic": "ALLOW мусор, DENY космос/люди",
        "trash_chance": 0.4,      # 40% найти мусор
        "human_chance": 0.2,     # 20% найти человека
        "space_chance": 0.15,     # 15% найти космос
        "nothing_chance": 0.25,   # 25% ничего
        "allow_classes": ALLOW_CLASSES,
        "deny_classes": DENY_CLASSES,
        "priority": "DENY > ALLOW (безопасность)"
    }
