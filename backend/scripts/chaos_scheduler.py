import schedule
import time
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def run_daily_chaos_tests():
    """Execute daily chaos engineering tests via pytest"""
    logger.info("🔥 Starting daily chaos tests...")
    
    try:
        # Run tests and capture output
        result = subprocess.run(
            ["pytest", "backend/tests/chaos/test_service_resilience.py", "-v"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Chaos tests passed successfully")
        else:
            logger.error(f"❌ Chaos tests failed:\n{result.stderr}")
            
    except Exception as e:
        logger.error(f"💥 Failed to execute chaos tests: {e}")

# Schedule for 02:00 AM daily
schedule.every().day.at("02:00").do(run_daily_chaos_tests)

if __name__ == "__main__":
    logger.info("Chaos Scheduler started. Waiting for next window...")
    # Run once on startup for verification (optional)
    # run_daily_chaos_tests()
    
    while True:
        schedule.run_pending()
        time.sleep(60)

