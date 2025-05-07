from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from db.database import Base


class YoloResult(Base):
    __tablename__ = "yolo_results"
    __table_args__ = {"schema": "capstone"}

    image = Column(String(255), primary_key=True)  # 이미지 파일명 (전체 경로)
    device = Column(String(255))  # 장치 시리얼 번호 (파일명에서 추출)
    date = Column(Date)  # 날짜 (파일명에서 추출)
    yolo_result = Column(JSONB)  # YOLO 추론 결과 (boxes, keypoints 포함)

    def __repr__(self):
        return f"<YoloResult(image='{self.image}', device='{self.device}', date='{self.date}')>"