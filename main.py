#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
import argparse
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from db.s3_utils import s3_client, S3_BUCKET
from db.database import Base, engine

# 프로젝트 루트 경로를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 좀 더 자세한 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yolo_processor.log')
    ]
)
logger = logging.getLogger(__name__)

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# 환경변수 로드
load_dotenv()



# 데이터베이스 스키마 및 테이블 생성 함수
def init_db():
    try:
        logger.info("데이터베이스 초기화 시작...")

        # capstone 스키마 생성 (없는 경우)
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
            conn.commit()
            logger.info("capstone 스키마 확인 완료")

        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류 발생: {str(e)}", exc_info=True)


# 데이터베이스 초기화 실행
init_db()

# 상수 설정
SERIAL_NUMBER = "SFRXC12515GF00001"  # 고정된 시리얼 번호
SLEEP_INTERVAL = 1  # 고정값 1초


# 현재 환경 정보 출력
def print_env_info():
    """현재 환경 설정 정보를 로그로 출력"""
    logger.info("----- 환경 설정 정보 -----")
    logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    logger.info(f"S3_BUCKET_NAME: {os.getenv('S3_BUCKET_NAME', 'Not set')}")
    logger.info(f"AWS_REGION: {os.getenv('AWS_REGION', 'Not set')}")
    logger.info(f"AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID', 'Not set')[:4]}... (일부만 표시)")
    logger.info(f"시리얼 번호: {SERIAL_NUMBER}")
    logger.info("------------------------")

    # 데이터베이스 연결 테스트
    try:
        from db.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        logger.info("데이터베이스 연결 성공")
        db.close()
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {str(e)}")

    # S3 연결 테스트
    try:
        from db.s3_utils import s3_client, S3_BUCKET
        response = s3_client.list_buckets()
        logger.info(f"S3 연결 성공. 버킷 목록: {[bucket['Name'] for bucket in response['Buckets']]}")

        # 대상 버킷 접근 테스트
        s3_client.head_bucket(Bucket=S3_BUCKET)
        logger.info(f"S3 버킷 '{S3_BUCKET}' 접근 성공")

    except Exception as e:
        logger.error(f"S3 연결 테스트 실패: {str(e)}")


async def process_images_for_date(target_date: date):
    """특정 날짜의 이미지를 처리하는 함수"""
    logger.info(f"===== 이미지 처리 시작 =====")
    logger.info(f"대상: {SERIAL_NUMBER} 장치의 {target_date.strftime('%Y-%m-%d')} 날짜 이미지")

    db = None
    try:
        # 필요한 모듈 임포트
        from db.database import SessionLocal
        from service.yolo_service import YoloService

        # 데이터베이스 세션 생성
        db = SessionLocal()
        logger.info("데이터베이스 세션 생성 완료")

        # YOLO 서비스 초기화
        logger.info("YOLO 서비스 초기화 중...")
        service = YoloService(db)
        logger.info("YOLO 서비스 초기화 완료")

        # 이미지 처리 요청
        logger.info("이미지 처리 요청 시작...")
        result = await service.process_images(SERIAL_NUMBER, target_date)
        logger.info(f"이미지 처리 완료: 상태={result.status}, 메시지={result.message}, 처리된 이미지={result.processed_images}")

        return result.processed_images

    except Exception as e:
        logger.error(f"이미지 처리 중 오류 발생: {str(e)}", exc_info=True)
        return 0
    finally:
        if db:
            db.close()
            logger.info("데이터베이스 세션 닫음")
        logger.info("===== 이미지 처리 종료 =====")


async def main(date_str: str = None):
    """메인 함수: 지정된 날짜 또는 오늘 날짜의 이미지를 계속 처리"""

    # 현재 환경 정보 출력
    print_env_info()

    # 날짜 설정
    if date_str:
        try:
            # 입력 날짜 형식: YYYY-MM-DD python main.py --date 2025-04-17
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"잘못된 날짜 형식: {date_str}. 'YYYY-MM-DD' 형식을 사용하세요.")
            return
    else:
        # 날짜가 지정되지 않으면 오늘 날짜 사용
        target_date = date.today()

    logger.info(f"처리 시작: 시리얼 번호={SERIAL_NUMBER}, 날짜={target_date.strftime('%Y-%m-%d')}")
    logger.info(f"간격: 1초마다 실행")

    try:
        while True:
            start_time = time.time()

            # 이미지 처리 실행
            processed_count = await process_images_for_date(target_date)

            # 처리 결과 로깅
            if processed_count > 0:
                logger.info(f"{processed_count}개 이미지 처리 완료")
            else:
                logger.info(f"처리할 새 이미지 없음 ({target_date.strftime('%Y-%m-%d')})")

            # 다음 실행까지 정확히 1초 대기
            execution_time = time.time() - start_time
            sleep_time = max(0.1, 1 - execution_time)  # 최소 0.1초 대기, 최대 1초
            logger.info(f"다음 실행까지 {sleep_time:.1f}초 대기")
            await asyncio.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("사용자에 의해 프로그램 종료")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}", exc_info=True)


if __name__ == "__main__":
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description="YOLO 이미지 처리 스크립트")
    parser.add_argument("-d", "--date", help="처리할 날짜 (YYYY-MM-DD 형식)", default=None)
    args = parser.parse_args()

    # 비동기 메인 함수 실행
    asyncio.run(main(args.date))