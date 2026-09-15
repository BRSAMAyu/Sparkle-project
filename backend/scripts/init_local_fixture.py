#!/usr/bin/env python3
"""Initialize deterministic local fixtures for end-to-end local debugging."""
import asyncio
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from loguru import logger
from seed_demo_user_enhanced import seed_demo_user
from setup_smoke_test_data import setup_data


async def main() -> int:
    logger.info("Initializing local fixtures...")
    await seed_demo_user()
    await setup_data()
    logger.success("Local fixtures initialized: demo user, community data, knowledge nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
