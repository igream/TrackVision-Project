import cv2
import numpy as np

img = cv2.imread(r"C:\Users\Fer\Desktop\OCR Placas\datasets\car_plate_detection\images\Cars0.png")

h, w = img.shape[:2]
location = np.array([[[0, 0]], [[0, h - 1]], [[w - 1, h - 1]], [[w - 1, 0]]], dtype=np.int32)

mask = np.zeros(img.shape[:2], np.uint8)
cv2.drawContours(mask, [location], 0, 255, -1)

(y, x) = np.where(mask == 255)
(topx, topy) = (np.min(x), np.min(y))
(bottomx, bottomy) = (np.max(x), np.max(y))

cropped_color = img[topy:bottomy + 1, topx:bottomx + 1]

print("Original shape:", img.shape)
print("Cropped shape:", cropped_color.shape)
