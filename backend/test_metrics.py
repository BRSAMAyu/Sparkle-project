import asyncio
import os
import sys
from loguru import logger
import httpx

# 添加项目根目录到 python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_metrics_endpoint():
    logger.info("Testing Prometheus Metrics Endpoint...")
    
    url = "http://localhost:8000/metrics"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                logger.info("✅ Successfully accessed /metrics")
                content = response.text
                
                # 检查是否包含自定义指标
                custom_metrics = [
                    "sparkle_requests_total",
                    "sparkle_request_latency_seconds",
                    "sparkle_tokens_total",
                    "sparkle_cache_hits_total"
                ]
                
                for metric in custom_metrics:
                    if metric in content:
                        logger.info(f"✅ Found custom metric: {metric}")
                    else:
                        logger.warning(f"❌ Custom metric not found: {metric} (Note: Metrics only appear after they've been incremented at least once)")
                
                # 打印前几行
                logger.info("Metrics preview:")
                for line in content.split("\n")[:10]:
                    if line.strip():
                        print(line)
            else:
                logger.error(f"❌ Failed to access /metrics. Status code: {response.status_code}")
                
    except Exception as e:
        logger.error(f"❌ Error connecting to FastAPI server: {e}")
        logger.info("Ensure the backend server is running (e.g., cd backend && python grpc_server.py or uvicorn app.main:app)")

if __name__ == "__main__":
    asyncio.run(test_metrics_endpoint())