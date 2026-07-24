import cv2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("cannot open camera 0")
    exit(1)

print("camera opened successfully, press q to quit")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("slouchd camera test", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
