"""
直接使用根目录 .env 中的 XiaoMi MIMO API Key 进行测试
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# 直接从根目录 .env 读取 XiaoMi MIMO API Key
root_env_path = "/Users/a/code/sparkle-flutter/.env"

with open(root_env_path) as f:
    content = f.read()
    for line in content.split('\n'):
        if line.startswith('XIAOMI_MIMO_API_KEY='):
            api_key = line.split('=')[1].strip()
            print(f"从根目录 .env 读取到 XiaoMi MIMO API Key")
            print(f"API Key: {api_key[:20]}...")

            if api_key and api_key != "your_xiaomi_mimo_api_key":
                asyncio.run(test_with_key(api_key))
            else:
                print("❌ API Key 未配置或为默认值")
            break


async def test_with_key(api_key: str):
    """使用指定的 API Key 测试"""
    print(f"\n" + "=" * 60)
    print("🔍 测试 XiaoMi MIMO API Key (根目录 .env)")
    print("=" * 60)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.xiaomimimo.com/v1"
        )

        print(f"\n🔄 正在测试 API 调用...")

        response = await client.chat.completions.create(
            model="mimo-v2-flash",
            messages=[
                {"role": "user", "content": "你好"}
            ],
            max_tokens=20
        )

        content = response.choices[0].message.content

        print(f"\n✅ XiaoMi MIMO API 测试成功！")
        print(f"   响应: {content}")
        print(f"   模型: mimo-v2-flash")
        print(f"   Token 使用: {response.usage.total_tokens} tokens")

        print(f"\n💡 API Key 有效！可以启用 XiaoMi MIMO 服务")

    except Exception as e:
        error_str = str(e)
        print(f"\n❌ XiaoMi MIMO API 测试失败")
        print(f"   错误: {error_str}")

        if "401" in error_str or "Invalid API Key" in error_str:
            print(f"\n   ⚠️  API Key 返回 401 错误，可能原因:")
            print(f"      1. API Key 已过期")
            print(f"      2. API Key 被吊销")
            print(f"      3. 账户余额不足")
            print(f"      4. API Key 格式错误")


if __name__ == "__main__":
    asyncio.run(test_with_key("sk-cmwqykkej4amo184uyqf700glf5xcqiuahremcrg2j2kb8o6o"))
