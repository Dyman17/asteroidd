import os
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

import io
import requests
import numpy as np
from PIL import Image
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel


# Config
AI_URL = os.getenv("AI_URL", "").strip()
DEFAULT_DEVICE_ID = os.getenv("DEFAULT_DEVICE_ID", "esp32-cam-1").strip()
MAX_FRAME_AGE_SECONDS = float(os.getenv("MAX_FRAME_AGE_SECONDS", "7"))
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "5"))
AI_PORT = os.getenv("AI_PORT", "8000").strip()
AI_PATH = os.getenv("AI_PATH", "/analyze_bytes").strip()
CAM_WIDTH = int(os.getenv("CAM_WIDTH", "320"))
CAM_HEIGHT = int(os.getenv("CAM_HEIGHT", "240"))


class AnalysisResponse(BaseModel):
    decision: str
    detections: list
    processing_time: float
    timestamp: datetime
    device_id: str
    source: str


app = FastAPI(
    title="Hybrid Relay Server",
    description="ESP32-CAM -> relay -> AI laptop -> relay -> ESP32-Servo",
    version="1.0.0",
)


last_seen: Dict[str, float] = {}
ai_url_runtime: Optional[str] = None
esp_cam_ip: Dict[str, str] = {}
latest_cam_device_id: Optional[str] = None
latest_results: Dict[str, AnalysisResponse] = {}
latest_raw_frames: Dict[str, bytes] = {}
latest_raw_meta: Dict[str, dict] = {}
lock = threading.Lock()


def _now() -> float:
    return time.time()


def _is_fresh(result: AnalysisResponse) -> bool:
    age = (datetime.now(timezone.utc) - result.timestamp).total_seconds()
    return age <= MAX_FRAME_AGE_SECONDS


def _get_ai_url() -> str:
    return ai_url_runtime or AI_URL


def _build_ai_url_from_ip(ip: str) -> str:
    if not ip:
        return ""
    return f"http://{ip}:{AI_PORT}{AI_PATH}"


