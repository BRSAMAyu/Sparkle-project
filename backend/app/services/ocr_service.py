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
from app.core.llm_client import SecureLLMClient
from app.services.circuit_breaker import CircuitBreakerOpenException, circuit_breaker_service


class OCRService:
    """OCR服务 - 支持 GLM 与 SiliconFlow 双供应商自动故障切换。"""

    def __init__(self):
        self.primary_provider = self._normalize_provider(settings.OCR_PROVIDER)
        self.backup_provider = self._normalize_provider(settings.OCR_BACKUP_PROVIDER)
        self.api_key = settings.ZHIPU_API_KEY
        self.base_url = settings.ZHIPU_OCR_BASE_URL.rstrip("/")
        self.model = settings.ZHIPU_OCR_MODEL
        self.timeout = httpx.Timeout(settings.ZHIPU_OCR_TIMEOUT_SECONDS)
        self.siliconflow_api_key = settings.SILICONFLOW_API_KEY
        self.siliconflow_base_url = settings.SILICONFLOW_BASE_URL.rstrip("/")
        self.siliconflow_model = settings.SILICONFLOW_OCR_MODEL
        self.siliconflow_timeout = httpx.Timeout(settings.SILICONFLOW_OCR_TIMEOUT_SECONDS)

    @staticmethod
    def _normalize_provider(provider_name: str | None) -> str:
        normalized = (provider_name or "").strip().lower()
        aliases = {
            "glm": "zhipu",
            "deepseek": "siliconflow",
        }
        return aliases.get(normalized, normalized or "zhipu")

    def _provider_order(self, preferred_provider: str | None = None) -> list[str]:
        ordered: list[str] = []
        for provider in (
            self._normalize_provider(preferred_provider) if preferred_provider else "",
            self.primary_provider,
            self.backup_provider,
            "zhipu",
            "siliconflow",
        ):
            if provider and provider not in ordered:
                ordered.append(provider)
        return ordered

    def _provider_configured(self, provider: str) -> bool:
        if provider == "zhipu":
            return bool(self.api_key)
        if provider == "siliconflow":
            return bool(self.siliconflow_api_key)
        return False

    def _circuit_key(self, provider: str) -> str:
        return f"ocr:{provider}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def ocr_from_url(self, image_url: str, prompt: str = "", preferred_provider: str | None = None) -> str:
        """
        从 URL 或 data URI 进行 OCR 识别。

        Args:
            image_url: 图片 URL 或 data URI
            prompt: 兼容旧接口，GLM OCR 下忽略

        Returns:
            识别出的 Markdown 文本
        """
        last_error: Exception | None = None
        for provider in self._provider_order(preferred_provider):
            if not self._provider_configured(provider):
                continue
            try:
                await circuit_breaker_service.check(self._circuit_key(provider))
                if provider == "zhipu":
                    text = await self._zhipu_ocr_from_url(image_url)
                else:
                    text = await self._siliconflow_ocr_from_url(image_url, prompt=prompt)
                if not text.strip():
                    raise RuntimeError(f"{provider} returned empty OCR result")
                await circuit_breaker_service.record_success(self._circuit_key(provider))
                logger.info(f"OCR completed via {provider}, text length: {len(text)}")
                return text
            except CircuitBreakerOpenException as exc:
                logger.warning(f"OCR provider {provider} skipped because circuit breaker is open: {exc}")
                last_error = exc
            except Exception as exc:
                logger.warning(f"OCR provider {provider} failed: {exc}")
                await circuit_breaker_service.record_failure(self._circuit_key(provider))
                last_error = exc

        if last_error:
            logger.error(f"OCR failed after all providers exhausted: {last_error}")
        return ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def ocr_from_base64(
        self,
        image_b64: str,
        prompt: str = "",
        preferred_provider: str | None = None,
    ) -> str:
        """
        从 base64 编码内容进行 OCR 识别。

        Args:
            image_b64: 原始 base64 或 data URI
            prompt: 兼容旧接口，GLM OCR 下忽略

        Returns:
            识别出的 Markdown 文本
        """
        return await self.ocr_from_url(image_b64, prompt=prompt, preferred_provider=preferred_provider)

    def ocr_from_base64_sync(
        self,
        image_b64: str,
        prompt: str = "",
        preferred_provider: str | None = None,
    ) -> str:
        """同步版 base64 OCR，供线程内文档清洗调用。"""
        last_error: Exception | None = None
        for provider in self._provider_order(preferred_provider):
            if not self._provider_configured(provider):
                continue
            try:
                if provider == "zhipu":
                    text = self._zhipu_ocr_from_base64_sync(image_b64)
                else:
                    text = self._siliconflow_ocr_from_base64_sync(image_b64, prompt=prompt)
                if text.strip():
                    logger.info(f"OCR sync completed via {provider}, text length: {len(text)}")
                    return text
                raise RuntimeError(f"{provider} returned empty OCR result")
            except Exception as exc:
                logger.warning(f"OCR sync provider {provider} failed: {exc}")
                last_error = exc

        if last_error:
            logger.error(f"OCR sync failed after all providers exhausted: {last_error}")
        return ""

    async def layout_parse(self, file_ref: str, **kwargs: Any) -> dict[str, Any]:
        """获取 GLM OCR 完整版面解析结果。"""
        raw_preferred_provider = kwargs.pop("preferred_provider", None)
        preferred_provider = self._normalize_provider(raw_preferred_provider) if raw_preferred_provider else ""
        if preferred_provider == "siliconflow":
            text = await self._siliconflow_ocr_from_url(file_ref, prompt=kwargs.get("prompt", ""))
            return {"md_results": text}

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

    def _build_siliconflow_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.siliconflow_api_key}",
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

    async def _zhipu_ocr_from_url(self, image_url: str) -> str:
        payload = self._build_payload(image_url)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/layout_parsing",
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()
            return self._extract_text(response.json())

    def _zhipu_ocr_from_base64_sync(self, image_b64: str) -> str:
        payload = self._build_payload(image_b64)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/layout_parsing",
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()
            return self._extract_text(response.json())

    def _build_siliconflow_payload(self, file_ref: str, prompt: str = "") -> dict[str, Any]:
        normalized_ref = self._normalize_file_ref(file_ref)
        instruction = prompt.strip() or (
            "Extract all readable text from this document. Preserve structure with concise Markdown. "
            "Return only OCR text."
        )
        return {
            "model": self.siliconflow_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an OCR engine. Return only the recognized text.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": normalized_ref}},
                    ],
                },
            ],
            "temperature": 0.0,
        }

    async def _siliconflow_ocr_from_url(self, image_url: str, prompt: str = "") -> str:
        client = SecureLLMClient.get(
            api_key=self.siliconflow_api_key,
            base_url=self.siliconflow_base_url,
            timeout_seconds=self.siliconflow_timeout.read or settings.SILICONFLOW_OCR_TIMEOUT_SECONDS,
        )
        payload = self._build_siliconflow_payload(image_url, prompt=prompt)
        return await client.chat(
            messages=payload["messages"],
            model=payload["model"],
            temperature=float(payload.get("temperature", 0.0) or 0.0),
        )

    def _siliconflow_ocr_from_base64_sync(self, image_b64: str, prompt: str = "") -> str:
        url = f"{self.siliconflow_base_url}/chat/completions"
        with httpx.Client(timeout=self.siliconflow_timeout) as client:
            response = client.post(
                url,
                headers=self._build_siliconflow_headers(),
                json=self._build_siliconflow_payload(image_b64, prompt=prompt),
            )
            response.raise_for_status()
            data = response.json()
        return self._extract_chat_json_text(data)

    def _extract_chat_text(self, response: Any) -> str:
        content = response.choices[0].message.content
        return self._normalize_chat_content(content)

    def _extract_chat_json_text(self, data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return json.dumps(data, ensure_ascii=False)
        return self._normalize_chat_content(content)

    def _normalize_chat_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
                elif isinstance(item, str) and item.strip():
                    parts.append(item.strip())
            return "\n".join(parts).strip()
        return str(content).strip()


# 全局单例
ocr_service = OCRService()
