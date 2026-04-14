import os
import time
import threading
import base64
import json
import requests
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
CLOUD_BACKEND_URL = os.getenv("CLOUD_BACKEND_URL", "https://asteroidd-server.onrender.com").strip()
AI_DEVICE_ID = os.getenv("AI_DEVICE_ID", "ai-laptop-1").strip()
PULL_INTERVAL = float(os.getenv("PULL_INTERVAL", "2.0"))
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
pull_thread_running = False


def _rgb565_to_image(raw: bytes, width: int, height: int) -> np.ndarray:
    """Convert RGB565 raw bytes to numpy BGR image."""
    expected = width * height * 2
    if len(raw) != expected:
        raise ValueError(f"RGB565 length mismatch: got {len(raw)} expected {expected}")
    data = np.frombuffer(raw, dtype=np.uint16).reshape((height, width))
    r = ((data >> 11) & 0x1F).astype(np.uint8)
    g = ((data >> 5) & 0x3F).astype(np.uint8)
    b = (data & 0x1F).astype(np.uint8)
    r = (r * 255 // 31).astype(np.uint8)
    g = (g * 255 // 63).astype(np.uint8)
    b = (b * 255 // 31).astype(np.uint8)
    return cv2.merge([b, g, r])


def _pull_frames_from_cloud():
    """Background thread: pull frames from cloud, analyze, and send results back."""
    global pull_thread_running
    pull_thread_running = True
    while pull_thread_running:
        try:
            if not CLOUD_BACKEND_URL or not detector.base_model and not detector.custom_model:
                time.sleep(PULL_INTERVAL)
                continue

            pull_url = CLOUD_BACKEND_URL.rstrip("/") + "/ai/pull_frame"
            resp = requests.get(
                pull_url,
                params={"ai_device_id": AI_DEVICE_ID},
                timeout=5,
            )
            resp.raise_for_status()
            payload = resp.json()

            if not payload.get("ok"):
                time.sleep(PULL_INTERVAL)
                continue

            frame_base64 = payload.get("frame_base64", "")
            width = payload.get("width", 320)
            height = payload.get("height", 240)
            fmt = payload.get("format", "RGB565")
            cam_device_id = payload.get("camera_device_id", "unknown")

            if not frame_base64 or fmt.upper() != "RGB565":
                time.sleep(PULL_INTERVAL)
                continue

            raw_frame = base64.b64decode(frame_base64)
            image = _rgb565_to_image(raw_frame, width, height)

            # Analyze
            detections: List[DetectionResult] = []
            if detector.base_model:
                detections.extend(detector._predict(detector.base_model, image, CONF_THRESHOLD, "base"))
            if detector.custom_model:
                detections.extend(detector._predict(detector.custom_model, image, CUSTOM_CONF_THRESHOLD, "custom"))

            decision = detector._make_decision(detections)
            processing_time = 0.0

            # Send result back to cloud
            result_payload = {
                "device_id": AI_DEVICE_ID,
                "camera_device_id": cam_device_id,
                "decision": decision,
                "detections": [
                    {
                        "class_name": d.class_name,
                        "confidence": d.confidence,
                        "bbox": d.bbox,
                        "model": d.model,
                    }
                    for d in detections
                ],
                "processing_time": processing_time,
            }
            result_url = CLOUD_BACKEND_URL.rstrip("/") + "/ai/result"
            result_resp = requests.post(result_url, json=result_payload, timeout=5)
            result_resp.raise_for_status()
            print(f"[Cloud Relay] Sent decision={decision} for device={cam_device_id}")

        except Exception as exc:
            print(f"[Cloud Relay Error] {exc}")

        time.sleep(PULL_INTERVAL)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "base_model": BASE_MODEL_PATH if detector.base_model else None,
        "custom_model": CUSTOM_MODEL_PATH if detector.custom_model else None,
        "cloud_backend": CLOUD_BACKEND_URL if CLOUD_BACKEND_URL else "disabled",
        "pulling_frames": pull_thread_running,
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


@app.on_event("startup")
def startup_event():
    """Start the cloud pull thread on app startup."""
    if CLOUD_BACKEND_URL:
        thread = threading.Thread(target=_pull_frames_from_cloud, daemon=True)
        thread.start()
        print(f"Started cloud pull thread (interval={PULL_INTERVAL}s)")


@app.on_event("shutdown")
def shutdown_event():
    """Stop the cloud pull thread on app shutdown."""
    global pull_thread_running
    pull_thread_running = False
    print("Stopped cloud pull thread")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
