# router/model/yolo_model.py 수정

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List, Dict, Any, Union


class YoloRequest(BaseModel):
    """YOLO 처리 요청 모델"""
    serial_number: str = Field(
        ...,
        description="장치 시리얼 번호",
        example="SFRXC12515GF00001"
    )
    target_date: date = Field(
        ...,
        description="처리할 이미지 날짜 (YYYY-MM-DD)",
        example="2025-04-21"
    )


class YoloResponse(BaseModel):
    """YOLO 처리 응답 모델"""
    status: str = Field("success", description="처리 결과 상태")
    message: str = Field("Images processed successfully", description="처리 결과 메시지")
    processed_images: int = Field(0, description="처리된 이미지 수")