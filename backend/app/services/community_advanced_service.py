"""
高级社群功能服务层
Advanced Community Service - 加密、风控、搜索、离线队列等

包含:
- EncryptionService: 端到端加密密钥管理
- ModerationService: 群管理与风控
- MessageSearchService: 高级消息搜索
- OfflineQueueService: 离线消息队列
- FavoriteService: 消息收藏
- ForwardService: 消息转发
- BroadcastService: 跨群广播
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, text
from sqlalchemy.orm import selectinload

from app.models.community import (
    Group, GroupRole, GroupMember, GroupMessage, PrivateMessage,
    MessageType, UserEncryptionKey, MessageReport, MessageFavorite,
    BroadcastMessage, OfflineMessageQueue,
    ReportReason, ReportStatus, ModerationAction, OfflineMessageStatus
)
from app.schemas.community import (
    EncryptionKeyCreate, MessageReportCreate, MessageReportReview,
    MessageFavoriteCreate, MessageForwardRequest, BroadcastMessageCreate,
    MessageSearchRequest, GroupAnnouncementUpdate, GroupModerationSettings,
    MemberMuteRequest, MemberWarnRequest, OfflineMessageRetryRequest
)


class EncryptionService:
    """端到端加密密钥管理服务"""

    @staticmethod
    async def register_public_key(
        db: AsyncSession,
        user_id: UUID,
        data: EncryptionKeyCreate
    ) -> UserEncryptionKey:
        """注册用户公钥"""
        # 如果有相同设备的旧密钥，将其设为非活跃
        if data.device_id:
            await db.execute(
                text("""
                    UPDATE user_encryption_keys
                    SET is_active = false, updated_at = NOW()
                    WHERE user_id = :user_id AND device_id = :device_id AND is_active = true
                """),
                {"user_id": str(user_id), "device_id": data.device_id}
            )

        key = UserEncryptionKey(
            user_id=user_id,
            public_key=data.public_key,
            key_type=data.key_type,
            device_id=data.device_id,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=365)  # 1年有效期
        )
        db.add(key)
        await db.flush()
        await db.refresh(key)
        return key

    @staticmethod
    async def get_user_public_keys(
        db: AsyncSession,
        user_id: UUID
    ) -> List[UserEncryptionKey]:
        """获取用户的活跃公钥列表"""
        result = await db.execute(
            select(UserEncryptionKey).where(
                UserEncryptionKey.user_id == user_id,
                UserEncryptionKey.is_active == True,
                or_(
                    UserEncryptionKey.expires_at == None,
                    UserEncryptionKey.expires_at > datetime.utcnow()
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def revoke_key(
        db: AsyncSession,
        user_id: UUID,
        key_id: UUID
    ) -> bool:
        """撤销密钥"""
        result = await db.execute(
            select(UserEncryptionKey).where(
                UserEncryptionKey.id == key_id,
                UserEncryptionKey.user_id == user_id
            )
        )
        key = result.scalar_one_or_none()
        if not key:
            return False

        key.is_active = False
        await db.flush()
        return True

    @staticmethod
    def verify_signature(content: str, signature: str, public_key: str) -> bool:
        """
        验证消息签名

        注意: 这是一个占位实现，实际使用时需要集成真正的加密库
        如 cryptography 或 nacl
        """
        # TODO: 实现真正的签名验证
        # 示例使用 Ed25519:
        # from nacl.signing import VerifyKey
        # verify_key = VerifyKey(base64.b64decode(public_key))
        # verify_key.verify(content.encode(), base64.b64decode(signature))
        return True  # 占位返回


class ModerationService:
    """群管理与风控服务"""

    @staticmethod
    async def update_announcement(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        data: GroupAnnouncementUpdate
    ) -> Group:
        """更新群公告"""
        # 验证权限
        member = await ModerationService._get_admin_member(db, group_id, user_id)
        if not member:
            raise ValueError("无权操作")

        group = await Group.get_by_id(db, group_id)
        if not group:
            raise ValueError("群组不存在")

        group.announcement = data.announcement
        group.announcement_updated_at = datetime.utcnow()
        await db.flush()
        return group

    @staticmethod
    async def update_moderation_settings(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        data: GroupModerationSettings
    ) -> Group:
        """更新群管理设置"""
        member = await ModerationService._get_admin_member(db, group_id, user_id)
        if not member:
            raise ValueError("无权操作")

        group = await Group.get_by_id(db, group_id)
        if not group:
            raise ValueError("群组不存在")

        if data.keyword_filters is not None:
            group.keyword_filters = data.keyword_filters
        if data.mute_all is not None:
            group.mute_all = data.mute_all
        if data.slow_mode_seconds is not None:
            group.slow_mode_seconds = data.slow_mode_seconds

        await db.flush()
        return group

    @staticmethod
    async def mute_member(
        db: AsyncSession,
        group_id: UUID,
        operator_id: UUID,
        data: MemberMuteRequest
    ) -> GroupMember:
        """禁言成员"""
        operator = await ModerationService._get_admin_member(db, group_id, operator_id)
        if not operator:
            raise ValueError("无权操作")

        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == data.user_id,
                GroupMember.not_deleted_filter()
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise ValueError("目标用户不是群成员")

        # 不能禁言群主
        if target.role == GroupRole.OWNER:
            raise ValueError("不能禁言群主")

        # 管理员不能禁言管理员
        if target.role == GroupRole.ADMIN and operator.role != GroupRole.OWNER:
            raise ValueError("只有群主可以禁言管理员")

        target.is_muted = True
        target.mute_until = datetime.utcnow() + timedelta(minutes=data.duration_minutes)
        await db.flush()
        return target

    @staticmethod
    async def unmute_member(
        db: AsyncSession,
        group_id: UUID,
        operator_id: UUID,
        target_user_id: UUID
    ) -> GroupMember:
        """解除禁言"""
        operator = await ModerationService._get_admin_member(db, group_id, operator_id)
        if not operator:
            raise ValueError("无权操作")

        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == target_user_id,
                GroupMember.not_deleted_filter()
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise ValueError("目标用户不是群成员")

        target.is_muted = False
        target.mute_until = None
        await db.flush()
        return target

    @staticmethod
    async def warn_member(
        db: AsyncSession,
        group_id: UUID,
        operator_id: UUID,
        data: MemberWarnRequest
    ) -> GroupMember:
        """警告成员"""
        operator = await ModerationService._get_admin_member(db, group_id, operator_id)
        if not operator:
            raise ValueError("无权操作")

        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == data.user_id,
                GroupMember.not_deleted_filter()
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise ValueError("目标用户不是群成员")

        target.warn_count += 1
        await db.flush()
        return target

    @staticmethod
    async def check_keyword_filter(
        db: AsyncSession,
        group_id: UUID,
        content: str
    ) -> Tuple[bool, List[str]]:
        """检查敏感词"""
        group = await Group.get_by_id(db, group_id)
        if not group or not group.keyword_filters:
            return True, []

        matched_keywords = []
        for keyword in group.keyword_filters:
            if keyword.lower() in content.lower():
                matched_keywords.append(keyword)

        return len(matched_keywords) == 0, matched_keywords

    @staticmethod
    async def _get_admin_member(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID
    ) -> Optional[GroupMember]:
        """获取管理员成员"""
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.role.in_([GroupRole.OWNER, GroupRole.ADMIN]),
                GroupMember.not_deleted_filter()
            )
        )
        return result.scalar_one_or_none()


class ReportService:
    """举报服务"""

    @staticmethod
    async def create_report(
        db: AsyncSession,
        reporter_id: UUID,
        data: MessageReportCreate
    ) -> MessageReport:
        """创建举报"""
        if not data.group_message_id and not data.private_message_id:
            raise ValueError("必须指定举报的消息")

        report = MessageReport(
            reporter_id=reporter_id,
            group_message_id=data.group_message_id,
            private_message_id=data.private_message_id,
            reason=data.reason,
            description=data.description,
            status=ReportStatus.PENDING
        )
        db.add(report)
        await db.flush()
        await db.refresh(report)
        return report

    @staticmethod
    async def review_report(
        db: AsyncSession,
        reviewer_id: UUID,
        report_id: UUID,
        data: MessageReportReview
    ) -> MessageReport:
        """审核举报"""
        report = await MessageReport.get_by_id(db, report_id)
        if not report:
            raise ValueError("举报不存在")

        report.status = data.status
        report.action_taken = data.action_taken
        report.reviewed_by = reviewer_id
        report.reviewed_at = datetime.utcnow()
        await db.flush()
        return report

    @staticmethod
    async def get_pending_reports(
        db: AsyncSession,
        group_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[MessageReport]:
        """获取待处理的举报"""
        query = select(MessageReport).where(
            MessageReport.status == ReportStatus.PENDING,
            MessageReport.not_deleted_filter()
        ).options(
            selectinload(MessageReport.reporter),
            selectinload(MessageReport.group_message)
        ).order_by(MessageReport.created_at.asc()).limit(limit)

        if group_id:
            query = query.join(GroupMessage).where(GroupMessage.group_id == group_id)

        result = await db.execute(query)
        return list(result.scalars().all())


class FavoriteService:
    """消息收藏服务"""

    @staticmethod
    async def add_favorite(
        db: AsyncSession,
        user_id: UUID,
        data: MessageFavoriteCreate
    ) -> MessageFavorite:
        """添加收藏"""
        if not data.group_message_id and not data.private_message_id:
            raise ValueError("必须指定收藏的消息")

        # 检查是否已收藏
        query = select(MessageFavorite).where(
            MessageFavorite.user_id == user_id,
            MessageFavorite.not_deleted_filter()
        )
        if data.group_message_id:
            query = query.where(MessageFavorite.group_message_id == data.group_message_id)
        if data.private_message_id:
            query = query.where(MessageFavorite.private_message_id == data.private_message_id)

        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise ValueError("已收藏该消息")

        favorite = MessageFavorite(
            user_id=user_id,
            group_message_id=data.group_message_id,
            private_message_id=data.private_message_id,
            note=data.note,
            tags=data.tags
        )
        db.add(favorite)
        await db.flush()
        await db.refresh(favorite)
        return favorite

    @staticmethod
    async def remove_favorite(
        db: AsyncSession,
        user_id: UUID,
        favorite_id: UUID
    ) -> bool:
        """移除收藏"""
        result = await db.execute(
            select(MessageFavorite).where(
                MessageFavorite.id == favorite_id,
                MessageFavorite.user_id == user_id,
                MessageFavorite.not_deleted_filter()
            )
        )
        favorite = result.scalar_one_or_none()
        if not favorite:
            return False

        await favorite.delete(db, soft=True)
        return True

    @staticmethod
    async def get_favorites(
        db: AsyncSession,
        user_id: UUID,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MessageFavorite]:
        """获取收藏列表"""
        query = select(MessageFavorite).where(
            MessageFavorite.user_id == user_id,
            MessageFavorite.not_deleted_filter()
        ).options(
            selectinload(MessageFavorite.group_message),
            selectinload(MessageFavorite.private_message)
        ).order_by(desc(MessageFavorite.created_at)).limit(limit).offset(offset)

        # TODO: 实现标签过滤 (JSON 数组包含查询)

        result = await db.execute(query)
        return list(result.scalars().all())


class ForwardService:
    """消息转发服务"""

    @staticmethod
    async def forward_message(
        db: AsyncSession,
        user_id: UUID,
        data: MessageForwardRequest
    ) -> Any:
        """转发消息"""
        if not data.target_group_id and not data.target_user_id:
            raise ValueError("必须指定转发目标")

        # 获取源消息
        if data.source_type == "group":
            source = await db.get(GroupMessage, data.source_message_id)
            if not source or source.is_deleted or source.is_revoked:
                raise ValueError("源消息不存在")
        else:
            source = await db.get(PrivateMessage, data.source_message_id)
            if not source or source.is_deleted or source.is_revoked:
                raise ValueError("源消息不存在")

        # 更新源消息转发计数
        source.forward_count += 1

        # 创建转发消息
        if data.target_group_id:
            # 验证是否是群成员
            member_result = await db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == data.target_group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.not_deleted_filter()
                )
            )
            if not member_result.scalar_one_or_none():
                raise ValueError("不是目标群组成员")

            forwarded = GroupMessage(
                group_id=data.target_group_id,
                sender_id=user_id,
                message_type=source.message_type,
                content=data.comment if data.comment else source.content,
                content_data=source.content_data,
                forwarded_from_id=data.source_message_id if data.source_type == "group" else None
            )
            db.add(forwarded)
        else:
            forwarded = PrivateMessage(
                sender_id=user_id,
                receiver_id=data.target_user_id,
                message_type=source.message_type,
                content=data.comment if data.comment else source.content,
                content_data=source.content_data,
                forwarded_from_id=data.source_message_id if data.source_type == "private" else None
            )
            db.add(forwarded)

        await db.flush()
        await db.refresh(forwarded)
        return forwarded


class BroadcastService:
    """跨群广播服务"""

    @staticmethod
    async def create_broadcast(
        db: AsyncSession,
        user_id: UUID,
        data: BroadcastMessageCreate
    ) -> BroadcastMessage:
        """创建跨群广播"""
        # 验证用户是否是所有目标群组的管理员
        for group_id in data.target_group_ids:
            member_result = await db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.role.in_([GroupRole.OWNER, GroupRole.ADMIN]),
                    GroupMember.not_deleted_filter()
                )
            )
            if not member_result.scalar_one_or_none():
                raise ValueError(f"无权在群组 {group_id} 中发送广播")

        # 创建广播记录
        broadcast = BroadcastMessage(
            sender_id=user_id,
            content=data.content,
            content_data=data.content_data,
            target_group_ids=[str(gid) for gid in data.target_group_ids],
            delivered_count=0
        )
        db.add(broadcast)
        await db.flush()

        # 在每个群组中创建消息
        for group_id in data.target_group_ids:
            message = GroupMessage(
                group_id=group_id,
                sender_id=user_id,
                message_type=MessageType.BROADCAST,
                content=data.content,
                content_data={
                    **(data.content_data or {}),
                    "broadcast_id": str(broadcast.id)
                }
            )
            db.add(message)
            broadcast.delivered_count += 1

        await db.flush()
        await db.refresh(broadcast)
        return broadcast


class MessageSearchService:
    """高级消息搜索服务"""

    @staticmethod
    async def search_group_messages(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        data: MessageSearchRequest
    ) -> Dict[str, Any]:
        """搜索群消息"""
        # 验证是否是群成员
        member_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        if not member_result.scalar_one_or_none():
            raise ValueError("不是群组成员")

        # 构建查询
        query = select(GroupMessage).where(
            GroupMessage.group_id == group_id,
            GroupMessage.not_deleted_filter(),
            GroupMessage.is_revoked == False
        )

        # 应用过滤条件
        if data.keyword:
            # 使用全文搜索
            query = query.where(
                func.to_tsvector('simple', func.coalesce(GroupMessage.content, '')).op('@@')(
                    func.plainto_tsquery('simple', data.keyword)
                )
            )

        if data.sender_id:
            query = query.where(GroupMessage.sender_id == data.sender_id)

        if data.start_date:
            query = query.where(GroupMessage.created_at >= data.start_date)

        if data.end_date:
            query = query.where(GroupMessage.created_at <= data.end_date)

        if data.message_types:
            query = query.where(GroupMessage.message_type.in_(data.message_types))

        if data.topic:
            query = query.where(GroupMessage.topic == data.topic)

        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (data.page - 1) * data.page_size
        query = query.options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to)
        ).order_by(desc(GroupMessage.created_at)).limit(data.page_size).offset(offset)

        result = await db.execute(query)
        messages = list(result.scalars().all())

        return {
            "messages": messages,
            "total": total,
            "page": data.page,
            "page_size": data.page_size,
            "has_more": offset + len(messages) < total
        }

    @staticmethod
    async def get_topics(
        db: AsyncSession,
        group_id: UUID
    ) -> List[Dict[str, Any]]:
        """获取群组话题列表"""
        result = await db.execute(
            select(
                GroupMessage.topic,
                func.count(GroupMessage.id).label("message_count")
            ).where(
                GroupMessage.group_id == group_id,
                GroupMessage.topic != None,
                GroupMessage.not_deleted_filter()
            ).group_by(GroupMessage.topic).order_by(desc("message_count")).limit(50)
        )

        return [{"topic": row[0], "message_count": row[1]} for row in result.all()]


class OfflineQueueService:
    """离线消息队列服务"""

    @staticmethod
    async def enqueue_message(
        db: AsyncSession,
        user_id: UUID,
        client_nonce: str,
        message_type: str,
        target_id: UUID,
        payload: Dict[str, Any],
        expires_in_hours: int = 24
    ) -> OfflineMessageQueue:
        """将消息加入离线队列"""
        # 检查去重
        existing = await db.execute(
            select(OfflineMessageQueue).where(
                OfflineMessageQueue.user_id == user_id,
                OfflineMessageQueue.client_nonce == client_nonce
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("消息已存在（重复nonce）")

        message = OfflineMessageQueue(
            user_id=user_id,
            client_nonce=client_nonce,
            message_type=message_type,
            target_id=target_id,
            payload=payload,
            status=OfflineMessageStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_pending_messages(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 50
    ) -> List[OfflineMessageQueue]:
        """获取待发送的离线消息"""
        result = await db.execute(
            select(OfflineMessageQueue).where(
                OfflineMessageQueue.user_id == user_id,
                OfflineMessageQueue.status == OfflineMessageStatus.PENDING,
                or_(
                    OfflineMessageQueue.expires_at == None,
                    OfflineMessageQueue.expires_at > datetime.utcnow()
                )
            ).order_by(OfflineMessageQueue.created_at.asc()).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def mark_as_sent(
        db: AsyncSession,
        message_id: UUID
    ) -> bool:
        """标记消息已发送"""
        result = await db.execute(
            select(OfflineMessageQueue).where(OfflineMessageQueue.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            return False

        message.status = OfflineMessageStatus.SENT
        await db.flush()
        return True

    @staticmethod
    async def mark_as_failed(
        db: AsyncSession,
        message_id: UUID,
        error: str
    ) -> bool:
        """标记消息发送失败"""
        result = await db.execute(
            select(OfflineMessageQueue).where(OfflineMessageQueue.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            return False

        message.status = OfflineMessageStatus.FAILED
        message.error_message = error
        message.retry_count += 1
        message.last_retry_at = datetime.utcnow()
        await db.flush()
        return True

    @staticmethod
    async def retry_messages(
        db: AsyncSession,
        user_id: UUID,
        data: OfflineMessageRetryRequest
    ) -> List[OfflineMessageQueue]:
        """重试失败的消息"""
        result = await db.execute(
            select(OfflineMessageQueue).where(
                OfflineMessageQueue.id.in_(data.message_ids),
                OfflineMessageQueue.user_id == user_id,
                OfflineMessageQueue.status == OfflineMessageStatus.FAILED
            )
        )
        messages = list(result.scalars().all())

        for message in messages:
            message.status = OfflineMessageStatus.PENDING
            message.error_message = None

        await db.flush()
        return messages

    @staticmethod
    async def cleanup_expired(
        db: AsyncSession
    ) -> int:
        """清理过期消息"""
        from sqlalchemy import update

        result = await db.execute(
            update(OfflineMessageQueue).where(
                OfflineMessageQueue.status == OfflineMessageStatus.PENDING,
                OfflineMessageQueue.expires_at < datetime.utcnow()
            ).values(status=OfflineMessageStatus.EXPIRED)
        )
        return result.rowcount

    @staticmethod
    async def get_failed_messages(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 50
    ) -> List[OfflineMessageQueue]:
        """获取失败的消息列表（用于批量重试UI）"""
        result = await db.execute(
            select(OfflineMessageQueue).where(
                OfflineMessageQueue.user_id == user_id,
                OfflineMessageQueue.status == OfflineMessageStatus.FAILED
            ).order_by(desc(OfflineMessageQueue.created_at)).limit(limit)
        )
        return list(result.scalars().all())
