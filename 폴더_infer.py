# -*- coding: utf-8 -*-
"""
Created on Wed Apr 30 15:37:40 2025

@author: gnltj
"""

from ultralytics import YOLO
import json
import os
import re  # 타임스탬프 추출

# 모델 로드
model = YOLO("train4_saffir_epoch200/weights/best.pt")

# 이미지 폴더를 대상으로 추론
results = model.predict(
    source=r"C:\Users\gnltj\saffir\infer_img\output_images",  # 이미지 폴더 경로
    conf=0.3,
    #device=0,
    device= "cpu",
    max_det=1
)

# 키포인트 이름 정보 생성
keypoint_names = [
    "head", "neck", "Rhand", "Lhand",
    "back", "Lfoot", "Rfoot", "tail"
]

# 결과 저장용 리스트
all_results = []

for result in results:
    filename = os.path.basename(result.path)

    #  파일명에서 타임스탬프 추출 
    match = re.search(r"(\d{8}_\d{6})", filename)  # ex) 20250417_170454
    timestamp = match.group(1) if match else None

    frame_data = {
        "filename": filename,
        "timestamp": timestamp, 
        "boxes": [],
        "keypoints": []
    }

    # 바운딩 박스 정보
    if result.boxes is not None:
        for box in result.boxes:
            frame_data["boxes"].append({
                "xyxy": box.xyxy[0].tolist(),
                "conf": box.conf[0].item(),
                "cls": int(box.cls[0].item())
            })

    # 키포인트 정보
    if result.keypoints is not None:
        for kp_set in result.keypoints:
            kps = kp_set.xy[0].tolist() if kp_set.xy is not None else []
            confs = kp_set.conf[0].tolist() if kp_set.conf is not None else []

            named_keypoints = [
                {
                    "name": keypoint_names[i] if i < len(keypoint_names) else f"kpt_{i}",
                    "xy": kps[i],
                    "conf": confs[i]
                }
                for i in range(len(kps))
            ]

            frame_data["keypoints"].append(named_keypoints)

    all_results.append(frame_data)

# JSON으로 저장
with open("detection_result_0430_2.json", "w") as f:
    json.dump(all_results, f, indent=4)

print(" 결과를 detection_results_with_names.json 파일로 저장 완료")