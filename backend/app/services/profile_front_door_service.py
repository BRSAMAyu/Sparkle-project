from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger
from pydantic import ValidationError

from app.core.profile_context import ProfileContext
from app.core.user_insight_state import UserInsightState
from app.profile.projection_contract import UserProjectionContract
from app.services.personalization.inferred_meta import INFERRED_META
from app.services.profile_context_service import ProfileContextService
from app.services.user_insight_transparency_service import UserInsightTransparencyService


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _display_value(value: Any) -> str:
    if isinstance(value, dict):
        if "value" in value and len(value) == 1:
            return _display_value(value.get("value"))
        return ", ".join(
            f"{key}={_display_value(item)}" for key, item in value.items() if item not in (None, "", [], {})
        )
    if isinstance(value, list):
        return ", ".join(_display_value(item) for item in value if item not in (None, "", [], {}))
    return _strip(value)


def _confidence_percent(value: Any) -> int:
    try:
        numeric = float(value or 0.0)
    except (TypeError, ValueError):
        numeric = 0.0
    numeric = max(0.0, min(1.0, numeric))
    return int(round(numeric * 100))


class ProfileFrontDoorService:
    """Build the chat-native read surface for canonical profile insight."""

    def __init__(self, db_session: Any, redis=None):
        self.db_session = db_session
        self.redis = redis

    async def load_profile_context(
        self,
        *,
        user_id: UUID,
        runtime_context: dict[str, Any] | None = None,
    ) -> ProfileContext:
        runtime_context = runtime_context or {}

        direct = self._coerce_profile_context(runtime_context.get("profile_context"))
        if direct is not None:
            return direct

        user_context_payload = runtime_context.get("user_context_payload")
        if isinstance(user_context_payload, dict):
            embedded = self._coerce_profile_context(user_context_payload.get("profile_context"))
            if embedded is not None:
                return embedded

        return await ProfileContextService(self.db_session, self.redis).get_profile_context(user_id)

    def build_payload(
        self,
        *,
        profile_context: ProfileContext,
        highlighted_claim_id: str | None = None,
        confirmation: dict[str, Any] | None = None,
        include_actions: bool = False,
    ) -> dict[str, Any]:
        contract = profile_context.user_projection_contract
        state = profile_context.user_insight_state

        if contract is None and state is not None:
            contract = UserProjectionContract.from_compiled_state(
                state=state,
                merged_preferences=dict(profile_context.preferences or {}),
            )
        if state is None and contract is not None:
            state = contract.canonical_state
        if state is None:
            state = UserInsightState()

        transparency_payload = (
            dict(contract.m5_transparency.transparency_payload or {})
            if contract is not None
            else UserInsightTransparencyService().build_payload(
                state=state,
                merged_preferences=dict(profile_context.preferences or {}),
                inferred_backups={},
            )
        )
        evidence_catalog = self._build_evidence_catalog(profile_context)

        claims = [
            self._build_claim_item(
                claim,
                highlighted_claim_id=highlighted_claim_id,
                include_actions=include_actions,
                evidence_catalog=evidence_catalog,
            )
            for claim in list(transparency_payload.get("claims") or [])[:4]
            if isinstance(claim, dict)
        ]
        predictions = [
            self._build_prediction_item(prediction, evidence_catalog=evidence_catalog)
            for prediction in list(transparency_payload.get("predictions") or [])[:2]
            if isinstance(prediction, dict)
        ]
        unknowns = [
            {
                "id": _strip(item.get("id")),
                "description": _strip(item.get("description")),
            }
            for item in list(transparency_payload.get("unknowns") or [])[:3]
            if isinstance(item, dict) and _strip(item.get("description"))
        ]
        recent_changes = [
            self._build_recent_change_item(item)
            for item in list(transparency_payload.get("recent_changes") or [])[:3]
            if isinstance(item, dict)
        ]
        calibration = self._build_calibration(transparency_payload.get("calibration"))

        return {
            "title": "这是我现在对你的理解",
            "headline": "当前画像前门",
            "summary": self._build_summary(
                claims=claims,
                predictions=predictions,
                unknowns=unknowns,
                calibration=calibration,
            ),
            "claims": claims,
            "predictions": predictions,
            "unknowns": unknowns,
            "recent_changes": recent_changes,
            "calibration": calibration,
            "evidence_legend": [
                {
                    "id": "raw_evidence",
                    "label": "原始依据",
                    "description": "点击后可查看允许暴露的 L0 依据或明确的脱敏/缺失状态。",
                },
                {
                    "id": "compiled_claim",
                    "label": "编译结论",
                    "description": "这是基于证据编译后的当前判断，不等于不可变事实。",
                },
                {
                    "id": "prediction",
                    "label": "推断/预测",
                    "description": "这是面向下一步的风险或趋势判断，不是既成事实。",
                },
                {
                    "id": "practice_outcome",
                    "label": "练习结果",
                    "description": "这是最近一次练习/复习的结果摘要，会回到错题详情而不是伪装成画像事实。",
                },
                {
                    "id": "user_correction",
                    "label": "用户纠正",
                    "description": "这是用户明确提交的修正，会优先影响后续读路径。",
                },
            ],
            "evidence_resolution": "l0_clickable_refs",
            "read_lane": "canonical_profile_front_door",
            "preference_version": profile_context.preference_version,
            "contract_version": getattr(contract, "contract_version", None),
            "generated_at": state.generated_at,
            "binding_note": (
                "当前前门展示的是 canonical 结论 + 可点击的 L0 依据引用；" "若没有可暴露依据，会明确显示为缺失或脱敏。"
            ),
            "follow_up_hint": "如果哪一条不对，你可以直接在聊天里指出，我会按用户纠正通道处理。",
            "confirmation": dict(confirmation or {}),
            "evidence_catalog_status": evidence_catalog["status"],
        }

    @staticmethod
    def _coerce_profile_context(value: Any) -> ProfileContext | None:
        if isinstance(value, ProfileContext):
            return value
        if isinstance(value, dict) and value:
            try:
                return ProfileContext(**value)
            except (TypeError, ValueError, ValidationError) as exc:
                logger.warning("Failed to coerce profile_context payload: {}", exc)
                return None
        return None

    def _build_claim_item(
        self,
        claim: dict[str, Any],
        *,
        highlighted_claim_id: str | None,
        include_actions: bool,
        evidence_catalog: dict[str, Any],
    ) -> dict[str, Any]:
        claim_id = _strip(claim.get("id"))
        label = _strip(claim.get("label") or claim_id)
        display_value = _display_value(claim.get("value"))
        evidence_refs = self._claim_evidence_refs(claim, evidence_catalog=evidence_catalog)
        direct_controls = [
            control
            for control in list(claim.get("controls") or [])
            if _strip(control) in {"wrong", "used_to_be_true", "exam_mode_only", "reset_override"}
        ]
        supports_direct_correction = bool(
            direct_controls or (INFERRED_META.get(claim_id) and INFERRED_META[claim_id].adjustable)
        )
        item = {
            "id": claim_id,
            "label": label,
            "value": display_value,
            "summary": self._build_claim_summary(
                label=label, value=display_value, explanation=claim.get("explanation")
            ),
            "confidence": round(float(claim.get("confidence") or 0.0), 3),
            "confidence_label": f"{_confidence_percent(claim.get('confidence'))}%",
            "evidence_class": "compiled_claim",
            "evidence_label": "编译结论",
            "source": _strip(claim.get("source")),
            "family": _strip(claim.get("family")),
            "surfaces": [str(item).strip() for item in list(claim.get("surfaces") or []) if str(item).strip()],
            "freshness": _strip(claim.get("freshness")),
            "status": _strip(claim.get("status")),
            "explanation": _strip(claim.get("explanation")),
            "correction_mode": "direct" if supports_direct_correction else "discussion_only",
            "correction_hint": "可直接在聊天里纠正" if supports_direct_correction else "如不准确，请在聊天里补充上下文",
            "highlighted": bool(highlighted_claim_id and claim_id == highlighted_claim_id),
            "evidence_refs": evidence_refs,
            "evidence_count": len(evidence_refs),
            "evidence_cta": "查看依据" if evidence_refs else "",
            "evidence_summary": f"{len(evidence_refs)} 条可点击依据" if evidence_refs else "暂无可点击依据",
            "evidence_missing": False,
        }
        if include_actions:
            item["actions"] = self._build_claim_actions(
                claim_id=claim_id,
                label=label,
                controls=direct_controls,
            )
        return item

    @staticmethod
    def _build_claim_summary(*, label: str, value: str, explanation: Any) -> str:
        explanation_text = _strip(explanation)
        if explanation_text:
            return explanation_text
        if value:
            return f"当前这条判断是：{label} = {value}"
        return f"当前这条判断围绕「{label}」展开，但值还不够稳定。"

    def _build_prediction_item(self, prediction: dict[str, Any], *, evidence_catalog: dict[str, Any]) -> dict[str, Any]:
        kind = _strip(prediction.get("kind") or prediction.get("id"))
        level = _strip(prediction.get("level"))
        explanation = _strip(prediction.get("explanation"))
        evidence_refs = self._prediction_evidence_refs(prediction, evidence_catalog=evidence_catalog)
        return {
            "id": _strip(prediction.get("id")),
            "label": kind,
            "level": level,
            "summary": explanation or f"当前预测：{kind}{' -> ' + level if level else ''}",
            "confidence": round(float(prediction.get("confidence") or 0.0), 3),
            "confidence_label": f"{_confidence_percent(prediction.get('confidence'))}%",
            "evidence_class": "prediction",
            "evidence_label": "推断/预测",
            "recommended_action": _strip(prediction.get("recommended_action")),
            "evidence_signals": [
                str(item).strip() for item in list(prediction.get("evidence_signals") or []) if str(item).strip()
            ],
            "calibration_status": _strip(prediction.get("calibration_status")),
            "evidence_refs": evidence_refs,
            "evidence_count": len(evidence_refs),
            "evidence_cta": "查看依据" if evidence_refs else "",
            "evidence_summary": f"{len(evidence_refs)} 条可点击依据" if evidence_refs else "暂无可点击依据",
            "evidence_missing": False,
        }

    def _build_recent_change_item(self, item: dict[str, Any]) -> dict[str, Any]:
        item_type = _strip(item.get("type"))
        label = _strip(item.get("label"))
        details = dict(item.get("details") or {})
        evidence_class = "user_correction" if item_type == "correction" else "compiled_claim"
        evidence_label = "用户纠正" if item_type == "correction" else "画像变化"
        summary = _strip(details.get("reason") or details.get("description") or label)
        return {
            "type": item_type,
            "label": label,
            "summary": summary or label,
            "details": details,
            "evidence_class": evidence_class,
            "evidence_label": evidence_label,
        }

    @staticmethod
    def _build_evidence_catalog(profile_context: ProfileContext) -> dict[str, Any]:
        weak_concepts = [
            {"type": "concept", "id": str(item.node_id), "schema_version": "concept.v1"}
            for item in list(profile_context.knowledge_summary.weak_spots or [])
            if str(item.node_id or "").strip() and not str(item.node_id).startswith("derived:")
        ]
        recent_concepts = [
            {"type": "concept", "id": str(item.node_id), "schema_version": "concept.v1"}
            for item in list(profile_context.knowledge_summary.recent_mastery_changes or [])
            if str(item.node_id or "").strip() and not str(item.node_id).startswith("derived:")
        ]
        recent_errors = [
            {"type": "error", "id": str(item.get("id")), "schema_version": "error.v1"}
            for item in list(profile_context.recent_errors or [])
            if _strip(item.get("id"))
        ]
        recent_practice_outcomes = [
            {"type": "practice_outcome", "id": str(item.get("id")), "schema_version": "practice_outcome.v1"}
            for item in list(profile_context.recent_errors or [])
            if _strip(item.get("id"))
            and int(item.get("review_count") or 0) > 0
            and _strip(item.get("last_reviewed_at"))
        ]
        return {
            "status": (
                "known" if any((weak_concepts, recent_concepts, recent_errors, recent_practice_outcomes)) else "sparse"
            ),
            "weak_concepts": weak_concepts[:3],
            "recent_concepts": recent_concepts[:3],
            "recent_errors": recent_errors[:3],
            "recent_practice_outcomes": recent_practice_outcomes[:3],
        }

    @staticmethod
    def _dedupe_evidence_refs(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        refs: list[dict[str, Any]] = []
        for group in groups:
            for item in group:
                key = (_strip(item.get("type")), _strip(item.get("id")))
                if not all(key) or key in seen:
                    continue
                seen.add(key)
                refs.append(dict(item))
        return refs[:3]

    def _claim_evidence_refs(self, claim: dict[str, Any], *, evidence_catalog: dict[str, Any]) -> list[dict[str, Any]]:
        source = _strip(claim.get("source"))
        family = _strip(claim.get("family"))
        claim_id = _strip(claim.get("id"))

        if source == "knowledge_summary" or family == "knowledge":
            return self._dedupe_evidence_refs(
                evidence_catalog.get("weak_concepts") or [],
                evidence_catalog.get("recent_concepts") or [],
            )
        if "error" in source or claim_id in {"anti_patterns", "cognitive_tendencies"} or family == "cognitive":
            return self._dedupe_evidence_refs(
                evidence_catalog.get("recent_practice_outcomes") or [],
                evidence_catalog.get("recent_errors") or [],
                evidence_catalog.get("weak_concepts") or [],
            )
        if source in {"achievement_signals", "workflow_signals"}:
            return self._dedupe_evidence_refs(
                evidence_catalog.get("recent_concepts") or [],
                evidence_catalog.get("recent_practice_outcomes") or [],
                evidence_catalog.get("recent_errors") or [],
            )
        return []

    def _prediction_evidence_refs(
        self,
        prediction: dict[str, Any],
        *,
        evidence_catalog: dict[str, Any],
    ) -> list[dict[str, Any]]:
        evidence_signals = {
            str(item).strip() for item in list(prediction.get("evidence_signals") or []) if str(item).strip()
        }
        if "error_summary" in evidence_signals:
            return self._dedupe_evidence_refs(
                evidence_catalog.get("recent_practice_outcomes") or [],
                evidence_catalog.get("recent_errors") or [],
                evidence_catalog.get("weak_concepts") or [],
            )
        if "recent_mastery_changes" in evidence_signals:
            return self._dedupe_evidence_refs(
                evidence_catalog.get("recent_concepts") or [],
                evidence_catalog.get("weak_concepts") or [],
            )
        return self._dedupe_evidence_refs(evidence_catalog.get("weak_concepts") or [])

    @staticmethod
    def _build_calibration(raw: Any) -> dict[str, Any]:
        calibration = dict(raw or {}) if isinstance(raw, dict) else {}
        posture = _strip(calibration.get("calibration_posture") or calibration.get("posture") or "uncalibrated")
        correction_count = int(calibration.get("recent_correction_count") or 0)
        uncertainty = len(list(calibration.get("recent_corrections") or []))
        summary_parts = [f"校准姿态：{posture}"]
        if correction_count > 0:
            summary_parts.append(f"最近有 {correction_count} 条用户纠正")
        if uncertainty > 0:
            summary_parts.append("因此我会更保守地表达结论")
        return {
            **calibration,
            "calibration_posture": posture,
            "summary": "；".join(summary_parts),
        }

    @staticmethod
    def _build_summary(
        *,
        claims: list[dict[str, Any]],
        predictions: list[dict[str, Any]],
        unknowns: list[dict[str, Any]],
        calibration: dict[str, Any],
    ) -> str:
        parts: list[str] = []
        if claims:
            lead = claims[0]
            if lead.get("value"):
                parts.append(f"我目前最稳定的一条判断是「{lead['label']} = {lead['value']}」。")
            else:
                parts.append(f"我目前最稳定的一条判断围绕「{lead['label']}」。")
        if predictions:
            lead_prediction = predictions[0]
            prediction_text = _strip(lead_prediction.get("label"))
            if prediction_text:
                parts.append(f"下一步我最关注的趋势是「{prediction_text}」。")
        if unknowns:
            parts.append(f"同时还有 {len(unknowns)} 个未知项没有完全钉住。")
        calibration_summary = _strip(calibration.get("summary"))
        if calibration_summary:
            parts.append(calibration_summary)
        if not parts:
            return "当前画像还比较稀薄，我更适合先从你的近期状态和证据开始问。"
        return " ".join(parts)

    @staticmethod
    def _build_claim_actions(
        *,
        claim_id: str,
        label: str,
        controls: list[str],
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if "wrong" in controls:
            actions.append(
                {
                    "label": "这条不对",
                    "type": "prompt",
                    "prompt": (
                        f"请把画像里的「{label}」这条标记为不对（target_id={claim_id}，action=wrong），"
                        "并基于更新后的 canonical 画像重新告诉我你现在怎么看我。"
                    ),
                }
            )
        if "used_to_be_true" in controls:
            actions.append(
                {
                    "label": "以前对，现在不对",
                    "type": "prompt",
                    "prompt": (
                        f"请把画像里的「{label}」改成『以前对，现在不对』"
                        f"（target_id={claim_id}，action=used_to_be_true），然后重新读一遍当前画像。"
                    ),
                }
            )
        if "exam_mode_only" in controls:
            actions.append(
                {
                    "label": "只在考试模式成立",
                    "type": "prompt",
                    "prompt": (
                        f"请把画像里的「{label}」限制为考试模式才成立"
                        f"（target_id={claim_id}，action=exam_mode_only），然后重新读一遍当前画像。"
                    ),
                }
            )
        return actions
