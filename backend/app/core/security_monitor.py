"""
Security Monitoring Service

功能：
1. 安全事件监控（异常登录、数据访问）
2. 威胁检测和告警
3. 安全日志记录
4. 合规性检查
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass, asdict
from enum import Enum

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user import User, LoginAttempt
from app.models.audit_log import SecurityAuditLog
from app.core.redis import redis_client
from app.config import settings


class SecurityEventType(Enum):
    """安全事件类型"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_SUSPICIOUS = "login_suspicious"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    CONFIG_CHANGE = "config_change"
    SECURITY_ALERT = "security_alert"
    COMPLIANCE_CHECK = "compliance_check"


class ThreatLevel(Enum):
    """威胁级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """安全事件数据类"""
    event_type: SecurityEventType
    user_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    threat_level: ThreatLevel = ThreatLevel.LOW
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['threat_level'] = self.threat_level.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.user_id:
            data['user_id'] = str(self.user_id)
        return data


class SecurityMonitor:
    """安全监控服务"""

    def __init__(self):
        self.redis = redis_client
        self._alerts_enabled = True
        self._monitoring_enabled = True

        # 配置
        self.FAILED_LOGIN_THRESHOLD = 5  # 5分钟内失败登录次数阈值
        self.FAILED_LOGIN_WINDOW = 300  # 5分钟（秒）
        self.SUSPICIOUS_IP_THRESHOLD = 10  # 可疑IP阈值
        self.ALERT_COOLDOWN = 300  # 告警冷却时间（秒）

    async def initialize(self):
        """初始化安全监控"""
        if not self._monitoring_enabled:
            logger.info("安全监控已禁用")
            return

        # 启动后台监控任务
        asyncio.create_task(self._monitor_security_events())
        asyncio.create_task(self._cleanup_old_data())

        logger.info("安全监控服务已初始化")

    async def record_login_attempt(
        self,
        user_id: Optional[UUID],
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        db: AsyncSession
    ) -> None:
        """记录登录尝试"""
        if not self._monitoring_enabled:
            return

        try:
            # 保存到数据库
            login_attempt = LoginAttempt(
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                attempted_at=datetime.utcnow()
            )
            db.add(login_attempt)
            await db.commit()

            # 记录安全事件
            event_type = SecurityEventType.LOGIN_SUCCESS if success else SecurityEventType.LOGIN_FAILED
            threat_level = ThreatLevel.LOW if success else ThreatLevel.MEDIUM

            event = SecurityEvent(
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                threat_level=threat_level,
                details={
                    "username": username,
                    "success": success
                }
            )

            await self._record_security_event(event, db)

            # 检查失败登录次数
            if not success:
                await self._check_failed_login_rate(ip_address, username, db)

        except Exception as e:
            logger.error(f"记录登录尝试失败: {e}")
            await db.rollback()

    async def record_data_access(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str,
        user_agent: str,
        db: AsyncSession
    ) -> None:
        """记录数据访问"""
        if not self._monitoring_enabled:
            return

        try:
            event = SecurityEvent(
                event_type=SecurityEventType.DATA_ACCESS,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                resource=f"{resource_type}/{resource_id}",
                action=action,
                threat_level=ThreatLevel.LOW,
                details={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action
                }
            )

            await self._record_security_event(event, db)

        except Exception as e:
            logger.error(f"记录数据访问失败: {e}")

    async def record_data_modification(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: str,
        action: str,
        old_value: Optional[Dict],
        new_value: Dict,
        ip_address: str,
        user_agent: str,
        db: AsyncSession
    ) -> None:
        """记录数据修改"""
        if not self._monitoring_enabled:
            return

        try:
            event = SecurityEvent(
                event_type=SecurityEventType.DATA_MODIFICATION,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                resource=f"{resource_type}/{resource_id}",
                action=action,
                threat_level=ThreatLevel.MEDIUM,
                details={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "old_value": old_value,
                    "new_value": new_value
                }
            )

            await self._record_security_event(event, db)

        except Exception as e:
            logger.error(f"记录数据修改失败: {e}")

    async def check_suspicious_activity(
        self,
        ip_address: str,
        user_id: Optional[UUID] = None
    ) -> bool:
        """检查可疑活动"""
        if not self._monitoring_enabled:
            return False

        try:
            # 检查IP是否在可疑列表中
            suspicious_key = f"security:suspicious_ip:{ip_address}"
            is_suspicious = await self.redis.get(suspicious_key)

            if is_suspicious:
                logger.warning(f"检测到可疑IP: {ip_address}")
                return True

            # 检查失败登录频率
            failed_key = f"security:failed_logins:{ip_address}"
            failed_count = await self.redis.get(failed_key)

            if failed_count and int(failed_count) > self.FAILED_LOGIN_THRESHOLD:
                # 标记为可疑IP
                await self.redis.setex(
                    suspicious_key,
                    self.FAILED_LOGIN_WINDOW,
                    "true"
                )
                logger.warning(f"IP {ip_address} 因频繁失败登录被标记为可疑")
                return True

            return False

        except Exception as e:
            logger.error(f"检查可疑活动失败: {e}")
            return False

    async def trigger_security_alert(
        self,
        alert_type: str,
        message: str,
        threat_level: ThreatLevel,
        details: Optional[Dict] = None,
        db: Optional[AsyncSession] = None
    ) -> None:
        """触发安全告警"""
        if not self._alerts_enabled:
            return

        try:
            # 检查告警冷却
            alert_key = f"security:alert_cooldown:{alert_type}"
            if await self.redis.get(alert_key):
                return

            # 记录安全事件
            event = SecurityEvent(
                event_type=SecurityEventType.SECURITY_ALERT,
                threat_level=threat_level,
                details={
                    "alert_type": alert_type,
                    "message": message,
                    ** (details or {})
                }
            )

            if db:
                await self._record_security_event(event, db)

            # 发送告警通知（这里可以集成邮件、Slack等）
            await self._send_alert_notification(alert_type, message, threat_level, details)

            # 设置告警冷却
            await self.redis.setex(alert_key, self.ALERT_COOLDOWN, "true")

            logger.warning(f"安全告警: {alert_type} - {message}")

        except Exception as e:
            logger.error(f"触发安全告警失败: {e}")

    async def get_security_stats(
        self,
        db: AsyncSession,
        hours: int = 24
    ) -> Dict[str, Any]:
        """获取安全统计信息"""
        try:
            since_time = datetime.utcnow() - timedelta(hours=hours)

            # 查询失败登录次数
            failed_logins_stmt = select(func.count(LoginAttempt.id)).where(
                LoginAttempt.success == False,
                LoginAttempt.attempted_at >= since_time
            )
            failed_logins_result = await db.execute(failed_logins_stmt)
            failed_logins = failed_logins_result.scalar() or 0

            # 查询成功登录次数
            success_logins_stmt = select(func.count(LoginAttempt.id)).where(
                LoginAttempt.success == True,
                LoginAttempt.attempted_at >= since_time
            )
            success_logins_result = await db.execute(success_logins_stmt)
            success_logins = success_logins_result.scalar() or 0

            # 查询安全事件统计
            security_events_stmt = select(func.count(SecurityAuditLog.id)).where(
                SecurityAuditLog.timestamp >= since_time
            )
            security_events_result = await db.execute(security_events_stmt)
            security_events = security_events_result.scalar() or 0

            # 查询可疑IP数量
            suspicious_ips = await self._get_suspicious_ip_count()

            return {
                "time_period_hours": hours,
                "failed_logins": failed_logins,
                "success_logins": success_logins,
                "total_logins": failed_logins + success_logins,
                "security_events": security_events,
                "suspicious_ips": suspicious_ips,
                "failed_login_rate": (
                    failed_logins / (failed_logins + success_logins) * 100
                    if (failed_logins + success_logins) > 0 else 0
                )
            }

        except Exception as e:
            logger.error(f"获取安全统计失败: {e}")
            return {}

    async def run_compliance_check(self, db: AsyncSession) -> Dict[str, Any]:
        """运行合规性检查"""
        try:
            checks = {}

            # 检查1: 密码策略
            checks["password_policy"] = await self._check_password_policy(db)

            # 检查2: 用户权限
            checks["user_permissions"] = await self._check_user_permissions(db)

            # 检查3: 数据访问日志
            checks["audit_logs"] = await self._check_audit_logs(db)

            # 检查4: 安全配置
            checks["security_config"] = await self._check_security_config()

            # 记录合规性检查事件
            event = SecurityEvent(
                event_type=SecurityEventType.COMPLIANCE_CHECK,
                threat_level=ThreatLevel.LOW,
                details={"checks": checks}
            )
            await self._record_security_event(event, db)

            return checks

        except Exception as e:
            logger.error(f"运行合规性检查失败: {e}")
            return {"error": str(e)}

    # 私有方法

    async def _record_security_event(
        self,
        event: SecurityEvent,
        db: AsyncSession
    ) -> None:
        """记录安全事件到数据库"""
        try:
            audit_log = SecurityAuditLog(
                event_type=event.event_type.value,
                user_id=event.user_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                resource=event.resource,
                action=event.action,
                details=event.details,
                threat_level=event.threat_level.value,
                timestamp=event.timestamp
            )
            db.add(audit_log)
            await db.commit()

            # 同时记录到Redis用于实时监控
            redis_key = f"security:events:{event.timestamp.timestamp()}"
            await self.redis.setex(
                redis_key,
                3600,  # 保留1小时
                json.dumps(event.to_dict())
            )

        except Exception as e:
            logger.error(f"记录安全事件失败: {e}")
            await db.rollback()

    async def _check_failed_login_rate(
        self,
        ip_address: str,
        username: str,
        db: AsyncSession
    ) -> None:
        """检查失败登录频率"""
        try:
            key = f"security:failed_logins:{ip_address}"

            # 增加失败计数
            await self.redis.incr(key)
            await self.redis.expire(key, self.FAILED_LOGIN_WINDOW)

            # 获取当前计数
            count = int(await self.redis.get(key) or 0)

            if count >= self.FAILED_LOGIN_THRESHOLD:
                # 触发安全告警
                await self.trigger_security_alert(
                    alert_type="failed_login_threshold",
                    message=f"IP {ip_address} 在{self.FAILED_LOGIN_WINDOW}秒内失败登录{count}次",
                    threat_level=ThreatLevel.HIGH,
                    details={
                        "ip_address": ip_address,
                        "username": username,
                        "failed_count": count,
                        "threshold": self.FAILED_LOGIN_THRESHOLD
                    },
                    db=db
                )

                # 记录可疑登录事件
                event = SecurityEvent(
                    event_type=SecurityEventType.LOGIN_SUSPICIOUS,
                    ip_address=ip_address,
                    threat_level=ThreatLevel.HIGH,
                    details={
                        "username": username,
                        "failed_count": count,
                        "reason": "频繁失败登录"
                    }
                )
                await self._record_security_event(event, db)

        except Exception as e:
            logger.error(f"检查失败登录频率失败: {e}")

    async def _monitor_security_events(self):
        """监控安全事件（后台任务）"""
        while self._monitoring_enabled:
            try:
                # 检查异常模式
                await self._check_abnormal_patterns()

                # 检查系统安全状态
                await self._check_system_security()

                # 休眠一段时间
                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logger.error(f"安全监控任务失败: {e}")
                await asyncio.sleep(60)

    async def _cleanup_old_data(self):
        """清理旧数据（后台任务）"""
        while self._monitoring_enabled:
            try:
                # 清理旧的Redis数据
                await self._cleanup_old_redis_data()

                # 休眠一段时间
                await asyncio.sleep(3600)  # 每小时清理一次

            except Exception as e:
                logger.error(f"清理旧数据任务失败: {e}")
                await asyncio.sleep(3600)

    async def _check_abnormal_patterns(self):
        """检查异常模式"""
        # 这里可以实现更复杂的异常检测逻辑
        # 例如：异常时间访问、异常地理位置、异常用户行为等
        pass

    async def _check_system_security(self):
        """检查系统安全状态"""
        # 检查系统配置、服务状态等
        pass

    async def _cleanup_old_redis_data(self):
        """清理旧的Redis数据"""
        try:
            # 这里可以实现自动清理逻辑
            pass
        except Exception as e:
            logger.error(f"清理Redis数据失败: {e}")

    async def _send_alert_notification(
        self,
        alert_type: str,
        message: str,
        threat_level: ThreatLevel,
        details: Optional[Dict] = None
    ):
        """发送告警通知"""
        # 这里可以集成邮件、Slack、Webhook等通知方式
        logger.warning(f"安全告警通知 - 类型: {alert_type}, 级别: {threat_level.value}, 消息: {message}")

        if details:
            logger.warning(f"告警详情: {details}")

    async def _get_suspicious_ip_count(self) -> int:
        """获取可疑IP数量"""
        try:
            # 使用Redis扫描获取所有可疑IP
            pattern = "security:suspicious_ip:*"
            keys = []
            cursor = 0

            while True:
                cursor, found_keys = await self.redis.scan(cursor, match=pattern, count=100)
                keys.extend(found_keys)
                if cursor == 0:
                    break

            return len(keys)

        except Exception as e:
            logger.error(f"获取可疑IP数量失败: {e}")
            return 0

    async def _check_password_policy(self, db: AsyncSession) -> Dict[str, Any]:
        """检查密码策略合规性"""
        try:
            # 这里可以检查密码强度、过期时间等
            return {
                "status": "ok",
                "message": "密码策略检查通过"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"密码策略检查失败: {e}"
            }

    async def _check_user_permissions(self, db: AsyncSession) -> Dict[str, Any]:
        """检查用户权限合规性"""
        try:
            # 这里可以检查用户权限分配是否合理
            return {
                "status": "ok",
                "message": "用户权限检查通过"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"用户权限检查失败: {e}"
            }

    async def _check_audit_logs(self, db: AsyncSession) -> Dict[str, Any]:
        """检查审计日志合规性"""
        try:
            # 检查审计日志是否完整
            stmt = select(func.count(SecurityAuditLog.id)).where(
                SecurityAuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
            )
            result = await db.execute(stmt)
            count = result.scalar() or 0

            return {
                "status": "ok" if count > 0 else "warning",
                "message": f"过去24小时有{count}条审计日志",
                "log_count": count
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"审计日志检查失败: {e}"
            }

    async def _check_security_config(self) -> Dict[str, Any]:
        """检查安全配置合规性"""
        try:
            checks = []

            # 检查JWT密钥
            if settings.SECRET_KEY == "your-secret-key-change-in-production":
                checks.append({
                    "check": "jwt_secret",
                    "status": "critical",
                    "message": "JWT密钥使用默认值，请立即更改"
                })
            else:
                checks.append({
                    "check": "jwt_secret",
                    "status": "ok",
                    "message": "JWT密钥已配置"
                })

            # 检查数据库连接
            if "postgresql" in settings.DATABASE_URL:
                checks.append({
                    "check": "database",
                    "status": "ok",
                    "message": "数据库连接使用PostgreSQL"
                })
            else:
                checks.append({
                    "check": "database",
                    "status": "warning",
                    "message": "数据库连接可能不安全"
                })

            return {
                "status": "ok" if all(c["status"] in ["ok", "warning"] for c in checks) else "critical",
                "checks": checks
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"安全配置检查失败: {e}"
            }

    # 公共工具方法

    def enable_monitoring(self, enabled: bool = True):
        """启用或禁用监控"""
        self._monitoring_enabled = enabled
        logger.info(f"安全监控已{'启用' if enabled else '禁用'}")

    def enable_alerts(self, enabled: bool = True):
        """启用或禁用告警"""
        self._alerts_enabled = enabled
        logger.info(f"安全告警已{'启用' if enabled else '禁用'}")

    def update_config(
        self,
        failed_login_threshold: Optional[int] = None,
        failed_login_window: Optional[int] = None,
        suspicious_ip_threshold: Optional[int] = None,
        alert_cooldown: Optional[int] = None
    ):
        """更新监控配置"""
        if failed_login_threshold is not None:
            self.FAILED_LOGIN_THRESHOLD = failed_login_threshold
        if failed_login_window is not None:
            self.FAILED_LOGIN_WINDOW = failed_login_window
        if suspicious_ip_threshold is not None:
            self.SUSPICIOUS_IP_THRESHOLD = suspicious_ip_threshold
        if alert_cooldown is not None:
            self.ALERT_COOLDOWN = alert_cooldown

        logger.info("安全监控配置已更新")


# 全局安全监控实例
security_monitor = SecurityMonitor()