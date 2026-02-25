import cv2
import numpy as np
from ultralytics import YOLO
import time
from typing import List, Tuple
from models import DetectionResult

class YOLODetector:
    def __init__(self, model_path: str = "yolov8n.pt"):
        """
        Инициализация YOLO детектора
        
        Args:
            model_path: путь к модели YOLO (по умолчанию yolov8n.pt)
        """
        self.model = YOLO(model_path)
        self.allow_classes = {
            'bottle', 'can', 'cup', 'book', 'cell phone',
            'asteroid', 'space_rock', 'meteor'
        }
        
    def detect_objects(self, image: np.ndarray, conf_threshold: float = 0.5) -> List[DetectionResult]:
        """
        Детекция объектов на изображении
        
        Args:
            image: изображение в формате numpy array (BGR)
            conf_threshold: порог уверенности
            
        Returns:
            список детекций
        """
        results = self.model(image, conf=conf_threshold)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Получаем координаты bbox
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    
                    # Получаем класс и уверенность
                    class_id = int(box.cls[0].cpu().numpy())
                    confidence = float(box.conf[0].cpu().numpy())
                    class_name = self.model.names[class_id]
                    
                    detection = DetectionResult(
                        class_name=class_name,
                        confidence=confidence,
                        bbox=[x1, y1, x2, y2]
                    )
                    detections.append(detection)
        
        return detections
    
    def make_decision(self, detections: List[DetectionResult]) -> str:
        """
        Принятие решения на основе детекций
        
        Args:
            detections: список детекций
            
        Returns:
            "ALLOW" если есть разрешенный объект, иначе "DENY"
        """
        for detection in detections:
            if detection.class_name.lower() in self.allow_classes:
                return "ALLOW"
        
        return "DENY"
    
    def process_image(self, image_bytes: bytes) -> Tuple[str, List[DetectionResult], float]:
        """
        Полная обработка изображения
        
        Args:
            image_bytes: изображение в виде байтов (JPEG)
            
        Returns:
            (decision, detections, processing_time)
        """
        start_time = time.time()
        
        # Декодируем изображение
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Не удалось декодировать изображение")
        
        # Детекция объектов
        detections = self.detect_objects(image)
        
        # Принятие решения
        decision = self.make_decision(detections)
        
        processing_time = time.time() - start_time
        
        return decision, detections, processing_time
    
    def add_allowed_class(self, class_name: str):
        """Добавление разрешенного класса"""
        self.allow_classes.add(class_name.lower())
    
    def remove_allowed_class(self, class_name: str):
        """Удаление разрешенного класса"""
        self.allow_classes.discard(class_name.lower())
    
    def get_allowed_classes(self) -> List[str]:
        """Получение списка разрешенных классов"""
        return list(self.allow_classes)
