import os
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

import requests
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel


# Config
AI_URL = os.getenv("AI_URL", "").strip()
DEFAULT_DEVICE_ID = os.getenv("DEFAULT_DEVICE_ID", "esp32-cam-1").strip()
MAX_FRAME_AGE_SECONDS = float(os.getenv("MAX_FRAME_AGE_SECONDS", "7"))
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "5"))


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
latest_results: Dict[str, AnalysisResponse] = {}
lock = threading.Lock()


def _now() -> float:
    return time.time()


def _is_fresh(result: AnalysisResponse) -> bool:
    age = (datetime.now(timezone.utc) - result.timestamp).total_seconds()
    return age <= MAX_FRAME_AGE_SECONDS


def _get_ai_url() -> str:
    return ai_url_runtime or AI_URL


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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ai_url": _get_ai_url()}


@app.get("/esp_cam/ping")
def esp_cam_ping(request: Request, device_id: str = DEFAULT_DEVICE_ID) -> dict:
    client_ip = request.client.host if request.client else ""
    with lock:
        last_seen[f"esp_cam:{device_id}"] = _now()
        if client_ip:
            esp_cam_ip[device_id] = client_ip
    return {"ok": True, "device_type": "esp_cam", "device_id": device_id, "ip": client_ip}


@app.get("/esp_servo/ping")
def esp_servo_ping(request: Request, device_id: str = DEFAULT_DEVICE_ID) -> dict:
    client_ip = request.client.host if request.client else ""
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
        if ai_url:
            if not (ai_url.startswith("http://") or ai_url.startswith("https://")):
                raise HTTPException(status_code=400, detail="ai_url must start with http:// or https://")
            global ai_url_runtime
            ai_url_runtime = ai_url.strip()
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


@app.get("/esp_servo/check", response_class=PlainTextResponse)
def check(device_id: str = DEFAULT_DEVICE_ID) -> str:
    # Servo pulls a decision; server pulls the latest frame from ESP32-CAM,
    # sends it to AI, then returns ALLOW/DENY.
    try:
        with lock:
            cam_ip = esp_cam_ip.get(device_id, "")
        if not cam_ip:
            return "DENY"
        cam_url = f"http://{cam_ip}/capture"
        cam_resp = requests.get(cam_url, timeout=AI_TIMEOUT)
        cam_resp.raise_for_status()
        image_bytes = cam_resp.content
    except Exception:
        return "DENY"

    try:
        result = _forward_to_ai(image_bytes, device_id=device_id)
    except HTTPException:
        return "DENY"

    with lock:
        latest_results[device_id] = result
        last_seen[f"esp_servo:{device_id}"] = _now()
        last_seen[f"esp_cam:{device_id}"] = _now()
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
        "hybrid_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "7860")),
        reload=False,
    )
