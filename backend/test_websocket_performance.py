"""
WebSocket 性能测试 - 验证 LLM 调用修复效果

测试项目：
1. 单条消息响应时间 (TTFC + Total)
2. 多条消息顺序发送
3. 并发消息处理 (模拟真实场景)
"""
import asyncio
import json
import time
import websockets
from loguru import logger
from test_websocket_client import _create_jwt, DEFAULT_USER_ID


async def test_single_message_performance():
    """测试单条消息的响应时间"""
    user_id = DEFAULT_USER_ID
    token = _create_jwt(user_id)
    uri = f"ws://localhost:8080/ws/chat?user_id={user_id}&token={token}"

    logger.info("=" * 70)
    logger.info("📊 Test 1: Single Message Performance")
    logger.info("=" * 70)

    try:
        async with websockets.connect(uri) as websocket:
            # 使用非 DEMO 模式的消息
            test_message = {
                "message": "Hi",  # 简单消息，触发实际 LLM 调用
                "session_id": "perf_test_001",
                "nickname": "Test"
            }

            start_time = time.perf_counter()
            await websocket.send(json.dumps(test_message))

            first_chunk_time = None
            ttfc = 0
            total_chunks = 0
            full_text = ""

            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    total_chunks += 1

                    data = json.loads(response)
                    response_type = data.get("type")

                    if response_type == "delta":
                        if first_chunk_time is None:
                            first_chunk_time = time.perf_counter()
                            ttfc = (first_chunk_time - start_time) * 1000
                            logger.info(f"⚡ TTFC (Time To First Chunk): {ttfc:.0f}ms")

                        delta = data.get("delta", "")
                        full_text += delta

                    elif data.get("finish_reason") and data.get("finish_reason") != "NULL":
                        total_time = (time.perf_counter() - start_time) * 1000
                        logger.info(f"✅ Total time: {total_time:.0f}ms")
                        logger.info(f"📝 Response: {full_text[:100]}...")
                        logger.info(f"📊 Chunks: {total_chunks}")

                        # 性能评估
                        if ttfc < 3000 and total_time < 10000:
                            logger.success("🎯 Performance: EXCELLENT")
                        elif ttfc < 5000 and total_time < 30000:
                            logger.info("✅ Performance: GOOD")
                        else:
                            logger.warning("⚠️  Performance: SLOW")
                        break

                except asyncio.TimeoutError:
                    total_time = (time.perf_counter() - start_time) * 1000
                    logger.error(f"❌ Timeout after {total_time:.0f}ms")
                    return False

            return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def test_sequential_messages():
    """测试顺序发送多条消息"""
    user_id = DEFAULT_USER_ID
    token = _create_jwt(user_id)
    uri = f"ws://localhost:8080/ws/chat?user_id={user_id}&token={token}"

    logger.info("\n" + "=" * 70)
    logger.info("📊 Test 2: Sequential Messages (3 messages)")
    logger.info("=" * 70)

    messages = ["Hi", "Hello", "Hey"]
    results = []

    try:
        async with websockets.connect(uri) as websocket:
            for i, msg in enumerate(messages, 1):
                logger.info(f"\n📤 Message {i}/{len(messages)}: {msg}")

                start_time = time.perf_counter()
                await websocket.send(json.dumps({
                    "message": msg,
                    "session_id": f"sequential_test_{i}",
                    "nickname": "Test"
                }))

                response_time = None
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        data = json.loads(response)

                        if data.get("type") == "delta" and response_time is None:
                            response_time = (time.perf_counter() - start_time) * 1000
                            logger.info(f"⚡ Response time: {response_time:.0f}ms")

                        if data.get("finish_reason") and data.get("finish_reason") != "NULL":
                            results.append(response_time or 0)
                            break

                    except asyncio.TimeoutError:
                        logger.error(f"❌ Message {i} timeout")
                        results.append(-1)
                        break

                # 短暂延迟避免请求过快
                await asyncio.sleep(0.5)

            avg_time = sum(r for r in results if r > 0) / len([r for r in results if r > 0])
            logger.info(f"\n📊 Average response time: {avg_time:.0f}ms")

            return all(r > 0 for r in results)

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def test_concurrent_connections():
    """测试并发 WebSocket 连接"""
    logger.info("\n" + "=" * 70)
    logger.info("📊 Test 3: Concurrent Connections (3 parallel)")
    logger.info("=" * 70)

    async def single_connection(conn_id):
        user_id = f"{DEFAULT_USER_ID[:-1]}{conn_id}"  # 生成不同的 user_id
        token = _create_jwt(user_id)
        uri = f"ws://localhost:8080/ws/chat?user_id={user_id}&token={token}"

        start_time = time.perf_counter()

        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps({
                    "message": "Hi",
                    "session_id": f"concurrent_{conn_id}",
                    "nickname": "Test"
                }))

                first_chunk_time = None
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(response)

                    if data.get("type") == "delta" and first_chunk_time is None:
                        first_chunk_time = time.perf_counter()
                        ttfc = (first_chunk_time - start_time) * 1000
                        logger.info(f"  [Conn {conn_id}] TTFC: {ttfc:.0f}ms")

                    if data.get("finish_reason") and data.get("finish_reason") != "NULL":
                        total_time = (time.perf_counter() - start_time) * 1000
                        logger.info(f"  [Conn {conn_id}] Total: {total_time:.0f}ms")
                        return total_time

        except Exception as e:
            logger.error(f"  [Conn {conn_id}] Error: {e}")
            return -1

    try:
        # 并发启动 3 个连接
        results = await asyncio.gather(
            single_connection(1),
            single_connection(2),
            single_connection(3),
        )

        valid_results = [r for r in results if r > 0]
        if len(valid_results) == 3:
            avg_time = sum(valid_results) / len(valid_results)
            logger.success(f"✅ All 3 connections successful, avg: {avg_time:.0f}ms")
            return True
        else:
            logger.warning(f"⚠️  Only {len(valid_results)}/3 connections successful")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def main():
    """运行所有性能测试"""
    logger.info("🚀 Starting WebSocket Performance Tests\n")

    results = {}

    # Test 1: 单条消息性能
    results["single"] = await test_single_message_performance()

    await asyncio.sleep(2)

    # Test 2: 顺序消息
    results["sequential"] = await test_sequential_messages()

    await asyncio.sleep(2)

    # Test 3: 并发连接
    results["concurrent"] = await test_concurrent_connections()

    # 汇总结果
    logger.info("\n" + "=" * 70)
    logger.info("🎯 Performance Test Summary")
    logger.info("=" * 70)
    logger.info(f"  Single Message:      {'✅ PASS' if results['single'] else '❌ FAIL'}")
    logger.info(f"  Sequential Messages: {'✅ PASS' if results['sequential'] else '❌ FAIL'}")
    logger.info(f"  Concurrent Connect:  {'✅ PASS' if results['concurrent'] else '❌ FAIL'}")
    logger.info("=" * 70)

    all_passed = all(results.values())
    if all_passed:
        logger.success("🎉 All tests PASSED!")
    else:
        logger.error("❌ Some tests FAILED")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
