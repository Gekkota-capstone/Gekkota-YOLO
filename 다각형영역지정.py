# -*- coding: utf-8 -*-
"""
Created on Wed Apr 30 15:55:36 2025

@author: gnltj
"""

import cv2
import numpy as np

# 경로 설정 (이미지 한 장)
image_path = "C:/Users/gnltj/saffir/infer_img/SFRXC12515GF00001_20250417_170454.jpg"
img = cv2.imread(image_path)
clone = img.copy()

# 클릭된 좌표 저장용
points = []

def click_event(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"📍 Point added: ({x}, {y})")
        cv2.circle(img, (x, y), 5, (0, 255, 0), -1)
        
        if len(points) > 1:
            cv2.line(img, points[-2], points[-1], (255, 0, 0), 2)
        cv2.imshow("Select hiding area (press Enter to finish)", img)

# 마우스 이벤트 등록
cv2.imshow("Select hiding area (press Enter to finish)", img)
cv2.setMouseCallback("Select hiding area (press Enter to finish)", click_event)

# Enter 키(13번) 누르면 종료
cv2.waitKey(0)
cv2.destroyAllWindows()

# 닫힌 다각형 형태로 연결
if len(points) > 2:
    cv2.polylines(clone, [np.array(points)], isClosed=True, color=(0, 0, 255), thickness=2)
    cv2.imshow("Final hiding area", clone)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# 저장된 좌표 출력
print("📝 최종 은신처 좌표 목록:")
for pt in points:
    print(pt)