def _forward_to_ai(image_bytes: bytes, device_id: str) -> AnalysisResponse:
    ai_url = _get_ai_url()
    if not ai_url:
        raise HTTPException(status_code=500, detail="AI URL is not configured")
    try:
        resp = requests.post(
            ai_url,
            data=image_bytes,
            headers={"Content-Type": "image/jpeg"},
            timeout=AI_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI error: {exc}") from exc

    return AnalysisResponse(
        decision=str(payload.get("decision", "DENY")),
        detections=payload.get("detections", []),
        processing_time=float(payload.get("processing_time", 0.0)),
        timestamp=datetime.now(timezone.utc),
        device_id=device_id,
        source="ai_http",
    )


def _rgb565_to_jpeg(raw: bytes, width: int, height: int) -> bytes:
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
    rgb = np.stack([r, g, b], axis=-1)
    img = Image.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ai_url": _get_ai_url()}


@app.get("/esp_cam/ping")
def esp_cam_ping(request: Request, device_id: str = DEFAULT_DEVICE_ID) -> dict:
    client_ip = request.client.host if request.client else ""
    if not device_id or device_id.lower() == "auto":
        device_id = client_ip or DEFAULT_DEVICE_ID
    with lock:
        last_seen[f"esp_cam:{device_id}"] = _now()
        if client_ip:
            esp_cam_ip[device_id] = client_ip
            global latest_cam_device_id
            latest_cam_device_id = device_id
    return {"ok": True, "device_type": "esp_cam", "device_id": device_id, "ip": client_ip}


@app.get("/esp_servo/ping")
def esp_servo_ping(request: Request, device_id: str = DEFAULT_DEVICE_ID) -> dict:
    client_ip = request.client.host if request.client else ""
    if not device_id or device_id.lower() == "auto":
        device_id = client_ip or DEFAULT_DEVICE_ID
    with lock:
        last_seen[f"esp_servo:{device_id}"] = _now()
    return {"ok": True, "device_type": "esp_servo", "device_id": device_id, "ip": client_ip}


@app.get("/ai/ping")
def ai_ping(
    request: Request,
    device_id: str = DEFAULT_DEVICE_ID,
    ai_url: Optional[str] = None,
) -> dict:
    client_ip = request.client.host if request.client else ""
    with lock:
        last_seen[f"ai_laptop:{device_id}"] = _now()
        global ai_url_runtime
        if ai_url:
            if not (ai_url.startswith("http://") or ai_url.startswith("https://")):
                raise HTTPException(status_code=400, detail="ai_url must start with http:// or https://")
            ai_url_runtime = ai_url.strip()
        else:
            auto_url = _build_ai_url_from_ip(client_ip)
            if auto_url:
                ai_url_runtime = auto_url
    return {
        "ok": True,
        "device_type": "ai_laptop",
        "device_id": device_id,
        "ip": client_ip,
        "ai_url": _get_ai_url(),
    }


@app.post("/esp_cam/ingest", response_model=AnalysisResponse)
async def ingest_frame(
    request: Request,
    x_device_id: Optional[str] = Header(default=None),
) -> AnalysisResponse:
    """
    Deprecated for current scheme. Kept for compatibility.
    """
    device_id = (x_device_id or DEFAULT_DEVICE_ID).strip()
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")

    result = _forward_to_ai(body, device_id=device_id)
    with lock:
        latest_results[device_id] = result
        last_seen[f"esp_cam:{device_id}"] = _now()
    return result


@app.post("/esp_cam/frame")
async def ingest_raw_frame(
    request: Request,
    x_device_id: Optional[str] = Header(default=None),
    x_width: Optional[str] = Header(default=None),
    x_height: Optional[str] = Header(default=None),
    x_format: Optional[str] = Header(default=None),
) -> dict:
    device_id = (x_device_id or DEFAULT_DEVICE_ID).strip()
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty request body")

    width = int(x_width) if x_width else CAM_WIDTH
    height = int(x_height) if x_height else CAM_HEIGHT
    fmt = (x_format or "RGB565").upper()

    with lock:
        latest_raw_frames[device_id] = raw
        latest_raw_meta[device_id] = {"width": width, "height": height, "format": fmt}
        last_seen[f"esp_cam:{device_id}"] = _now()
        global latest_cam_device_id
        latest_cam_device_id = device_id

    return {"ok": True, "device_id": device_id, "width": width, "height": height, "format": fmt}


@app.get("/esp_servo/check", response_class=PlainTextResponse)
def check(device_id: str = DEFAULT_DEVICE_ID) -> str:
    # Servo pulls a decision; server pulls the latest frame from ESP32-CAM,
    # sends it to AI, then returns ALLOW/DENY.
    try:
        with lock:
            lookup_id = device_id
            if not lookup_id or lookup_id.lower() == "auto":
                lookup_id = latest_cam_device_id or DEFAULT_DEVICE_ID
            raw = latest_raw_frames.get(lookup_id)
            meta = latest_raw_meta.get(lookup_id, {})
        if not raw:
            return "DENY"
        if meta.get("format", "RGB565").upper() != "RGB565":
            return "DENY"
        image_bytes = _rgb565_to_jpeg(raw, int(meta.get("width", CAM_WIDTH)), int(meta.get("height", CAM_HEIGHT)))
    except Exception:
        return "DENY"

    try:
        result = _forward_to_ai(image_bytes, device_id=device_id)
    except HTTPException:
        return "DENY"

    with lock:
        latest_results[lookup_id] = result
        last_seen[f"esp_servo:{device_id}"] = _now()
        last_seen[f"esp_cam:{lookup_id}"] = _now()
    return result.decision


@app.get("/ai/latest", response_model=AnalysisResponse)
def latest(device_id: str = DEFAULT_DEVICE_ID) -> AnalysisResponse:
    with lock:
        result = latest_results.get(device_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No result yet")
    return result


@app.post("/ai/result", response_model=AnalysisResponse)
async def ai_result(request: Request) -> AnalysisResponse:
    """
    Optional: AI laptop can push its own result here.
    Body must be JSON with at least decision, detections, processing_time, device_id.
    """
    payload = await request.json()
    device_id = str(payload.get("device_id", DEFAULT_DEVICE_ID))
    result = AnalysisResponse(
        decision=str(payload.get("decision", "DENY")),
        detections=payload.get("detections", []),
        processing_time=float(payload.get("processing_time", 0.0)),
        timestamp=datetime.now(timezone.utc),
        device_id=device_id,
        source="ai_push",
    )
    with lock:
        latest_results[device_id] = result
        last_seen[f"ai_laptop:{device_id}"] = _now()
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "7860")),
        reload=False,
    )
