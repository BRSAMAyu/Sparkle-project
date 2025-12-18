"""
LLM Schemas
用于 AI 交互的宽容模式数据结构 (v2.2)

v2.2 增强:
- 中文数字转换 (一到九十九, 百)
- 时间单位换算 (小时 -> 分钟)
- 中文布尔值支持
- 日期标准化
"""
import re
from datetime import date, timedelta
from typing import Any, Optional, List
from pydantic import BaseModel, BeforeValidator, field_validator, Field
from typing_extensions import Annotated
from loguru import logger

# ==================== 中文数字映射 ====================

CN_NUM_MAP = {
    '零': 0, '〇': 0,
    '一': 1, '壹': 1,
    '二': 2, '贰': 2, '两': 2, '俩': 2,
    '三': 3, '叁': 3,
    '四': 4, '肆': 4,
    '五': 5, '伍': 5,
    '六': 6, '陆': 6,
    '七': 7, '柒': 7,
    '八': 8, '捌': 8,
    '九': 9, '玖': 9,
    '十': 10, '拾': 10,
    '百': 100, '佰': 100,
}


def _parse_chinese_number(s: str) -> Optional[int]:
    """
    解析中文数字 (支持 0-999)

    Examples:
    - "五" -> 5
    - "十五" -> 15
    - "二十" -> 20
    - "二十三" -> 23
    - "一百" -> 100
    - "一百二十三" -> 123
    - "三百五" -> 350 (口语中 "三百五" = 350)
    """
    s = s.strip()
    if not s:
        return None

    # 检查是否全是中文数字字符
    valid_chars = set(CN_NUM_MAP.keys())
    if not all(c in valid_chars for c in s):
        return None

    result = 0
    temp = 0

    for char in s:
        num = CN_NUM_MAP.get(char)
        if num is None:
            return None

        if num == 100:  # 百
            if temp == 0:
                temp = 1
            result += temp * 100
            temp = 0
        elif num == 10:  # 十
            if temp == 0:
                temp = 1
            result += temp * 10
            temp = 0
        else:
            temp = num

    result += temp

    # 处理口语习惯: "三百五" = 350, "二百三" = 230
    # 检测模式: X百Y (其中 Y 是个位数，且不是"零")
    if len(s) >= 3:
        hundred_idx = -1
        for i, c in enumerate(s):
            if c in ('百', '佰'):
                hundred_idx = i
                break

        if hundred_idx >= 0 and hundred_idx == len(s) - 2:
            # "百" 后面只有一个字符
            last_char = s[-1]
            last_num = CN_NUM_MAP.get(last_char, 0)
            # 如果最后一个字符是 1-9 的个位数，且不是"十"
            if 1 <= last_num <= 9:
                # 当前 result 是 X * 100 + Y，需要改成 X * 100 + Y * 10
                result = result - last_num + last_num * 10

    return result if result > 0 else (0 if s == '零' or s == '〇' else None)


def _extract_time_multiplier(s: str) -> tuple[str, int]:
    """
    提取时间单位并返回乘数

    Returns:
        (清理后的字符串, 乘数)

    Examples:
    - "1.5小时" -> ("1.5", 60)
    - "30分钟" -> ("30", 1)
    - "2h" -> ("2", 60)
    - "45" -> ("45", 1)
    """
    s = s.strip().lower()
    multiplier = 1

    # 小时单位
    hour_patterns = ['小时', 'hour', 'hours', 'hr', 'hrs', 'h']
    for pattern in hour_patterns:
        if pattern in s:
            multiplier = 60
            s = s.replace(pattern, '')
            break

    # 分钟单位 (需要在小时之后处理，避免 "h" 和 "min" 冲突)
    if multiplier == 1:
        minute_patterns = ['分钟', 'minute', 'minutes', 'min', 'mins', 'm', '分']
        for pattern in minute_patterns:
            if pattern in s:
                s = s.replace(pattern, '')
                break

    return s.strip(), multiplier


# ==================== 宽容类型转换器 ====================

def coerce_int(v: Any) -> int:
    """
    宽容的 int 转换 (v2.2 增强版)

    处理 LLM 常见输出：
    - 阿拉伯数字: "15" -> 15, 15.0 -> 15
    - 中文数字: "十五" -> 15, "四十五" -> 45
    - 带单位: "1.5小时" -> 90, "30分钟" -> 30, "2h" -> 120
    """
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)

    if isinstance(v, str):
        original = v
        s = v.strip()

        if not s:
            raise ValueError(f"Cannot coerce empty string to int")

        # 1. 提取时间单位和乘数
        s, multiplier = _extract_time_multiplier(s)

        # 2. 尝试直接转换为数字
        try:
            return int(float(s) * multiplier)
        except ValueError:
            pass

        # 3. 尝试解析中文数字
        cn_result = _parse_chinese_number(s)
        if cn_result is not None:
            return cn_result * multiplier

        # 4. Fallback: 正则提取第一个数字序列
        match = re.search(r'[\d.]+', original)
        if match:
            try:
                return int(float(match.group()) * multiplier)
            except ValueError:
                pass

        logger.warning(f"coerce_int fallback failed for: {original!r}")

    raise ValueError(f"Cannot coerce {v!r} to int")


