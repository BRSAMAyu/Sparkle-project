"""
科大讯飞语音识别 STT Provider.

实现 iFlytek 语音听写 WebSocket v2 协议。
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
import wave
from collections.abc import AsyncGenerator
from email.utils import formatdate
from urllib.parse import urlencode

import websockets
from loguru import logger

from app.config import settings
from app.services.stt.providers.base import STTProvider


class XunFeiProvider(STTProvider):
    """科大讯飞语音听写 Provider。"""

    def __init__(self):
        self.app_id = settings.XUNFEI_APP_ID
        self.api_key = settings.XUNFEI_API_KEY
        self.api_secret = settings.XUNFEI_API_SECRET
        self.domain = settings.XUNFEI_STT_DOMAIN or "iat"
        self.language = settings.XUNFEI_STT_LANGUAGE
        self.sample_rate = settings.XUNFEI_STT_SAMPLE_RATE
        self.eos_ms = settings.XUNFEI_STT_EOS_MS

        if not self.app_id or not self.api_key or not self.api_secret:
            logger.warning("科大讯飞 API 密钥或 AppID 未配置，XunFeiProvider 将无法工作")

    def _generate_auth_url(self) -> str:
        """生成科大讯飞 WebSocket 鉴权 URL。"""
        host = "iat-api.xfyun.cn"
        path = "/v2/iat"

        date = formatdate(timeval=None, localtime=False, usegmt=True)
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"

        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature_base64 = base64.b64encode(signature).decode("utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_base64}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        query_string = urlencode({
            "authorization": authorization,
            "date": date,
            "host": host,
        })
        return f"wss://{host}{path}?{query_string}"

    def _normalize_language(self, language: str | None) -> tuple[str, str | None]:
        target_language = (language or self.language or "zh-CN").lower()
        if target_language.startswith("zh"):
            return "zh_cn", "mandarin"
        if target_language.startswith("en"):
            return "en_us", None
        return "zh_cn", "mandarin"

    def _extract_ws_words(self, ws_items: list[dict]) -> str | None:
        text_parts: list[str] = []
        for item in ws_items:
            cw = item.get("cw", [])
            if not isinstance(cw, list):
                continue
            for word in cw:
                if not isinstance(word, dict):
                    continue
                token = word.get("w", "")
                if token:
                    text_parts.append(token)
        if not text_parts:
            return None
        return "".join(text_parts)

    def _parse_response(self, data: dict) -> str | None:
        """解析科大讯飞识别结果。"""
        if not isinstance(data, dict):
            return None

        code = data.get("code")
        if code not in (0, None):
            message = data.get("message") or data.get("desc") or "未知错误"
            raise RuntimeError(str(message))

        payload = data.get("data")
        if isinstance(payload, dict):
            result = payload.get("result")
            if isinstance(result, dict):
                ws_items = result.get("ws", [])
                if isinstance(ws_items, list):
                    return self._extract_ws_words(ws_items)
            ws_items = payload.get("ws", [])
            if isinstance(ws_items, list):
                return self._extract_ws_words(ws_items)

        # 历史兼容：payload.result.text(base64-json)
        legacy_payload = data.get("payload")
        if isinstance(legacy_payload, dict):
            result = legacy_payload.get("result")
            if isinstance(result, dict) and "text" in result:
                decoded = base64.b64decode(result["text"]).decode("utf-8")
                decoded_json = json.loads(decoded)
                ws_items = decoded_json.get("ws", [])
                if isinstance(ws_items, list):
                    return self._extract_ws_words(ws_items)

        return None

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str | None = None,
        sample_rate: int | None = None,
    ) -> AsyncGenerator[str, None]:
        if not self.app_id or not self.api_key or not self.api_secret:
            yield "科大讯飞API密钥未配置"
            return

        target_language, accent = self._normalize_language(language)
        target_sample_rate = sample_rate or self.sample_rate
        ws_url = self._generate_auth_url()

        try:
            async with websockets.connect(ws_url, max_size=2**22) as websocket:
                logger.info("科大讯飞 WebSocket 连接已建立")
                last_text = ""
                sequence = 1

                async for audio_chunk in audio_stream:
                    if not audio_chunk:
                        continue

                    is_first = sequence == 1
                    frame_status = 0 if is_first else 1
                    frame: dict[str, object] = {
                        "data": {
                            "status": frame_status,
                            "format": f"audio/L16;rate={target_sample_rate}",
                            "encoding": "raw",
                            "audio": base64.b64encode(audio_chunk).decode("utf-8"),
                        }
                    }
                    if is_first:
                        business = {
                            "domain": self.domain,
                            "language": target_language,
                            "vad_eos": self.eos_ms,
                            "dwa": "wpgs",
                            "ptt": 0,
                        }
                        if accent:
                            business["accent"] = accent
                        frame["common"] = {"app_id": self.app_id}
                        frame["business"] = business

                    await websocket.send(json.dumps(frame))
                    sequence += 1

                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.6)
                        response_data = json.loads(response)
                        text = self._parse_response(response_data)
                        if text and text != last_text:
                            last_text = text
                            yield text
                    except asyncio.TimeoutError:
                        pass
                    except Exception as exc:
                        logger.warning(f"接收识别结果失败: {exc}")

                end_frame = {
                    "data": {
                        "status": 2,
                        "format": f"audio/L16;rate={target_sample_rate}",
                        "encoding": "raw",
                        "audio": "",
                    }
                }
                await websocket.send(json.dumps(end_frame))

                deadline = time.monotonic() + 3.0
                while time.monotonic() < deadline:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=0.8)
                        response_data = json.loads(response)
                        text = self._parse_response(response_data)
                        if text and text != last_text:
                            last_text = text
                            yield text
                        status = (response_data.get("data") or {}).get("status")
                        if status == 2:
                            break
                    except asyncio.TimeoutError:
                        continue
                    except Exception as exc:
                        logger.warning(f"接收最终识别结果失败: {exc}")
                        break

        except Exception as exc:
            logger.error(f"科大讯飞语音识别失败: {exc}")
            yield f"科大讯飞语音识别失败: {exc}"

    async def transcribe_file(
        self,
        file_path: str,
        language: str | None = None,
    ) -> str:
        if not self.app_id or not self.api_key or not self.api_secret:
            return "科大讯飞API密钥或AppID未配置"

        if not os.path.exists(file_path):
            return "文件不存在"

        try:
            audio_data = b""
            detected_sample_rate = None
            if file_path.lower().endswith(".wav"):
                with wave.open(file_path, "rb") as wf:
                    detected_sample_rate = wf.getframerate()
                    audio_data = wf.readframes(wf.getnframes())
            else:
                with open(file_path, "rb") as file:
                    audio_data = file.read()

            async def audio_generator():
                sample_rate = detected_sample_rate or self.sample_rate
                bytes_per_40ms = int(sample_rate * 2 * 0.04)
                chunk_size = max(
                    1280,
                    min(10000, (bytes_per_40ms // 1280) * 1280 or 1280),
                )
                for index in range(0, len(audio_data), chunk_size):
                    yield audio_data[index:index + chunk_size]
                    await asyncio.sleep(0.04)

            results: list[str] = []
            async for text in self.transcribe_stream(
                audio_generator(),
                language=language,
                sample_rate=detected_sample_rate,
            ):
                results.append(text)
            return results[-1] if results else ""
        except Exception as exc:
            logger.error(f"文件语音识别失败: {exc}")
            return f"文件语音识别失败: {exc}"

    async def close(self) -> None:
        pass
