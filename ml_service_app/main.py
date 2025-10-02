from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import base64
import numpy as np

try:
    import cv2  # type: ignore
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

app = FastAPI(title="ML Inference Service (Placeholder)", version="1.0.0")


class DetectRequest(BaseModel):
    image_base64: str
    confidence_threshold: Optional[float] = 0.5


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ml_inference_placeholder",
        "cv2_available": CV2_AVAILABLE,
    }


def decode_image(image_base64: str) -> np.ndarray:
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]
    raw = base64.b64decode(image_base64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR) if CV2_AVAILABLE else None
    return img


@app.post("/detect")
async def detect(req: DetectRequest) -> Dict[str, Any]:
    # Placeholder detector: either returns a static tool list or very simple contour-based boxes if cv2 present
    if not req.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    tools: List[Dict[str, Any]] = []

    if CV2_AVAILABLE:
        img = decode_image(req.image_base64)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        count = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w * h < 500:  # filter tiny noise
                continue
            count += 1
            tools.append({
                "class_name": "tool_placeholder",
                "confidence": 75.0,
                "detected_quantity": 1,
                "bounding_box": {"x1": int(x), "y1": int(y), "x2": int(x + w), "y2": int(y + h)},
            })
        # collapse to one summary row with quantity
        if tools:
            tools = [{
                "class_name": "tool_placeholder",
                "confidence": 75.0,
                "detected_quantity": len(tools),
                "bounding_box": None,
            }]
    else:
        tools = [{
            "class_name": "tool_placeholder",
            "confidence": 80.0,
            "detected_quantity": 3,
            "bounding_box": None,
        }]

    return {
        "success": True,
        "results": {
            "detected_tools": tools,
            "total_detected": sum(t.get("detected_quantity", 1) for t in tools) if tools else 0,
            "processing_time": 0.0,
        }
    }


