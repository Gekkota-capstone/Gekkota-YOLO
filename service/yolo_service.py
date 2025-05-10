import os
import shutil
import logging
import re
from datetime import date
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from repository.yolo_repository import YoloRepository
from db.s3_utils import s3_client, S3_BUCKET
from router.model.yolo_model import YoloResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.3"))
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "train7_0510_black/weights/best.pt")
MAX_DETECTIONS = int(os.getenv("MAX_DETECTIONS", "1"))

class YoloService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = YoloRepository(db)
        self.model = self._load_yolo_model()
        self.keypoint_names = [
            "head", "neck", "Rhand", "Lhand",
            "back", "Lfoot", "Rfoot", "tail"
        ]

    def _load_yolo_model(self):
        try:
            from ultralytics import YOLO
            model = YOLO(YOLO_MODEL_PATH)
            model.to('cuda')
            logger.info(f"Successfully loaded YOLO model from {YOLO_MODEL_PATH}")
            return model
        except Exception as e:
            logger.error(f"Error loading YOLO model: {str(e)}")
            return None

    async def process_images(self, serial_number: str, request_date: date) -> YoloResponse:
        date_str = request_date.strftime("%Y%m%d")
        local_folder = f"{serial_number}_{date_str}"
        os.makedirs(local_folder, exist_ok=True)

        try:
            s3_prefix = f"opencv/{serial_number}/{date_str}/"
            downloaded_files = self._download_images_from_s3(s3_prefix, local_folder)

            if not downloaded_files:
                return YoloResponse(
                    status="warning",
                    message="No images found in S3 for the given criteria",
                    processed_images=0
                )

            processed_count = await self._process_local_images(local_folder, serial_number, request_date)

            return YoloResponse(
                status="success",
                message=f"Successfully processed {processed_count} images",
                processed_images=processed_count
            )

        except Exception as e:
            logger.error(f"Error in process_images: {str(e)}")
            raise
        finally:
            if os.path.exists(local_folder):
                shutil.rmtree(local_folder)

    def _download_images_from_s3(self, prefix: str, local_folder: str) -> List[str]:
        downloaded_files = []

        try:
            logger.info(f"S3에서 객체 리스트 요청 - 버킷: {S3_BUCKET}, 접두사: {prefix}")
            response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)

            if 'Contents' not in response:
                logger.warning(f"No objects found in S3 with prefix: {prefix}")
                return downloaded_files

            logger.info(f"S3에서 {len(response['Contents'])}개 객체 발견")

            for obj in response['Contents']:
                key = obj['Key']
                if any(key.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                    filename = os.path.basename(key)
                    local_path = os.path.join(local_folder, filename)

                    logger.info(f"다운로드 시도: {key} -> {local_path}")
                    s3_client.download_file(S3_BUCKET, key, local_path)
                    downloaded_files.append(local_path)
                    logger.info(f"다운로드 성공: {key} -> {local_path}")

                    try:
                        logger.info(f"S3 객체 삭제 시도: {key}")
                        s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
                        logger.info(f"S3 객체 삭제 성공: {key}")
                    except Exception as e:
                        logger.error(f"S3 객체 삭제 실패 ({key}): {str(e)}")

            return downloaded_files

        except Exception as e:
            logger.error(f"Error downloading from S3: {str(e)}", exc_info=True)
            raise

    async def _process_local_images(self, folder_path: str, serial_number: str, request_date: date) -> int:
        processed_count = 0
        image_files = [f for f in os.listdir(folder_path)
                       if os.path.isfile(os.path.join(folder_path, f)) and
                       any(f.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png'])]

        if not image_files:
            logger.warning(f"No image files found in folder: {folder_path}")
            return processed_count

        try:
            results = self._run_yolo_inference(folder_path)

            for result in results:
                image_filename = os.path.basename(result.path)
                timestamp_match = re.search(r"(\d{8}_\d{6})", image_filename)
                timestamp = timestamp_match.group(1) if timestamp_match else None

                yolo_result = self._format_yolo_result(result, image_filename, timestamp)
                date_str = request_date.strftime('%Y%m%d')
                image_s3_path = f"opencv/{serial_number}/{date_str}/{image_filename}"

                self.repository.create(
                    image_path=image_s3_path,
                    image_filename=image_filename,
                    yolo_result=yolo_result
                )

                processed_count += 1
                logger.info(f"Processed image: {image_filename}")

                image_path = os.path.join(folder_path, image_filename)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"Error processing images in folder {folder_path}: {str(e)}")
            raise

        return processed_count

    def _run_yolo_inference(self, folder_path: str) -> List:
        if self.model is None:
            raise Exception("YOLO model not loaded")

        try:
            results = self.model.predict(
                source=folder_path,
                conf=CONFIDENCE_THRESHOLD,
                device=0,
                max_det=MAX_DETECTIONS
            )
            return results

        except Exception as e:
            logger.error(f"YOLO inference error: {str(e)}")
            raise

    def _format_yolo_result(self, result, filename: str, timestamp: str) -> Dict[str, Any]:
        formatted_result = {
            "timestamp": timestamp,
            "boxes": [],
            "keypoints": []
        }

        if result.boxes is not None:
            for box in result.boxes:
                formatted_result["boxes"].append({
                    "xyxy": box.xyxy[0].tolist() if box.xyxy is not None else [],
                    "conf": float(box.conf[0].item()) if box.conf is not None else 0.0,
                    "cls": int(box.cls[0].item()) if box.cls is not None else -1
                })

        if result.keypoints is not None:
            for kp_set in result.keypoints:
                keypoints = []
                kps = kp_set.xy[0].tolist() if kp_set.xy is not None else []
                confs = kp_set.conf[0].tolist() if kp_set.conf is not None else []

                for i in range(len(kps)):
                    keypoint_name = self.keypoint_names[i] if i < len(self.keypoint_names) else f"kpt_{i}"
                    keypoints.append({
                        "name": keypoint_name,
                        "xy": kps[i],
                        "conf": float(confs[i]) if i < len(confs) else 0.0
                    })

                formatted_result["keypoints"].append(keypoints)

        return formatted_result
