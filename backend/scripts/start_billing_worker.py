import os
import sys
import asyncio
from loguru import logger

# 添加项目根目录到 python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.billing_worker import BillingWorker

async def main():
    logger.info("Starting Token Billing Worker...")
    worker = BillingWorker(
        batch_size=int(os.getenv("BILLING_BATCH_SIZE", "10")),
        flush_interval=int(os.getenv("BILLING_FLUSH_INTERVAL", "5"))
    )
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Billing Worker stopped by user.")
    except Exception as e:
        logger.error(f"Billing Worker failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())