# -*- coding: utf-8 -*-
"""
Created on Wed Apr 30 16:08:00 2025

@author: gnltj
"""

from shapely.geometry import Point, Polygon
import json

# 은신처 다각형 좌표
hiding_polygon_coords = [
    (923, 533), (855, 582), (934, 633), (1173, 658),
    (1187, 723), (1484, 759), (1559, 620),
    (1561, 574), (1197, 491), (930, 530)
]
hiding_zone = Polygon(hiding_polygon_coords)

# JSON 로딩
with open("detection_result_0430.json", "r") as f:
    data = json.load(f)

hide_log = []

for frame in data:
    filename = frame["filename"]
    keypoints = frame.get("keypoints", [])

    if not keypoints:
        continue

    # 중심 좌표 계산 (box 중심 또는 keypoint 평균)
    all_kps = keypoints[0]
    valid_points = [kp for kp in all_kps if kp["conf"] > 0.1]
    if not valid_points:
        continue

    # 전체 keypoints 중 신뢰도가 낮거나 좌표가 의미 없는 것 (0에 가까움)
    low_conf_count = 0
    for kp in all_kps:
        x, y = kp["xy"]
        conf = kp["conf"]
        if conf < 0.2 or (x < 10 and y < 10):  # 좌표가 (0,0)에 가까우면 무시됨
            low_conf_count += 1

    # 바운딩 박스 중심 or 주요 keypoints 중 하나라도 은신처 안에 있다면
    center_xs = [kp["xy"][0] for kp in valid_points]
    center_ys = [kp["xy"][1] for kp in valid_points]
    center = Point(np.mean(center_xs), np.mean(center_ys))

    if hiding_zone.contains(center) and low_conf_count >= 4:
        hide_log.append({
            "filename": filename,
            "low_conf_kpts": low_conf_count,
            "status": "hiding"
        })

print(f"📦 은신 상태로 판단된 프레임 수: {len(hide_log)}")
for log in hide_log[:5]:
    print(log)
