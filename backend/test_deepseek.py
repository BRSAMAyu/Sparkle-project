
import asyncio
import sys
import os

# 将 backend 目录添加到 python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import llm_service
from app.config import settings

async def test_deepseek_connection():
    print(f"Testing DeepSeek Integration...")
    print(f"Provider: {settings.LLM_PROVIDER}")
    print(f"Model: {settings.LLM_MODEL_NAME}")
    print(f"Base URL: {settings.DEEPSEEK_BASE_URL}")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}, 
        {"role": "user", "content": "Hello, who are you? Please reply in one short sentence."} 
    ]
    
    try:
        print("\nSending request...")
        response = await llm_service.chat(messages)
        print(f"\nResponse: {response}")
        print("\n✅ DeepSeek integration is working correctly!")
    except Exception as e:
        print(f"\n❌ Error during API call: {e}")

if __name__ == "__main__":
    asyncio.run(test_deepseek_connection())
