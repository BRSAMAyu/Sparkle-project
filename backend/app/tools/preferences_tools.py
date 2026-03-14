from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, Field

from app.core.memory_constants import PREFERENCE_KEYS
from app.services.profile_write_service import ProfileWriteService
from app.tools.base import BaseTool, ToolCategory, ToolResult


class UpdateUserPreferenceParams(BaseModel):
    pref_key: str = Field(..., description="Preference key to update")
    value: Any = Field(..., description="New preference value")
    confidence: float | None = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence of this explicit user-confirmed update",
    )


class UpdateUserPreferenceTool(BaseTool):
    name = "update_user_preference"
    description = "Update a user's preference when they explicitly confirm or correct it."
    category = ToolCategory.QUERY
    parameters_schema = UpdateUserPreferenceParams
    requires_confirmation = True

    async def execute(
        self,
        params: UpdateUserPreferenceParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            pref_key = params.pref_key.strip()
            if pref_key not in PREFERENCE_KEYS:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    tool_call_id=tool_call_id,
                    error_message=f"Unsupported pref_key: {pref_key}",
                    error_type="invalid_pref_key",
                )

            pref_value = params.value
            if not isinstance(pref_value, dict):
                pref_value = {"value": pref_value}

            profile_write_service = ProfileWriteService(db_session)
            evidence_ref = {
                "type": "user_state",
                "id": f"user_confirmed:{pref_key}:{uuid4()}",
                "schema_version": "v1",
            }
            write_result = await profile_write_service.set_explicit_preference(
                user_id=UUID(user_id),
                pref_key=pref_key,
                pref_value=pref_value,
                evidence_refs=[evidence_ref],
                confidence=params.confidence,
                source_type="user_state",
                source="manual_edit",
            )

            try:
                from app.services.system_update_service import SystemUpdateService, build_system_update
                update_service = SystemUpdateService()
                await update_service.enqueue(
                    user_id=user_id,
                    payload=build_system_update(
                        update_type="profile_update",
                        category="preference",
                        title="偏好已更新",
                        description=f"已更新你的偏好：{pref_key}",
                        priority="low",
                        metadata={"pref_key": pref_key, "source": "user_confirmed"},
                    ),
                )
            except Exception as exc:
                logger.warning(f"Failed to enqueue system update: {exc}")

            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={
                    "pref_key": pref_key,
                    "pref_value": pref_value,
                    "explicit_updated": True,
                    "record_id": write_result.history_record_id,
                    "preference_version": write_result.preference_version,
                    "history_version": write_result.history_version,
                },
            )
        except Exception as exc:
            logger.error(f"update_user_preference failed: {exc}")
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=str(exc),
                error_type="exception",
            )
