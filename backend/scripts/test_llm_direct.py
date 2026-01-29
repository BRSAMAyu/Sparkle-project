#!/usr/bin/env python3
"""
Direct LLM API test script to diagnose performance issues.

Usage:
    cd backend && python scripts/test_llm_direct.py

This script tests the LLM API directly without going through the WebSocket/gRPC stack.
"""

import asyncio
import time
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.llm_service import LLMService
from app.core.agent_profiles import AgentRole


async def test_llm_direct():
    """Test LLM API directly to measure actual response time."""

    print("=" * 60)
    print("LLM Direct API Test")
    print("=" * 60)

    # Initialize LLM service
    llm = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    print(f"\nConfiguration:")
    print(f"  Model: {llm.chat_model}")
    print(f"  Extra body: {llm._extra_body}")
    print(f"  Demo mode: {llm.demo_mode}")

    if llm.demo_mode:
        print("\n[WARNING] Running in demo mode - no actual LLM calls will be made")
        return

    # Simple test message
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Reply briefly."},
        {"role": "user", "content": "Hello! Say 'Hi' in one word."}
    ]

    print("\n" + "-" * 60)
    print("Test 1: Non-streaming chat")
    print("-" * 60)

    try:
        start = time.perf_counter()
        response = await llm.chat(messages, temperature=0.3)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"  Response: {response[:100]}...")
        print(f"  Elapsed: {elapsed:.0f}ms")
        print(f"  Status: {'OK' if elapsed < 5000 else 'SLOW'}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "-" * 60)
    print("Test 2: Streaming chat")
    print("-" * 60)

    try:
        start = time.perf_counter()
        first_chunk_time = None
        chunks = []

        async for chunk in llm.stream_chat(messages, temperature=0.3):
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter()
                ttfc = (first_chunk_time - start) * 1000
                print(f"  Time to first chunk: {ttfc:.0f}ms")
            chunks.append(chunk)

        elapsed = (time.perf_counter() - start) * 1000
        full_response = "".join(chunks)

        print(f"  Full response: {full_response[:100]}...")
        print(f"  Total elapsed: {elapsed:.0f}ms")
        print(f"  Chunks received: {len(chunks)}")
        print(f"  Status: {'OK' if elapsed < 5000 else 'SLOW'}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "-" * 60)
    print("Test 3: Concurrent requests (2 parallel)")
    print("-" * 60)

    try:
        start = time.perf_counter()

        async def single_request(idx):
            req_start = time.perf_counter()
            response = await llm.chat(messages, temperature=0.3)
            req_elapsed = (time.perf_counter() - req_start) * 1000
            return idx, req_elapsed, response[:50]

        results = await asyncio.gather(single_request(1), single_request(2))

        total_elapsed = (time.perf_counter() - start) * 1000

        for idx, elapsed, resp in results:
            print(f"  Request {idx}: {elapsed:.0f}ms - {resp}...")

        print(f"  Total (parallel): {total_elapsed:.0f}ms")
        print(f"  Status: {'OK' if total_elapsed < 10000 else 'SLOW'}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_llm_direct())
