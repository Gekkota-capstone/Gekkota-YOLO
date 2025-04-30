from fastapi import FastAPI, status
import logging
from router import yolo_router
from db.database import Base, engine
import uvicorn

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# FastAPI 앱 생성
app = FastAPI(
    title="DIREP YOLO API",
    description="YOLO 객체 감지 결과를 처리하고 저장하는 API",
    version="1.0.0",
)

# 라우터 등록
app.include_router(yolo_router.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)