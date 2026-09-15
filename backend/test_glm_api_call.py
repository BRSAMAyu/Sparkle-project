"""
实际调用 GLM-4.7-Flash API 进行测试

需要设置 ZHIPU_API_KEY 环境变量
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.services.llm_service import LLMService
from app.core.llm_router import llm_router
from app.core.agent_profiles import AgentRole
from loguru import logger


async def test_glm_flash_no_thinking():
    """测试 GLM-4.7-Flash 非思考模式"""
    print("\n" + "=" * 60)
    print("测试 1: GLM-4.7-Flash 非思考模式（快速响应）")
    print("=" * 60)

    # 选择非思考模式
    selection = llm_router.select_specific_model(
        "glm_4_7_flash_no_thinking",
        agent_role=AgentRole.GENERATION
    )

    kwargs = llm_router.get_openai_client_kwargs(selection)

    print(f"\n配置:")
    print(f"  - Model: {kwargs['model']}")
    print(f"  - Base URL: {kwargs['base_url']}")
    print(f"  - Extra Body: {kwargs.get('extra_body', {})}")
    print(f"  - API Key: {'已设置' if kwargs['api_key'] else '未设置'}")

    if not kwargs['api_key']:
        print("\n⚠️  跳过 API 调用（未设置 API Key）")
        return

    # 创建 LLM 服务
    llm_service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=False)

    # 强制使用 glm-4.7-flash 非思考模式
    llm_service._provider = llm_service._provider.__class__(
        api_key=kwargs['api_key'],
        base_url=kwargs['base_url']
    )
    llm_service.chat_model = kwargs['model']

    # 如果有 extra_body，保存它
    llm_service._extra_body = kwargs.get('extra_body')

    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ]

    print(f"\n发送请求...")
    try:
        response = await llm_service.chat(messages, temperature=0.7)
        print(f"\n✅ 响应成功:")
        print(f"  {response[:200]}...")
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        logger.exception("API call failed")


async def test_glm_flash_thinking():
    """测试 GLM-4.7-Flash 思考模式"""
    print("\n" + "=" * 60)
    print("测试 2: GLM-4.7-Flash 思考模式（深度推理）")
    print("=" * 60)

    # 选择思考模式
    selection = llm_router.select_specific_model(
        "glm_4_7_flash_thinking",
        agent_role=AgentRole.GENERATION
    )

    kwargs = llm_router.get_openai_client_kwargs(selection)

    print(f"\n配置:")
    print(f"  - Model: {kwargs['model']}")
    print(f"  - Base URL: {kwargs['base_url']}")
    print(f"  - Extra Body: {kwargs.get('extra_body', {})}")
    print(f"  - API Key: {'已设置' if kwargs['api_key'] else '未设置'}")

    if not kwargs['api_key']:
        print("\n⚠️  跳过 API 调用（未设置 API Key）")
        return

    # 创建 LLM 服务
    llm_service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=False)

    # 强制使用 glm-4.7-flash 思考模式
    llm_service._provider = llm_service._provider.__class__(
        api_key=kwargs['api_key'],
        base_url=kwargs['base_url']
    )
    llm_service.chat_model = kwargs['model']
    llm_service._extra_body = kwargs.get('extra_body')

    messages = [
        {"role": "user", "content": "解释一下什么是递归，并给出一个简单的例子。"}
    ]

    print(f"\n发送请求（思考模式可能需要更长时间）...")
    try:
        response = await llm_service.chat(messages, temperature=0.7)
        print(f"\n✅ 响应成功:")
        print(f"  {response[:300]}...")
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        logger.exception("API call failed")


async def test_stream_chat():
    """测试流式聊天"""
    print("\n" + "=" * 60)
    print("测试 3: GLM-4.7-Flash 流式聊天")
    print("=" * 60)

    # 选择非思考模式
    selection = llm_router.select_specific_model(
        "glm_4_7_flash_no_thinking",
        agent_role=AgentRole.GENERATION
    )

    kwargs = llm_router.get_openai_client_kwargs(selection)

    if not kwargs['api_key']:
        print("\n⚠️  跳过 API 调用（未设置 API Key）")
        return

    # 创建 LLM 服务
    llm_service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=False)
    llm_service._provider = llm_service._provider.__class__(
        api_key=kwargs['api_key'],
        base_url=kwargs['base_url']
    )
    llm_service.chat_model = kwargs['model']
    llm_service._extra_body = kwargs.get('extra_body')

    messages = [
        {"role": "user", "content": "用50个字以内说明什么是人工智能。"}
    ]

    print(f"\n发送流式请求...")
    print(f"\n响应:")

    try:
        full_response = ""
        async for chunk in llm_service.stream_chat(messages, temperature=0.7):
            print(chunk, end='', flush=True)
            full_response += chunk
        print(f"\n\n✅ 流式响应完成 (总长度: {len(full_response)})")
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        logger.exception("Stream API call failed")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("GLM-4.7-Flash API 调用测试")
    print("=" * 60)

    # 检查 API Key
    from app.config import settings
    if not settings.ZHIPU_API_KEY:
        print("\n⚠️  警告: 未设置 ZHIPU_API_KEY 环境变量")
        print("请在 .env 文件中设置 ZHIPU_API_KEY 后再运行此测试")
        print("\n仅测试配置逻辑，跳过实际 API 调用...")

    try:
        await test_glm_flash_no_thinking()
        await test_glm_flash_thinking()
        await test_stream_chat()

        print("\n" + "=" * 60)
        print("✅ 测试完成")
        print("=" * 60)
        print()

    except Exception as e:
        logger.exception("测试失败")
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
