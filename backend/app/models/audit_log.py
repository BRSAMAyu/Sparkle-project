"""
Security Audit Log Models

安全审计日志模型，用于记录所有安全相关事件
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class SecurityAuditLog(Base):
    """安全审计日志表"""
    __tablename__ = "security_audit_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, index=True)

    # 事件信息
    event_type = Column(String(100), nullable=False, index=True)  # 事件类型
    threat_level = Column(String(20), nullable=False, index=True)  # 威胁级别

    # 用户信息
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)  # 支持IPv6
    user_agent = Column(Text, nullable=True)

    # 资源信息
    resource = Column(String(500), nullable=True, index=True)  # 访问的资源
    action = Column(String(100), nullable=True)  # 执行的操作

    # 事件详情
    details = Column(JSON, nullable=True)  # 事件详细信息

    # 时间戳
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="security_audit_logs")

    def __repr__(self):
        return f"<SecurityAuditLog {self.event_type} {self.timestamp}>"


class DataAccessLog(Base):
    """数据访问日志表"""
    __tablename__ = "data_access_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, index=True)

    # 用户信息
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)

    # 访问信息
    resource_type = Column(String(100), nullable=False, index=True)  # 资源类型
    resource_id = Column(String(100), nullable=False, index=True)  # 资源ID
    action = Column(String(50), nullable=False, index=True)  # 操作类型: read, write, delete等

    # 访问详情
    request_method = Column(String(10), nullable=True)  # HTTP方法
    request_path = Column(String(500), nullable=True)  # 请求路径
    request_params = Column(JSON, nullable=True)  # 请求参数
    response_status = Column(String(10), nullable=True)  # 响应状态

    # 时间戳
    accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="data_access_logs")

    def __repr__(self):
        return f"<DataAccessLog {self.user_id} {self.resource_type}/{self.resource_id} {self.action}>"


class SystemConfigChangeLog(Base):
    """系统配置变更日志表"""
    __tablename__ = "system_config_change_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, index=True)

    # 变更信息
    config_key = Column(String(200), nullable=False, index=True)  # 配置键
    old_value = Column(JSON, nullable=True)  # 旧值
    new_value = Column(JSON, nullable=False)  # 新值
    change_type = Column(String(50), nullable=False)  # 变更类型: create, update, delete

    # 变更者信息
    changed_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # 变更详情
    reason = Column(Text, nullable=True)  # 变更原因
    impact_level = Column(String(20), nullable=True)  # 影响级别: low, medium, high, critical

    # 时间戳
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    changer = relationship("User", back_populates="system_config_change_logs")

    def __repr__(self):
        return f"<SystemConfigChangeLog {self.config_key} {self.change_type}>"


class ComplianceCheckLog(Base):
    """合规性检查日志表"""
    __tablename__ = "compliance_check_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, index=True)

    # 检查信息
    check_type = Column(String(100), nullable=False, index=True)  # 检查类型
    check_name = Column(String(200), nullable=False)  # 检查名称
    standard = Column(String(100), nullable=True)  # 合规标准: GDPR, HIPAA, PCI-DSS等

    # 检查结果
    status = Column(String(20), nullable=False)  # 状态: passed, failed, warning
    details = Column(JSON, nullable=True)  # 检查详情
    findings = Column(JSON, nullable=True)  # 发现的问题

    # 执行信息
    executed_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    automated = Column(String(10), nullable=False, default="true")  # 是否自动执行

    # 时间戳
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 关系
    executor = relationship("User", back_populates="compliance_check_logs")

    def __repr__(self):
        return f"<ComplianceCheckLog {self.check_type} {self.status}>"


# 在User模型中添加关系（需要更新User模型）
# 在User类中添加以下关系：
# security_audit_logs = relationship("SecurityAuditLog", back_populates="user")
# data_access_logs = relationship("DataAccessLog", back_populates="user")
# system_config_change_logs = relationship("SystemConfigChangeLog", back_populates="changer", foreign_keys=[SystemConfigChangeLog.changed_by])
# compliance_check_logs = relationship("ComplianceCheckLog", back_populates="executor", foreign_keys=[ComplianceCheckLog.executed_by])