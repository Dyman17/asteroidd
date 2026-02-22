from fastapi import FastAPI
import requests
import cv2
import numpy as np

app = FastAPI()

# ===== CONFIG =====
CAMERA_URL = "http://172.20.10.9/capture"
TIMEOUT = 3

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

# ===== MOCK YOLO (заглушка) =====
def yolo_detect(image):
    """
    Здесь потом подключишь YOLOv8
    Сейчас просто пример
    """
    detected_classes = ["bottle"]  # <- тест
    return detected_classes

# ===== UTILS =====
def get_camera_frame():
    r = requests.get(CAMERA_URL, timeout=TIMEOUT)
    if r.status_code != 200:
        return None

    img_array = np.frombuffer(r.content, np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return frame

# ===== ROUTES =====
@app.get("/")
def status():
    return {
        "status": "running",
        "camera": CAMERA_URL,
        "server_ip": "172.20.10.2"
    }

@app.get("/check")
def check_object():
    try:
        frame = get_camera_frame()
        if frame is None:
            return "DENY"

        detected = yolo_detect(frame)

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
            "final_result": "DENY"
        }

    detected = yolo_detect(frame)

    return {
        "camera": "ok",
        "yolo_detected": len(detected) > 0,
        "detected_classes": detected,
        "final_result": "ALLOW" if any(c in ALLOW_CLASSES for c in detected) else "DENY"
    }
