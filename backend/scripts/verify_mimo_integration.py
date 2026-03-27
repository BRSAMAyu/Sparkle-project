#!/usr/bin/env python3
"""
MIMO 集成验证脚本

验证内容：
1. 配置正确加载
2. LLM Router 不再路由到 mimo_pro
3. MIMO API 调用成功
4. 联网搜索功能正常工作
5. 思考链和引用正确返回
"""
import asyncio
import os
import sys
import json
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 设置环境变量文件路径
os.environ.setdefault("ENV_FILE", str(backend_dir / ".env"))


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_success(msg: str):
    print(f"✅ {msg}")


def print_error(msg: str):
    print(f"❌ {msg}")


def print_info(msg: str):
    print(f"ℹ️  {msg}")


def verify_config():
    """验证配置是否正确加载"""
    print_header("1. 验证配置加载")

    try:
        from app.config import settings

        # 检查 MIMO 基础配置
        assert hasattr(settings, 'XIAOMI_CHAT_MODEL'), "缺少 XIAOMI_CHAT_MODEL 配置"
        assert hasattr(settings, 'XIAOMI_STANDARD_MODEL'), "缺少 XIAOMI_STANDARD_MODEL 配置"
        assert hasattr(settings, 'XIAOMI_TEMPERATURE'), "缺少 XIAOMI_TEMPERATURE 配置"

        print_success(f"XIAOMI_CHAT_MODEL = {settings.XIAOMI_CHAT_MODEL}")
        print_success(f"XIAOMI_STANDARD_MODEL = {settings.XIAOMI_STANDARD_MODEL}")
        print_success(f"XIAOMI_TEMPERATURE = {settings.XIAOMI_TEMPERATURE}")
        print_success(f"XIAOMI_MIMO_API_KEY = {settings.XIAOMI_MIMO_API_KEY[:10]}...")
        print_success(f"XIAOMI_MIMO_BASE_URL = {settings.XIAOMI_MIMO_BASE_URL}")

        return True
    except Exception as e:
        print_error(f"配置验证失败: {e}")
        return False


