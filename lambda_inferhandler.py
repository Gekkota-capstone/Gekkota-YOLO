# -*- coding: utf-8 -*-
"""
Created on Wed Apr 30 15:35:53 2025

@author: gnltj
"""

import os
import json
import pymysql
import boto3
import requests
from urllib.parse import unquote_plus
from datetime import datetime
import logging

#%%
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 환경 변수 로드
rds_host = os.environ['RDS_HOST']
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
ai_server_url = os.environ['AI_SERVER_URL']

def lambda_handler(event, context):
    logger.info(f"🔥 Lambda triggered with event: {json.dumps(event)}")

    s3_key = unquote_plus(event['Records'][0]['s3']['object']['key'])
    image_name = s3_key.split("/")[-1]
    local_image_path = f"C:/Users/gnltj/OneDrive/Desktop/study/CAP/s3_downloads/opencv/{image_name}"
    logger.info(f"📸 처리할 이미지 경로: {local_image_path}")

    try:
        response = requests.post(
            ai_server_url,
            json={"image_path": local_image_path},
            timeout=10
        )
        result = response.json()
        logger.info(f"📦 AI 결과 수신 완료: {json.dumps(result)}")
    except Exception as e:
        logger.error(f"❌ AI 서버 요청 실패: {str(e)}")
        return {"statusCode": 500, "body": f"AI 서버 요청 실패: {str(e)}"}

    # 결과가 리스트인지 확인
    if not isinstance(result, list):
        logger.error(f"❌ AI 응답 형식 오류: {result}")
        return {"statusCode": 500, "body": f"AI 응답 형식 오류: {result}"}

    try:
        conn = pymysql.connect(
            host=rds_host,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        with conn.cursor() as cursor:
            for item in result:
                file_name = item.get("filename")
                timestamp_str = item.get("timestamp")

                # timestamp 없을 경우 filename에서 추출
                if not timestamp_str:
                    try:
                        timestamp_str = file_name.replace("record_", "").replace(".jpg", "")
                    except:
                        logger.warning(f"⚠️ 타임스탬프 추출 실패: {file_name}")
                        continue

                try:
                    file_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d-%H-%M-%S")
                except Exception:
                    logger.warning(f"❌ 잘못된 타임스탬프 형식: {timestamp_str}, 건너뜀")
                    continue

                boxes = item.get("boxes", [])
                keypoints = item.get("keypoints", [])

                if not boxes or not keypoints or len(keypoints[0]) < 1:
                    logger.warning(f"⏭️ 누락된 박스/키포인트, 건너뜀: {file_name}")
                    continue

                box = boxes[0]
                kps = keypoints[0]

                values = [
                    "default", file_name, file_timestamp,
                    *box.get("xyxy", [None]*4),
                    box.get("conf", None)
                ]

                # keypoints 최대 8개 보장
                for kp in kps:
                    values.extend(kp.get("xy", [None, None]))
                    values.append(kp.get("conf", None))

                while len(kps) < 8:
                    values.extend([None, None, None])
                    kps.append({})  # dummy padding for indexing

                values.append(datetime.utcnow())  # created_at

                if len(values) != 33:
                    logger.error(f"⚠️ 값 개수 오류: {len(values)}개, 예상 33개. 값 목록: {values}")
                    continue

                sql = """
                    INSERT INTO inference_results (
                        user_id, file_name, file_timestamp,
                        bbox_x1, bbox_y1, bbox_x2, bbox_y2, bbox_conf,
                        head_x, head_y, head_conf,
                        neck_x, neck_y, neck_conf,
                        rhand_x, rhand_y, rhand_conf,
                        lhand_x, lhand_y, lhand_conf,
                        back_x, back_y, back_conf,
                        lfoot_x, lfoot_y, lfoot_conf,
                        rfoot_x, rfoot_y, rfoot_conf,
                        tail_x, tail_y, tail_conf,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, values)
                logger.info(f"✅ DB 삽입 완료: {file_name}")

            conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ RDS 저장 실패: {str(e)}")
        return {"statusCode": 500, "body": f"RDS 저장 실패: {str(e)}"}

    return {
        "statusCode": 200,
        "body": f"✅ 추론 및 DB 저장 성공: {file_name}"
    }
