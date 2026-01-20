"""
科大讯飞星火语音识别STT Provider
实现科大讯飞iFlytek Spark语音识别服务
"""
import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import AsyncGenerator, Optional
from urllib.parse import urlparse

import websockets
from loguru import logger

from app.config import settings
from app.services.stt.providers.base import STTProvider


class XunFeiProvider(STTProvider):
    """
    科大讯飞星火语音识别Provider

    使用科大讯飞iFlytek Spark语音识别API进行实时语音识别。
    支持流式音频输入和实时识别结果返回。
    """

    def __init__(self):
        """初始化科大讯飞配置"""
        self.api_key = settings.XUNFEI_API_KEY
        self.api_secret = settings.XUNFEI_API_SECRET
        self.domain = settings.XUNFEI_STT_DOMAIN
        self.language = settings.XUNFEI_STT_LANGUAGE
        self.sample_rate = settings.XUNFEI_STT_SAMPLE_RATE
        self.eos_ms = settings.XUNFEI_STT_EOS_MS

        if not self.api_key or not self.api_secret:
            logger.warning(
                "科大讯飞API密钥未配置，XunFeiProvider将无法工作"
            )

    def _generate_auth_url(self) -> str:
        """
        生成科大讯飞WebSocket鉴权URL

        科大讯飞使用HMAC-SHA256签名进行鉴权
        参考：https://www.xfyun.cn/doc/asr/iat/doc.html
        """
        # WebSocket URL
        host = "iat.xf-yun.com"
        path = "/v1/iat"

        # 构造待签名的字符串
        # 格式: host\npath\napi_key\napi_secret
        signature_origin = f"{host}\n{path}\n{self.api_key}\n{self.api_secret}"

        # HMAC-SHA256签名
        signature = hmac.new(
            signature_origin.encode("utf-8"),
            self.api_secret.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        # Base64编码
        signature_base64 = base64.b64encode(signature).decode("utf-8")

        # 构造请求参数
        params = {
            "authorization": signature_base64,
            "date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
            "host": host,
        }

        # 构造WebSocket URL
        # wss://iat.xf-yun.com/v1/iat?authorization=...&date=...&host=...
        ws_url = f"wss://{host}{path}"
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{ws_url}?{query_string}"

        logger.debug(f"Generated XunFei WebSocket URL: {full_url}")
        return full_url

    def _build_audio_frame(self, audio_data: bytes, is_last: bool = False) -> bytes:
        """
        构造科大讯飞音频帧格式

        科大讯飞要求音频数据按照特定格式封装：
        - 帧头：4字节长度 + 2字节标志位
        - 帧体：音频数据
        """
        # 帧头：4字节长度 + 2字节标志位
        # 标志位：0x0001表示普通帧，0x0002表示最后一帧
        frame_header = bytearray()
        frame_header.extend(len(audio_data).to_bytes(4, "big"))  # 长度
        frame_header.extend((0x0002 if is_last else 0x0001).to_bytes(2, "big"))  # 标志位

        return bytes(frame_header) + audio_data

    def _parse_response(self, data: dict) -> Optional[str]:
        """
        解析科大讯飞识别结果

        返回：
        - 识别到的文本
        - None表示没有识别结果
        """
        if "data" not in data:
            return None

        result = data["data"]
        if "result" not in result:
            return None

        # result结构: {"ws": [{"bg": 0, "cw": [{"w": "你好"}]}]}
        ws = result.get("ws", [])
        if not ws:
            return None

        # 提取所有文本片段
        text_parts = []
        for item in ws:
            cw = item.get("cw", [])
            for word in cw:
                w = word.get("w", "")
                if w:
                    text_parts.append(w)

        if text_parts:
            return "".join(text_parts)

        return None

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: Optional[str] = None,
        sample_rate: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        实时语音识别流式接口

        使用科大讯飞WebSocket API进行实时语音识别。
        音频流实时转发到科大讯飞，收到识别结果后立即返回。
        """
        if not self.api_key or not self.api_secret:
            yield "科大讯飞API密钥未配置"
            return

        # 使用配置的语言
        target_language = language or self.language
        target_sample_rate = sample_rate or self.sample_rate

        ws_url = self._generate_auth_url()

        try:
            # 建立WebSocket连接
            async with websockets.connect(ws_url) as websocket:
                logger.info("科大讯飞WebSocket连接已建立")

                # 发送配置帧
                config_frame = {
                    "type": "config",
                    "data": {
                        "audio_format": "raw",
                        "sample_rate": target_sample_rate,
                        "language": target_language,
                        "eos_ms": self.eos_ms,  # 静音检测阈值
                    },
                }
                await websocket.send(json.dumps(config_frame))

                # 发送音频数据
                last_text = ""
                async for audio_chunk in audio_stream:
                    if not audio_chunk:
                        continue

                    # 发送音频帧
                    audio_frame = self._build_audio_frame(audio_chunk, is_last=False)
                    await websocket.send(audio_frame)

                    # 接收识别结果
                    try:
                        response = await websocket.recv()
                        response_data = json.loads(response)

                        # 解析识别结果
                        text = self._parse_response(response_data)

                        if text and text != last_text:
                            last_text = text
                            yield text

                    except Exception as e:
                        logger.warning(f"接收识别结果失败: {e}")

                # 发送结束帧
                end_frame = self._build_audio_frame(b"", is_last=True)
                await websocket.send(end_frame)

                # 接收最终结果
                try:
                    response = await websocket.recv()
                    response_data = json.loads(response)

                    # 解析最终识别结果
                    text = self._parse_response(response_data)

                    if text and text != last_text:
                        yield text

                except Exception as e:
                    logger.warning(f"接收最终识别结果失败: {e}")

        except Exception as e:
            logger.error(f"科大讯飞语音识别失败: {e}")
            yield f"科大讯飞语音识别失败: {str(e)}"

    async def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
    ) -> str:
        """
        文件语音识别接口

        科大讯飞主要支持流式识别，文件识别可以通过流式接口实现
        """
        if not self.api_key or not self.api_secret:
            return "科大讯飞API密钥未配置"

        if not os.path.exists(file_path):
            return "文件不存在"

        try:
            # 读取文件内容
            with open(file_path, "rb") as f:
                audio_data = f.read()

            # 创建音频流生成器
            async def audio_generator():
                # 分块发送，每块10KB
                chunk_size = 10240
                for i in range(0, len(audio_data), chunk_size):
                    yield audio_data[i : i + chunk_size]

            # 使用流式识别
            results = []
            async for text in self.transcribe_stream(
                audio_generator(),
                language=language,
            ):
                results.append(text)

            # 返回最新的识别结果
            return results[-1] if results else ""

        except Exception as e:
            logger.error(f"文件语音识别失败: {e}")
            return f"文件语音识别失败: {str(e)}"

    async def close(self) -> None:
        """清理资源"""
        pass
