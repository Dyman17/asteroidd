#!/usr/bin/env python3
"""
🧠 Полная информация о классах объектов для AI Smart Grabber
"""

# ===== СТАНДАРТНЫЕ КЛАССЫ COCO (YOLOv8) =====
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
    8: "boat",
    9: "traffic light",
    10: "fire hydrant",
    11: "stop sign",
    12: "parking meter",
    13: "bench",
    14: "bird",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
    22: "zebra",
    23: "giraffe",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    29: "frisbee",
    30: "skis",
    31: "snowboard",
    32: "sports ball",
    33: "kite",
    34: "baseball bat",
    35: "baseball glove",
    36: "skateboard",
    37: "surfboard",
    38: "tennis racket",
    39: "bottle",          # ✅ РАЗРЕШЕННЫЙ
    40: "wine glass",
    41: "cup",             # ✅ РАЗРЕШЕННЫЙ
    42: "fork",
    43: "knife",
    44: "spoon",
    45: "bowl",
    46: "banana",
    47: "apple",
    48: "sandwich",
    49: "orange",
    50: "broccoli",
    51: "carrot",
    52: "hot dog",
    53: "pizza",
    54: "donut",
    55: "cake",
    56: "chair",
    57: "couch",
    58: "potted plant",
    59: "bed",
    60: "dining table",
    61: "toilet",
    62: "tv",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell phone",      # ✅ РАЗРЕШЕННЫЙ
    68: "microwave",
    69: "oven",
    70: "toaster",
    71: "sink",
    72: "refrigerator",
    73: "book",            # ✅ РАЗРЕШЕННЫЙ
    74: "clock",
    75: "vase",
    76: "scissors",
    77: "teddy bear",
    78: "hair drier",
    79: "toothbrush"
}

# ===== РАЗРЕШЕННЫЕ КЛАССЫ ДЛЯ МАНИПУЛЯТОРА =====
ALLOW_CLASSES = [
    "bottle",      # Бутылка (пластик/стекло)
    "can",         # Жестяная банка (доп. класс)
    "cup",         # Чашка/кружка
    "book",        # Книга
    "cell phone",  # Мобильный телефон
    "asteroid",    # Астероид (ваша модель)
    "space_rock",  # Космический камень (доп. класс)
    "meteor",      # Метеорит (доп. класс)
]

# ===== ЗАПРЕЩЕННЫЕ КЛАССЫ (ПО УМОЛЧАНИЮ) =====
DENY_CLASSES = [
    "person",      # Люди
    "animal",      # Животные
    "food",        # Еда
    "electronics", # Электроника (кроме телефона)
    "dangerous",   # Опасные предметы
]

# ===== КАТЕГОРИИ КЛАССОВ =====
CLASS_CATEGORIES = {
    "Посуда": ["bottle", "cup", "wine glass", "bowl"],
    "Еда": ["banana", "apple", "sandwich", "pizza", "cake"],
    "Электроника": ["cell phone", "laptop", "tv", "remote"],
    "Транспорт": ["car", "bicycle", "motorcycle", "bus"],
    "Животные": ["cat", "dog", "horse", "cow"],
    "Люди": ["person"],
    "Космические": ["asteroid", "space_rock", "meteor"],
    "Книги": ["book"],
    "Спорт": ["sports ball", "frisbee", "skateboard"],
    "Одежда": ["backpack", "handbag", "tie"],
}

# ===== ДОПОЛНИТЕЛЬНЫЕ КЛАССЫ ДЛЯ ОБУЧЕНИЯ =====
CUSTOM_CLASSES = {
    "can": "Жестяная банка для напитков",
    "space_rock": "Космический камень/обломок",
    "meteor": "Метеорит или метеороид",
    "plastic_bottle": "Пластиковая бутылка",
    "glass_bottle": "Стеклянная бутылка",
    "soda_can": "Алюминиевая банка с газировкой",
    "food_container": "Контейнер для еды",
    "toy": "Игрушка",
    "tool": "Инструмент",
    "stationery": "Канцелярские товары",
}

