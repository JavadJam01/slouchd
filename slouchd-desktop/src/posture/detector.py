import os
import urllib.request
import numpy as np
import cv2
from pathlib import Path

from src.config import get_app_dir, get_resource_path

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"

class PostureDetector:
    def __init__(self):
        self.mode = None
        self.detector = None
        self.mp = None

        bundled_model_path = get_resource_path("models/pose_landmarker_lite.task")	# check bundled model path, app dir, or local assets
        assets_model_path = get_resource_path("assets/models/pose_landmarker_lite.task")
        app_model_path = get_app_dir() / "pose_landmarker_lite.task"

        if bundled_model_path.exists():
            model_path = bundled_model_path
        elif assets_model_path.exists():
            model_path = assets_model_path
        elif app_model_path.exists():
            model_path = app_model_path
        else:
            model_path = app_model_path
            part_path = model_path.with_suffix(".task.part")
            try:
                model_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"downloading model to {model_path}...")
                urllib.request.urlretrieve(MODEL_URL, str(part_path))
                if part_path.exists() and part_path.stat().st_size > 1024:
                    if model_path.exists():
                        model_path.unlink()
                    part_path.rename(model_path)
            except Exception as dl_err:
                print(f"model download failed: {dl_err}")
                if part_path.exists():
                    try:
                        part_path.unlink()
                    except Exception:
                        pass

        try:	# try initing mediapipe tasks api
            import mediapipe as mp
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision

            if model_path.exists():
                base_options = mp_tasks.BaseOptions(model_asset_path=str(model_path))
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    num_poses=1,
                    min_pose_detection_confidence=0.5,
                    min_pose_presence_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.detector = vision.PoseLandmarker.create_from_options(options)
                self.mp = mp
                self.mode = "TASKS"
                print("mediapipe tasks initialized")
            else:
                print(f"model not found: {model_path}")
        except Exception as e:
            print(f"tasks api error: {e}")
            try:	# fallback to legacy mediapipe solutions
                import mediapipe as mp
                if hasattr(mp, "solutions") and hasattr(mp.solutions, "pose"):
                    self.mp_pose = mp.solutions.pose
                    self.detector = self.mp_pose.Pose(
                        static_image_mode=False,
                        model_complexity=0,	# model complexity 0 for low cpu
                        smooth_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    self.mp = mp
                    self.mode = "SOLUTIONS"
                    print("mediapipe solutions initialized")
            except Exception as e2:
                print(f"legacy solutions error: {e2}")

        self.face_cascade = None	# opencv haar cascade fallback for face detection if pose detector failed
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            pass

    def _is_valid_pose_geometry(self, nose, l_ear, r_ear, l_shoulder, r_shoulder, shoulder_width, inter_ear_dist, ear_shoulder_dist, nose_shoulder_dist) -> bool:
        """validate pose geometry to reject false background detections"""
        # head must be vertically above shoulders
        if ear_shoulder_dist <= 0.015 or nose_shoulder_dist <= 0.015:
            return False

        # nose must be above shoulders midpoint
        shoulders_y = (l_shoulder[1] + r_shoulder[1]) / 2.0
        if nose[1] >= shoulders_y:
            return False

        # minimum shoulder width for seated user
        if shoulder_width < 0.14:
            return False

        # minimum distance between ears
        if inter_ear_dist < 0.035:
            return False

        # head cannot be at the bottom edge
        if nose[1] > 0.85:
            return False

        return True

    def process_frame(self, frame_bgr, annotate: bool = True):
        """process bgr frame and return posture metrics."""
        h, w, _ = frame_bgr.shape
        
        if w > 640 or h > 480:	# downscale large frames to save cpu
            scale = min(640.0 / w, 480.0 / h)
            new_w, new_h = int(w * scale), int(h * scale)
            new_w = new_w - (new_w % 2)
            new_h = new_h - (new_h % 2)
            frame_det = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            frame_det = frame_bgr
            new_w, new_h = w, h

        annotated_frame = np.ascontiguousarray(frame_det.copy()) if annotate else None

        if self.mode == "TASKS" and self.detector:
            try:
                frame_rgb = cv2.cvtColor(frame_det, cv2.COLOR_BGR2RGB)
                mp_image = self.mp.Image(
                    image_format=self.mp.ImageFormat.SRGB,
                    data=frame_rgb
                )
                results = self.detector.detect(mp_image)

                if not results.pose_landmarks or len(results.pose_landmarks) == 0:
                    return None, annotated_frame

                landmarks = results.pose_landmarks[0]

                nose = np.array([landmarks[0].x, landmarks[0].y, landmarks[0].z])	# 0: nose, 7: left ear, 8: right ear, 11: left shoulder, 12: right shoulder
                l_ear = np.array([landmarks[7].x, landmarks[7].y, landmarks[7].z])
                r_ear = np.array([landmarks[8].x, landmarks[8].y, landmarks[8].z])
                l_shoulder = np.array([landmarks[11].x, landmarks[11].y, landmarks[11].z])
                r_shoulder = np.array([landmarks[12].x, landmarks[12].y, landmarks[12].z])

                def _extract_vis(lm):
                    v = getattr(lm, 'visibility', None)
                    if v is None:
                        v = getattr(lm, 'presence', 1.0)
                    return float(v) if v is not None else 1.0

                vis_scores = [
                    _extract_vis(landmarks[0]),
                    _extract_vis(landmarks[7]),
                    _extract_vis(landmarks[8]),
                    _extract_vis(landmarks[11]),
                    _extract_vis(landmarks[12]),
                ]
                min_visibility = float(min(vis_scores))

                ears_midpoint = (l_ear + r_ear) / 2.0
                shoulders_midpoint = (l_shoulder + r_shoulder) / 2.0

                ear_shoulder_dist = shoulders_midpoint[1] - ears_midpoint[1]
                nose_shoulder_dist = shoulders_midpoint[1] - nose[1]
                shoulder_width = float(np.linalg.norm(l_shoulder[:2] - r_shoulder[:2]))
                if shoulder_width < 1e-4:
                    shoulder_width = 1e-4

                inter_ear_dist = float(np.linalg.norm(l_ear[:2] - r_ear[:2]))
                if not self._is_valid_pose_geometry(nose, l_ear, r_ear, l_shoulder, r_shoulder, shoulder_width, inter_ear_dist, ear_shoulder_dist, nose_shoulder_dist):
                    return None, annotated_frame

                normalized_ear_shoulder = ear_shoulder_dist / shoulder_width
                normalized_nose_shoulder = nose_shoulder_dist / shoulder_width

                metrics = {
                    "ear_shoulder_dist": float(ear_shoulder_dist),
                    "nose_shoulder_dist": float(nose_shoulder_dist),
                    "normalized_ear_shoulder": float(normalized_ear_shoulder),
                    "normalized_nose_shoulder": float(normalized_nose_shoulder),
                    "shoulder_width": float(shoulder_width),
                    "inter_ear_dist": float(inter_ear_dist),
                    "visibility": float(min_visibility),
                }

                if annotate and annotated_frame is not None:
                    points = [	# draw skeleton points and lines
                        (int(nose[0]*new_w), int(nose[1]*new_h)),
                        (int(l_ear[0]*new_w), int(l_ear[1]*new_h)),
                        (int(r_ear[0]*new_w), int(r_ear[1]*new_h)),
                        (int(l_shoulder[0]*new_w), int(l_shoulder[1]*new_h)),
                        (int(r_shoulder[0]*new_w), int(r_shoulder[1]*new_h)),
                    ]
                    cv2.line(annotated_frame, points[1], points[3], (0, 255, 0), 2)	# draw ear-to-shoulder lines
                    cv2.line(annotated_frame, points[2], points[4], (0, 255, 0), 2)
                    cv2.line(annotated_frame, points[3], points[4], (255, 200, 0), 3)

                    for pt in points:
                        cv2.circle(annotated_frame, pt, 6, (0, 165, 255), -1)

                return metrics, annotated_frame

            except Exception as e:
                print(f"tasks frame error: {e}")
                return self._process_opencv_fallback(frame_det, annotated_frame, annotate=annotate)

        elif self.mode == "SOLUTIONS" and self.detector:
            try:	# legacy solutions processing
                frame_rgb = cv2.cvtColor(frame_det, cv2.COLOR_BGR2RGB)
                results = self.detector.process(frame_rgb)
                if not results.pose_landmarks:
                    return None, annotated_frame

                landmarks = results.pose_landmarks.landmark
                nose = np.array([landmarks[0].x, landmarks[0].y, landmarks[0].z])
                l_ear = np.array([landmarks[7].x, landmarks[7].y, landmarks[7].z])
                r_ear = np.array([landmarks[8].x, landmarks[8].y, landmarks[8].z])
                l_shoulder = np.array([landmarks[11].x, landmarks[11].y, landmarks[11].z])
                r_shoulder = np.array([landmarks[12].x, landmarks[12].y, landmarks[12].z])

                def _extract_vis(lm):
                    v = getattr(lm, 'visibility', None)
                    if v is None:
                        v = getattr(lm, 'presence', 1.0)
                    return float(v) if v is not None else 1.0

                vis_scores = [
                    _extract_vis(landmarks[0]),
                    _extract_vis(landmarks[7]),
                    _extract_vis(landmarks[8]),
                    _extract_vis(landmarks[11]),
                    _extract_vis(landmarks[12]),
                ]
                min_visibility = float(min(vis_scores))

                ears_midpoint = (l_ear + r_ear) / 2.0
                shoulders_midpoint = (l_shoulder + r_shoulder) / 2.0

                ear_shoulder_dist = shoulders_midpoint[1] - ears_midpoint[1]
                nose_shoulder_dist = shoulders_midpoint[1] - nose[1]
                shoulder_width = max(1e-4, float(np.linalg.norm(l_shoulder[:2] - r_shoulder[:2])))
                inter_ear_dist = float(np.linalg.norm(l_ear[:2] - r_ear[:2]))
                if not self._is_valid_pose_geometry(nose, l_ear, r_ear, l_shoulder, r_shoulder, shoulder_width, inter_ear_dist, ear_shoulder_dist, nose_shoulder_dist):
                    return None, annotated_frame

                normalized_ear_shoulder = ear_shoulder_dist / shoulder_width
                normalized_nose_shoulder = nose_shoulder_dist / shoulder_width

                metrics = {
                    "ear_shoulder_dist": float(ear_shoulder_dist),
                    "nose_shoulder_dist": float(nose_shoulder_dist),
                    "normalized_ear_shoulder": float(normalized_ear_shoulder),
                    "normalized_nose_shoulder": float(normalized_nose_shoulder),
                    "shoulder_width": float(shoulder_width),
                    "inter_ear_dist": float(inter_ear_dist),
                    "visibility": float(min_visibility),
                }

                if annotate and annotated_frame is not None and self.mp:
                    self.mp.solutions.drawing_utils.draw_landmarks(
                        annotated_frame,
                        results.pose_landmarks,
                        self.mp.solutions.pose.POSE_CONNECTIONS
                    )
                return metrics, annotated_frame
            except Exception as e:
                print(f"solutions frame error: {e}")
                return self._process_opencv_fallback(frame_det, annotated_frame, annotate=annotate)

        return self._process_opencv_fallback(frame_det, annotated_frame, annotate=annotate)

    def _process_opencv_fallback(self, frame_bgr, annotated_frame, annotate: bool = True):
        """fallback face detection using opencv haar when pose failed"""
        if not self.face_cascade:
            return None, annotated_frame

        try:
            h, w, _ = frame_bgr.shape
            scale = 320.0 / max(w, 1)
            small_w, small_h = int(w * scale), int(h * scale)
            small_bgr = cv2.resize(frame_bgr, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
            gray = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(24, 24))

            if len(faces) == 0:
                return None, annotated_frame

            (sx, sy, sw, sh) = faces[0]
            x, y, w_box, h_box = int(sx / scale), int(sy / scale), int(sw / scale), int(sh / scale)
            if annotate and annotated_frame is not None:
                cv2.rectangle(annotated_frame, (x, y), (x + w_box, y + h_box), (255, 100, 0), 2)
            
            frame_h, frame_w, _ = frame_bgr.shape
            
            norm_face_h = h_box / float(frame_h)	# approximations compatible with pose landmark proportions
            norm_face_w = w_box / float(frame_w)
            
            estimated_shoulder_width = max(1e-4, norm_face_w * 1.8)	# an average neck/shoulder span is ~1.8x face width and ear-to-shoulder is ~1.2x face height
            estimated_ear_shoulder_dist = norm_face_h * 1.2
            estimated_inter_ear_dist = norm_face_w * 0.75
            normalized_ear_shoulder = estimated_ear_shoulder_dist / estimated_shoulder_width

            metrics = {
                "ear_shoulder_dist": float(estimated_ear_shoulder_dist),
                "nose_shoulder_dist": float(norm_face_h * 1.4),
                "normalized_ear_shoulder": float(normalized_ear_shoulder),
                "normalized_nose_shoulder": float((norm_face_h * 1.4) / estimated_shoulder_width),
                "shoulder_width": float(estimated_shoulder_width),
                "inter_ear_dist": float(estimated_inter_ear_dist),
                "visibility": 0.5,
                "is_fallback": True
            }
            return metrics, annotated_frame
        except Exception:
            return None, annotated_frame

    def evaluate_slouch(self, metrics, baseline, sensitivity=1.0):
        if not metrics or not baseline or not baseline.get("calibrated"):
            return False, 0.0

        if metrics.get("visibility", 1.0) < 0.35:	# ignore low confidence poses or occluded ones
            return False, 0.0

        # reject detections much smaller than calibrated shoulders
        base_w = baseline.get("shoulder_width", 0.0)
        if base_w > 0.1 and metrics.get("shoulder_width", 0.0) < base_w * 0.35:
            return False, 0.0

        base_norm_dist = baseline.get("normalized_ear_shoulder", 0.0)
        curr_norm_dist = metrics.get("normalized_ear_shoulder", 0.0)

        if base_norm_dist <= 0:
            return False, 0.0

        drop = (base_norm_dist - curr_norm_dist) / base_norm_dist	# vertical neck drop (head collapsing down toward shoulders)

        base_ear_dist = baseline.get("inter_ear_dist", 1.0)	# distance from screen change
        curr_ear_dist = metrics.get("inter_ear_dist", 1.0)
        lean_forward_ratio = (curr_ear_dist - base_ear_dist) / base_ear_dist if base_ear_dist > 0 else 0

        if drop > 0:	# posture scoring: true slouch drops vertical neck alignment (drop > 0)
            score = (drop * 1.1) + (max(0.0, lean_forward_ratio) * 0.4)
        else:
            score = max(0.0, lean_forward_ratio - 0.35) * 0.4	# sitting tall, only flag if extreme forward head protrusion ( >35% )

        threshold = 0.15 / max(0.2, sensitivity)

        is_slouching = score >= threshold
        slouch_ratio = float(np.clip(score / max(1e-4, threshold * 1.5), 0.0, 1.0))

        return is_slouching, slouch_ratio

    def close(self):
        if self.detector and hasattr(self.detector, 'close'):
            try:
                self.detector.close()
            except Exception:
                pass
