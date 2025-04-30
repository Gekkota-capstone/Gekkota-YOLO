from datetime import date
from typing import Dict, Any
import os
from sqlalchemy.orm import Session
from repository.entity.yolo_entity import YoloResult


class YoloRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, image_path: str, image_filename: str, yolo_result: Dict[str, Any]) -> YoloResult:
        """
        Create a new YOLO result record in the database
        파일명에서 시리얼 번호와 날짜를 추출하여 저장

        Args:
            image_path: S3 경로 포함 이미지 전체 경로
            image_filename: 이미지 파일명 (시리얼번호_날짜_시간.확장자 형식)
            yolo_result: YOLO 추론 결과 (JSON 형식)

        Returns:
            생성된 YoloResult 객체
        """
        # 예: "SFRXC12515GF00001_20250417_170454.jpg" → ["SFRXC12515GF00001", "20250417", "170454"]
        filename_parts = os.path.splitext(image_filename)[0].split('_')

        # 시리얼 번호 추출
        device_serial = filename_parts[0]

        # 날짜 추출 및 Date 객체로 변환
        date_str = filename_parts[1]
        image_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))

        # 확장자 제거한 파일명만 저장 (예: "SFRXC12515GF00001_20250417_170454")
        image_stem = os.path.splitext(os.path.basename(image_path))[0]

        # DB 저장
        db_yolo_result = YoloResult(
            image=image_stem,
            device=device_serial,
            date=image_date,
            yolo_result=yolo_result
        )

        self.db.add(db_yolo_result)
        self.db.commit()
        self.db.refresh(db_yolo_result)

        return db_yolo_result