# ===== ПРАВИЛА ПРИНЯТИЯ РЕШЕНИЙ =====
DECISION_RULES = {
    "ALLOW_RULES": [
        "Объект в ALLOW_CLASSES -> ALLOW",
        "Уверенность > 0.5 + разрешенный класс -> ALLOW",
        "Несколько разрешенных объектов -> ALLOW",
    ],
    "DENY_RULES": [
        "Объект не в ALLOW_CLASSES -> DENY",
        "Человек в кадре -> DENY (безопасность)",
        "Животное в кадре -> DENY (безопасность)",
        "Уверенность < 0.3 -> DENY (слишком сомнительно)",
        "Нет объектов -> DENY",
    ],
    "SPECIAL_CASES": [
        "cell phone + high confidence -> ALLOW (ценный предмет)",
        "bottle + plastic -> ALLOW (переработка)",
        "book + hardcover -> ALLOW (сохранность)",
    ]
}

# ===== КОНФИГУРАЦИЯ ДЕТЕКЦИИ =====
DETECTION_CONFIG = {
    "STANDARD_YOLO": {
        "model": "yolov8n.pt",
        "confidence_threshold": 0.5,
        "iou_threshold": 0.45,
        "max_detections": 100,
    },
    "ASTEROID_MODEL": {
        "model": "asteroid_detector_v2.pt",
        "confidence_threshold": 0.3,  # ниже для астероидов
        "iou_threshold": 0.45,
        "max_detections": 50,
    },
    "REAL_TIME": {
        "image_size": 640,
        "processing_threads": 1,
        "max_fps": 30,
    }
}

def print_all_classes():
    """Выводит все классы с категориями"""
    print("🧠 КЛАССЫ ОБЪЕКТОВ ДЛЯ AI SMART GRABBER")
    print("=" * 60)
    
    print("\n✅ РАЗРЕШЕННЫЕ КЛАССЫ (для захвата):")
    for i, cls in enumerate(ALLOW_CLASSES, 1):
        print(f"  {i}. {cls}")
    
    print(f"\n❌ ЗАПРЕЩЕННЫЕ КЛАССЫ (игнорируются):")
    for category, classes in CLASS_CATEGORIES.items():
        if category not in ["Посуда", "Электроника", "Книги", "Космические"]:
            print(f"  {category}: {', '.join(classes)}")
    
    print(f"\n📊 ВСЕ КЛАССЫ COCO (стандартная YOLO):")
    for class_id, class_name in COCO_CLASSES.items():
        status = "✅" if class_name in ALLOW_CLASSES else "❌"
        print(f"  {class_id:2d}. {class_name:<15} {status}")
    
    print(f"\n🌑 ДОПОЛНИТЕЛЬНЫЕ КЛАССЫ (для обучения):")
    for cls, desc in CUSTOM_CLASSES.items():
        print(f"  • {cls}: {desc}")
    
    print(f"\n🎯 ПРАВИЛА ПРИНЯТИЯ РЕШЕНИЙ:")
    print("  ALLOW:")
    for rule in DECISION_RULES["ALLOW_RULES"]:
        print(f"    • {rule}")
    print("  DENY:")
    for rule in DECISION_RULES["DENY_RULES"]:
        print(f"    • {rule}")

def check_class_status(class_name):
    """Проверяет статус класса"""
    if class_name in ALLOW_CLASSES:
        return f"✅ ALLOW - {class_name}"
    elif class_name in COCO_CLASSES.values():
        return f"❌ DENY - {class_name}"
    elif class_name in CUSTOM_CLASSES:
        return f"🔶 CUSTOM - {class_name}"
    else:
        return f"❓ UNKNOWN - {class_name}"

if __name__ == "__main__":
    print_all_classes()
    
    print("\n" + "=" * 60)
    print("🔍 ПРОВЕРКА СТАТУСА КЛАССОВ:")
    test_classes = ["bottle", "person", "asteroid", "cat", "can", "unknown_object"]
    for cls in test_classes:
        print(f"  {check_class_status(cls)}")
