"""A-05 · Aurora policy patch store（aurora_policy_patches 表）。

存储真源 = policy patch 行本身（六面白名单 + 生命周期状态的持久面）：
- **revoke ≠ 删除**：撤销是状态迁移（state=revoked + revoked_at + 审计
  history 保留），行永不物理删除——「用户纠正可撤销」的审计依据是行内
  append-only ``transition_history``，不是会消失的 outbox；
- 幂等：``uq_policy_patch_once (patch_id)``——patch_id 内容寻址
  （core ``derive_policy_patch_id``），同内容重提议命中唯一约束（服务层
  返回既有行，不双写）；
- 枚举列不带 DB CHECK（X-01/D-05 同款纪律：封闭词表由应用层契约强制——
  core/policy_patch.py 的 fail-closed 验证是唯一写入路径）。

契约真源：backend/app/core/policy_patch.py（aurora_policy_patch.v1）。
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class PolicyPatchRecord(BaseModel):
    """id/created_at/updated_at/deleted_at 由 BaseModel 提供（软删除口径；
    本表不使用软删——revoked/rejected 是显式终态，删除面（M-07）不适用）。"""

    __tablename__ = "aurora_policy_patches"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # -- patch 身份（内容寻址；core derive_policy_patch_id 派生）--------------
    patch_id = Column(String(64), nullable=False, unique=True, index=True)
    surface = Column(String(32), nullable=False)  # 六面白名单（POLICY_PATCH_SURFACES）
    payload = Column(JSON, nullable=False, default=dict)  # 单键面 schema（V2/V3 fail-closed）

    # -- 情境 scope（可选约束；D-05 切片词表成员或 NULL=不限）----------------
    scope_goal_type = Column(String(32), nullable=True)
    scope_friction_tag = Column(String(40), nullable=True)

    # -- 生命周期 ----------------------------------------------------------------
    state = Column(String(24), nullable=False, default="candidate", index=True)
    provenance = Column(String(32), nullable=False, default="decision_loop")

    # -- 证据面（evidence 门核验后的镜像；真源在 M-06/D-05）--------------------
    evidence_refs = Column(JSON, nullable=False, default=list)  # memory://experience/… | decision://aurora_…
    evidence_tier = Column(String(24), nullable=True)  # D-05 档位（核验后回填）
    evidence_verified_at = Column(DateTime, nullable=True)

    # -- 确认 / 生效 / 撤销 / 过期 ------------------------------------------------
    user_confirmed = Column(Boolean, nullable=False, default=False)
    confirmed_at = Column(DateTime, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String(200), nullable=True)

    # -- 审计（append-only；revoke 即时生效且审计永久保留）----------------------
    transition_history = Column(JSON, nullable=False, default=list)

    user = relationship("User", backref="aurora_policy_patches")
