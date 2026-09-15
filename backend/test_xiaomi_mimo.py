"""
重新验证 XiaoMi MIMO API Key
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings


async def test_xiaomi_mimo():
    """测试 XiaoMi MIMO API Key"""
    print("\n" + "=" * 60)
    print("🔍 重新验证 XiaoMi MIMO API Key")
    print("=" * 60)

    # 检查配置
    print(f"\n📋 配置信息:")
    print(f"  - API Key: {settings.XIAOMI_MIMO_API_KEY[:20]}...")
    print(f"  - Base URL: {settings.XIAOMI_MIMO_BASE_URL}")
    print(f"  - Chat Model: {settings.XIAOMI_CHAT_MODEL}")

    if not settings.XIAOMI_MIMO_API_KEY or settings.XIAOMI_MIMO_API_KEY == "your_xiaomi_mimo_api_key":
        print(f"\n❌ API Key 未配置或为默认值")
        return False

    # 测试 API 调用
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.XIAOMI_MIMO_API_KEY,
            base_url=settings.XIAOMI_MIMO_BASE_URL
        )

        print(f"\n🔄 正在测试 API 调用...")

        response = await client.chat.completions.create(
            model=settings.XIAOMI_CHAT_MODEL,
            messages=[
                {"role": "user", "content": "你好，请简单介绍一下你自己。"}
            ],
            max_tokens=50,
            temperature=0.3
        )

        content = response.choices[0].message.content

        print(f"\n✅ XiaoMi MIMO API 测试成功！")
        print(f"   完整响应: {content}")
        print(f"   模型: {settings.XIAOMI_CHAT_MODEL}")
        print(f"   Token 使用: {response.usage.total_tokens} tokens")

        return True

    except Exception as e:
        error_str = str(e)
        print(f"\n❌ XiaoMi MIMO API 测试失败")
        print(f"   错误: {error_str}")

        # 分析错误
        if "401" in error_str or "Invalid API Key" in error_str:
            print(f"\n   💡 可能原因:")
            print(f"      1. API Key 已过期或失效")
            print(f"      2. API Key 格式不正确")
            print(f"           3. API Key 权限不足")
        elif "timeout" in error_str.lower():
            print(f"\n   💡 可能原因: 网络超时")
        elif "connection" in error_str.lower():
            print(f"\n   💡 可能原因: 网络连接问题")

        return False


async def main():
    """主函数"""
    success = await test_xiaomi_mimo()

    print(f"\n" + "=" * 60)
    if success:
        print("✅ XiaoMi MIMO API Key 有效")
        print("\n💡 建议操作:")
        print("  1. 恢复 backend/.env 中的 XiaoMi MIMO 配置")
        print("  2. 在 llm_router.py 中重新添加 xiaomi_chat 到 FAST tier")
        print("  3. 使用 XiaoMi MIMO 作为快速响应模型")
    else:
        print("❌ XiaoMi MIMO API Key 无效")
        print("\n💡 建议操作:")
        print("  1. 保持 XiaoMi MIMO 禁用状态")
        print("  2. 使用 zhipu_flash 作为 FAST tier 模型")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
