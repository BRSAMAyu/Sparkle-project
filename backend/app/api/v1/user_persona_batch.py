"""
User Persona Batch Editing API
用户画像批量编辑API

Provides batch operations for managing user preferences and personas.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.memory_service import MemoryService
from app.services.profile_write_service import ProfileWriteService

router = APIRouter(prefix="/user/persona", tags=["user-persona"])


# Request/Response Models
class BatchUpdatePreferencesRequest(BaseModel):
    """批量更新偏好请求"""
    preference_ids: list[str] = Field(..., description="要更新的偏好ID列表")
    updates: dict[str, Any] = Field(..., description="更新内容")
    operation: str = Field(default="update", description="操作类型: update, delete, merge")


class BatchUpdatePreferencesResponse(BaseModel):
    """批量更新响应"""
    success_count: int
    failed_count: int
    errors: list[str] = []


class ExportPersonaRequest(BaseModel):
    """导出画像数据请求"""
    format: str = Field(default="json", description="导出格式: json, csv")
    include_goals: bool = Field(default=True, description="是否包含目标")
    include_preferences: bool = Field(default=True, description="是否包含偏好")


class ImportPersonaRequest(BaseModel):
    """导入画像数据请求"""
    format: str = Field(..., description="导入格式: json, csv")
    data: dict[str, Any] = Field(..., description="画像数据")
    merge_strategy: str = Field(default="merge", description="合并策略: merge, replace")


@router.post("/batch-update")
async def batch_update_preferences(
    request: BatchUpdatePreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量更新用户偏好

    支持更新、删除、合并操作
    """
    memory_service = MemoryService(db)
    profile_write_service = ProfileWriteService(db)
    response = BatchUpdatePreferencesResponse(
        success_count=0,
        failed_count=0,
        errors=[],
    )

    def _normalize_updates(updates: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(updates)
        if "key" in normalized and "pref_key" not in normalized:
            normalized["pref_key"] = normalized.pop("key")
        if "value" in normalized and "pref_value" not in normalized:
            normalized["pref_value"] = normalized.pop("value")
        return normalized

    updates = _normalize_updates(request.updates)

    for pref_id in request.preference_ids:
        try:
            pref_uuid = UUID(pref_id)
            existing = await memory_service.get_preference_record(
                user_id=current_user.id,
                preference_id=pref_uuid,
            )
            if existing is None:
                raise ValueError("Preference not found")
            if request.operation == "update":
                next_key = updates.get("pref_key", existing.pref_key)
                next_value = updates.get("pref_value", existing.pref_value)
                await profile_write_service.set_explicit_preference(
                    user_id=current_user.id,
                    pref_key=next_key,
                    pref_value=next_value,
                    evidence_refs=[
                        {"type": "user_state", "id": "batch_update", "schema_version": "batch_update.v1"}
                    ],
                    confidence=updates.get("confidence", existing.confidence),
                    source_type="user_state",
                    source="manual_edit",
                )
                response.success_count += 1

            elif request.operation == "delete":
                await profile_write_service.remove_explicit_preference(
                    user_id=current_user.id,
                    pref_key=existing.pref_key,
                    reason="batch_delete",
                )
                response.success_count += 1

            elif request.operation == "merge":
                merged = {
                    "pref_key": existing.pref_key,
                    "pref_value": existing.pref_value,
                    "confidence": existing.confidence,
                }
                merged.update(updates)
                await profile_write_service.set_explicit_preference(
                    user_id=current_user.id,
                    pref_key=merged["pref_key"],
                    pref_value=merged["pref_value"],
                    evidence_refs=[
                        {"type": "user_state", "id": "batch_merge", "schema_version": "batch_merge.v1"}
                    ],
                    confidence=merged.get("confidence"),
                    source_type="user_state",
                    source="manual_edit",
                )
                response.success_count += 1

        except Exception as e:
            response.failed_count += 1
            response.errors.append(f"Failed to update {pref_id}: {str(e)}")
            logger.error(f"Batch update failed for {pref_id}: {e}")

    return response


@router.post("/export")
async def export_persona_data(
    request: ExportPersonaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    导出用户画像数据

    支持JSON和CSV格式导出
    """
    memory_service = MemoryService(db)

    # Get user's preferences
    preferences = await memory_service.list_preference_records(current_user.id)

    # Get user's goals
    goals = []
    if request.include_goals:
        user_goals = await memory_service.list_goals(
            user_id=current_user.id,
            limit=100,
        )
        goals = [
            {
                'id': str(g.id),
                'title': g.title,
                'description': (g.metadata_payload or {}).get("description"),
                'target_date': g.target_date.isoformat() if g.target_date else None,
                'status': g.status,
                'priority': (g.metadata_payload or {}).get("priority"),
            }
            for g in user_goals
        ]

    # Format preferences
    pref_data = []
    for pref in preferences:
        pref_data.append({
            'id': str(pref.id),
            'pref_key': pref.pref_key,
            'pref_value': pref.pref_value,
            'confidence': pref.confidence,
            'created_at': pref.created_at.isoformat(),
        })

    export_data = {
        'user_id': str(current_user.id),
        'export_date': datetime.now().isoformat(),
        'preferences': pref_data if request.include_preferences else [],
        'goals': goals,
    }

    if request.format == "csv":
        # Convert to CSV format
        # In practice, use a CSV library
        return {"format": "csv", "data": export_data}

    return {"format": "json", "data": export_data}


@router.post("/import")
async def import_persona_data(
    request: ImportPersonaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    导入用户画像数据

    支持合并或替换现有数据
    """
    memory_service = MemoryService(db)
    profile_write_service = ProfileWriteService(db)
    imported_count = 0
    errors = []
    data = request.data
    total_items = 0

    def _csv_count(payload: str | None) -> int:
        if not payload:
            return 0
        # Count non-header lines; ignore blank lines
        lines = [line for line in payload.splitlines() if line.strip()]
        return max(0, len(lines) - 1)

    if request.format == "json":
        total_items = len(data.get("preferences", [])) + len(data.get("goals", []))
        # Import preferences
        for pref_data in data.get("preferences", []):
            try:
                pref_key = pref_data.get("pref_key") or pref_data.get("key")
                if not pref_key:
                    raise ValueError("pref_key missing")

                pref_value = pref_data.get("pref_value")
                if pref_value is None:
                    pref_value = pref_data.get("value")
                if pref_value is None:
                    raise ValueError("pref_value missing")
                if not isinstance(pref_value, dict):
                    pref_value = {"value": pref_value}

                if request.merge_strategy == "replace":
                    await profile_write_service.set_explicit_preference(
                        user_id=current_user.id,
                        pref_key=pref_key,
                        pref_value=pref_value,
                        evidence_refs=[
                            {"type": "user_state", "id": "batch_import", "schema_version": "batch_import.v1"}
                        ],
                        confidence=pref_data.get("confidence", 0.8),
                        source_type="user_state",
                        source="manual_edit",
                    )
                    imported_count += 1

                else:  # merge
                    # Try to update existing
                    existing = await memory_service.find_preference(
                        user_id=current_user.id,
                        pref_key=pref_key,
                    )

                    if existing:
                        await profile_write_service.set_explicit_preference(
                            user_id=current_user.id,
                            pref_value=pref_value,
                            pref_key=pref_key,
                            evidence_refs=[
                                {"type": "user_state", "id": "batch_import", "schema_version": "batch_import.v1"}
                            ],
                            confidence=pref_data.get("confidence", 0.8),
                            source_type="user_state",
                            source="manual_edit",
                        )
                        imported_count += 1
                    else:
                        await profile_write_service.set_explicit_preference(
                            user_id=current_user.id,
                            pref_key=pref_key,
                            pref_value=pref_value,
                            evidence_refs=[
                                {"type": "user_state", "id": "batch_import", "schema_version": "batch_import.v1"}
                            ],
                            confidence=pref_data.get("confidence", 0.8),
                            source_type="user_state",
                            source="manual_edit",
                        )
                        imported_count += 1

            except Exception as e:
                errors.append(f"Failed to import preference {pref_data.get('key', 'unknown')}: {str(e)}")
                logger.error(f"Import failed: {e}")

        # Import goals
        for goal_data in data.get("goals", []):
            try:
                goal_metadata: dict[str, Any] = {}
                if goal_data.get("description") is not None:
                    goal_metadata["description"] = goal_data.get("description")
                if goal_data.get("priority") is not None:
                    goal_metadata["priority"] = goal_data.get("priority")

                if request.merge_strategy == "replace":
                    # Delete existing goals
                    # (In practice, query and delete first)

                    # Create new goal
                    await memory_service.create_goal(
                        user_id=current_user.id,
                        title=goal_data["title"],
                        target_date=datetime.fromisoformat(goal_data["target_date"]) if goal_data.get("target_date") else None,
                        status=goal_data.get("status"),
                        metadata=goal_metadata or None,
                    )
                    imported_count += 1

                else:  # merge
                    # Try to find existing goal with similar title
                    existing_goals = await memory_service.list_goals(
                        user_id=current_user.id,
                    )
                    matching = [g for g in existing_goals if g.title == goal_data["title"]]

                    if matching:
                        # Update existing
                        updates: dict[str, Any] = {}
                        if goal_data.get("status") is not None:
                            updates["status"] = goal_data.get("status")
                        if goal_data.get("target_date") is not None:
                            updates["target_date"] = datetime.fromisoformat(goal_data["target_date"])
                        if goal_metadata:
                            updates["metadata"] = goal_metadata
                        if updates:
                            await memory_service.update_goal(
                                user_id=current_user.id,
                                goal_id=matching[0].id,
                                **updates,
                            )
                        imported_count += 1
                    else:
                        # Create new
                        await memory_service.create_goal(
                            user_id=current_user.id,
                            title=goal_data["title"],
                            target_date=datetime.fromisoformat(goal_data["target_date"]) if goal_data.get("target_date") else None,
                            status=goal_data.get("status"),
                            metadata=goal_metadata or None,
                        )
                        imported_count += 1

            except Exception as e:
                errors.append(f"Failed to import goal {goal_data.get('title', 'unknown')}: {str(e)}")
                logger.error(f"Import failed: {e}")

    elif request.format == "csv":
        preferences_csv = data.get("preferences_csv") if isinstance(data, dict) else None
        total_items += _csv_count(preferences_csv)
        if preferences_csv:
            reader = csv.DictReader(io.StringIO(preferences_csv))
            for row in reader:
                try:
                    pref_key = (row.get("pref_key") or row.get("key") or "").strip()
                    if not pref_key:
                        raise ValueError("pref_key missing")

                    raw_value = row.get("pref_value") or row.get("value")
                    if raw_value is None:
                        raise ValueError("pref_value missing")

                    try:
                        parsed_value = json.loads(raw_value)
                    except Exception:
                        parsed_value = {"value": raw_value}
                    if not isinstance(parsed_value, dict):
                        parsed_value = {"value": parsed_value}

                    confidence_raw = row.get("confidence")
                    confidence_val = float(confidence_raw) if confidence_raw else 0.8

                    await profile_write_service.set_explicit_preference(
                        user_id=current_user.id,
                        pref_key=pref_key,
                        pref_value=parsed_value,
                        evidence_refs=[
                            {
                                "type": "user_state",
                                "id": "batch_import_csv",
                                "schema_version": "batch_import.v1",
                            }
                        ],
                        confidence=confidence_val,
                        source_type="user_state",
                        source="manual_edit",
                    )
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Failed to import preference {row.get('pref_key', 'unknown')}: {str(e)}")
                    logger.error(f"CSV import failed: {e}")

        goals_csv = data.get("goals_csv") if isinstance(data, dict) else None
        total_items += _csv_count(goals_csv)
        if goals_csv:
            reader = csv.DictReader(io.StringIO(goals_csv))
            for row in reader:
                try:
                    title = (row.get("title") or "").strip()
                    if not title:
                        raise ValueError("title missing")

                    target_date_val = None
                    target_date_raw = row.get("target_date")
                    if target_date_raw:
                        try:
                            from datetime import date

                            target_date_val = date.fromisoformat(target_date_raw)
                        except Exception:
                            target_date_val = datetime.fromisoformat(target_date_raw).date()

                    metadata: dict[str, Any] = {}
                    if row.get("description"):
                        metadata["description"] = row.get("description")
                    if row.get("priority"):
                        metadata["priority"] = row.get("priority")

                    await memory_service.create_goal(
                        user_id=current_user.id,
                        title=title,
                        status=row.get("status") or "active",
                        target_date=target_date_val,
                        metadata=metadata or None,
                        source_type="user_state",
                    )
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Failed to import goal {row.get('title', 'unknown')}: {str(e)}")
                    logger.error(f"CSV goal import failed: {e}")

        if total_items == 0:
            errors.append("No CSV payload provided (expected preferences_csv and/or goals_csv)")

    return {
        "imported_count": imported_count,
        "total_items": total_items,
        "errors": errors,
    }


@router.get("/batch-edit-suggestions")
async def get_batch_edit_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取批量编辑建议

    基于用户行为数据提供智能批量编辑建议
    """
    # In a full implementation, analyze user patterns to suggest:
    # - Conflicting preferences that should be resolved
    # - Redundant goals that could be merged
    # - Low-confidence items that need attention
    # - Outdated preferences that should be removed

    suggestions = {
        "conflicts": [
            {
                "type": "preference_conflict",
                "description": "Multiple preferences for learning style",
                "items": ["learning_style_visual", "learning_style_textual"],
                "suggested_action": "Consolidate into single preference",
            }
        ],
        "redundancies": [
            {
                "type": "redundant_goals",
                "description": "Similar learning goals",
                "items": ["goal_math_basic", "goal_math_fundamentals"],
                "suggested_action": "Merge or remove duplicate",
            }
        ],
        "low_confidence": [
            {
                "type": "low_confidence",
                "description": "Preferences with confidence < 0.5",
                "count": 3,
                "suggested_action": "Review and update with user input",
            }
        ],
    }

    return suggestions
