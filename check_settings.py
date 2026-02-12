
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.config import settings

print(f"LLM_PROVIDER: {settings.LLM_PROVIDER}")
print(f"LLM_MODEL_NAME: {settings.LLM_MODEL_NAME}")
print(f"LLM_API_BASE_URL: {settings.LLM_API_BASE_URL}")
print(f"DEEPSEEK_BASE_URL: {settings.DEEPSEEK_BASE_URL}")
print(f"Environment: {settings.ENVIRONMENT}")
