import os
import time
import asyncio
import aiofiles
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.responses import JSONResponse
import requests

from models import AnalysisResponse, DetectionResult, StatusResponse
from yolo_detector import YOLODetector

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при запуске сервера"""
    global detector
    try:
        detector = YOLODetector(model_path=MODEL_PATH)
        print(f"✅ YOLO модель загружена: {MODEL_PATH}")
        print(f"🎯 Разрешенные классы: {detector.get_allowed_classes()}")
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        detector = None
    yield
    # Cleanup code here if needed

app = FastAPI(
    title="AI Smart Grabber Server",
    description="Сервер для анализа изображений с YOLO и принятия решений",
    version="1.0.0",
    lifespan=lifespan
)

# Глобальные переменные
detector: Optional[YOLODetector] = None
start_time = time.time()

# Конфигурация
ESP32_CAM_URL = os.getenv("ESP32_CAM_URL", "http://192.168.1.100/capture")
MODEL_PATH = os.getenv("MODEL_PATH", "yolov8n.pt")
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.5"))

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "AI Smart Grabber Server",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Получение статуса сервера"""
    uptime = time.time() - start_time
    return StatusResponse(
        status="healthy" if detector else "error",
        server_time=datetime.now(),
        model_loaded=detector is not None,
        uptime=uptime
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    Анализ загруженного изображения
    
    Args:
        file: изображение для анализа
        
    Returns:
        результат анализа с решением ALLOW/DENY
    """
    if not detector:
        raise HTTPException(status_code=503, detail="YOLO модель не загружена")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")
    
    try:
        # Читаем файл
        image_bytes = await file.read()
        
        # Обрабатываем изображение
        decision, detections, processing_time = detector.process_image(image_bytes)
        
        return AnalysisResponse(
            decision=decision,
            detections=detections,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки изображения: {str(e)}")

@app.post("/analyze_from_camera", response_model=AnalysisResponse)
async def analyze_from_camera():
    """
    Анализ изображения с ESP32-CAM
    
    Returns:
        результат анализа с решением ALLOW/DENY
    """
    if not detector:
        raise HTTPException(status_code=503, detail="YOLO модель не загружена")
    
    try:
        # Получаем изображение с ESP32-CAM
        response = requests.get(ESP32_CAM_URL, timeout=5)
        response.raise_for_status()
        
        # Обрабатываем изображение
        decision, detections, processing_time = detector.process_image(response.content)
        
        return AnalysisResponse(
            decision=decision,
            detections=detections,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ошибка подключения к ESP32-CAM: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки изображения: {str(e)}")

@app.get("/classes")
async def get_allowed_classes():
    """Получение списка разрешенных классов"""
    if not detector:
        raise HTTPException(status_code=503, detail="YOLO модель не загружена")
    
    return {
        "allowed_classes": detector.get_allowed_classes(),
        "total": len(detector.get_allowed_classes())
    }

@app.post("/classes/add")
async def add_allowed_class(class_name: str):
    """Добавление разрешенного класса"""
    if not detector:
        raise HTTPException(status_code=503, detail="YOLO модель не загружена")
    
    detector.add_allowed_class(class_name)
    return {
        "message": f"Класс '{class_name}' добавлен в разрешенные",
        "allowed_classes": detector.get_allowed_classes()
    }

@app.delete("/classes/{class_name}")
async def remove_allowed_class(class_name: str):
    """Удаление разрешенного класса"""
    if not detector:
        raise HTTPException(status_code=503, detail="YOLO модель не загружена")
    
    detector.remove_allowed_class(class_name)
    return {
        "message": f"Класс '{class_name}' удален из разрешенных",
        "allowed_classes": detector.get_allowed_classes()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Внутренняя ошибка сервера: {str(exc)}"}
    )

if __name__ == "__main__":
    print("🚀 Запуск AI Smart Grabber Server...")
    print(f"📷 ESP32-CAM URL: {ESP32_CAM_URL}")
    print(f"🧠 YOLO модель: {MODEL_PATH}")
    print(f"🎯 Порог уверенности: {CONF_THRESHOLD}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False if os.getenv("PORT") else True,
        log_level="info"
    )
