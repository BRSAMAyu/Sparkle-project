"""J-06 · Hybrid Flagship Journey —— 分段产物与 citation 结构持久化模型.

旅程分段产物的唯一真源表：四段链（Agent prep → Human judgment →
Agent execute/check → Outcome）每一段的产物各落一行，统一携带
``citations``（封闭结构的引用列表：citation_id / scheme / ref /
source_ref / file_id / file_name / page_numbers）——「每段产出可溯源」
（卡面 work 3）的持久断言面。

不重建真源纪律：
- 旅程脊柱与 handoff = X-05/X-07 ``agent_runs``（steps / awaiting /
  完成戳）；本表只存**产物内容**（run 聚合只持引用，不持本体——
  X-07 artifact-ref 纪律的产物侧落点）；
- 材料本体真源 = ``stored_files`` / ``document_chunks``（citations 的
  ref 指向真实 chunk 行，不复制内容正文）；
- 工具执行账本 = X-06 ``agent_tool_calls``（prep 的执行证据）；
- 图谱接线 = X-08 outcome 捕获 + G-02 既有吸收器（本表零图谱写）。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")

#: 产物所属段（封闭词表 = 四段链段名）。
HYBRID_JOURNEY_STAGES: frozenset[str] = frozenset({"prep", "judgment", "execute_check", "outcome"})

#: 产物 kind（封闭词表；每段一种）。
HYBRID_JOURNEY_ARTIFACT_KINDS: frozenset[str] = frozenset(
    {
        "citations",  # prep：真实检索候选引用集
        "selection",  # judgment：用户的选择（哪些来源进入交付）
        "checked_outline",  # execute_check：带引用草稿 + 确定性 check 结论
        "delivery_receipt",  # outcome：交付回执（任务完成 + outcome 引用）
    }
)


class HybridJourneyArtifact(BaseModel):
    """一段旅程产物（per run per stage 恰一行；append-only）。"""

    __tablename__ = "hybrid_journey_artifacts"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: 交付锚点任务（可选；outcome 段确认后经既有 TaskService 路径完成）。
    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    #: 段名（HYBRID_JOURNEY_STAGES 成员）。
    stage: Mapped[str] = mapped_column(String(24), nullable=False)
    #: 产物类型（HYBRID_JOURNEY_ARTIFACT_KINDS 成员）。
    artifact_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    #: 统一 citation 结构（非空；每段产物可溯源的持久断言面）::
    #:   [{"citation_id": "S1", "scheme": "document_chunk", "ref": <chunk_id>,
    #:     "source_ref": "document_chunk://<chunk_id>", "file_id": ...,
    #:     "file_name": ..., "page_numbers": [...], "score": ...}]
    citations: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    #: C-01 对齐的来源引用（goal:// / task:// / run:// / document:// / tool_call://）。
    source_refs: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    #: 段内产物本体（prep 查询面 / 判断面 / 草稿+check 结论 / 交付回执）。
    payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    #: 旅程 schema 版本（漂移审计）。
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    def projection(self) -> dict[str, Any]:
        """只读 wire 投影（API/回放面）。"""
        return {
            "id": str(self.id),
            "run_id": str(self.run_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "stage": self.stage,
            "artifact_kind": self.artifact_kind,
            "citations": list(self.citations or []),
            "source_refs": list(self.source_refs or []),
            "payload": dict(self.payload or {}),
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return (
            f"<HybridJourneyArtifact(id={self.id}, run_id={self.run_id}, "
            f"stage={self.stage}, kind={self.artifact_kind})>"
        )
