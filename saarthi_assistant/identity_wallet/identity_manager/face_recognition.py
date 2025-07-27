from collections import deque

import numpy as np
from deepface import DeepFace
from typing import List, Optional, Dict, Any, Iterable
from enum import Enum
import cv2
import numpy as np

class FaceRecognitionModels(Enum):
    facenet = "Facenet"
    vgg_face = "VGG-Face"
    facenet_512 = "Facenet512"
    open_face = "OpenFace"

class FaceRecognitionBackends(Enum):
    opencv = "opencv"
    yolo_v8 = "yolov8"
    yolo_v11_s = "yolov11s"
    yolo_v11_n = "yolov11n"
    yolo_v11_m = "yolov11m"
    retinaface = "retinaface"


class FaceRecognitionUtility:
    model = FaceRecognitionModels.facenet.value # Facenet for accuracy and medium inference speed
    backend = FaceRecognitionBackends.retinaface.value #nano model for fast face detection
    validation_distance = 0.4 # Low cosine similarity threshold for face validation

    @classmethod
    def match_embeddings(cls, embedding1: np.ndarray, embedding2: np.ndarray) -> bool:
        """
        Compare two face embeddings to check if they match.
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            threshold: Cosine similarity threshold for matching
            
        Returns:
            True if embeddings match, False otherwise
        """
        result = DeepFace.verify(embedding1, embedding2, model_name=cls.model, detector_backend=cls.backend, distance_metric="cosine")
        return result["verified"]
    
    @classmethod
    def get_embedding(cls, image: np.ndarray) -> Dict[str, Any]:

        try:
            embedding = DeepFace.represent(image, model_name=cls.model, align=True)
            return {
                "result": True,
                "embedding": embedding,
            }
        except ValueError as e:
            print(f"Error in getting embedding: {e}")            
            return {
                "result": False,
                "error": "Face not detected in the image."
            }

    @classmethod
    def verify_embeddings(cls, frames):
        if len(frames) < 10:
            return {
                "result": False,
                "error": "At least 10 frames are required for verification."
            }

        embeddings = []
        for frame in frames:
            embedding_result = cls.get_embedding(frame)
            if not embedding_result["result"]:
                return {
                    "result": False,
                    "error": embedding_result["error"]
                }
            embeddings.append(embedding_result["embedding"][0]["embedding"])

        # Calculate cosine similarity between the first and subsequent embeddings
        first_embedding = embeddings[0]
        for i, embedding in enumerate(embeddings[1:], start=1):
            result = cls.match_embeddings(first_embedding, embedding)
            if not result:
                return {
                    "result": False,
                    "error": f"Retry capture."
                }
        return {
            "result": True,
            "embedding": first_embedding
        }

class CameraManager:
    def __init__(self, camera_id: int = 0):
        self.camera_id = camera_id
        self.capture = None

    def get_frames(self) -> Optional[deque[np.ndarray]]:
        self.capture = cv2.VideoCapture(self.camera_id)
        if not self.capture.isOpened():
            print("Camera not opened.")
            return None

        frames = deque(maxlen=10)
        while len(frames) < 10:
            ret, frame = self.capture.read()
            if not ret:
                print("Failed to capture frame from camera.")
                return None
            frames.append(frame)
        self.release()
        return frames

    def release(self):
        if self.capture and self.capture.isOpened():
            self.capture.release()
