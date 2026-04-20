"""Expression layer validator — rule-based, no LLM calls.

Validates that generated user messages satisfy TurnDecision constraints.
Used for reactive hard constraints enforcement.
"""
from __future__ import annotations

import re


# Patterns that indicate an empty/generic acknowledgment
_EMPTY_ACKNOWLEDGMENTS = {
    "好的", "嗯嗯", "谢谢", "了解", "明白", "知道了", "好的呢",
    "收到", "OK", "ok", "嗯", "好", "行", "嗯好", "好嘞",
    "谢谢老师", "谢谢AI", "谢谢你的建议", "谢谢你的帮助",
}

# Patterns that indicate a person mention
_PERSON_PATTERNS = re.compile(
    r"(妈妈|爸爸|同学|朋友|老师|同事|他|她|哥哥|姐姐|弟弟|妹妹|"
    r"室友|同桌|班长|学长|学姐|领导|老板|经理|辅导员|"
    r"闺蜜|哥们|师傅|徒弟|侄子|侄女|叔叔|阿姨|"
    r"我[们俩]|我们班|我们组|我们宿舍|我们团队|"
    r"张|李|王|刘|陈|杨|赵|黄|周|吴|徐|孙|胡|朱|高|林|何|郭|马|罗|梁|宋|郑|谢|韩|唐|冯|于|董|萧|程|曹|袁|邓|许|傅|沈|曾|彭|吕|苏|卢|蒋|蔡|贾|丁|魏|薛|叶|阎|余|潘|杜|戴|夏|钟|汪|田|任|姜|范|方|石|姚|谭|廖|邹|熊|金|陆|郝|孔|白|崔|康|毛|邱|秦|江|史|顾|侯|邵|孟|龙|万|段|雷|钱|汤|尹|黎|易|常|武|乔|贺|赖|龚|文)"
)

# Patterns that indicate a time anchor
_TIME_ANCHOR_PATTERNS = re.compile(
    r"(今天|明天|后天|大后天|昨天|前天|"
    r"这周|下周|上周|这周末|下周末|"
    r"今晚|明晚|今晚|"
    r"月底|年底|期末|寒假|暑假|"
    r"之前|以后|之后|"
    r"最近|将来|马上|"
    r"(\d+)月|(\d+)号|(\d+)日|"
    r"周一|周二|周三|周四|周五|周六|周日|"
    r"星期一|星期二|星期三|星期四|星期五|星期六|星期日)"
)

# Minimum message length that suggests actual content (not just "ok")
_MIN_SUBSTANTIVE_LENGTH = 12


def validate_expression(message: str, must_include: list[str], must_avoid: list[str]) -> tuple[bool, str]:
    """Validate a generated user message against TurnDecision constraints.

    Returns:
        (passed, reason) — True if message satisfies all constraints
    """
    if not message or not message.strip():
        return False, "empty_message"

    msg = message.strip()

    # Check must_avoid
    for avoidance in must_avoid:
        if avoidance == "empty_acknowledgment":
            if msg in _EMPTY_ACKNOWLEDGMENTS or len(msg) <= 3:
                return False, "empty_acknowledgment"
            # Check if message is just "好的" + trailing punctuation
            if msg.rstrip("。！？!?.") in _EMPTY_ACKNOWLEDGMENTS:
                return False, "empty_acknowledgment"
        elif avoidance == "thank_you_only":
            if re.match(r"^(谢谢|感谢|多谢).{0,5}$", msg):
                return False, "thank_you_only"

    # Check must_include
    for requirement in must_include:
        if requirement == "specific_reference":
            # Message must be substantive enough to contain a reference
            if len(msg) < _MIN_SUBSTANTIVE_LENGTH:
                return False, "too_short_for_reference"
        elif requirement == "mention_person":
            if not _PERSON_PATTERNS.search(msg):
                return False, "no_person_mentioned"
        elif requirement == "time_anchor":
            if not _TIME_ANCHOR_PATTERNS.search(msg):
                return False, "no_time_anchor"
        elif requirement == "opening_context":
            # First message should have some context
            if len(msg) < 8:
                return False, "opening_too_short"
        elif requirement == "clarification":
            if len(msg) < 10:
                return False, "clarification_too_short"

    return True, ""
