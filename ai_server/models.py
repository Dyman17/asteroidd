from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class DetectionResult(BaseModel):
    class_name: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]

class AnalysisResponse(BaseModel):
    decision: str  # "ALLOW" or "DENY"
    detections: List[DetectionResult]
    processing_time: float
    timestamp: datetime

class CaptureRequest(BaseModel):
    device_id: Optional[str] = None
    quality: Optional[int] = 10  # 1-31, lower is better

class StatusResponse(BaseModel):
    status: str
    server_time: datetime
    model_loaded: bool
    uptime: float
