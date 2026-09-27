"""
Core: infra
Phase: sense
Stage: V3-FIX-333

五族外部能力（embedding/stt/tts/ocr）运行时状态登记 —— V3-FIX-333「能力宣称
真实化」。llm 族不使用本模块：llm_router 的 E-07 三相滞回本身就是真实流量
驱动的状态机，宣称面在 capability_registry_service 按 ModelHealthState 映射。

状态机（封闭集，全部为对外宣称语义，不是路由语义）：
- not_configured: 凭据缺失（各 service 按自身键判定后落此态）-> 不可用
- unverified:     凭据在、无任何真实调用证据 ->「已配置未验证」，绝不冒充可用
- verified:       最近一次真实调用成功（事件驱动证据）-> 可宣称可用
- unavailable:    最近一次真实调用失败 -> 不可用（后续成功可翻回 verified）

证据纪律（红线）：
- 只接受真实调用的成败回调（evidence=real_traffic，与生产调用同路径）；
  本模块不发起网络请求，也不提供任何「假探测」入口。是否值得为各族加
  定时主动 probe（evidence=explicit_probe）是成本裁决，本版不启用——
  见台账 V3-FIX-333 行的各族终态语义与理由。
- 状态为进程内内存态（与 llm_router 健康态同级），重启后回到 unverified，
  与「宣称必须有当下证据」的语义一致。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime

# 宣称词封闭集（DoD 词表）。仓内既有消费词表的对齐关系见
# capability_selection_policy：verified 视为健康，unverified 可选但不健康，
# not_configured/unavailable 视为 blocked。
CAPABILITY_STATE_NOT_CONFIGURED = "not_configured"
CAPABILITY_STATE_UNVERIFIED = "unverified"
CAPABILITY_STATE_VERIFIED = "verified"
CAPABILITY_STATE_UNAVAILABLE = "unavailable"
CAPABILITY_STATES: frozenset[str] = frozenset(
    {
        CAPABILITY_STATE_NOT_CONFIGURED,
        CAPABILITY_STATE_UNVERIFIED,
        CAPABILITY_STATE_VERIFIED,
        CAPABILITY_STATE_UNAVAILABLE,
    }
)

# 证据来源封闭集。本版生产代码只产生 real_traffic；explicit_probe 为后续
# 主动探活预留，当前任何入口都不应伪造它。
EVIDENCE_REAL_TRAFFIC = "real_traffic"
EVIDENCE_EXPLICIT_PROBE = "explicit_probe"

# 依赖外部凭据的媒体能力族（registry 对外五族中除 llm 外的四族）
MEDIA_CAPABILITY_FAMILIES: tuple[str, ...] = ("embedding", "stt", "tts", "ocr")

_DETAIL_MAX_CHARS = 200


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


def _clean_detail(detail: str | None) -> str:
    return str(detail or "").strip()[:_DETAIL_MAX_CHARS]


@dataclass(frozen=True)
class CapabilityObservation:
    """一次真实调用成败后的宣称状态（immutable 证据快照）。"""

    state: str
    evidence: str
    observed_at: str
    detail: str = ""


def aggregate_family_state(states: list[str] | tuple[str, ...]) -> str:
    """族级宣称聚合（诚实优先序：有证据才敢宣称可用）。

    - 任一 provider verified        -> verified（族内至少一条可用通道）
    - 否则任一 unverified           -> unverified（配置存在但全族无证据）
    - 全部 not_configured           -> not_configured
    - 混有 unavailable（含与
      not_configured 混合）         -> unavailable
    - 空输入按 not_configured 处理
    """
    normalized = [str(item or "").strip() for item in states if str(item or "").strip()]
    if any(item == CAPABILITY_STATE_VERIFIED for item in normalized):
        return CAPABILITY_STATE_VERIFIED
    if any(item == CAPABILITY_STATE_UNVERIFIED for item in normalized):
        return CAPABILITY_STATE_UNVERIFIED
    if normalized and all(item == CAPABILITY_STATE_NOT_CONFIGURED for item in normalized):
        return CAPABILITY_STATE_NOT_CONFIGURED
    if any(item == CAPABILITY_STATE_UNAVAILABLE for item in normalized):
        return CAPABILITY_STATE_UNAVAILABLE
    return CAPABILITY_STATE_NOT_CONFIGURED


class CapabilityRuntimeStatus:
    """进程内五族能力状态登记（线程安全；只登记真实调用证据）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._observations: dict[tuple[str, str], CapabilityObservation] = {}

    def observe_success(
        self,
        family: str,
        provider: str,
        *,
        evidence: str = EVIDENCE_REAL_TRAFFIC,
        detail: str = "",
    ) -> None:
        """登记一次真实调用成功（family/provider 如 "embedding"/"dashscope"）。"""
        self._record(family, provider, CAPABILITY_STATE_VERIFIED, evidence, detail)

    def observe_failure(
        self,
        family: str,
        provider: str,
        detail: str = "",
        *,
        evidence: str = EVIDENCE_REAL_TRAFFIC,
    ) -> None:
        """登记一次真实调用失败。"""
        self._record(family, provider, CAPABILITY_STATE_UNAVAILABLE, evidence, detail)

    def status(self, family: str, provider: str) -> CapabilityObservation | None:
        """读取当前证据；无任何真实调用证据时返回 None（调用方按 unverified 处理）。"""
        key = (str(family or "").strip(), str(provider or "").strip())
        with self._lock:
            return self._observations.get(key)

    def runtime_state(self, family: str, provider: str, *, configured: bool) -> str:
        """宣称态判定（组合键存在性与登记证据）：

        键空 -> not_configured；键在无证据 -> unverified；有证据 -> 登记态。
        """
        if not configured:
            return CAPABILITY_STATE_NOT_CONFIGURED
        observation = self.status(family, provider)
        if observation is None:
            return CAPABILITY_STATE_UNVERIFIED
        return observation.state if observation.state in CAPABILITY_STATES else CAPABILITY_STATE_UNVERIFIED

    def snapshot(self, family: str) -> dict[str, dict[str, str]]:
        """族内全部已登记证据的快照（不含未登记 provider）。"""
        prefix = str(family or "").strip()
        with self._lock:
            return {
                provider: {
                    "state": observation.state,
                    "evidence": observation.evidence,
                    "observed_at": observation.observed_at,
                    "detail": observation.detail,
                }
                for (family, provider), observation in self._observations.items()
                if family == prefix
            }

    def reset(self) -> None:
        """清空登记（测试隔离用；生产路径不调用）。"""
        with self._lock:
            self._observations.clear()

    def _record(
        self,
        family: str,
        provider: str,
        state: str,
        evidence: str,
        detail: str,
    ) -> None:
        normalized_family = str(family or "").strip()
        normalized_provider = str(provider or "").strip()
        if not normalized_family or not normalized_provider:
            return
        normalized_evidence = str(evidence or "").strip() or EVIDENCE_REAL_TRAFFIC
        observation = CapabilityObservation(
            state=state,
            evidence=normalized_evidence,
            observed_at=_utcnow_iso(),
            detail=_clean_detail(detail),
        )
        with self._lock:
            self._observations[(normalized_family, normalized_provider)] = observation


# 全局单例：五族 service 的真实调用路径向它登记证据
capability_runtime_status = CapabilityRuntimeStatus()
