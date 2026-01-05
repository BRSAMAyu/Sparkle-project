"""
Thumbnail generation service
缩略图生成服务
"""
import os
import tempfile
from typing import Optional
from uuid import UUID

import httpx
from loguru import logger


class ThumbnailService:
    async def generate_and_upload(
        self,
        file_path: str,
        file_id: UUID,
        upload_url: Optional[str],
    ) -> None:
        if not upload_url:
            return

        thumbnail_path = await self._generate_thumbnail(file_path)
        if not thumbnail_path:
            return

        try:
            await self._upload_thumbnail(upload_url, thumbnail_path)
        finally:
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)

    async def _generate_thumbnail(self, file_path: str) -> Optional[str]:
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if ext != ".pdf":
            return None

        try:
            import pdfplumber
        except Exception:
            logger.warning("pdfplumber is not installed; skipping thumbnail generation")
            return None

        try:
            with pdfplumber.open(file_path) as pdf:
                if not pdf.pages:
                    return None
                page = pdf.pages[0]
                image = page.to_image(resolution=150).original
        except Exception as exc:
            logger.warning(f"Failed to render thumbnail: {exc}")
            return None

        try:
            handle, temp_path = tempfile.mkstemp(prefix="thumb_", suffix=".jpg")
            os.close(handle)
            image.save(temp_path, "JPEG")
            return temp_path
        except Exception as exc:
            logger.warning(f"Failed to save thumbnail: {exc}")
            return None

    async def _upload_thumbnail(self, upload_url: str, thumbnail_path: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(thumbnail_path, "rb") as handle:
                resp = await client.put(upload_url, content=handle, headers={"Content-Type": "image/jpeg"})
                resp.raise_for_status()


thumbnail_service = ThumbnailService()
