"""Service managing server storage for professional athlete and personal user videos."""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2

from services.camera import CameraService
from services.db import db
from services.settings import BASE_DIR

logger = logging.getLogger(__name__)

STORAGE_DIR = BASE_DIR / "server_storage"
PRO_DIR = STORAGE_DIR / "pro"
PERSONAL_DIR = STORAGE_DIR / "personal"
THUMBNAIL_DIR = STORAGE_DIR / "thumbnails"


class VideoService:
    """Manages server video storage, upload permissions, and library retrieval."""

    def __init__(self) -> None:
        self._ensure_storage_dirs()

    def _ensure_storage_dirs(self) -> None:
        """Creates storage directories if not existing."""
        for d in [STORAGE_DIR, PRO_DIR, PERSONAL_DIR, THUMBNAIL_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def generate_thumbnail(self, video_path: str, output_path: str) -> bool:
        """Extracts a middle video frame as a JPEG thumbnail."""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            target_frame = max(0, total // 3)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            success, frame = cap.read()
            cap.release()
            if success and frame is not None:
                # Resize thumbnail to max 320x180
                h, w = frame.shape[:2]
                thumb_w = 320
                thumb_h = int(h * (thumb_w / w))
                thumb = cv2.resize(frame, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
                cv2.imwrite(output_path, thumb)
                return True
        except Exception as e:
            logger.warning("Failed to generate thumbnail for %s: %s", video_path, e)
        return False

    def seed_default_pro_videos(self) -> None:
        """Disabled: only genuine locally uploaded athlete reference videos are maintained."""
        pass

    def upload_video(
        self,
        source_file_path: str,
        title: str,
        category: str = "personal",
        sport: str = "General",
        user_id: Optional[int] = None,
        description: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Uploads a video to the server storage.
        PERMISSION: Only authenticated users (user_id is not None) can upload.
        """
        if not user_id:
            return False, "Access Denied: Only registered athletes may upload videos. Please sign in.", None

        source_p = Path(source_file_path)
        if not source_p.exists():
            return False, f"File does not exist: {source_file_path}", None

        # Clean title
        clean_title = title.strip() or source_p.stem

        # Target directory: personal or pro
        target_dir = PRO_DIR if category == "pro" else PERSONAL_DIR
        dest_filename = f"{user_id}_{int(os.times().system * 1000)}_{source_p.name}"
        dest_path = target_dir / dest_filename

        try:
            shutil.copy2(source_p, dest_path)

            # Generate thumbnail
            thumb_filename = f"thumb_{dest_path.stem}.jpg"
            thumb_path = THUMBNAIL_DIR / thumb_filename
            self.generate_thumbnail(str(dest_path), str(thumb_path))

            # Extract info
            info = CameraService.get_video_info(str(dest_path)) or {}
            resolution = f"{info.get('width', 1920)}x{info.get('height', 1080)}"
            fps = info.get("fps", 30.0)
            total_frames = info.get("total_frames", 0)
            duration = info.get("duration_seconds", 0.0)

            vid_id = db.add_uploaded_video(
                title=clean_title,
                category=category,
                sport=sport,
                file_path=str(dest_path),
                thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
                user_id=user_id,
                fps=fps,
                total_frames=total_frames,
                duration_seconds=duration,
                resolution=resolution,
                description=description,
            )

            if vid_id:
                record = db.get_video_by_id(vid_id)
                return True, "Video successfully uploaded to server storage.", record
            return False, "Failed to register video in database.", None

        except Exception as e:
            logger.error("Error uploading video %s: %s", source_file_path, e)
            return False, f"Upload error: {str(e)}", None

    def get_library(
        self,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
        sport: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves videos honoring the permission rules."""
        return db.get_uploaded_videos(category=category, user_id=user_id, sport=sport)

    def get_pro_videos(self, sport: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves professional reference videos accessible to all athletes and guests."""
        return db.get_uploaded_videos(category="pro", sport=sport)

    def get_personal_videos(self, user_id: Optional[int], sport: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves personal training videos uploaded by specific authenticated user."""
        if not user_id:
            return []
        return db.get_uploaded_videos(category="personal", user_id=user_id, sport=sport)

    def delete_video(self, video_id: int) -> bool:
        """Deletes a video record and removes associated server storage file."""
        rec = db.get_video_by_id(video_id)
        if not rec:
            return False
        try:
            p = Path(rec["file_path"])
            if p.exists():
                p.unlink()
            if rec.get("thumbnail_path"):
                tp = Path(rec["thumbnail_path"])
                if tp.exists():
                    tp.unlink()
        except Exception as e:
            logger.warning("Could not delete file from disk: %s", e)
        return db.delete_uploaded_video(video_id)


# Singleton instance
video_service = VideoService()
