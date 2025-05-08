#!/usr/bin/env python3
import asyncio
import os
import sys
import time
import argparse
from datetime import date, datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from db.s3_utils import s3_client, S3_BUCKET
from db.database import Base, engine


# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# 상수 설정
SERIAL_NUMBER = "SFRXC12515GF00001"
SLEEP_INTERVAL = 1  # 1초 간격

# 데이터베이스 초기화
Base.metadata.create_all(bind=engine)


def init_db():
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
            conn.commit()
    except Exception:
        pass  # 로그 제거됨


def print_env_info():
    """환경 변수 및 연결 테스트"""
    from db.database import SessionLocal

    db_url = os.getenv("DATABASE_URL")
    s3_bucket = os.getenv("S3_BUCKET_NAME")

    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception:
        pass

    try:
        s3_client.list_buckets()
        s3_client.head_bucket(Bucket=S3_BUCKET)
    except Exception:
        pass


async def process_images_for_date(target_date: date):
    """특정 날짜의 이미지 처리"""
    from db.database import SessionLocal
    from service.yolo_service import YoloService

    db: Session = None
    try:
        db = SessionLocal()
        service = YoloService(db)
        result = await service.process_images(SERIAL_NUMBER, target_date)
        return result.processed_images
    except Exception:
        return 0
    finally:
        if db:
            db.close()


async def main(date_str: str = None):
    """메인 루프"""
    print_env_info()

    if date_str:
        try: 
            # 입력 날짜 형식: YYYY-MM-DD python main.py --date 2025-04-17
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return
    else:
        target_date = date.today()

    try:
        while True:
            start_time = time.time()
            await process_images_for_date(target_date)
            sleep_time = max(0.1, 1 - (time.time() - start_time))
            await asyncio.sleep(sleep_time)
    except KeyboardInterrupt:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO 이미지 처리 스크립트")
    parser.add_argument("-d", "--date", help="처리할 날짜 (YYYY-MM-DD 형식)", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.date))
