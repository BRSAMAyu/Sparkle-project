from __future__ import annotations

"""
内容审核服务
Content Moderation Service - 敏感词过滤、内容审核、违规处理

功能:
- Unicode正规化（对抗变体字符）
- 零宽字符过滤
- 全局敏感词库（带Redis缓存）
- 群组自定义敏感词
- 违规记录和自动处理
"""
import unicodedata
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import (
    Group,
    GroupMember,
    ModerationAction,
)


def _utcnow() -> datetime:
    """Return naive UTC datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


# ============ Unicode 正规化和清理 ============

def normalize_text(text: str) -> str:
    """
    Unicode正规化处理

    将变体字符、组合字符等转换为标准形式
    用于对抗使用特殊字符绕过过滤的行为
    """
    if not text:
        return text

    # NFKC正规化：兼容性分解后规范化
    normalized = unicodedata.normalize('NFKC', text)

    # 移除零宽字符
    zero_width_chars = [
        '\u200b',  # Zero Width Space
        '\u200c',  # Zero Width Non-Joiner
        '\u200d',  # Zero Width Joiner
        '\u200e',  # Left-to-Right Mark
        '\u200f',  # Right-to-Left Mark
        '\ufeff',  # Byte Order Mark
        '\u2060',  # Word Joiner
        '\u2061',  # Function Application
        '\u2062',  # Invisible Times
        '\u2063',  # Invisible Separator
        '\u2064',  # Invisible Plus
    ]

    for char in zero_width_chars:
        normalized = normalized.replace(char, '')

    # 移除不可见的控制字符
    normalized = ''.join(c for c in normalized if not unicodedata.category(c).startswith('C'))

    return normalized


def remove_invisible_chars(text: str) -> str:
    """移除所有不可见字符"""
    if not text:
        return text
    return ''.join(c for c in text if c.isprintable() or c.isspace())


# ============ 敏感词模型（简化版，实际应使用数据库表） ============

class ModerationKeyword:
    """
    敏感词模型（用于类型提示）

    实际存储在数据库中，这里只是示意
    """
    pass


class ContentModerationService:
    """内容审核服务"""

    # Redis缓存键前缀
    GLOBAL_KEYWORDS_KEY = "moderation:global_keywords"
    USER_VIOLATIONS_KEY = "moderation:user_violations:{user_id}"
    GROUP_KEYWORDS_KEY = "moderation:group_keywords:{group_id}"

    # 违规阈值
    WARN_THRESHOLD = 3  # 警告阈值
    MUTE_THRESHOLD = 5  # 禁言阈值
    BAN_THRESHOLD = 10  # 封禁阈值

    @staticmethod
    async def get_global_keywords(redis: redis.Redis | None = None) -> set[str]:
        """获取全局敏感词列表（带缓存）"""
        if redis:
            try:
                cached = await redis.get(ContentModerationService.GLOBAL_KEYWORDS_KEY)
                if cached:
                    return set(cached.split('\n'))
            except Exception as e:
                logger.warning(f"Failed to get cached keywords: {e}")

        # 从数据库加载（这里简化为硬编码示例）
        # 实际实现应从数据库的 moderation_keywords 表加载
        default_keywords = {
            # 政治敏感词
            "政治敏感词1", "政治敏感词2",
            # 色情词汇
            "色情词汇1", "色情词汇2",
            # 暴力词汇
            "暴力词汇1", "暴力词汇2",
            # 广告词
            "加微信", "加Q群", "私聊赚钱",
        }

        if redis:
            try:
                await redis.setex(
                    ContentModerationService.GLOBAL_KEYWORDS_KEY,
                    3600,  # 1小时缓存
                    '\n'.join(default_keywords)
                )
            except Exception as e:
                logger.warning(f"Failed to cache keywords: {e}")

        return default_keywords

    @staticmethod
    async def get_group_keywords(
        db: AsyncSession,
        group_id: UUID,
        redis: redis.Redis | None = None
    ) -> set[str]:
        """获取群组自定义敏感词"""
        cache_key = ContentModerationService.GROUP_KEYWORDS_KEY.format(group_id=group_id)

        if redis:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    return set(cached.split('\n')) if cached else set()
            except Exception as e:
                logger.warning(f"Failed to get cached group keywords: {e}")

        # 从群组设置加载
        group = await db.get(Group, group_id)
        keywords = set()
        if group and group.keyword_filters:
            keywords = set(group.keyword_filters)

        if redis:
            try:
                await redis.setex(
                    cache_key,
                    1800,  # 30分钟缓存
                    '\n'.join(keywords) if keywords else ''
                )
            except Exception as e:
                logger.warning(f"Failed to cache group keywords: {e}")

        return keywords

    @staticmethod
    async def check_content(
        db: AsyncSession,
        content: str,
        user_id: UUID,
        group_id: UUID | None = None,
        redis: redis.Redis | None = None
    ) -> dict[str, Any]:
        """
        检查内容是否包含敏感词

        Returns:
            {
                "is_clean": bool,
                "matched_keywords": list[str],
                "severity": str,  # low, medium, high
                "action": str  # none, warn, mute, ban
            }
        """
        if not content:
            return {"is_clean": True, "matched_keywords": [], "severity": "none", "action": "none"}

        # 正规化处理
        normalized_content = normalize_text(content)
        normalized_content = remove_invisible_chars(normalized_content)
        normalized_content = normalized_content.lower()

        # 获取敏感词列表
        global_keywords = await ContentModerationService.get_global_keywords(redis)
        group_keywords = set()
        if group_id:
            group_keywords = await ContentModerationService.get_group_keywords(db, group_id, redis)

        all_keywords = global_keywords | group_keywords

        # 匹配敏感词
        matched_keywords = []
        for keyword in all_keywords:
            normalized_keyword = normalize_text(keyword).lower()
            if normalized_keyword in normalized_content:
                matched_keywords.append(keyword)

        if not matched_keywords:
            return {"is_clean": True, "matched_keywords": [], "severity": "none", "action": "none"}

        # 确定严重程度
        severity = "low"
        if any(kw in global_keywords for kw in matched_keywords):
            severity = "high"
        elif len(matched_keywords) >= 3:
            severity = "medium"

        # 获取用户违规历史
        violation_count = await ContentModerationService.get_user_violations(user_id, redis)
        violation_count += 1

        # 确定处罚动作
        action = "none"
        if violation_count >= ContentModerationService.BAN_THRESHOLD or severity == "high":
            action = "ban"
        elif violation_count >= ContentModerationService.MUTE_THRESHOLD:
            action = "mute"
        elif violation_count >= ContentModerationService.WARN_THRESHOLD:
            action = "warn"

        # 记录违规
        await ContentModerationService.record_violation(
            user_id=user_id,
            content=content,
            matched_keywords=matched_keywords,
            severity=severity,
            redis=redis
        )

        return {
            "is_clean": False,
            "matched_keywords": matched_keywords,
            "severity": severity,
            "action": action,
            "violation_count": violation_count
        }

    @staticmethod
    async def record_violation(
        user_id: UUID,
        content: str,
        matched_keywords: list[str],
        severity: str,
        redis: redis.Redis | None = None
    ):
        """记录用户违规"""
        if not redis:
            return

        key = ContentModerationService.USER_VIOLATIONS_KEY.format(user_id=user_id)
        violation = {
            "timestamp": _utcnow().isoformat(),
            "content_preview": content[:100] if content else None,
            "matched_keywords": matched_keywords,
            "severity": severity
        }

        try:
            # 添加到违规列表
            await redis.rpush(key, str(violation))
            # 设置24小时过期
            await redis.expire(key, 86400)
        except Exception as e:
            logger.warning(f"Failed to record violation: {e}")

    @staticmethod
    async def get_user_violations(user_id: UUID, redis: redis.Redis | None = None) -> int:
        """获取用户24小时内的违规次数"""
        if not redis:
            return 0

        key = ContentModerationService.USER_VIOLATIONS_KEY.format(user_id=user_id)
        try:
            count = await redis.llen(key)
            return count
        except Exception as e:
            logger.warning(f"Failed to get user violations: {e}")
            return 0

    @staticmethod
    async def apply_moderation_action(
        db: AsyncSession,
        user_id: UUID,
        group_id: UUID,
        action: str,
        duration_minutes: int = 60
    ) -> bool:
        """
        应用审核处罚

        Args:
            db: 数据库会话
            user_id: 用户ID
            group_id: 群组ID
            action: 处罚动作 (warn, mute, kick, ban)
            duration_minutes: 禁言时长（分钟）

        Returns:
            是否成功
        """
        # 获取群成员
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False

        action_enum = ModerationAction(action)

        if action_enum == ModerationAction.WARN:
            member.warn_count += 1

        elif action_enum == ModerationAction.MUTE:
            member.is_muted = True
            member.mute_until = _utcnow() + datetime.timedelta(minutes=duration_minutes)

        elif action_enum == ModerationAction.KICK:
            member.soft_delete()

        elif action_enum == ModerationAction.BAN:
            member.is_muted = True
            member.mute_until = _utcnow() + datetime.timedelta(days=365)  # 1年
            # TRACKED(TD-008): 可能还需要加入全局黑名单

        await db.flush()
        return True

    @staticmethod
    async def invalidate_cache(redis: redis.Redis | None, group_id: UUID | None = None):
        """使缓存失效"""
        if not redis:
            return

        try:
            if group_id:
                cache_key = ContentModerationService.GROUP_KEYWORDS_KEY.format(group_id=group_id)
                await redis.delete(cache_key)
            else:
                await redis.delete(ContentModerationService.GLOBAL_KEYWORDS_KEY)
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")
