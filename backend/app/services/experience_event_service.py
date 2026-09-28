"""V4-D01 · 真实呈现（rendered exposure）→ experience_event.v1 服务面。

修的语义缺口（卡 V4-D01；S07 裁决「任意 delivered=用户真的看到」不可推导）：

- **G1 交付即曝光（现状混写）**：FIX-507 写面 1a 在 ``mark_delivered``（服务端
  下发收敛点）记 D-05 ``exposed`` 漏斗锚点——后台/不可见下发也计成了「已曝光」。
  本卡**保留**该接线与其全部既有语义/测试（交付回执面不动），只在「真实呈现」
  上做增量：``exposed`` 行从今天起具备双语义读法——detail 携
  ``exposure_basis="delivered"`` 的**交付回执**；「用户实际可见面」由本模块的
  rendered 事件承载，不再由下发代替看到。
- **G2 真实呈现无记录（现状）**：``mark_seen``（客户端确认真实渲染 / 等价无障碍
  曝光的 SEEN 转场）在 FIX-507 接线中「无词表成员，不接线」——渲染事实零记录。
- **G3 呈现面无投影**：全仓无 experience_event.v1；呈现侧只有 outbox 集成通知
  （7 天清理、无 receipt_ref/commit_state/dedupe_key）——不是 B05 §3 意义的呈现回执。

增量设计（不推翻 FIX-507 三写面，无新事件总线、无新表/迁移）：

- **真实呈现门**：本服务只从 ``mark_seen``（SEEN 真实转场）进入；任何下发路径
  （mark_delivered / spine directive）**永不**调本服务——不可见/后台下发不算看到。
- **权威回执双门（I2）**：投影前必须查证 D-05 ``exposed`` 行真实存在（同 user、
  未软删）——``receipt_ref = intervention_lifecycle://<decision_id>`` 必指权威
  回执；回执缺失 → 可观测降级（``no_authoritative_receipt``，不产事件、不抛异常、
  不伪造成功呈现）。
- **幂等（重复 render 不重复曝光）**：事件身份内容寻址
  （``dedupe_key``/``event_id`` 派生自 receipt_ref+kind+version_token，不含时间）
  ——同一 record+decision 的任意次渲染/重放恒同 id；消费方按 event_id 去重；
  写侧 ``mark_seen`` 仅在真实转场挂勾（已 SEEN 短路，不重复发布）。
- **丢事件可重放**：投影是权威事实（InterventionRecord 行 + D-05 exposed 行）的
  确定性纯函数，:meth:`ExperienceEventService.replay_rendered_exposure` 任意时点
  重算恒得同事件。
- **不拖跨主业务（韧性壳，FIX-530/507 判例）**：本模块任何失败只
  ``logger.warning`` + 可观测 ``RenderedExposureResult``，SEEN 转场永不被拖垮。
- **发布走既有进程内 EventBus**（``experience.event_projected`` 主题，与
  ``intervention_record.status_changed`` 同一条总线）——**不是**新同义事件总线；
  事件语义（真实呈现回执，receipt_ref 挂权威回执）与
  ``intervention.exposed``（服务端下发回执）不同义。WS ``ExperienceEventFrame``
  的 proto 增量归 contract-owner（B05 §8），本卡不越权改 proto。

事件形态（experience_event.v1，词表冻结）：
- ``kind=state_confirmed``：真实呈现是「已确认的呈现状态」——E1 全要求的
  committed + receipt_ref 必选与 I2 同构；subject.type=intervention（不跨域冒充
  任务/记忆 committed——反例「记忆回执当任务修改呈现」）。
- ``commit_state=committed``：唯一真源 = D-05 exposed 行已落账（交付面权威回执）。
- ``presentation.modalities``：rendered_surface=``visual`` → ``["visual"]``；
  ``accessibility``（等价无障碍曝光：读屏/替代感官面）→ ``["audio"]``。二者都算
  「用户实际可见面」，但按真实操作记录，不互混。
- ``expires_at=None``：本事件是「发生过什么」的回执，不是可动作提示，不过期。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.experience_event import (
    EXPERIENCE_EVENT_SCHEMA_VERSION,
    ExperienceCommitState,
    ExperienceEvent,
    ExperienceEventKind,
    ExperiencePresentation,
    ExperienceSubject,
)
from app.core.intervention_lifecycle import LifecycleEventType
from app.models.card_protocol import InterventionRecord
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.services.intervention_lifecycle_wiring import build_record_decision_contract

EXPERIENCE_EVENT_SERVICE_VERSION = "experience-event.d01.v1"

#: 真实呈现发布主题（既有进程内 EventBus；非新总线、与下发回执不同义）。
EXPERIENCE_EVENT_TOPIC = "experience.event_projected"

#: 等价无障碍曝光的封闭面词表（卡面「等价无障碍曝光」；非法值拒收——真实操作
#: 按其本面记录，不静默归一成 visual）。
RENDERED_SURFACES: frozenset[str] = frozenset({"visual", "accessibility"})

#: rendered_surface → presentation.modalities（冻结投影；空集不合法，见契约 §3）。
_SURFACE_TO_MODALITIES: dict[str, tuple[str, ...]] = {
    "visual": ("visual",),
    "accessibility": ("audio",),
}

#: 冻结文案表键位（键→文案冻结表 owner = V4-F03，B05 §3 R1-C5；本卡只落键纪律）。
RENDERED_EXPOSURE_COPY_KEY = "intervention.rendered"


@dataclass(frozen=True)
class RenderedExposureResult:
    """一次真实呈现记录的结果（幂等/降级语义对调用方可观测）。"""

    projected: bool
    reason: str
    event_id: str
    dedupe_key: str
    decision_id: str
    receipt_ref: str | None
    event: dict[str, Any] | None
    published: bool


def _refused(reason: str, decision_id: str = "") -> RenderedExposureResult:
    logger.info("ExperienceEvent: rendered exposure not projected (reason={}, decision={})", reason, decision_id)
    return RenderedExposureResult(
        projected=False,
        reason=reason,
        event_id="",
        dedupe_key="",
        decision_id=decision_id,
        receipt_ref=None,
        event=None,
        published=False,
    )


class ExperienceEventService:
    """真实呈现 → experience_event.v1 投影 + 既有总线发布（D01 增量面）。"""

    def __init__(self, db: AsyncSession, event_bus: Any | None = None):
        self.db = db
        self.event_bus = event_bus

    # ------------------------------------------------------------------
    # 真实呈现记录（唯一入口 = mark_seen 真实转场；下发路径禁入）
    # ------------------------------------------------------------------

    async def record_rendered_exposure(
        self,
        record: InterventionRecord,
        *,
        rendered_surface: str = "visual",
        issued_at: datetime | None = None,
        publish: bool = True,
    ) -> RenderedExposureResult:
        """把一次真实呈现落成 experience_event.v1（幂等；三态可观测）。

        三态：曝光（投影+发布）/ 未曝光（非真实呈现路径不会进本方法；决策契约
        不可投影时 refused）/ 回执缺失降级（``no_authoritative_receipt``——I2：
        无 committed 权威回执不产成功类呈现事件）。
        """
        surface = str(rendered_surface or "").strip().lower()
        if surface not in RENDERED_SURFACES:
            return _refused("rendered_surface_invalid")

        contract = build_record_decision_contract(record)
        if contract is None:
            # 未登记 trigger / inert：与 FIX-507 交付面同语义——宁可无呈现记录，
            # 不产词表外事件。
            return _refused("decision_contract_unprojectable", str(record.id))
        decision_id = contract.decision_id_or_compute()

        receipt = await self._get_authoritative_receipt(decision_id=decision_id, user_id=record.user_id)
        if receipt is None:
            # 回执缺失降级（I2）：渲染上报存在但交付面权威回执不在——不投影成功
            # 类呈现事件；可观测 reason，不抛异常、不拖垮 SEEN 转场。
            return _refused("no_authoritative_receipt", decision_id)

        receipt_ref = f"intervention_lifecycle://{decision_id}"
        event = ExperienceEvent.project(
            kind=ExperienceEventKind.STATE_CONFIRMED.value,
            commit_state=ExperienceCommitState.COMMITTED.value,
            receipt_ref=receipt_ref,
            subject=ExperienceSubject(
                type="intervention",
                id=str(record.id),
                version_token=str(record.content_version or "1"),
            ),
            presentation=ExperiencePresentation(
                modalities=_SURFACE_TO_MODALITIES[surface],
                copy_key=RENDERED_EXPOSURE_COPY_KEY,
            ),
            issued_at=issued_at or datetime.utcnow(),
            expires_at=None,
        )

        published = False
        if publish and self.event_bus is not None:
            published = await self._publish(event=event, record=record, rendered_surface=surface)
        return RenderedExposureResult(
            projected=True,
            reason="",
            event_id=event.event_id,
            dedupe_key=event.dedupe_key,
            decision_id=decision_id,
            receipt_ref=receipt_ref,
            event=event.to_dict(),
            published=published,
        )

    async def replay_rendered_exposure(
        self,
        record: InterventionRecord,
        *,
        rendered_surface: str = "visual",
    ) -> RenderedExposureResult:
        """丢事件重放：按权威事实重算（确定性——恒得同 event_id/dedupe_key）。

        与首次投影唯一差别是 ``publish=True`` 重发同 id 事件（消费方按 event_id
        去重）；不查环当前 acceptance 状态——重放面向已确认的权威事实行。
        """
        return await self.record_rendered_exposure(record, rendered_surface=rendered_surface, publish=True)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    async def _get_authoritative_receipt(
        self, *, decision_id: str, user_id: Any
    ) -> InterventionLifecycleEvent | None:
        """I2 双门第二门：D-05 exposed 行真实存在（同 user、未软删）。"""
        row = (
            await self.db.execute(
                select(InterventionLifecycleEvent)
                .where(
                    InterventionLifecycleEvent.decision_id == str(decision_id),
                    InterventionLifecycleEvent.user_id == user_id,
                    InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
                    InterventionLifecycleEvent.not_deleted_filter(),
                )
                .order_by(InterventionLifecycleEvent.occurred_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return row

    async def _publish(self, *, event: ExperienceEvent, record: InterventionRecord, rendered_surface: str) -> bool:
        """既有总线发布（韧性壳：发布失败只留痕，投影结果照常返回可重放）。"""
        if self.event_bus is None:
            return False
        try:
            await self.event_bus.publish(
                EXPERIENCE_EVENT_TOPIC,
                {
                    "schema_version": EXPERIENCE_EVENT_SCHEMA_VERSION,
                    "service_version": EXPERIENCE_EVENT_SERVICE_VERSION,
                    "event_id": event.event_id,
                    "dedupe_key": event.dedupe_key,
                    "event": event.to_dict(),
                    "rendered_surface": rendered_surface,
                    "intervention_record_id": str(record.id),
                    "user_id": str(record.user_id),
                },
            )
            return True
        except Exception as exc:  # noqa: BLE001 — 呈现事件发布失败不拖垮宿主链路
            logger.warning(
                "ExperienceEvent: publish failed (event_id={}, record={}): {}",
                event.event_id,
                getattr(record, "id", "-"),
                exc,
            )
            return False


async def record_rendered_exposure_safe(
    db: AsyncSession,
    event_bus: Any | None,
    record: InterventionRecord,
    *,
    rendered_surface: str = "visual",
) -> RenderedExposureResult | None:
    """``mark_seen`` 挂点（韧性壳，FIX-507 写面 1a 同款形态）。

    任何异常只 ``logger.warning``，SEEN 转场永不被呈现投影拖垮；refused 是本
    模块可观测降级语义，原样返回给调用方留痕。
    """
    try:
        return await ExperienceEventService(db, event_bus).record_rendered_exposure(
            record,
            rendered_surface=rendered_surface,
        )
    except Exception as exc:  # noqa: BLE001 — 韧性壳
        logger.warning(
            "ExperienceEvent rendered exposure recording failed (record={}): {}",
            getattr(record, "id", "-"),
            exc,
        )
        return None


__all__ = [
    "EXPERIENCE_EVENT_SERVICE_VERSION",
    "EXPERIENCE_EVENT_TOPIC",
    "RENDERED_EXPOSURE_COPY_KEY",
    "RENDERED_SURFACES",
    "ExperienceEventService",
    "RenderedExposureResult",
    "record_rendered_exposure_safe",
]
