import os
import cv2
import numpy as np
from ultralytics import YOLO
import yaml
from pathlib import Path

def create_yolo_dataset_structure(dataset_path: str, output_path: str):
    """
    Создает структуру датасета YOLO из папки с изображениями астероидов
    
    Args:
        dataset_path: путь к папке с изображениями астероидов
        output_path: путь для создания YOLO датасета
    """
    
    # Создаем структуру папок
    os.makedirs(f"{output_path}/images/train", exist_ok=True)
    os.makedirs(f"{output_path}/images/val", exist_ok=True)
    os.makedirs(f"{output_path}/labels/train", exist_ok=True)
    os.makedirs(f"{output_path}/labels/val", exist_ok=True)
    
    # Получаем список изображений
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(Path(dataset_path).glob(f"*{ext}"))
        image_files.extend(Path(dataset_path).glob(f"*{ext.upper()}"))
    
    print(f"📸 Найдено изображений: {len(image_files)}")
    
    # Разделяем на train/val (80/20)
    train_split = int(0.8 * len(image_files))
    train_files = image_files[:train_split]
    val_files = image_files[train_split:]
    
    # Класс астероидов - ID 0
    class_id = 0
    
    def process_images(image_files, split_name):
        """Обрабатывает изображения и создает YOLO аннотации"""
        for i, img_path in enumerate(image_files):
            try:
                # Копируем изображение
                img = cv2.imread(str(img_path))
                if img is None:
                    print(f"⚠️ Пропуск поврежденного изображения: {img_path}")
                    continue
                
                h, w = img.shape[:2]
                
                # Сохраняем изображение
                output_img_path = f"{output_path}/images/{split_name}/{i:06d}.jpg"
                cv2.imwrite(output_img_path, img)
                
                # Создаем YOLO аннотацию (весь объект - астероид)
                # Формат: class_id x_center y_center width height (нормализованные)
                label_path = f"{output_path}/labels/{split_name}/{i:06d}.txt"
                
                with open(label_path, 'w') as f:
                    # Предполагаем что весь кадр - это астероид
                    # В реальности нужно разметить bounding boxes
                    x_center, y_center, width, height = 0.5, 0.5, 1.0, 1.0
                    f.write(f"{class_id} {x_center} {y_center} {width} {height}\n")
                
                if i % 10 == 0:
                    print(f"📝 Обработано {i+1}/{len(image_files)} изображений для {split_name}")
                    
            except Exception as e:
                print(f"❌ Ошибка обработки {img_path}: {e}")
    
    # Обрабатываем train и val
    process_images(train_files, "train")
    process_images(val_files, "val")
    
    print(f"✅ Датасет создан в {output_path}")
    print(f"📊 Train: {len(train_files)}, Val: {len(val_files)}")

def create_dataset_yaml(output_path: str):
    """Создает YAML файл конфигурации датасета"""
    
    yaml_content = {
        'path': str(Path(output_path).absolute()),
        'train': 'images/train',
        'val': 'images/val',
        'nc': 1,  # количество классов
        'names': ['asteroid']  # имена классов
    }
    
    yaml_path = f"{output_path}/dataset.yaml"
    with open(yaml_path, 'w') as f:
        yaml.dump(yaml_content, f, default_flow_style=False)
    
    print(f"📄 Создан YAML файл: {yaml_path}")
    return yaml_path

def train_asteroid_model(dataset_path: str, model_output: str = "asteroid_detector.pt"):
    """
    Обучает YOLO модель на датасете астероидов
    
    Args:
        dataset_path: путь к YOLO датасету
        model_output: имя выходной модели
    """
    
    print("🧠 Начинаю обучение YOLO модели...")
    
    # Загружаем предобученную модель
    model = YOLO('yolov8n.pt')  # nano версия для быстрого обучения
    
    # Параметры обучения
    training_params = {
        'data': f"{dataset_path}/dataset.yaml",
        'epochs': 50,  # количество эпох
        'imgsz': 640,  # размер изображений
        'batch': 16,   # размер батча
        'name': 'asteroid_detector',  # имя эксперимента
        'project': 'runs/detect',     # папка для результатов
        'save': True,     # сохранять лучшие веса
        'plots': True,    # строить графики
        'device': 'cpu'   # можно изменить на 'cuda' если есть GPU
    }
    
    # Обучаем модель
    try:
        results = model.train(**training_params)
        
        # Сохраняем лучшую модель
        best_model_path = f"runs/detect/asteroid_detector/weights/best.pt"
        if os.path.exists(best_model_path):
            # Копируем модель в нужное место
            import shutil
            shutil.copy2(best_model_path, model_output)
            print(f"✅ Модель сохранена как: {model_output}")
            print(f"📊 Метрики обучения:")
            print(f"   mAP50: {results.results_dict['metrics/mAP50-50']:.4f}")
            print(f"   mAP50-95: {results.results_dict['metrics/mAP50-95']:.4f}")
        else:
            print(f"⚠️ Файл модели не найден: {best_model_path}")
            
    except Exception as e:
        print(f"❌ Ошибка обучения: {e}")
        return None
    
    return model_output

def test_model(model_path: str, test_image_path: str = None):
    """Тестирует обученную модель"""
    
    print(f"🧪 Тестирую модель: {model_path}")
    
    try:
        model = YOLO(model_path)
        
        if test_image_path and os.path.exists(test_image_path):
            # Тестируем на конкретном изображении
            results = model(test_image_path)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        print(f"🎯 Найден: {model.names[class_id]} (уверенность: {confidence:.2f})")
                else:
                    print("❌ Астероиды не найдены")
        else:
            print("✅ Модель загружена успешно")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")

if __name__ == "__main__":
    # Параметры для обучения
    ASTEROID_DATASET_PATH = "asteroid_images"  # папка с вашими изображениями
    YOLO_DATASET_PATH = "asteroid_yolo_dataset"
    MODEL_OUTPUT = "asteroid_detector.pt"
    
    print("🚀 Подготовка датасета астероидов...")
    
    # Шаг 1: Создаем YOLO датасет
    if os.path.exists(ASTEROID_DATASET_PATH):
        create_yolo_dataset_structure(ASTEROID_DATASET_PATH, YOLO_DATASET_PATH)
        create_dataset_yaml(YOLO_DATASET_PATH)
        
        # Шаг 2: Обучаем модель
        model_path = train_asteroid_model(YOLO_DATASET_PATH, MODEL_OUTPUT)
        
        # Шаг 3: Тестируем модель
        if model_path and os.path.exists(model_path):
            test_model(model_path)
            
        print("\n🎉 Обучение завершено!")
        print(f"📁 Модель сохранена: {MODEL_OUTPUT}")
        print("💡 Теперь можно использовать модель в main.py")
        
    else:
        print(f"❌ Папка с изображениями не найдена: {ASTEROID_DATASET_PATH}")
        print("📝 Создайте папку 'asteroid_images' и добавьте туда фотографии астероидов")
