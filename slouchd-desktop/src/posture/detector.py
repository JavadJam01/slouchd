import cv2
import numpy as np
import mediapipe as mp

class PostureDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.detector = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def process_frame(self, frame_bgr, annotate: bool = True):
        h, w, _ = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.detector.process(frame_rgb)
        if not results.pose_landmarks:
            return None, frame_bgr

        landmarks = results.pose_landmarks.landmark
        l_ear = np.array([landmarks[7].x, landmarks[7].y])
        r_ear = np.array([landmarks[8].x, landmarks[8].y])
        l_shoulder = np.array([landmarks[11].x, landmarks[11].y])
        r_shoulder = np.array([landmarks[12].x, landmarks[12].y])

        ears_mid = (l_ear + r_ear) / 2.0
        shoulders_mid = (l_shoulder + r_shoulder) / 2.0
        ear_shoulder_dist = shoulders_mid[1] - ears_mid[1]
        shoulder_width = float(np.linalg.norm(l_shoulder - r_shoulder))
        if shoulder_width < 1e-4:
            shoulder_width = 1e-4

        normalized_ear_shoulder = ear_shoulder_dist / shoulder_width

        metrics = {
            "ear_shoulder_dist": float(ear_shoulder_dist),
            "shoulder_width": float(shoulder_width),
            "normalized_ear_shoulder": float(normalized_ear_shoulder),
        }
        return metrics, frame_bgr
