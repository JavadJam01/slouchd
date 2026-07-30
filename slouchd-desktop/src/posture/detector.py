import cv2
import numpy as np
import mediapipe as mp
import os

class PostureDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.detector = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.face_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            pass

    def process_frame(self, frame_bgr, annotate: bool = True):
        h, w, _ = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.detector.process(frame_rgb)
        if not results.pose_landmarks:
            return self._process_opencv_fallback(frame_bgr)

        landmarks = results.pose_landmarks.landmark
        nose = np.array([landmarks[0].x, landmarks[0].y])
        l_ear = np.array([landmarks[7].x, landmarks[7].y])
        r_ear = np.array([landmarks[8].x, landmarks[8].y])
        l_shoulder = np.array([landmarks[11].x, landmarks[11].y])
        r_shoulder = np.array([landmarks[12].x, landmarks[12].y])

        ears_mid = (l_ear + r_ear) / 2.0
        shoulders_mid = (l_shoulder + r_shoulder) / 2.0
        ear_shoulder_dist = shoulders_mid[1] - ears_mid[1]
        nose_shoulder_dist = shoulders_mid[1] - nose[1]
        shoulder_width = max(1e-4, float(np.linalg.norm(l_shoulder - r_shoulder)))
        inter_ear_dist = float(np.linalg.norm(l_ear - r_ear))
        normalized_ear_shoulder = ear_shoulder_dist / shoulder_width

        metrics = {
            "ear_shoulder_dist": float(ear_shoulder_dist),
            "nose_shoulder_dist": float(nose_shoulder_dist),
            "shoulder_width": float(shoulder_width),
            "inter_ear_dist": float(inter_ear_dist),
            "normalized_ear_shoulder": float(normalized_ear_shoulder),
            "visibility": 1.0
        }
        return metrics, frame_bgr

    def _process_opencv_fallback(self, frame_bgr):
        if not self.face_cascade:
            return None, frame_bgr
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        if len(faces) == 0:
            return None, frame_bgr
        (sx, sy, sw, sh) = faces[0]
        frame_h, frame_w, _ = frame_bgr.shape
        norm_face_h = sh / float(frame_h)
        norm_face_w = sw / float(frame_w)
        estimated_shoulder_width = max(1e-4, norm_face_w * 1.8)
        estimated_ear_shoulder_dist = norm_face_h * 1.2
        return {
            "ear_shoulder_dist": float(estimated_ear_shoulder_dist),
            "shoulder_width": float(estimated_shoulder_width),
            "inter_ear_dist": float(norm_face_w * 0.75),
            "normalized_ear_shoulder": float(estimated_ear_shoulder_dist / estimated_shoulder_width),
            "visibility": 0.5,
            "is_fallback": True
        }, frame_bgr
