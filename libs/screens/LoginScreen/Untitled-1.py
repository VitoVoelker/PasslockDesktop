import numpy as np
import cv2 as cv2

img = cv2.imread(r"C:\\Main 01.12.2022 22_29_20.png")

cv2.rectangle(img,(1100-165-370,850-243+66),(1100-165,850-243),(0,255,0),3)
#cv2.circle(img, (1100-165,850-234), 1, (0,255,0), 3)
cv2.imwrite("my.png",img)
cv2.imshow("lalala", img)
k = cv2.waitKey(0)