def coerce_float(v: Any) -> float:
    """宽容的 float 转换"""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            pass
    raise ValueError(f"Cannot coerce {v!r} to float")


def coerce_bool(v: Any) -> bool:
    """
    宽容的 bool 转换 (v2.2 增强版)

    处理 LLM 常见输出：
    - 英文: "true", "yes", "on" -> True
    - 中文: "是", "对", "需要", "要", "好", "可以", "完成" -> True
    - 中文: "否", "不", "不要", "没", "没有", "不需要" -> False
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()

        # True 值
        true_values = {
            # 英文
            "true", "yes", "on", "1", "ok", "y",
            # 中文
            "是", "对", "是的", "对的", "需要", "要", "好", "好的",
            "可以", "行", "完成", "完成了", "已完成", "成功", "确定",
            "有", "正确", "同意", "可", "嗯", "对啊", "是啊"
        }

        # False 值
        false_values = {
            # 英文
            "false", "no", "off", "0", "n",
            # 中文
            "否", "不", "不是", "不对", "不要", "不需要", "不行",
            "没", "没有", "没完成", "未完成", "失败", "取消",
            "错", "错误", "不可以", "不好", "算了", "不用"
        }

        if s in true_values:
            return True
        if s in false_values:
            return False

        # 模糊匹配: 包含否定词
        negation_prefixes = ["不", "没", "未", "非", "无"]
        for prefix in negation_prefixes:
            if s.startswith(prefix):
                return False

    raise ValueError(f"Cannot coerce {v!r} to bool")


def coerce_str_list(v: Any) -> List[str]:
    """
    宽容的字符串列表转换

    处理：
    - "tag1" -> ["tag1"]
    - ["tag1", "tag2"] -> ["tag1", "tag2"]
    - "tag1, tag2" -> ["tag1", "tag2"]  # 逗号分隔
    """
    if isinstance(v, list):
        return [str(item).strip() for item in v if item]
    if isinstance(v, str):
        if "," in v:
            return [s.strip() for s in v.split(",") if s.strip()]
        return [v.strip()] if v.strip() else []
    return []


def coerce_date(v: Any) -> Optional[str]:
    """
    宽容的日期转换 (v2.2)

    将各种日期格式标准化为 ISO 格式 (YYYY-MM-DD)

    处理：
    - ISO 格式: "2025-01-15" -> "2025-01-15"
    - 斜杠格式: "2025/01/15" -> "2025-01-15"
    - 点号格式: "2025.01.15" -> "2025-01-15"
    - 中文格式: "2025年1月15日" -> "2025-01-15"
    - 相对日期: "明天", "后天", "下周一" 等
    """
    if v is None:
        return None

    if isinstance(v, date):
        return v.isoformat()

    if not isinstance(v, str):
        return None

    s = v.strip()
    if not s:
        return None

    today = date.today()

    # 1. 相对日期处理
    relative_map = {
        "今天": 0, "today": 0,
        "明天": 1, "明日": 1, "tomorrow": 1,
        "后天": 2, "后日": 2,
        "大后天": 3,
    }

    if s in relative_map:
        target = today + timedelta(days=relative_map[s])
        return target.isoformat()

    # 2. "X天后" / "X日后" 格式
    days_later_match = re.match(r'(\d+)\s*(天|日|days?)\s*(后|later)?', s)
    if days_later_match:
        days = int(days_later_match.group(1))
        target = today + timedelta(days=days)
        return target.isoformat()

    # 3. "下周X" 格式
    weekday_map = {
        "一": 0, "1": 0, "mon": 0, "monday": 0,
        "二": 1, "2": 1, "tue": 1, "tuesday": 1,
        "三": 2, "3": 2, "wed": 2, "wednesday": 2,
        "四": 3, "4": 3, "thu": 3, "thursday": 3,
        "五": 4, "5": 4, "fri": 4, "friday": 4,
        "六": 5, "6": 5, "sat": 5, "saturday": 5,
        "日": 6, "天": 6, "7": 6, "sun": 6, "sunday": 6,
    }

    next_week_match = re.match(r'下\s*周\s*(.)', s)
    if next_week_match:
        target_weekday = weekday_map.get(next_week_match.group(1).lower())
        if target_weekday is not None:
            current_weekday = today.weekday()
            days_ahead = target_weekday - current_weekday + 7
            target = today + timedelta(days=days_ahead)
            return target.isoformat()

    # 4. "这周X" / "本周X" 格式
    this_week_match = re.match(r'(这|本)\s*周\s*(.)', s)
    if this_week_match:
        target_weekday = weekday_map.get(this_week_match.group(2).lower())
        if target_weekday is not None:
            current_weekday = today.weekday()
            days_ahead = target_weekday - current_weekday
            if days_ahead < 0:
                days_ahead += 7  # 如果已过去，到下周
            target = today + timedelta(days=days_ahead)
            return target.isoformat()

    # 5. 各种日期格式标准化
    # 中文格式: 2025年1月15日 或 1月15日
    cn_full_match = re.match(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', s)
    if cn_full_match:
        year, month, day = cn_full_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    cn_short_match = re.match(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日?', s)
    if cn_short_match:
        month, day = cn_short_match.groups()
        return f"{today.year}-{int(month):02d}-{int(day):02d}"

    # 斜杠/点号格式
    date_match = re.match(r'(\d{4})[/.](\d{1,2})[/.](\d{1,2})', s)
    if date_match:
        year, month, day = date_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # ISO 格式 (已经标准)
    iso_match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', s)
    if iso_match:
        year, month, day = iso_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # 无法解析，返回原值并记录警告
    logger.warning(f"coerce_date: 无法解析日期 '{s}'，保留原值")
    return s


# ==================== 宽容类型别名 ====================

CoercedInt = Annotated[int, BeforeValidator(coerce_int)]
CoercedFloat = Annotated[float, BeforeValidator(coerce_float)]
CoercedBool = Annotated[bool, BeforeValidator(coerce_bool)]
CoercedStrList = Annotated[List[str], BeforeValidator(coerce_str_list)]
CoercedDate = Annotated[Optional[str], BeforeValidator(coerce_date)]


# ==================== LLM Action Schemas ====================

class CreateTaskParams(BaseModel):
    """创建任务参数 - 宽容模式 (v2.2)"""
    title: str
    type: str = "learning"
    estimated_minutes: CoercedInt = 15
    tags: CoercedStrList = []
    difficulty: CoercedInt = 3
    guide_content: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty")
        if len(v) > 100:
            logger.warning(f"任务标题过长 ({len(v)} 字符)，已截断为 100 字符")
            return v[:100]
        return v

    @field_validator("difficulty")
    @classmethod
    def difficulty_in_range(cls, v: int) -> int:
        """验证难度范围，超出范围时警告并修正"""
        if v < 1:
            logger.warning(f"难度值 {v} 低于最小值 1，已修正为 1")
            return 1
        if v > 5:
            logger.warning(f"难度值 {v} 超过最大值 5，已修正为 5")
            return 5
        return v

    @field_validator("estimated_minutes")
    @classmethod
    def minutes_in_range(cls, v: int) -> int:
        """
        验证时间范围 (v2.2)

        - 最小值: 2 分钟
        - 最大值: 480 分钟 (8小时) - 扩大上限以支持长时任务如模考
        - 超出范围时记录警告并修正
        """
        if v < 2:
            logger.warning(f"预计时间 {v} 分钟低于最小值 2，已修正为 2 分钟")
            return 2
        if v > 480:
            logger.warning(f"预计时间 {v} 分钟超过最大值 480 (8小时)，已修正为 480 分钟")
            return 480
        return v

    class Config:
        extra = "ignore"  # 忽略额外字段


class CreatePlanParams(BaseModel):
    """创建计划参数 - 宽容模式 (v2.2)"""
    name: str
    type: str = "sprint"
    target_date: CoercedDate = None  # v2.2: 自动日期标准化
    subject: Optional[str] = None
    daily_available_minutes: CoercedInt = 60

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("plan name cannot be empty")
        return v

    @field_validator("daily_available_minutes")
    @classmethod
    def daily_minutes_in_range(cls, v: int) -> int:
        """验证每日可用时间范围"""
        if v < 10:
            logger.warning(f"每日可用时间 {v} 分钟低于最小值 10，已修正为 10 分钟")
            return 10
        if v > 720:
            logger.warning(f"每日可用时间 {v} 分钟超过最大值 720 (12小时)，已修正为 720 分钟")
            return 720
        return v

    class Config:
        extra = "ignore"

class LLMResponse(BaseModel):
    assistant_message: Optional[str] = None
    actions: List[Any] = Field(default_factory=list)
    parse_degraded: bool = False
    degraded_reason: Optional[str] = None

    class Config:
        extra = "ignore"

