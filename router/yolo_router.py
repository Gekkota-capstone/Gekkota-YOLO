# POST 요청 하나 열어두기 / 특별한 token 인증 없음
# request, device serial number, date
# response 로 200ok 만 취급
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from router.model.yolo_model import YoloRequest, YoloResponse
from service.yolo_service import YoloService
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 라우터 설정
router = APIRouter(
    prefix="/yolo",
    tags=["yolo"],
    responses={
        status.HTTP_200_OK: {"description": "Success"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"}
    },
)


@router.post("/process", response_model=YoloResponse, status_code=status.HTTP_200_OK)
async def process_images(request: YoloRequest, db: Session = Depends(get_db)):
    """
    S3에서 이미지를 가져와 YOLO 모델로 처리하고 결과를 DB에 저장

    - **serial_number**: 장치 시리얼 번호
    - **date**: 날짜 (YYYY-MM-DD)

    Returns:
        200 OK와 처리 상태 정보
    """
    try:
        # 서비스 생성 및 이미지 처리 요청
        service = YoloService(db)
        result = await service.process_images(request.serial_number, request.target_date)

        # 성공 응답 반환
        return YoloResponse(
            status="success",
            message="Images processed successfully",
            processed_images=result.processed_images
        )

    except Exception as e:
        # 오류 로깅
        logger.error(f"Error processing images: {str(e)}")

        # 클라이언트에게 500 에러와 함께 에러 메시지 반환
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process images"
        )