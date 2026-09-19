import numpy as np
import cv2
import os

os.makedirs('backend/demo/samples', exist_ok=True)

# Create a blank white image
img = np.ones((400, 600, 3), dtype=np.uint8) * 255

# Draw a fake document structure
cv2.rectangle(img, (20, 20), (580, 380), (0, 0, 0), 2)
cv2.putText(img, "SENTINEL DEMO DOCUMENT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
cv2.putText(img, "Name: John Doe", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
cv2.putText(img, "ID: 1234 5678 9012", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

# Add a fake QR code box
cv2.rectangle(img, (400, 250), (550, 400), (0, 0, 0), 2)
cv2.putText(img, "QR AREA", (430, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

cv2.imwrite('backend/demo/samples/demo_document_1.jpg', img)

# Create a low-quality, blurry document to trigger high risk
img2 = img.copy()
img2 = cv2.GaussianBlur(img2, (15, 15), 0)
cv2.imwrite('backend/demo/samples/demo_document_high_risk.jpg', img2)
