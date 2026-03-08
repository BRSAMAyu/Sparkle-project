"""
OCR 服务 - 使用智谱 GLM OCR 进行版面解析与文字提取。
"""
import base64
import binascii
import json
import uuid
from typing import Any

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class OCRService:
    """OCR服务 - 使用 GLM OCR 模型。"""

    def __init__(self):
        self.api_key = settings.ZHIPU_API_KEY
        self.base_url = settings.ZHIPU_OCR_BASE_URL.rstrip("/")
        self.model = settings.ZHIPU_OCR_MODEL
        self.timeout = httpx.Timeout(settings.ZHIPU_OCR_TIMEOUT_SECONDS)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def ocr_from_url(self, image_url: str, prompt: str = "") -> str:
        """
        从 URL 或 data URI 进行 OCR 识别。

        Args:
            image_url: 图片 URL 或 data URI
            prompt: 兼容旧接口，GLM OCR 下忽略

        Returns:
            识别出的 Markdown 文本
        """
        del prompt
        if not self.api_key:
            logger.warning("ZHIPU_API_KEY not set, returning empty OCR result")
            return ""

        try:
            payload = self._build_payload(image_url)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/layout_parsing",
                    headers=self._build_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                text = self._extract_text(data)
                logger.info(f"OCR completed, text length: {len(text)}")
                return text

        except httpx.HTTPError as e:
            logger.error(f"OCR HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def ocr_from_base64(self, image_b64: str, prompt: str = "") -> str:
        """
        从 base64 编码内容进行 OCR 识别。

        Args:
            image_b64: 原始 base64 或 data URI
            prompt: 兼容旧接口，GLM OCR 下忽略

        Returns:
            识别出的 Markdown 文本
        """
        del prompt
        return await self.ocr_from_url(image_b64)

    def ocr_from_base64_sync(self, image_b64: str, prompt: str = "") -> str:
        """同步版 base64 OCR，供线程内文档清洗调用。"""
        del prompt
        if not self.api_key:
            logger.warning("ZHIPU_API_KEY not set, returning empty OCR result")
            return ""

        try:
            payload = self._build_payload(image_b64)
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/layout_parsing",
                    headers=self._build_headers(),
                    json=payload,
                )
                response.raise_for_status()
                return self._extract_text(response.json())
        except httpx.HTTPError as e:
            logger.error(f"OCR HTTP error: {e}")
            return ""
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    async def layout_parse(self, file_ref: str, **kwargs: Any) -> dict[str, Any]:
        """获取 GLM OCR 完整版面解析结果。"""
        payload = self._build_payload(file_ref, **kwargs)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/layout_parsing",
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def ocr_for_math(self, image_url: str) -> str:
        """数学题 OCR。GLM OCR 返回结构化 Markdown。"""
        return await self.ocr_from_url(image_url)

    async def ocr_for_document(self, image_url: str) -> str:
        """文档 OCR，返回 Markdown。"""
        return await self.ocr_from_url(image_url)

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, file_ref: str, **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "file": self._normalize_file_ref(file_ref),
            "request_id": kwargs.get("request_id") or f"ocr_{uuid.uuid4().hex}",
        }

        optional_fields = {
            "return_crop_images": kwargs.get("return_crop_images"),
            "need_layout_visualization": kwargs.get("need_layout_visualization"),
            "start_page_id": kwargs.get("start_page_id"),
            "end_page_id": kwargs.get("end_page_id"),
            "user_id": kwargs.get("user_id"),
        }
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value
        return payload

    def _normalize_file_ref(self, file_ref: str) -> str:
        normalized = file_ref.strip()
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized
        if normalized.startswith("data:"):
            return normalized
        return self._wrap_base64_as_data_uri(normalized)

    def _wrap_base64_as_data_uri(self, file_ref: str) -> str:
        try:
            raw = base64.b64decode(file_ref, validate=True)
        except (binascii.Error, ValueError):
            return file_ref

        mime_type = "image/png"
        if raw.startswith(b"%PDF-"):
            mime_type = "application/pdf"
        elif raw.startswith(b"\xFF\xD8\xFF"):
            mime_type = "image/jpeg"
        elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"

        return f"data:{mime_type};base64,{file_ref}"

    def _extract_text(self, data: dict[str, Any]) -> str:
        md_results = data.get("md_results")
        if isinstance(md_results, str) and md_results.strip():
            return md_results.strip()

        layout_details = data.get("layout_details")
        if isinstance(layout_details, list):
            pages: list[str] = []
            for page in layout_details:
                if not isinstance(page, list):
                    continue
                parts: list[str] = []
                for item in sorted(
                    [entry for entry in page if isinstance(entry, dict)],
                    key=lambda entry: entry.get("index", 0),
                ):
                    content = item.get("content")
                    if isinstance(content, str) and content.strip():
                        parts.append(content.strip())
                if parts:
                    pages.append("\n".join(parts))
            if pages:
                return "\n\n".join(pages)

        return json.dumps(data, ensure_ascii=False)


# 全局单例
ocr_service = OCRService()
