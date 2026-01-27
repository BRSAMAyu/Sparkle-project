"""
OCR服务 - 使用DeepSeek OCR进行图片文字识别
支持SiliconFlow API
"""
from typing import Optional
from loguru import logger
from httpx import AsyncClient, HTTPError

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class OCRService:
    """OCR服务 - 使用DeepSeek OCR模型"""

    def __init__(self):
        self.api_key = settings.SILICONFLOW_API_KEY
        self.base_url = settings.SILICONFLOW_BASE_URL.rstrip("/")
        self.model = settings.SILICONFLOW_OCR_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def ocr_from_url(self, image_url: str, prompt: str = "OCR this image.") -> str:
        """
        从图片URL进行OCR识别

        Args:
            image_url: 图片URL（支持http/https或base64 data URI）
            prompt: OCR提示词

        Returns:
            识别出的文本内容
        """
        if not self.api_key:
            logger.warning("SILICONFLOW_API_KEY not set, returning empty OCR result")
            return ""

        # 构建请求
        if not prompt.startswith("<|grounding|>"):
            prompt = f"<|grounding|>{prompt}"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.0
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

                text = data["choices"][0]["message"]["content"]
                logger.info(f"OCR completed, text length: {len(text)}")
                return text

        except HTTPError as e:
            logger.error(f"OCR HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def ocr_from_base64(self, image_b64: str, prompt: str = "OCR this image.") -> str:
        """
        从base64编码的图片进行OCR识别

        Args:
            image_b64: base64编码的图片数据（不含data:image前缀）
            prompt: OCR提示词

        Returns:
            识别出的文本内容
        """
        # 添加data URI前缀
        if not image_b64.startswith("data:"):
            image_b64 = f"data:image/jpeg;base64,{image_b64}"

        return await self.ocr_from_url(image_b64, prompt)

    async def ocr_for_math(self, image_url: str) -> str:
        """数学题OCR优化提示词"""
        return await self.ocr_from_url(
            image_url,
            prompt="Extract all text and mathematical expressions from this image. Preserve the structure and formatting."
        )

    async def ocr_for_document(self, image_url: str) -> str:
        """文档OCR优化提示词 - 转换为Markdown"""
        return await self.ocr_from_url(
            image_url,
            prompt="Convert the document to markdown."
        )


# 全局单例
ocr_service = OCRService()
