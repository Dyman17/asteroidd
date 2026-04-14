import os
import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from ultralytics import YOLO


BASE_MODEL_PATH = os.getenv("BASE_MODEL_PATH", "models/yolov8n.pt").strip()
CUSTOM_MODEL_PATH = os.getenv("CUSTOM_MODEL_PATH", "models/asteroid_detector.pt").strip()
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.5"))
CUSTOM_CONF_THRESHOLD = float(os.getenv("CUSTOM_CONF_THRESHOLD", str(CONF_THRESHOLD)))
ALLOW_CLASSES = set(
    [
        c.strip().lower()
        for c in os.getenv(
            "ALLOW_CLASSES",
            "bottle,cup,wine glass,book,cell phone,laptop,backpack,handbag,suitcase,umbrella,"
            "fork,knife,spoon,bowl,banana,apple,orange,sandwich,pizza,donut,cake,vase",
        ).split(",")
        if c.strip()
    ]
)
DENY_CLASSES = set(
    [c.strip().lower() for c in os.getenv("DENY_CLASSES", "person,hand").split(",") if c.strip()]
)


class DetectionResult(BaseModel):
    class_name: str
    confidence: float
    bbox: List[int]
    model: str


class AnalysisResponse(BaseModel):
    decision: str
    detections: List[DetectionResult]
    processing_time: float
    timestamp: datetime


def _load_model(path: str) -> Optional[YOLO]:
    if not path:
        return None
    if not os.path.exists(path):
        return None
    return YOLO(path)


class Detector:
    def __init__(self) -> None:
        self.base_model = _load_model(BASE_MODEL_PATH)
        self.custom_model = _load_model(CUSTOM_MODEL_PATH)

    def _predict(self, model: YOLO, image: np.ndarray, conf: float, label: str) -> List[DetectionResult]:
        detections: List[DetectionResult] = []
        results = model(image, conf=conf, verbose=False)
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int).tolist()
                class_id = int(box.cls[0].cpu().numpy())
                confidence = float(box.conf[0].cpu().numpy())
                class_name = str(model.names[class_id]).lower()
                detections.append(
                    DetectionResult(
                        class_name=class_name,
                        confidence=confidence,
                        bbox=[x1, y1, x2, y2],
                        model=label,
                    )
                )
        return detections

    def analyze(self, image_bytes: bytes) -> Tuple[str, List[DetectionResult], float]:
        start = time.time()

        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode image")

        detections: List[DetectionResult] = []
        if self.base_model:
            detections.extend(self._predict(self.base_model, image, CONF_THRESHOLD, "base"))
        if self.custom_model:
            detections.extend(self._predict(self.custom_model, image, CUSTOM_CONF_THRESHOLD, "custom"))

        decision = self._make_decision(detections)
        return decision, detections, time.time() - start

    @staticmethod
    def _make_decision(detections: List[DetectionResult]) -> str:
        names = [d.class_name.lower() for d in detections]
        if any(n in DENY_CLASSES for n in names):
            return "DENY"
        if any(n in ALLOW_CLASSES for n in names):
            return "ALLOW"
        return "DENY"


app = FastAPI(title="Local AI Server", version="1.0.0")
detector = Detector()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "base_model": BASE_MODEL_PATH if detector.base_model else None,
        "custom_model": CUSTOM_MODEL_PATH if detector.custom_model else None,
    }


@app.post("/analyze_bytes", response_model=AnalysisResponse)
async def analyze_bytes(request: Request):
    if not detector.base_model and not detector.custom_model:
        raise HTTPException(status_code=503, detail="No models loaded")

    image_bytes = await request.body()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty request body")

    try:
        decision, detections, processing_time = detector.analyze(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AnalysisResponse(
        decision=decision,
        detections=detections,
        processing_time=processing_time,
        timestamp=datetime.now(timezone.utc),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
