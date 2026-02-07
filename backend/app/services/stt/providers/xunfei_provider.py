"""
科大讯飞星火语音识别STT Provider
实现科大讯飞iFlytek Spark语音识别服务
"""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
from email.utils import formatdate
from urllib.parse import urlencode
import wave
from collections.abc import AsyncGenerator

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
        self.app_id = settings.XUNFEI_APP_ID
        self.api_key = settings.XUNFEI_API_KEY
        self.api_secret = settings.XUNFEI_API_SECRET
        self.domain = settings.XUNFEI_STT_DOMAIN
        self.language = settings.XUNFEI_STT_LANGUAGE
        self.sample_rate = settings.XUNFEI_STT_SAMPLE_RATE
        self.eos_ms = settings.XUNFEI_STT_EOS_MS

        if not self.app_id or not self.api_key or not self.api_secret:
            logger.warning(
                "科大讯飞API密钥或AppID未配置，XunFeiProvider将无法工作"
            )

    def _generate_auth_url(self) -> str:
        """
        生成科大讯飞WebSocket鉴权URL

        使用科大讯飞语音听写（流式版）API
        参考：https://www.xfyun.cn/doc/asr/voicedictation/API.html
        """
        host = "iat.xf-yun.com"
        path = "/v1/iat"

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

        query_string = urlencode({"authorization": authorization, "date": date, "host": host})
        ws_url = f"wss://{host}{path}?{query_string}"
        logger.debug(f"Generated XunFei WebSocket URL: {ws_url}")
        return ws_url

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

    def _parse_response(self, data: dict) -> str | None:
        """
        解析科大讯飞大模型识别结果

        官方返回格式：
        {
          "header": {...},
          "payload": {
            "result": {
              "text": "base64编码的JSON字符串"
            }
          }
        }

        text 字段 base64 解码后：
        {
          "ws": [
            {
              "cw": [
                {"w": "字1"},
                {"w": "字2"}
              ]
            }
          ]
        }

        返回：
        - 识别到的文本
        - None表示没有识别结果
        """
        if not isinstance(data, dict):
            return None

        # 检查是否有 payload.result.text
        try:
            # 兼容旧测试与部分历史响应格式: {"data": {"ws": [...]}}
            if "data" in data and isinstance(data["data"], dict):
                ws = data["data"].get("ws", [])
                text_parts = []
                for item in ws:
                    cw = item.get("cw", [])
                    for word in cw:
                        w = word.get("w", "")
                        if w:
                            text_parts.append(w)
                if text_parts:
                    return "".join(text_parts)

            if "payload" in data and isinstance(data["payload"], dict):
                result = data["payload"].get("result")
                if isinstance(result, dict) and "text" in result:
                    # Base64 解码
                    text_b64 = result["text"]
                    decoded = base64.b64decode(text_b64).decode("utf-8")
                    decoded_json = json.loads(decoded)

                    # 提取 ws 数组
                    ws = decoded_json.get("ws", [])
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
        except Exception as e:
            logger.warning(f"解析识别结果失败: {e}")

        return None

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str | None = None,
        sample_rate: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        实时语音识别流式接口

        使用科大讯飞大模型WebSocket API进行实时语音识别。
        音频流实时转发到科大讯飞，收到识别结果后立即返回。

        官方文档：https://www.xfyun.cn/doc/asr/voicedictation/API.html
        """
        if not self.app_id or not self.api_key or not self.api_secret:
            yield "科大讯飞API密钥未配置"
            return

        # 使用配置的语言
        target_language = (language or self.language).lower()
        if target_language.startswith("zh"):
            target_language = "zh_cn"
        elif target_language.startswith("en"):
            target_language = "en_us"
        target_sample_rate = sample_rate or self.sample_rate

        ws_url = self._generate_auth_url()

        try:
            # 建立WebSocket连接
            async with websockets.connect(ws_url) as websocket:
                logger.info("科大讯飞WebSocket连接已建立")

                # 发送音频数据
                last_text = ""
                seq = 1
                async for audio_chunk in audio_stream:
                    if not audio_chunk:
                        continue

                    # 构造符合官方规范的请求帧
                    # 第一帧：status=0
                    # 中间帧：status=1
                    # 最后一帧：status=2
                    is_first = (seq == 1)
                    frame_status = 0 if is_first else 1

                    iat_params = {
                        "domain": self.domain,  # 官方要求 slm
                        "language": target_language,
                        "eos": self.eos_ms,
                        "vinfo": 1,
                        "dwa": "wpgs",  # 开启动态修正
                        "result": {
                            "encoding": "utf8",
                            "compress": "raw",
                            "format": "json",
                        },
                    }
                    if target_language == "zh_cn":
                        iat_params["accent"] = "mandarin"

                    frame = {
                        "header": {
                            "app_id": self.app_id,
                            "status": frame_status
                        },
                        "payload": {
                            "audio": {
                                "encoding": "raw",
                                "sample_rate": target_sample_rate,
                                "channels": 1,
                                "bit_depth": 16,
                                "seq": seq,
                                "status": frame_status,
                                "audio": base64.b64encode(audio_chunk).decode("utf-8")
                            }
                        }
                    }
                    if is_first:
                        frame["parameter"] = {"iat": iat_params}

                    await websocket.send(json.dumps(frame))
                    seq += 1

                    # 接收识别结果
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response_data = json.loads(response)

                        # 解析识别结果
                        text = self._parse_response(response_data)

                        if text and text != last_text:
                            last_text = text
                            yield text

                    except asyncio.TimeoutError:
                        pass
                    except Exception as e:
                        logger.warning(f"接收识别结果失败: {e}")

                # 发送结束帧
                end_frame = {
                    "header": {
                        "app_id": self.app_id,
                        "status": 2
                    },
                    "payload": {
                        "audio": {
                            "encoding": "raw",
                            "sample_rate": target_sample_rate,
                            "channels": 1,
                            "bit_depth": 16,
                            "seq": seq,
                            "status": 2,
                            "audio": ""
                        }
                    }
                }
                await websocket.send(json.dumps(end_frame))

                # 接收最终结果
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    response_data = json.loads(response)

                    # 解析最终识别结果
                    text = self._parse_response(response_data)

                    if text and text != last_text:
                        yield text

                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.warning(f"接收最终识别结果失败: {e}")

        except Exception as e:
            logger.error(f"科大讯飞语音识别失败: {e}")
            yield f"科大讯飞语音识别失败: {str(e)}"

    async def transcribe_file(
        self,
        file_path: str,
        language: str | None = None,
    ) -> str:
        """
        文件语音识别接口

        科大讯飞主要支持流式识别，文件识别可以通过流式接口实现
        """
        if not self.app_id or not self.api_key or not self.api_secret:
            return "科大讯飞API密钥或AppID未配置"

        if not os.path.exists(file_path):
            return "文件不存在"

        try:
            # 读取文件内容
            audio_data = b""
            detected_sample_rate = None
            if file_path.lower().endswith(".wav"):
                with wave.open(file_path, "rb") as wf:
                    detected_sample_rate = wf.getframerate()
                    audio_data = wf.readframes(wf.getnframes())
            else:
                with open(file_path, "rb") as f:
                    audio_data = f.read()

            # 创建音频流生成器
            async def audio_generator():
                # 官方建议：每次发送间隔40ms，字节数为1280的整数倍且<=10000
                # 16kHz/16bit/mono: 40ms=1280 bytes
                sample_rate = detected_sample_rate or self.sample_rate
                bytes_per_40ms = int(sample_rate * 2 * 0.04)
                chunk_size = max(1280, min(10000, (bytes_per_40ms // 1280) * 1280 or 1280))
                for i in range(0, len(audio_data), chunk_size):
                    yield audio_data[i : i + chunk_size]
                    # 官方建议间隔40ms
                    import asyncio
                    await asyncio.sleep(0.04)

            # 使用流式识别
            results = []
            async for text in self.transcribe_stream(
                audio_generator(),
                language=language,
                sample_rate=detected_sample_rate,
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
