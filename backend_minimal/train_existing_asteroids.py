import os
import yaml
from ultralytics import YOLO
from pathlib import Path

def create_dataset_yaml():
    """Создает YAML файл для существующего датасета"""
    
    dataset_path = "../asteroids"
    
    yaml_content = {
        'path': str(Path(dataset_path).absolute()),
        'train': 'train/images',
        'val': 'valid/images',
        'test': 'test/images',
        'nc': 1,  # количество классов
        'names': ['asteroid']  # имена классов
    }
    
    yaml_path = f"{dataset_path}/dataset.yaml"
    with open(yaml_path, 'w') as f:
        yaml.dump(yaml_content, f, default_flow_style=False)
    
    print(f"📄 Создан YAML файл: {yaml_path}")
    return yaml_path

def train_asteroid_model():
    """Обучает YOLO модель на существующем датасете астероидов"""
    
    print("🌑 Начинаю обучение модели астероидов...")
    
    # Проверяем наличие датасета
    dataset_path = "../asteroids"
    if not os.path.exists(dataset_path):
        print(f"❌ Папка '{dataset_path}' не найдена!")
        return None
    
    # Создаем YAML конфигурацию
    yaml_path = create_dataset_yaml()
    
    # Загружаем предобученную модель
    model = YOLO('yolov8n.pt')  # nano версия для быстрого обучения
    
    # Параметры обучения
    training_params = {
        'data': yaml_path,
        'epochs': 100,  # увеличиваем эпохи для лучшего качества
        'imgsz': 640,  # размер изображений
        'batch': 16,   # размер батча
        'name': 'asteroid_detector_v2',  # имя эксперимента
        'project': 'runs/detect',     # папка для результатов
        'save': True,     # сохранять лучшие веса
        'plots': True,    # строить графики
        'device': 'cpu',   # можно изменить на 'cuda' если есть GPU
        'patience': 20,   # ранняя остановка если нет улучшений
        'lr0': 0.01,      # начальная скорость обучения
        'optimizer': 'AdamW'  # оптимизатор
    }
    
    print(f"📊 Параметры обучения:")
    print(f"   Эпохи: {training_params['epochs']}")
    print(f"   Размер изображения: {training_params['imgsz']}")
    print(f"   Батч: {training_params['batch']}")
    print(f"   Устройство: {training_params['device']}")
    
    try:
        # Обучаем модель
        results = model.train(**training_params)
        
        # Сохраняем лучшую модель
        best_model_path = f"runs/detect/asteroid_detector_v2/weights/best.pt"
        final_model_path = "asteroid_detector_v2.pt"
        
        if os.path.exists(best_model_path):
            # Копируем модель в корень
            import shutil
            shutil.copy2(best_model_path, final_model_path)
            
            print(f"✅ Модель сохранена как: {final_model_path}")
            print(f"📊 Метрики обучения:")
            if hasattr(results, 'results_dict') and results.results_dict:
                print(f"   mAP50: {results.results_dict.get('metrics/mAP50-50', 'N/A'):.4f}")
                print(f"   mAP50-95: {results.results_dict.get('metrics/mAP50-95', 'N/A'):.4f}")
                print(f"   Precision: {results.results_dict.get('metrics/precision(B)', 'N/A'):.4f}")
                print(f"   Recall: {results.results_dict.get('metrics/recall(B)', 'N/A'):.4f}")
            
            return final_model_path
        else:
            print(f"⚠️ Файл модели не найден: {best_model_path}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка обучения: {e}")
        return None

def test_model(model_path: str):
    """Тестирует обученную модель на валидационных данных"""
    
    print(f"🧪 Тестирую модель: {model_path}")
    
    try:
        model = YOLO(model_path)
        
        # Валидация на тестовом наборе
        test_path = "../asteroids/test/images"
        if os.path.exists(test_path):
            test_images = list(Path(test_path).glob("*.jpg"))
            if test_images:
                print(f"📸 Найдено тестовых изображений: {len(test_images)}")
                
                # Тестируем на нескольких изображениях
                for i, img_path in enumerate(test_images[:5]):  # первые 5 изображений
                    results = model(str(img_path))
                    
                    print(f"🖼️ Тест {i+1}: {img_path.name}")
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                class_id = int(box.cls[0])
                                confidence = float(box.conf[0])
                                print(f"   🎯 Найден: {model.names[class_id]} (уверенность: {confidence:.2f})")
                        else:
                            print("   ❌ Астероиды не найдены")
                print("✅ Тестирование завершено")
            else:
                print("⚠️ Тестовые изображения не найдены")
        else:
            print(f"⚠️ Папка {test_path} не найдена")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")

def update_main_py():
    """Обновляет main_with_yolo.py для использования новой модели"""
    
    new_model_path = "asteroid_detector_v2.pt"
    
    if os.path.exists(new_model_path):
        try:
            with open("main_with_yolo.py", 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Заменяем путь к модели астероидов
            content = content.replace(
                'ASTEROID_MODEL = "asteroid_detector.pt"',
                f'ASTEROID_MODEL = "{new_model_path}"'
            )
            
            with open("main_with_yolo.py", 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ main_with_yolo.py обновлен для использования {new_model_path}")
            
        except Exception as e:
            print(f"❌ Ошибка обновления main_with_yolo.py: {e}")

if __name__ == "__main__":
    print("🚀 Обучение модели астероидов на готовом датасете...")
    print("=" * 50)
    
    # Шаг 1: Обучение модели
    model_path = train_asteroid_model()
    
    if model_path and os.path.exists(model_path):
        print("\n" + "=" * 50)
        print("✅ Обучение успешно завершено!")
        
        # Шаг 2: Тестирование модели
        print("\n🧪 Тестирование модели...")
        test_model(model_path)
        
        # Шаг 3: Обновление конфигурации
        print("\n🔧 Обновление конфигурации...")
        update_main_py()
        
        print("\n" + "=" * 50)
        print("🎉 Готово! Теперь можно запустить:")
        print("   uvicorn main_with_yolo:app --host 0.0.0.0 --port 5000")
        print("=" * 50)
        
    else:
        print("\n❌ Обучение не удалось!")
        print("Проверьте:")
        print("1. Наличие папки '../asteroids' с правильной структурой")
        print("2. Установленные зависимости: pip install ultralytics pyyaml")
        print("3. Достаточно места на диске")
