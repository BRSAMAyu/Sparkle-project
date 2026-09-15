from app.orchestration.prompts import _estimate_prompt_tokens


def test_estimate_prompt_tokens_accounts_for_cjk_density():
    chinese_text = "这是一个用于测试中文 token 估算的长句子。"
    ascii_text = "this is a sentence used to test token estimation."

    assert _estimate_prompt_tokens(chinese_text) > len(chinese_text) // 4
    assert _estimate_prompt_tokens(chinese_text) > _estimate_prompt_tokens(ascii_text[: len(chinese_text)])