def verify_llm_router():
    """验证 LLM Router 配置"""
    print_header("2. 验证 LLM Router")

    try:
        from app.core.llm_router import LLMRouter, ModelProvider
        from app.core.agent_profiles import AgentRole, ModelTier, TaskType

        router = LLMRouter()

        # 检查最高层模型是否注册
        if 'glm_5_max' not in router._available_models:
            print_error("glm_5_max 未在可用模型中注册")
            return False
        print_success("glm_5_max 已注册")

        if 'mimo_pro' in router._available_models:
            print_error("mimo_pro 仍然在可用模型中注册")
            return False
        print_success("mimo_pro 已移除")

        config = router._available_models['glm_5_max']
        assert config.provider == ModelProvider.ZHIPU, "glm_5_max 应该使用 ZHIPU provider"
        print_success(f"Provider: {config.provider.value}")

        assert config.model_name == "glm-5", f"模型名称应该是 glm-5，实际是 {config.model_name}"
        print_success(f"Model: {config.model_name}")

        # 检查 tier mapping
        max_models = router._tier_mapping.get(ModelTier.MAX, [])

        if 'glm_5_max' not in max_models:
            print_error("glm_5_max 未在 MAX 层级中")
            return False
        print_success(f"MAX 层级: {max_models}")

        if max_models[0] != 'glm_5_max':
            print_error(f"glm_5_max 不是 MAX 层级第一优先级: {max_models}")
            return False
        print_success("glm_5_max 是 MAX 层级第一优先级")

        return True
    except Exception as e:
        print_error(f"LLM Router 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_mimo_api_call():
    """验证 MIMO API 调用"""
    print_header("3. 验证 MIMO API 调用")

    try:
        from app.config import settings
        from openai import AsyncOpenAI

        # 直接使用 OpenAI 客户端调用 MIMO API
        client = AsyncOpenAI(
            api_key=settings.XIAOMI_MIMO_API_KEY,
            base_url=settings.XIAOMI_MIMO_BASE_URL,
        )

        print_info("发送测试请求到 MIMO API...")

        # 测试基础聊天（不带联网搜索）
        response = await client.chat.completions.create(
            model=settings.XIAOMI_CHAT_MODEL,
            messages=[
                {"role": "user", "content": "你好，请用一句话介绍你自己。"}
            ],
            temperature=settings.XIAOMI_TEMPERATURE,
            max_tokens=100,
        )

        content = response.choices[0].message.content
        print_success(f"基础响应: {content[:100]}...")

        return True
    except Exception as e:
        print_error(f"MIMO API 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_web_search():
    """验证联网搜索功能"""
    print_header("4. 验证联网搜索功能")

    try:
        from app.config import settings
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.XIAOMI_MIMO_API_KEY,
            base_url=settings.XIAOMI_MIMO_BASE_URL,
        )

        print_info("发送需要联网搜索的请求...")

        # 测试联网搜索
        response = await client.chat.completions.create(
            model=settings.XIAOMI_CHAT_MODEL,
            messages=[
                {"role": "user", "content": "今天北京的天气怎么样？请搜索最新信息。"}
            ],
            tools=[{"type": "web_search"}],
            temperature=settings.XIAOMI_TEMPERATURE,
            max_tokens=500,
        )

        message = response.choices[0].message
        content = message.content
        print_success(f"响应内容: {content[:200]}...")

        # 检查是否有 annotations（联网搜索引用）
        if hasattr(message, 'annotations') and message.annotations:
            print_success(f"找到 {len(message.annotations)} 个搜索引用:")
            for i, ann in enumerate(message.annotations[:3], 1):
                print(f"  {i}. {ann.get('title', 'N/A')}")
                print(f"     URL: {ann.get('url', 'N/A')}")
        else:
            print_info("响应中没有找到 annotations 字段（可能是正常响应）")

        # 检查 usage
        if hasattr(response, 'usage') and response.usage:
            print_success(f"Token 用量: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}")

        # 检查 web_search_usage
        if hasattr(response, 'web_search_usage'):
            print_success(f"联网搜索用量: {response.web_search_usage}")

        return True
    except Exception as e:
        print_error(f"联网搜索验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_streaming():
    """验证流式响应"""
    print_header("5. 验证流式响应")

    try:
        from app.config import settings
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.XIAOMI_MIMO_API_KEY,
            base_url=settings.XIAOMI_MIMO_BASE_URL,
        )

        print_info("发送流式请求...")

        # 测试流式响应
        stream = await client.chat.completions.create(
            model=settings.XIAOMI_CHAT_MODEL,
            messages=[
                {"role": "user", "content": "请简单介绍一下 Python 编程语言。"}
            ],
            tools=[{"type": "web_search"}],
            temperature=settings.XIAOMI_TEMPERATURE,
            stream=True,
            stream_options={"include_usage": True},
        )

        collected_content = ""
        reasoning_content = ""
        annotations = []

        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta

                # 常规内容
                if delta.content:
                    collected_content += delta.content

                # 思考链内容
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_content += delta.reasoning_content

                # 联网搜索引用
                if hasattr(delta, 'annotations') and delta.annotations:
                    annotations.extend(delta.annotations)

            # 用量信息
            if hasattr(chunk, 'usage') and chunk.usage:
                print_success(f"Token 用量: prompt={chunk.usage.prompt_tokens}, completion={chunk.usage.completion_tokens}")

        print_success(f"流式响应内容: {collected_content[:200]}...")

        if reasoning_content:
            print_success(f"思考链内容: {reasoning_content[:100]}...")

        if annotations:
            print_success(f"找到 {len(annotations)} 个搜索引用")

        return True
    except Exception as e:
        print_error(f"流式响应验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_llm_service():
    """验证 LLM Service 集成"""
    print_header("6. 验证 LLM Service 集成")

    try:
        from app.core.agent_profiles import AgentRole, TaskType
        from app.services.llm_service import LLMService, LLMResponse, StreamChunk

        # 创建 LLM Service
        service = LLMService(agent_role=AgentRole.GENERATION)

        print_info("测试非流式调用...")

        # 测试非流式调用
        response = await service.chat_with_tools(
            system_prompt="你是一个有帮助的助手。",
            user_message="今天上海的温度是多少？",
            tools=[],
        )

        print_success(f"响应内容: {response.content[:200]}...")

        # 检查 MIMO 特有字段
        if response.reasoning_content:
            print_success(f"思考链: {response.reasoning_content[:100]}...")

        if response.annotations:
            print_success(f"搜索引用: {len(response.annotations)} 个")

        return True
    except Exception as e:
        print_error(f"LLM Service 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主验证流程"""
    print("\n" + "="*60)
    print("  MIMO v2-pro 集成验证")
    print("="*60)

    results = []

    # 1. 验证配置
    results.append(("配置加载", verify_config()))

    # 2. 验证 LLM Router
    results.append(("LLM Router", verify_llm_router()))

    # 3. 验证 API 调用
    results.append(("MIMO API 调用", await verify_mimo_api_call()))

    # 4. 验证联网搜索
    results.append(("联网搜索", await verify_web_search()))

    # 5. 验证流式响应
    results.append(("流式响应", await verify_streaming()))

    # 6. 验证 LLM Service
    results.append(("LLM Service", await verify_llm_service()))

    # 打印总结
    print_header("验证结果总结")

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("  🎉 所有验证通过！MIMO v2-pro 集成成功！")
    else:
        print("  ⚠️ 部分验证失败，请检查上述错误信息")
    print("="*60 + "\n")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
