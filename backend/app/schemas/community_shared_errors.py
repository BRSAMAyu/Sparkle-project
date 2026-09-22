"""小队错题卡分享 schemas（D-COMM-5 · 错题卡互助分享）。

隐私与反抄答案裁决落在形状上：
- 分享请求体**只有 error_id**——分享内容一律服务端从 error_records 取
  真实内容（客户端不可伪造内容，也不可选字段）；
- 列表/详情响应是服务端白名单投影（见 services/
  community_shared_error_service.py::_build_content_snapshot）：
  题目/科目/知识点/错因/掌握度快照——**不含** correct_answer /
  user_answer / 解题思路（备考互助≠抄答案）；
- 图片仅回 ``sparkle-file://`` 引用原样字符串，走既有 MinIO 鉴权面，
  不解析、不新开公共 URL。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 每成员在小队内的在册分享上限（防刷量防线，非榜分——分享零榜分/零光子）。
# 小队 3-8 人、期末周期 1-2 周，50 张/人远超正常互助用量，只拦滥用。
MAX_ACTIVE_SHARED_ERRORS_PER_MEMBER = 50

# 列表分页上限（照 D-COMM-4 榜分页防御惯例：形状防御，非业务语义）。
SHARED_ERRORS_DEFAULT_LIMIT = 50
SHARED_ERRORS_MAX_LIMIT = 100


class SharedErrorCreate(BaseModel):
    """分享一张自己的错题——**只收 error_id**，内容服务端取（不可伪造）。"""

    error_id: UUID = Field(description="要分享的错题 ID（必须是本人名下未删除的错题）")
    note: str | None = Field(
        default=None,
        max_length=500,
        description="分享者附言（可空；与快照文本同过安全过滤）",
    )


class SharedKnowledgeNode(BaseModel):
    """错题关联知识点（白名单投影内的定位信息）。"""

    id: UUID
    name: str
    is_primary: bool = False


class SharedErrorEntry(BaseModel):
    """一条错题卡分享（小队成员可见的最小信息面）。"""

    share_id: UUID
    group_id: UUID
    sharer_id: UUID = Field(description="分享者（小队成员，非匿名——互助要可找到人）")
    sharer_name: str | None = Field(default=None, description="分享者昵称或用户名（缺失为 None）")
    error_id: UUID
    question_text: str | None = None
    question_image_ref: str | None = Field(
        default=None,
        description="题目图片引用（sparkle-file:// 原样，走既有 MinIO 鉴权面；无图为 None）",
    )
    subject_code: str
    chapter: str | None = None
    knowledge_nodes: list[SharedKnowledgeNode] = Field(default_factory=list)
    cognitive_tags: list[str] = Field(default_factory=list)
    error_type: str | None = Field(default=None, description="错因分类（服务端快照）")
    root_cause: str | None = Field(default=None, description="错因根因（服务端快照，诚实呈现卡点）")
    study_suggestion: str | None = Field(default=None, description="学习建议（服务端快照）")
    note: str | None = Field(default=None, description="分享者附言")
    mastery_level: float = Field(ge=0.0, le=1.0, description="分享时刻掌握度快照（0.0-1.0）")
    mastery_delta: float | None = Field(default=None, description="分享时刻本题掌握度变化（负=诊断扣分）")
    review_count: int = Field(default=0, ge=0, description="分享时刻复习次数快照")
    created_at: datetime = Field(description="分享时刻")

    model_config = ConfigDict(from_attributes=True)


class SharedErrorListResponse(BaseModel):
    """小队错题卡分享列表（仅小队成员可见，非成员 403）。"""

    squad_id: UUID
    total: int = Field(ge=0, description="在册分享总数（分页在全集上计）")
    limit: int
    offset: int
    generated_at: datetime
    items: list[SharedErrorEntry]


class SharedErrorRetractResponse(BaseModel):
    """撤回（软删）结果。幂等诚实：重复撤回 already_retracted=True。"""

    share_id: UUID
    retracted: bool
    already_retracted: bool = False
