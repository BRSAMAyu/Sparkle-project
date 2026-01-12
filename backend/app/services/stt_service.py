import os
import shutil
import uuid
import tempfile
from typing import Optional, List, Dict, Any, AsyncGenerator
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
import asyncio

from app.config import settings
from app.services.llm_service import llm_service
# We'll use the LLM provider's client if available, or create a new OpenAI client for audio
from app.services.llm.providers import OpenAICompatibleProvider

class STTService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Initialize OpenAI client for Audio (Whisper)
        # Assuming the LLM_API_KEY and BASE_URL work for Audio, or strictly OpenAI
        # For this implementation, we try to use the configured LLM settings.
        # If the provider is NOT openai, this might fail if they don't support /audio/transcriptions.
        # So we default to OpenAI logic or fallback.
        
        # Note: Many "OpenAI Compatible" providers (like DeepSeek, Qwen) do NOT support Audio API.
        # We really need a real OpenAI key or a specific ASR provider.
        # For robustness, we will try to use the 'openai' package directly with settings.
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_API_BASE_URL
            )
        except ImportError:
            logger.error("OpenAI package not found. STT will not work.")
            self.client = None

    async def transcribe_file(self, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe an audio file using OpenAI Whisper API.
        """
        if not self.client:
            return {"text": "STT Service Unavailable (Client Init Failed)", "error": True}

        if not os.path.exists(file_path):
            return {"text": "", "error": "File not found"}

        try:
            logger.info(f"Transcribing file: {file_path}")
            
            with open(file_path, "rb") as audio_file:
                # Call OpenAI Whisper API
                # model="whisper-1" is standard
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language=language,
                    response_format="json"
                )
            
            return {"text": transcript.text, "error": False}
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            # Mock response in Demo Mode if failure
            if settings.DEMO_MODE:
                return {"text": "这是演示模式下的模拟语音转写结果。实际调用失败，请检查 API 配置。", "error": False}
            return {"text": f"Transcription Error: {str(e)}", "error": True}

    async def enhance_transcript(self, text: str) -> str:
        """
        Use LLM to post-process text:
        - Add punctuation
        - Correct typos
        - Separate speakers (if apparent)
        """
        if not text or len(text) < 2:
            return text

        system_prompt = """
        You are a professional transcript editor.
        Task: Optimize the following Automatic Speech Recognition (ASR) text.
        
        Requirements:
        1. Correct punctuation and capitalization.
        2. Fix obvious homophone errors (typos).
        3. If there are clearly multiple speakers (based on context), try to format it as "Speaker A: ... Speaker B: ...".
        4. Keep the original meaning and tone.
        5. Output ONLY the corrected text.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        try:
            enhanced_text = await llm_service.chat(messages, temperature=0.3)
            return enhanced_text.strip()
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return text

    async def handle_websocket_stream(self, websocket: WebSocket):
        """
        Handle WebSocket audio stream.
        Current implementation strategy:
        - Receive chunks of audio bytes.
        - Buffer until a silence threshold or size threshold.
        - Save to temp file.
        - Transcribe.
        - Send back partial/final result.
        """
        await websocket.accept()
        
        session_id = str(uuid.uuid4())
        temp_filename = os.path.join(self.upload_dir, f"stream_{session_id}.webm")
        
        # Buffer config
        CHUNK_THRESHOLD = 100 * 1024 # 100KB buffer (approx 3-5 seconds of audio depending on codec)
        buffer = bytearray()
        
        try:
            while True:
                # Receive data
                # We expect bytes (audio) or text (control commands)
                data = await websocket.receive()
                
                if "bytes" in data:
                    chunk = data["bytes"]
                    buffer.extend(chunk)
                    
                    if len(buffer) >= CHUNK_THRESHOLD:
                        # Process buffer
                        await self._process_buffer(websocket, buffer, temp_filename)
                        buffer = bytearray() # Clear buffer
                        
                elif "text" in data:
                    text = data["text"]
                    if text == "STOP":
                        # Process remaining buffer
                        if len(buffer) > 0:
                            await self._process_buffer(websocket, buffer, temp_filename)
                        
                        # Send completion signal
                        await websocket.send_json({"type": "status", "content": "completed"})
                        break
                        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.send_json({"type": "error", "content": str(e)})
        finally:
            # Cleanup
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    async def _process_buffer(self, websocket: WebSocket, audio_data: bytearray, filename: str):
        """Helper to write buffer to file and transcribe"""
        # Write to temp file
        # Note: In a real streaming setup, we'd append. 
        # But for Whisper API, we need a valid file header usually.
        # If the client sends raw PCM, we need to wrap it.
        # If the client sends chunks of a webm stream, simply concatenating might break headers.
        # For simplicity in this generic implementation:
        # We assume the client sends valid standalone chunks OR we just overwrite the file to test.
        # 
        # Better Strategy for "Pseudo-Streaming":
        # Save the current buffer as a standalone file (if possible) or append to a growing file 
        # and transcribe the *difference*? No, OpenAI transcribes the whole file.
        #
        # Simple Approach: Write current buffer to a file, transcribe it.
        # This assumes the buffer contains a valid audio segment (e.g. from a client recorder that flushes on silence).
        
        with open(filename, "wb") as f:
            f.write(audio_data)
            
        # Transcribe
        result = await self.transcribe_file(filename)
        
        if not result["error"]:
            text = result["text"]
            # Enhance
            # enhanced = await self.enhance_transcript(text) # Optional: might be too slow for stream
            
            await websocket.send_json({
                "type": "transcription", 
                "text": text,
                "is_final": False 
            })

stt_service = STTService()
