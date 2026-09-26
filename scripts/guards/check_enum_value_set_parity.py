#!/usr/bin/env python3
"""Rule ENUM-PARITY: backend StrEnum ↔ mobile Dart enum 值集对账守卫。

背景：B06 实体真源审计（v3/06_agent_fleet/B06_ENTITY_TRUTH_BASELINE.md §4 建议 1）
——proto/DB/身份三块单源治理执行良好，但 backend StrEnum ↔ mobile Dart enum 是
纯手工镜像段，此前无任何常驻守卫覆盖；V3-FIX-259（StreakDayStatus.WEAK 四层断链）
与 V3-FIX-260（AchievementType.PLANNING 单面新增）都是该空档产物。本守卫封堵空档
防再发：本卡不做值修复（修复属 wt539 / FIX-260 后续卡）。

机制：
- 对「双面都存在」的枚举族做值集 diff（FAMILIES 显式映射表，家族真源以 backend
  app/models/ 与 app/core/run_state_machine.py 的 StrEnum 为准；wt548 扩表后 65 族
  = dual 44 + passthrough 21，逐族判定证据见映射表内注释）：
  * backend 值集 ⊄ mobile 可解析 wire 值集，且 mobile 无 unknown 哨兵兜底 → FAIL
    （EP001，列出差集）；
  * mobile 有 unknown 哨兵兜底 → 解析不崩，降级 WARN（EP001T，仍应尽快对齐）；
  * mobile 多余值 → WARN（EP002）；
  * 声明了哨兵但 mobile 侧实际不存在该哨兵 → FAIL（EP005，安全网名存实亡）；
  * 单源直通族（如 RunStatus，引擎持有、mobile 字符串直通）在 mobile 出现同名
    Dart enum → FAIL（EP003，第二真源苗头）。
- 已知断链豁免（KNOWN_DRIFT）：显式 allowlist 段，含修复卡号、归属与到期日；
  命中豁免的 FAIL 照常打印（KNOWN-DRIFT 行，绝不静默跳过）；到期后豁免自动失效
  重新变红，提示删豁免或续期。映射完整性问题（EP004）不适用豁免——守卫必须始终
  指向真实代码。
- backend-only 族（BACKEND_ONLY 清单）：无 wire 下发面/纯服务端状态的 StrEnum 不进
  映射表，从 INFO 扩表候选中分离单列展示（判定证据逐族在清单内，file:line 可复核）；
  一旦接线下发 mobile 须改判 passthrough 挪入 FAMILIES。
- --self-test：构造临时双面样本红绿自证全部判定路径。

登记：scripts/rule_guard_manifest.tsv（Rule ENUM-PARITY）。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
MOBILE_ROOT = REPO_ROOT / "mobile"
MODELS_DIR = BACKEND_ROOT / "app" / "models"

TODAY = _dt.date.today()

# ---------------------------------------------------------------------------
# 家族映射表：family → backend(class@file) ↔ mobile(enum@file)
# mobile 侧路径相对 MOBILE_ROOT，backend 侧路径相对 BACKEND_ROOT。
# unknown_sentinel：mobile 枚举里的兜底哨兵标识符（execution_intent_model.dart
# 的 unknown 哨兵是仓内范式，B06 正面样例）。
# mode="passthrough"：单源设计族——mobile 不得定义同名镜像 enum（RunStatus：
# 状态机真源在引擎，网关零复制、mobile 只读字符串直通，B06 §1 agent_run 行）。
# ---------------------------------------------------------------------------
FAMILIES: dict[str, dict] = {
    "TaskType": {
        "backend": ("app/models/task.py", "TaskType"),
        "mobile": ("lib/shared/entities/task_model.dart", "TaskType"),
        "mode": "dual",
    },
    "TaskStatus": {
        "backend": ("app/models/task.py", "TaskStatus"),
        "mobile": ("lib/shared/entities/task_model.dart", "TaskStatus"),
        "mode": "dual",
    },
    "SubTaskStatus": {
        "backend": ("app/models/task.py", "SubTaskStatus"),
        "mobile": ("lib/shared/entities/subtask_model.dart", "SubTaskStatus"),
        "mode": "dual",
    },
    "ExecutionIntentStatus": {
        "backend": ("app/models/execution_intent.py", "ExecutionIntentStatus"),
        "mobile": (
            "lib/features/task/data/models/execution_intent_model.dart",
            "ExecutionIntentStatus",
        ),
        "mode": "dual",
        "unknown_sentinel": "unknown",
    },
    "TrustLevel": {
        # backend 名 TrustLevel，mobile 名 ExecutionTrustLevel（同名不同形，映射表钉死）
        "backend": ("app/models/execution_intent.py", "TrustLevel"),
        "mobile": (
            "lib/features/task/data/models/execution_intent_model.dart",
            "ExecutionTrustLevel",
        ),
        "mode": "dual",
        "unknown_sentinel": "unknown",
    },
    "AchievementRarity": {
        "backend": ("app/models/achievement.py", "AchievementRarity"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "AchievementRarity"),
        "mode": "dual",
    },
    "AchievementType": {
        "backend": ("app/models/achievement.py", "AchievementType"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "AchievementType"),
        "mode": "dual",
    },
    "VisualEffectType": {
        "backend": ("app/models/achievement.py", "VisualEffectType"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "VisualEffectType"),
        "mode": "dual",
    },
    "ContractStatus": {
        "backend": ("app/models/achievement.py", "ContractStatus"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "ContractStatus"),
        "mode": "dual",
    },
    "StreakDayStatus": {
        "backend": ("app/models/achievement.py", "StreakDayStatus"),
        "mobile": ("lib/shared/entities/achievement_model.dart", "StreakDayStatus"),
        "mode": "dual",
    },
    "MessageRole": {
        "backend": ("app/models/chat.py", "MessageRole"),
        "mobile": ("lib/features/chat/data/models/chat_message_model.dart", "MessageRole"),
        "mode": "dual",
    },
    "PlanType": {
        # 真源 models/plan.py；backend/app/tools/schemas.py 另有一份工具参数用
        # PlanType/PlanStage（仓内既存副本，当前值集一致）——不在本守卫范围
        "backend": ("app/models/plan.py", "PlanType"),
        "mobile": ("lib/features/plan/data/models/plan_model.dart", "PlanType"),
        "mode": "dual",
    },
    "PlanStage": {
        "backend": ("app/models/plan.py", "PlanStage"),
        "mobile": ("lib/features/plan/data/models/plan_model.dart", "PlanStage"),
        "mode": "dual",
    },
    "PlanPriority": {
        "backend": ("app/models/plan.py", "PlanPriority"),
        "mobile": ("lib/features/plan/data/models/plan_model.dart", "PlanPriority"),
        "mode": "dual",
    },
    "RunStatus": {
        "backend": ("app/core/run_state_machine.py", "RunStatus"),
        "mode": "passthrough",
    },
    # -----------------------------------------------------------------------
    # wt548 扩表（ENUM-PARITY 守卫扩表卡）：15 → 65 族（dual 44 + passthrough 21），
    # 另 24 族判定 backend-only 进 BACKEND_ONLY 清单（不进表、从 INFO 候选分离）。
    # 判定方法：grep mobile/lib 找同名 Dart enum（dual）；无镜像则按 wire 面证据
    # 分 passthrough（值达 mobile 的字符串直通，RunStatus 判例）与 backend-only
    # （无 wire 下发面）。证据逐族 file:line 注释如下，可 grep 复核。
    # -----------------------------------------------------------------------
    # ===== dual：accountability / background_task =====
    "AccountabilityStatus": {
        # mobile 镜像 accountability_model.dart:8 enum AccountabilityStatus（4 值对齐）
        "backend": ("app/models/accountability.py", "AccountabilityStatus"),
        "mobile": ("lib/features/community/data/models/accountability_model.dart", "AccountabilityStatus"),
        "mode": "dual",
    },
    "BackgroundTaskType": {
        # mobile 镜像 background_task_model.dart:4 enhanced enum 构造器形态（5 值对齐）
        "backend": ("app/models/background_task.py", "BackgroundTaskType"),
        "mobile": ("lib/shared/entities/background_task_model.dart", "BackgroundTaskType"),
        "mode": "dual",
    },
    "BackgroundTaskStatus": {
        # mobile 镜像 background_task_model.dart:22（5 值对齐）
        "backend": ("app/models/background_task.py", "BackgroundTaskStatus"),
        "mobile": ("lib/shared/entities/background_task_model.dart", "BackgroundTaskStatus"),
        "mode": "dual",
    },
    # ===== dual：cognitive =====
    "PatternType": {
        # mobile 镜像 behavior_pattern_model.dart:1（ctor wire + unknown 哨兵 parse 兜底）；
        # mobile 多 'unknown' wire 值属哨兵族 EP002 WARN（StreakDayStatus 先例）。
        # 注：不声明 unknown_sentinel——ctor 形态下 identifiers 为空，声明会误触 EP005。
        "backend": ("app/models/cognitive.py", "PatternType"),
        "mobile": ("lib/features/cognitive/data/models/behavior_pattern_model.dart", "PatternType"),
        "mode": "dual",
    },
    # ===== dual：community（9 族）=====
    "FriendshipStatus": {
        # mobile 镜像 community_model.dart:73（@JsonValue，3 值对齐；proto 侧 FriendshipStatus 另有生成物不在本表）
        "backend": ("app/models/community.py", "FriendshipStatus"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "FriendshipStatus"),
        "mode": "dual",
    },
    "GroupType": {
        # mobile 镜像 community_model.dart:11 仅 squad/sprint，缺 'official'（V3-FIX-266 豁免）；
        # models 层真源含 official（community.py），API 面 schemas GroupTypeEnum 现仅 squad/sprint。
        "backend": ("app/models/community.py", "GroupType"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "GroupType"),
        "mode": "dual",
    },
    "GroupRole": {
        # mobile 镜像 community_model.dart:18（3 值对齐）
        "backend": ("app/models/community.py", "GroupRole"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "GroupRole"),
        "mode": "dual",
    },
    "MessageType": {
        # mobile 镜像 community_model.dart:37（@JsonValue+@HiveField 叠注）11 值缺 'broadcast'
        # （V3-FIX-267 豁免；wt297 实录广播真实落库并经列表下发，schemas/community.py:58-60）
        "backend": ("app/models/community.py", "MessageType"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "MessageType"),
        "mode": "dual",
    },
    "SharedResourceType": {
        # mobile 镜像 community_model.dart:1713；mobile 多 fragment/capsule/achievement/file
        # 4 个旧 wire 值（EP002 WARN 实录，不做豁免——WARN 不挡提交）
        "backend": ("app/models/community.py", "SharedResourceType"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "SharedResourceType"),
        "mode": "dual",
    },
    "ReportReason": {
        # mobile 镜像 community_model.dart:114（7 值对齐，hateSpeech 大小写映射经 @JsonValue）
        "backend": ("app/models/community.py", "ReportReason"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "ReportReason"),
        "mode": "dual",
    },
    "ReportStatus": {
        # mobile 镜像 community_model.dart:131（4 值对齐）
        "backend": ("app/models/community.py", "ReportStatus"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "ReportStatus"),
        "mode": "dual",
    },
    "ModerationAction": {
        # mobile 镜像 community_model.dart:142（4 值对齐）
        "backend": ("app/models/community.py", "ModerationAction"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "ModerationAction"),
        "mode": "dual",
    },
    "OfflineMessageStatus": {
        # mobile wire 镜像 community_model.dart:155（4 值对齐）。注意 core/offline/models/
        # offline_chat_message.dart:6 有同名本地队列枚举（pending/sent/acked/failed，含 acked
        # 无 expired）——语义为离线发送队列生命周期非 backend 镜像，不进映射（本表映射 wire 面）。
        "backend": ("app/models/community.py", "OfflineMessageStatus"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "OfflineMessageStatus"),
        "mode": "dual",
    },
    # ===== dual：execution_intent / file_storage =====
    "ExecutionMode": {
        # mobile 镜像 execution_intent_model.dart:3（标识符即 wire 值，3 值对齐）
        "backend": ("app/models/execution_intent.py", "ExecutionMode"),
        "mobile": ("lib/features/task/data/models/execution_intent_model.dart", "ExecutionMode"),
        "mode": "dual",
    },
    "SourceLifecycleStatus": {
        # mobile 镜像 task_model.dart:45（4 值对齐，source_lifecycle_badge.dart:152+ 消费）；
        # document_library_models.dart:21 第二镜像同值集（fromRaw parse 形态），同源同值。
        "backend": ("app/models/file_storage.py", "SourceLifecycleStatus"),
        "mobile": ("lib/shared/entities/task_model.dart", "SourceLifecycleStatus"),
        "mode": "dual",
    },
    # ===== dual：seed_content（4 族）=====
    "LibraryCategory": {
        # mobile 镜像 seed_library_model.dart:11（4 值对齐）
        "backend": ("app/models/seed_content.py", "LibraryCategory"),
        "mobile": ("lib/features/seed_library/data/models/seed_library_model.dart", "LibraryCategory"),
        "mode": "dual",
    },
    "LibraryVisibility": {
        # mobile 镜像 seed_library_model.dart:23（3 值对齐）
        "backend": ("app/models/seed_content.py", "LibraryVisibility"),
        "mobile": ("lib/features/seed_library/data/models/seed_library_model.dart", "LibraryVisibility"),
        "mode": "dual",
    },
    "ItemType": {
        # mobile 镜像 seed_library_model.dart:33（5 值对齐）
        "backend": ("app/models/seed_content.py", "ItemType"),
        "mobile": ("lib/features/seed_library/data/models/seed_library_model.dart", "ItemType"),
        "mode": "dual",
    },
    "DifficultyLevel": {
        # mobile 镜像 seed_library_model.dart:47（4 值对齐）
        "backend": ("app/models/seed_content.py", "DifficultyLevel"),
        "mobile": ("lib/features/seed_library/data/models/seed_library_model.dart", "DifficultyLevel"),
        "mode": "dual",
    },
    # ===== dual：shop（4 族；PhotonTransactionType 漂移见 V3-FIX-268）=====
    "PhotonTransactionType": {
        # mobile 镜像 photon_model.dart:19（@JsonValue + $enumDecode 硬解码，见行内 D-COMM-2
        # 注释：缺成员即交易历史解析崩）缺 contract_escrow/grant_bonus/guest_seed（V3-FIX-268 豁免）
        "backend": ("app/models/shop.py", "PhotonTransactionType"),
        "mobile": ("lib/shared/entities/photon_model.dart", "PhotonTransactionType"),
        "mode": "dual",
    },
    "ShopItemType": {
        # mobile 镜像 shop_model.dart:7（5 值对齐）
        "backend": ("app/models/shop.py", "ShopItemType"),
        "mobile": ("lib/shared/entities/shop_model.dart", "ShopItemType"),
        "mode": "dual",
    },
    "ItemRarity": {
        # mobile 镜像 shop_model.dart:21（4 值对齐）
        "backend": ("app/models/shop.py", "ItemRarity"),
        "mobile": ("lib/shared/entities/shop_model.dart", "ItemRarity"),
        "mode": "dual",
    },
    "ConsumableEffectType": {
        # mobile 镜像 shop_model.dart:42（6 值对齐）
        "backend": ("app/models/shop.py", "ConsumableEffectType"),
        "mobile": ("lib/shared/entities/shop_model.dart", "ConsumableEffectType"),
        "mode": "dual",
    },
    # ===== dual：user / visual_element =====
    "UserStatus": {
        # mobile 镜像 user_brief.dart:7（3 值对齐）
        "backend": ("app/models/user.py", "UserStatus"),
        "mobile": ("lib/shared/entities/user_brief.dart", "UserStatus"),
        "mode": "dual",
    },
    "AvatarStatus": {
        # mobile 镜像 user_model.dart:6（3 值对齐）
        "backend": ("app/models/user.py", "AvatarStatus"),
        "mobile": ("lib/shared/entities/user_model.dart", "AvatarStatus"),
        "mode": "dual",
    },
    "SearchVisibility": {
        # mobile 镜像 community_model.dart:1570（3 值对齐；proto UserPrivacySettings 同面）
        "backend": ("app/models/user.py", "SearchVisibility"),
        "mobile": ("lib/features/community/data/models/community_model.dart", "SearchVisibility"),
        "mode": "dual",
    },
    "VisualElementType": {
        # mobile 镜像 visual_element_model.dart:8（4 值对齐）
        "backend": ("app/models/visual_element.py", "VisualElementType"),
        "mobile": ("lib/shared/entities/visual_element_model.dart", "VisualElementType"),
        "mode": "dual",
    },
    "VisualElementRarity": {
        # mobile 镜像 visual_element_model.dart:20（4 值对齐）
        "backend": ("app/models/visual_element.py", "VisualElementRarity"),
        "mobile": ("lib/shared/entities/visual_element_model.dart", "VisualElementRarity"),
        "mode": "dual",
    },
    "VisualElementUnlockSource": {
        # mobile 镜像 visual_element_model.dart:32（5 值对齐）
        "backend": ("app/models/visual_element.py", "VisualElementUnlockSource"),
        "mobile": ("lib/shared/entities/visual_element_model.dart", "VisualElementUnlockSource"),
        "mode": "dual",
    },
    "SectorCode": {
        # 名异形镜像（TrustLevel→ExecutionTrustLevel 判例）：backend SectorCode 7 值 ↔
        # mobile galaxy_model.dart:127 SectorEnum（@JsonValue COSMOS..VOID 全对齐）；
        # wire 面 schemas/galaxy.py:274 sector_code + knowledge_detail_model.dart:89 parse-switch
        "backend": ("app/models/sector.py", "SectorCode"),
        "mobile": ("lib/shared/entities/galaxy_model.dart", "SectorEnum"),
        "mode": "dual",
    },
    # ===== passthrough：值达 mobile 的字符串直通族（出现同名 Dart enum 即 EP003 FAIL）=====
    "AccountabilitySlotType": {
        # backend accountability.py 'core' → community API slot_type 字符串
        # （accountability_model.dart:57-58 @JsonKey slot_type String 直读）
        "backend": ("app/models/accountability.py", "AccountabilitySlotType"),
        "mode": "passthrough",
    },
    "AgentRunKind": {
        # backend agent_run.py → runs.py:79 kind 字段往返（mobile agent_run_read_service.dart:152
        # 读 json['kind'] 字符串）
        "backend": ("app/models/agent_run.py", "AgentRunKind"),
        "mode": "passthrough",
    },
    "AuthAuditAction": {
        # backend auth_security.py → users.py:528 /users/me/security-log 下发 action 字符串
        # （mobile security_log_screen.dart:90/110/140 case parse-switch 直读）
        "backend": ("app/models/auth_security.py", "AuthAuditAction"),
        "mode": "passthrough",
    },
    "CardType": {
        # backend card_protocol.py → card_service.py:80-81 card_type 载荷（mobile
        # entity_card_payloads.dart:20-21 CardProtocolRef 直读 card_type、:52 case 'KNOWLEDGE'）
        "backend": ("app/models/card_protocol.py", "CardType"),
        "mode": "passthrough",
    },
    "CardLifecycleStatus": {
        # backend card_protocol.py → cards.py:244 / plans.py:1211 lifecycle_status 下发
        # （mobile plan_phase_model.dart:42 直读默认 'DRAFT'、plan_repository.dart:343）
        "backend": ("app/models/card_protocol.py", "CardLifecycleStatus"),
        "mode": "passthrough",
    },
    "OccurrenceStatus": {
        # backend card_protocol.py → cards.py:314 defer occurrence 响应 status 字符串
        # （mobile api_endpoints.dart:201 deferCardOccurrence 调用面）
        "backend": ("app/models/card_protocol.py", "OccurrenceStatus"),
        "mode": "passthrough",
    },
    "InterventionTriggerType": {
        # backend card_protocol.py → intervention_event_consumer.py:122 通知 metadata trigger_type
        # （mobile notification_center_provider.dart:320 直读）
        "backend": ("app/models/card_protocol.py", "InterventionTriggerType"),
        "mode": "passthrough",
    },
    "DeliveryChannel": {
        # backend card_protocol.py → intervention_event_consumer.py:145 metadata delivery_channel
        # （mobile unified_notification_model.dart:218 直读）
        "backend": ("app/models/card_protocol.py", "DeliveryChannel"),
        "mode": "passthrough",
    },
    "InterventionAcceptanceStatus": {
        # backend card_protocol.py → 通知 metadata acceptance_status
        # （mobile unified_notification_model.dart:267 直读）
        "backend": ("app/models/card_protocol.py", "InterventionAcceptanceStatus"),
        "mode": "passthrough",
    },
    "InterventionOutcomeStatus": {
        # backend card_protocol.py → 通知 metadata outcome_status
        # （mobile unified_notification_model.dart:302 直读、unified_notification_card.dart:817
        # case 'EFFECTIVE' 标签映射）
        "backend": ("app/models/card_protocol.py", "InterventionOutcomeStatus"),
        "mode": "passthrough",
    },
    "SharePermission": {
        # backend card_protocol.py → community.py:1174-1182 legacy permission 字符串映射、
        # schemas/community.py:772 permission 下发（mobile community_share_repository.dart:75
        # 发送 'permission'、community_model.dart:1831 解析）
        "backend": ("app/models/card_protocol.py", "SharePermission"),
        "mode": "passthrough",
    },
    "AnalysisStatus": {
        # backend cognitive.py → schemas/cognitive.py:45 analysis_status（cognitive.py:302
        # /cognitive/fragments 下发；mobile api_endpoints.dart:554 调用面）
        "backend": ("app/models/cognitive.py", "AnalysisStatus"),
        "mode": "passthrough",
    },
    "ExecutorType": {
        # backend execution_intent.py → executions.py:66/366 executor 字段（mobile
        # task_repository.dart:526/646 发 'executor':'openclaw'、execution_intent_model.dart:124
        # 读 ?? 'manual'）
        "backend": ("app/models/execution_intent.py", "ExecutorType"),
        "mode": "passthrough",
    },
    "ExecutionTargetEnv": {
        # backend execution_intent.py → execution_service.py:870 target_env 进 chat suggestion
        # metadata（mobile chat_provider.dart:729 直读；executions.py:67/92 请求面 str 字段）
        "backend": ("app/models/execution_intent.py", "ExecutionTargetEnv"),
        "mode": "passthrough",
    },
    "ExecutionScheduleTriggerType": {
        # backend execution_schedule.py → executions.py:303/653 schedules 响应
        # （execution_schedule.py:62 to_dict trigger_type；mobile openclaw_automation_service.dart:
        # 108 读 trigger_type、:297 调 ApiEndpoints.executionSchedules）
        "backend": ("app/models/execution_schedule.py", "ExecutionScheduleTriggerType"),
        "mode": "passthrough",
    },
    "FocusType": {
        # backend focus.py → focus.py:29/65 focus_type 字符串校验（mobile
        # focus_session_record.dart:26 'pomodoro'/'stopwatch' 本地记录 + /focus/sessions 同步
        # api_endpoints.dart:574）
        "backend": ("app/models/focus.py", "FocusType"),
        "mode": "passthrough",
    },
    "FocusStatus": {
        # backend focus.py → focus.py:66 status 校验（mobile focus_session_record.dart:29/108
        # 'completed'/'interrupted'）
        "backend": ("app/models/focus.py", "FocusStatus"),
        "mode": "passthrough",
    },
    "GroupFileTrustLevel": {
        # backend group_files.py → proto/community_service.proto:33 + schemas/community.py:40
        # trust_level 字符串（mobile file_models.dart:243 直读、file_repository.dart:223 发送）
        "backend": ("app/models/group_files.py", "GroupFileTrustLevel"),
        "mode": "passthrough",
    },
    "PlanStateStatus": {
        # backend plan_state.py → plans.py:1677/1729/1750 plan-state status 下发
        # （mobile planArchive /plans/{id}/archive 调用面 api_endpoints.dart:178）
        "backend": ("app/models/plan_state.py", "PlanStateStatus"),
        "mode": "passthrough",
    },
    "AssetStatus": {
        # backend learning_assets.py → vocabulary_service.py learning_loop 摘要
        # "learning_asset".status 下发（vocabulary.py:336/366 装配；mobile
        # vocabulary_repository.dart:41 调用面）
        "backend": ("app/models/learning_assets.py", "AssetStatus"),
        "mode": "passthrough",
    },
}

# ---------------------------------------------------------------------------
# 已知断链豁免清单（显式 allowlist——修复落地后必须删除对应条目，不许静默跳过：
# 豁免命中照样打印 KNOWN-DRIFT 行；过期后自动失效重新变红）。
#   expiry：UTC 日期。到期日选官方截止（比赛提交 2026-10-07）：
#   到期未修 = 守卫重新变红，逼一次显式续期决策而非无限期忍耐。
# 只对 EP001（mobile 缺值）生效；映射完整性（EP004）不适用豁免。
# ---------------------------------------------------------------------------
KNOWN_DRIFT: dict[str, dict] = {
    # V3-FIX-259 豁免已删：wt539 修复落地（迁移补 weak 四值/engine savepoint/
    # mobile weak+unknown 哨兵），守卫实测对齐，豁免即删保持棘轮纯净。
    # V3-FIX-260 豁免已删：wt542 修复落地（mobile 补 planning+unknown 哨兵，
    # 守卫实测对齐仅剩 EP002 unknown WARN），豁免即删保持棘轮纯净。
    # V3-FIX-269/270/271 豁免已删：wt553 修复落地（mobile GroupType 补
    # official、MessageType 补 broadcast、PhotonTransactionType 补
    # grant_bonus/contract_escrow/guest_seed，三族均加 unknown 哨兵 +
    # unknownEnumValue 兜底 + 消费面穷举 switch/l10n），豁免即删保持棘轮纯净。
}

# ---------------------------------------------------------------------------
# 已判定 backend-only 清单（wt548 扩表卡逐族判定，证据 file:line 可 grep 复核）：
# 无 wire 下发面/纯服务端状态——不进 FAMILIES 对账（mobile 无镜像也无直通消费面），
# 从 INFO 扩表候选中分离以消噪声。族名 → 判定证据摘要。
# 注意：这些族一旦接线下发 mobile，必须改判 passthrough 并挪入 FAMILIES。
# ---------------------------------------------------------------------------
BACKEND_ONLY: dict[str, str] = {
    "CardVisibility": "card_snapshot_service.py:149 仅进 POST /cards/{id}/snapshot 载荷"
    "（cards.py:325，mobile api_endpoints 无对应调用、值 0 命中）",
    "CardSourceType": "card_snapshot_service.py:150/:433 同 CardVisibility 面，mobile 无调用",
    "CardCreatedBy": "服务端归属标注（card_snapshot_service.py:357），无下发面",
    "EdgeType": "cards.py:44 /cards/{id}/link 请求面存在但 mobile 无 linkCard 调用方"
    "（api_endpoints.dart:198 定义未接线、值 0 命中）",
    "BindingMode": "同 EdgeType（cards.py:45，默认 REFERENCE 服务端兜底）",
    "ArtifactType": "plans.py:535/:804 服务端 artifact 流（mobile api_endpoints 无 artifact 面、"
    "GLOBAL_COMPASS/DISCOVERY_DOSSIER 等 0 命中）；接线时改判 passthrough",
    "ArtifactStatus": "planning_artifact_service 服务端状态机（weekly_digest_service 同），无下发面",
    "DeliveryStrategy": "intervention_event_consumer.py:136 仅服务端 title 构建，通知 metadata"
    " 只含 trigger_type/delivery_channel/acceptance_status/outcome_status",
    "ImportMode": "community.py:4008 服务端从 permission 推导（'fork'→FORK 否则 ADOPT），"
    "cards.py:87 请求面 mobile 无调用",
    "ShareScope": "community.py:3536 服务端按 target 设定 GROUP/USER；SharedResourceInfo 响应"
    "（schemas/community.py:752-772）无 scope 字段，mobile repository 的 'scope' 参数为 feed "
    "scope 非本族",
    "CustomExpertSource": "仅 models/custom_expert.py 定义，无 API/schema/服务引用（休眠面）",
    "ExperimentStatus": "experiments.py:375 服务端实验框架；mobile api_endpoints 无 experiments",
    "MetricType": "实验框架服务端（profile_transparency 命中为 NorthStarMetricType 子串误报）",
    "JobType": "models/job.py 服务端异步任务（job_service 未挂任何 API 路由，grep api/v1 零命中）",
    "JobStatus": "同 JobType（models/job.py）。注意 mobile capsule_generation_job_model.dart:7 有"
    "同名 enum JobStatus，但对应的是 capsule_generation_job.py 的 enum.Enum（非 StrEnum、不在本"
    "守卫盘点且值集 pending/generating/completed/failed 已对齐）——故本族不能判 passthrough"
    "（会误触 EP003），只能 backend-only",
    "AssetKind": "assets.py:111 请求校验 + vocabulary.py:331 服务端创建（AssetKind.WORD），"
    "不下发 mobile（learning_loop 摘要只含 asset status 不含 kind）",
    "MatchStrength": "core/fuzzy_match.py 服务端匹配打分，无 API 面",
    "SuggestionDecision": "learning_asset_service 服务端建议引擎决策记录，无下发面",
    "UserSuggestionResponse": "assets.py 建议反馈端点 mobile 无调用（mobile 仅 /tasks/suggestions"
    " 属他域）",
    "PlanStatus": "models/plan.py:57 无列引用（plan_service.py:512 注释自证「PlanStatus 枚举无列"
    "引用」），plans.py 无下发；agents/graph/state.py:20 另有同名 LangGraph 内部类均服务端",
    "InteractionType": "仅 models/recommendation.py 定义，无 API/schema/服务引用（休眠面）",
    "CognitiveOwnership": "action_authorization/allocation_policy 等服务端动作分配，无 api/schema 面",
    "RiskClass": "同 CognitiveOwnership（服务端风险分级），无下发面",
    "TaskResourceType": "tasks.py:297-328/:852 请求面 + schemas/task.py:471 响应字段存在，但 "
    "mobile api_endpoints 无 task resources 调用（仅 community shared-resources 属他域）、"
    "值 0 命中；接线时改判 passthrough",
}

# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------

PY_CLASS_RE = re.compile(r"^class\s+(?P<name>\w+)\s*\(\s*(?:enum\.)?StrEnum\s*\)\s*:", re.MULTILINE)
PY_MEMBER_RE = re.compile(
    r"^\s+(?P<member>[A-Z][A-Z0-9_]*)\s*(?::\s*[\w\.]+\s*)?=\s*[\"'](?P<value>[^\"']*)[\"']",
    re.MULTILINE,
)


def extract_python_str_enum(root: Path, rel_path: str, class_name: str) -> dict[str, str] | None:
    """从 Python 源码抽 StrEnum 类的 {member: value}；类不存在返回 None。

    纯文本解析不 import（守卫运行环境不保证 backend 依赖齐全）；遇到类内
    def（如 __new__）或下一个顶层 class 即停，避免把方法体当成员。
    """
    path = root / rel_path
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    for m in PY_CLASS_RE.finditer(text):
        if m.group("name") != class_name:
            continue
        body_start = m.end()
        next_boundary = len(text)
        nxt = PY_CLASS_RE.search(text, body_start)
        if nxt:
            next_boundary = nxt.start()
        body = text[body_start:next_boundary]
        members: dict[str, str] = {}
        for line in body.splitlines():
            if re.match(r"^\s+def\s", line):
                break  # 类内方法（如 __new__）之后不再是成员区
            pm = PY_MEMBER_RE.match(line)
            if pm:
                members[pm.group("member")] = pm.group("value")
        return members
    return None


@dataclass
class DartEnum:
    identifiers: set[str] = field(default_factory=set)
    wire_values: set[str] = field(default_factory=set)


_DART_ENUM_HEAD_RE = r"\benum\s+{name}\s*\{{"
_DART_JSON_VALUE_RE = re.compile(r"@JsonValue\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
_DART_CTOR_ARG_RE = re.compile(r"^\s*(\w+)\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE)
_DART_CASE_RE = re.compile(r"case\s+['\"]([^'\"]+)['\"]")
_DART_FUNC_RET_RE = r"\b{name}\s+\w+\s*\([^)]*\)\s*(?:async\s*)?\{{"


def _brace_span(text: str, open_idx: int) -> tuple[int, int]:
    """返回 (body_start, body_end)，open_idx 指向 '{'。"""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return open_idx + 1, i
    return open_idx + 1, len(text)


def extract_dart_enum(root: Path, rel_path: str, enum_name: str) -> DartEnum | None:
    """抽 Dart enum 的标识符集与可接受 wire 值集；不存在返回 None。

    wire 值集 = @JsonValue 注解值 ∪ enhanced-enum 构造器字符串实参 ∪
    返回该 enum 的解析函数里的 case 字面量；三者全空时回退为标识符本身
    （json_serializable 默认按 name 编解码，如 MessageRole）。
    """
    path = root / rel_path
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(_DART_ENUM_HEAD_RE.format(name=re.escape(enum_name)), text)
    if not m:
        return None
    body_start, body_end = _brace_span(text, m.end() - 1)
    body = text[body_start:body_end]

    # 常量区：enhanced enum 以 ';' 结束常量列表（其后是成员/方法）。
    semi = body.find(";")
    constants = body if semi < 0 else body[:semi]
    constants_no_comments = re.sub(r"//[^\n]*", "", constants)

    result = DartEnum()
    result.wire_values.update(_DART_JSON_VALUE_RE.findall(constants))
    result.wire_values.update(m2.group(2) for m2 in _DART_CTOR_ARG_RE.finditer(constants_no_comments))

    # 标识符：剥掉注解与构造器实参后按行取行首词。
    stripped = _DART_JSON_VALUE_RE.sub("", constants_no_comments)
    stripped = _DART_CTOR_ARG_RE.sub("", stripped)
    for line in stripped.splitlines():
        lm = re.match(r"^\s*([a-zA-Z_]\w*)\s*,?\s*$", line)
        if lm and lm.group(1) not in {"const", "final", "static"}:
            result.identifiers.add(lm.group(1))

    # 解析函数 case 字面量（_parseExecutionStatus 范式；跳过 enum 体内的非常规命中）。
    for fm in re.finditer(_DART_FUNC_RET_RE.format(name=re.escape(enum_name)), text):
        if fm.start() < body_start:
            continue
        f_start, f_end = _brace_span(text, text.find("{", fm.end() - 1))
        result.wire_values.update(_DART_CASE_RE.findall(text[f_start:f_end]))

    # 三形态全空 → json_serializable 默认按标识符编解码（如 MessageRole）。
    if not result.wire_values:
        result.wire_values = set(result.identifiers)
    return result


def inventory_unmapped_backend_enums(backend_root: Path) -> list[tuple[str, str]]:
    """盘点 app/models/ 下未进映射表的 StrEnum 类（供 main 按 BACKEND_ONLY 分流展示）。"""
    known = {spec["backend"][1] for spec in FAMILIES.values() if "backend" in spec}
    found: list[tuple[str, str]] = []
    if not (backend_root / "app" / "models").exists():
        return found
    for py in sorted((backend_root / "app" / "models").rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        for m in PY_CLASS_RE.finditer(text):
            # 名为 StrEnum 的是项目内基类定义本身，不是业务枚举族
            if m.group("name") not in known and m.group("name") != "StrEnum":
                rel = py.relative_to(backend_root)
                found.append((m.group("name"), str(rel)))
    return found


# ---------------------------------------------------------------------------
# 对账
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    family: str
    code: str  # EP001 / EP001T / EP002 / EP003 / EP004 / EP005
    severity: str  # FAIL / WARN
    message: str
    exempt: str | None = None  # 豁免标注（fix 号），非 None 则不影响退出码


def _family_check(
    family: str,
    spec: dict,
    backend_root: Path,
    mobile_root: Path,
    allowlist: dict[str, dict],
    today: _dt.date,
) -> list[Finding]:
    findings: list[Finding] = []
    mode = spec.get("mode", "dual")
    be_path, be_class = spec["backend"]

    def _exempt_if_allowed(f: Finding) -> Finding:
        entry = allowlist.get(family)
        if f.severity == "FAIL" and f.code == "EP001" and entry is not None:
            if today <= entry["expiry"]:
                f.exempt = f"{entry['fix']}（{entry['owner']}，到期 {entry['expiry'].isoformat()}）"
            else:
                f.message += (
                    f"  [豁免已过期 {entry['expiry'].isoformat()}（{entry['fix']}，"
                    f"{entry['owner']}）——修复应已落地，请删豁免条目或显式续期]"
                )
        return f

    py_members = extract_python_str_enum(backend_root, be_path, be_class)
    if py_members is None:
        findings.append(
            Finding(
                family,
                "EP004",
                "FAIL",
                f"映射完整性：backend {be_class} 未找到（{be_path}）——映射表必须指向真实代码，不得豁免",
            )
        )
        return findings
    be_values = set(py_members.values())
    if len(py_members) != len(be_values):
        dupes = sorted(v for v in be_values if list(py_members.values()).count(v) > 1)
        findings.append(
            Finding(
                family,
                "EP004",
                "FAIL",
                f"映射完整性：backend {be_class} 存在重复值 {dupes}——StrEnum 值必须唯一",
            )
        )

    if mode == "passthrough":
        # 在 mobile 全 lib 找同名 enum（单源族出现任何镜像定义即违规）
        mirror = _find_dart_enum_anywhere(mobile_root, be_class)
        if mirror is not None:
            findings.append(
                _exempt_if_allowed(
                    Finding(
                        family,
                        "EP003",
                        "FAIL",
                        f"单源直通族 {family} 在 mobile 出现镜像 enum {be_class}"
                        "——该族真源在 backend（引擎持有/mobile 字符串直通），禁止手工镜像",
                    )
                )
            )
        else:
            findings.append(
                Finding(
                    family,
                    "OK",
                    "PASS",
                    f"单源直通族 {family}（backend {len(be_values)} 值）mobile 无镜像 enum ✓",
                )
            )
        return findings

    mo_rel, mo_class = spec["mobile"]
    dart = extract_dart_enum(mobile_root, mo_rel, mo_class)
    if dart is None:
        findings.append(
            Finding(
                family,
                "EP004",
                "FAIL",
                f"映射完整性：mobile enum {mo_class} 未找到（{mo_rel}）——映射表必须指向真实代码，不得豁免",
            )
        )
        return findings

    sentinel = spec.get("unknown_sentinel")
    has_sentinel = sentinel is not None and sentinel in dart.identifiers
    if sentinel is not None and not has_sentinel:
        findings.append(
            Finding(
                family,
                "EP005",
                "FAIL",
                f"映射表声明 mobile {mo_class} 应有 unknown 哨兵兜底，但实际不存在——安全网失效",
            )
        )

    missing = sorted(be_values - dart.wire_values)
    if missing:
        if has_sentinel:
            findings.append(
                Finding(
                    family,
                    "EP001T",
                    "WARN",
                    f"backend {be_class} 值集 ⊄ mobile {mo_class}：缺 {missing}"
                    f"——mobile unknown 哨兵兜底解析不崩，降级 WARN，仍应尽快对齐",
                )
            )
        else:
            findings.append(
                _exempt_if_allowed(
                    Finding(
                        family,
                        "EP001",
                        "FAIL",
                        f"backend {be_class} 值集 ⊄ mobile {mo_class}：缺 {missing}"
                        f"（mobile 无 unknown 哨兵兜底，下发即解析崩）",
                    )
                )
            )

    extra = sorted(dart.wire_values - be_values)
    if extra:
        findings.append(
            Finding(
                family,
                "EP002",
                "WARN",
                f"mobile {mo_class} 有 backend {be_class} 之外的 wire 值 {extra}",
            )
        )

    if not any(f.code != "OK" for f in findings):
        findings.append(
            Finding(
                family,
                "OK",
                "PASS",
                f"{family}: backend {len(be_values)} 值 = mobile {len(dart.wire_values)} 值对齐 ✓",
            )
        )
    return findings


def _find_dart_enum_anywhere(mobile_root: Path, enum_name: str) -> Path | None:
    if not mobile_root.exists():
        return None
    pat = re.compile(rf"\benum\s+{re.escape(enum_name)}\b")
    for dart in sorted(mobile_root.rglob("*.dart")):
        parts = dart.parts
        if any(p in {"gen", ".dart_tool", "build"} for p in parts):
            continue
        if pat.search(dart.read_text(encoding="utf-8")):
            return dart
    return None


def run_checks(
    backend_root: Path,
    mobile_root: Path,
    families: dict[str, dict] | None = None,
    allowlist: dict[str, dict] | None = None,
    today: _dt.date | None = None,
) -> list[Finding]:
    families = families if families is not None else FAMILIES
    allowlist = allowlist if allowlist is not None else KNOWN_DRIFT
    today = today or TODAY
    findings: list[Finding] = []
    for family in sorted(families):
        findings.extend(_family_check(family, families[family], backend_root, mobile_root, allowlist, today))
    return findings


# ---------------------------------------------------------------------------
# 自证（--self-test）：临时双面样本红绿验证全部判定路径
# ---------------------------------------------------------------------------


def _write_python_enum(root: Path, rel: str, cls: str, members: list[tuple[str, str]]) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f'    {m} = "{v}"' for m, v in members)
    # 同文件多类：追加而非覆盖（fixture 各族共用 a.py）
    with p.open("a", encoding="utf-8") as fh:
        fh.write(f"import enum\n\n\nclass {cls}(enum.StrEnum):\n{body}\n")


def _write_dart_enum(
    root: Path,
    rel: str,
    enum_name: str,
    *,
    json_values: list[str] | None = None,
    ctor: list[tuple[str, str]] | None = None,
    plain: list[str] | None = None,
    sentinel: str | None = None,
    parse_cases: list[str] | None = None,
) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [f"enum {enum_name} {{", ""]
    if json_values:
        for v in json_values:
            lines.append(f"  @JsonValue('{v}')")
            lines.append(f"  {v},")
    if ctor:
        lines[-1] = ""
        for ident, v in ctor:
            lines.append(f"  {ident}('{v}'),")
    if plain:
        for ident in plain:
            lines.append(f"  {ident},")
    if sentinel:
        lines.append(f"  {sentinel},")
    lines.append("}")
    if parse_cases:
        lines.append("")
        lines.append(f"{enum_name} parse{enum_name}(String? value) {{")
        lines.append("  switch (value) {")
        for c in parse_cases:
            lines.append(f"    case '{c}':")
            lines.append(f"      return {enum_name}.{c}Camel;")
        lines.append("    default:")
        if sentinel:
            lines.append(f"      return {enum_name}.{sentinel};")
        lines.append("  }")
        lines.append("}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test() -> int:
    """构造临时双面样本，逐路径断言判定结果；失败打印实录并返回 1。"""
    with tempfile.TemporaryDirectory() as td:
        be = Path(td) / "backend"
        mo = Path(td) / "mobile"
        today = _dt.date(2026, 9, 25)
        expired_allow: dict[str, dict] = {
            "Alpha": {
                "fix": "V3-FIX-XXX",
                "owner": "test",
                "expiry": _dt.date(2026, 1, 1),
                "note": "expired",
            },
        }

        # 用例 1：对齐族 → PASS
        # 用例 2：backend 多值 + mobile 无哨兵 → FAIL EP001（未豁免）
        # 用例 3：backend 多值 + mobile 有哨兵 → WARN EP001T（不 FAIL）
        # 用例 4：mobile 多余 wire 值 → WARN EP002
        # 用例 5：豁免在期 → FAIL 降为 exempt；豁免过期 → 仍 FAIL
        # 用例 6：passthrough 族 mobile 出现镜像 enum → FAIL EP003
        # 用例 7：映射完整性（backend 类缺失）→ FAIL EP004 且不受豁免影响
        families = {
            "Aligned": {
                "backend": ("app/models/a.py", "Aligned"),
                "mobile": ("lib/a.dart", "Aligned"),
                "mode": "dual",
            },
            "Alpha": {
                "backend": ("app/models/a.py", "Alpha"),
                "mobile": ("lib/b.dart", "Alpha"),
                "mode": "dual",
            },
            "Beta": {
                "backend": ("app/models/a.py", "Beta"),
                "mobile": ("lib/c.dart", "Beta"),
                "mode": "dual",
                "unknown_sentinel": "unknown",
            },
            "Gamma": {
                "backend": ("app/models/a.py", "Gamma"),
                "mobile": ("lib/d.dart", "Gamma"),
                "mode": "dual",
            },
            "Delta": {
                "backend": ("app/models/a.py", "Delta"),
                "mobile": ("lib/e.dart", "Delta"),
                "mode": "dual",
            },
            "RunLike": {
                "backend": ("app/models/a.py", "RunLike"),
                "mode": "passthrough",
            },
            "Ghost": {
                "backend": ("app/models/a.py", "NoSuchBackendClass"),
                "mobile": ("lib/f.dart", "Ghost"),
                "mode": "dual",
            },
        }

        def members(prefix: str, values: list[str]) -> list[tuple[str, str]]:
            return [(v.upper(), v) for v in [prefix] + values]

        _write_python_enum(be, "app/models/a.py", "Aligned", [("RED", "red"), ("GREEN", "green")])
        _write_dart_enum(mo, "lib/a.dart", "Aligned", json_values=["red", "green"])

        _write_python_enum(be, "app/models/a.py", "Alpha", members("alpha", ["x1", "x2"]))
        _write_dart_enum(mo, "lib/b.dart", "Alpha", json_values=["alpha", "x1"])

        _write_python_enum(be, "app/models/a.py", "Beta", members("beta", ["y1", "y2"]))
        _write_dart_enum(mo, "lib/c.dart", "Beta", json_values=["beta", "y1"], sentinel="unknown")

        _write_python_enum(be, "app/models/a.py", "Gamma", [("G1", "g1")])
        _write_dart_enum(mo, "lib/d.dart", "Gamma", json_values=["g1", "ghost_extra"])

        _write_python_enum(be, "app/models/a.py", "Delta", [("D1", "d1"), ("D2", "d2")])
        _write_dart_enum(mo, "lib/e.dart", "Delta", json_values=["d1"])

        _write_python_enum(be, "app/models/a.py", "RunLike", [("R1", "r1")])
        _write_dart_enum(mo, "lib/run_like.dart", "RunLike", plain=["r1"])  # 单源族的违例镜像

        # Ghost：backend 类不存在，映射完整性 FAIL；同时挂一份（无效的）豁免验证豁免不覆盖 EP004
        expired_allow["Ghost"] = expired_allow["Alpha"]

        all_findings = run_checks(be, mo, families, expired_allow, today=today)

        def sev_of(findings: list[Finding], family: str, code: str) -> tuple[str, str | None]:
            for f in findings:
                if f.family == family and f.code == code:
                    return f.severity, f.exempt
            return "<absent>", None

        checks: list[tuple[str, bool]] = []

        checks.append(("case1 对齐族 PASS", sev_of(all_findings, "Aligned", "OK")[0] == "PASS"))

        s, ex = sev_of(all_findings, "Alpha", "EP001")
        checks.append(("case2 缺值无哨兵 FAIL", s == "FAIL"))
        checks.append(("case2 未豁免", ex is None))

        s, ex = sev_of(all_findings, "Beta", "EP001T")
        checks.append(("case3 哨兵兜底 WARN 不 FAIL", s == "WARN"))
        checks.append(("case3 Beta 无 FAIL", all(f.severity != "FAIL" for f in all_findings if f.family == "Beta")))

        s, _ = sev_of(all_findings, "Gamma", "EP002")
        checks.append(("case4 mobile 多余值 WARN", s == "WARN"))

        s, ex = sev_of(all_findings, "Delta", "EP001")
        checks.append(("case5a 豁免过期仍 FAIL", s == "FAIL"))
        checks.append(("case5a 过期豁免不标 exempt", ex is None))
        checks.append(
            (
                "case5a 报文带过期提示",
                "豁免已过期" in next(f.message for f in all_findings if f.family == "Alpha" and f.code == "EP001"),
            )
        )

        s, _ = sev_of(all_findings, "RunLike", "EP003")
        checks.append(("case6 passthrough 镜像 FAIL", s == "FAIL"))

        s, ex = sev_of(all_findings, "Ghost", "EP004")
        checks.append(("case7 映射完整性 FAIL", s == "FAIL"))
        checks.append(("case7 EP004 不受豁免", ex is None))

        # 用例 8：在期豁免 → FAIL 带 exempt 标注，exit 语义由调用方按 exempt 过滤
        live_allow = {
            "Delta": {
                "fix": "V3-FIX-YYY",
                "owner": "test",
                "expiry": _dt.date(2027, 1, 1),
                "note": "live",
            },
        }
        live_findings = run_checks(be, mo, families, live_allow, today=today)
        d = next(f for f in live_findings if f.family == "Delta" and f.code == "EP001")
        checks.append(("case5b 在期豁免标注 exempt", d.severity == "FAIL" and d.exempt is not None))

        # 用例 9：哨兵声明但缺失 → FAIL EP005
        _write_dart_enum(mo, "lib/c.dart", "Beta", json_values=["beta", "y1", "y2"])
        no_sent_findings = run_checks(be, mo, families, {}, today=today)
        s, _ = sev_of(no_sent_findings, "Beta", "EP005")
        checks.append(("case9 声明哨兵缺失 FAIL EP005", s == "FAIL"))
        # 同一对齐后 Beta 应无其他 FAIL（y2 已补）
        checks.append(
            ("case9 补值后 Beta 无 EP001", all(f.code != "EP001" for f in no_sent_findings if f.family == "Beta"))
        )

        # 用例 10：passthrough 无镜像 → PASS
        mo_no_mirror = Path(td) / "mobile_clean"
        mo_no_mirror.mkdir()
        clean_findings = run_checks(be, mo_no_mirror, {"RunLike": families["RunLike"]}, {}, today=today)
        checks.append(
            ("case10 passthrough 无镜像 PASS", any(f.code == "OK" and f.severity == "PASS" for f in clean_findings))
        )

        # 解析器回归：真实仓样本形态（enhanced enum 构造器 + JsonValue + parse-case）
        _write_dart_enum(
            mo,
            "lib/real.dart",
            "Real",
            json_values=["a_b"],
            ctor=[("cD", "C_D")],
            sentinel="unknown",
            parse_cases=["e_f"],
        )
        real = extract_dart_enum(mo, "lib/real.dart", "Real")
        checks.append(
            (
                "case11 Dart 解析器三形态",
                real is not None and real.wire_values == {"a_b", "C_D", "e_f"} and "unknown" in real.identifiers,
            )
        )
        py_real = extract_python_str_enum(
            be,
            "app/models/a.py",
            "Aligned",
        )
        checks.append(("case12 Python 解析器", py_real == {"RED": "red", "GREEN": "green"}))

        # 用例 13：inventory 盘点 + BACKEND_ONLY 分流（backend-only 判定的输出契约）
        _write_python_enum(be, "app/models/a.py", "InteractionType", [("I1", "i1")])
        inv = inventory_unmapped_backend_enums(be)
        inv_names = {name for name, _ in inv}
        checks.append(
            ("case13 盘点含未映射 fixture 族", {"Aligned", "RunLike", "InteractionType"} <= inv_names)
        )
        judged = [x for x in inv if x[0] in BACKEND_ONLY]
        checks.append(("case13 BACKEND_ONLY 分流命中", ("InteractionType", "app/models/a.py") in judged))
        undecided = [name for name, _ in inv if name not in BACKEND_ONLY]
        checks.append(
            ("case13 未判定候选不含已判定族", "InteractionType" not in undecided and "Aligned" in undecided)
        )

        print("[Rule ENUM-PARITY] SELF-TEST 实录：")
        for label, ok in checks:
            mark = "PASS" if ok else "FAIL"
            print(f"  [{mark}] {label}")
        bad = [label for label, ok in checks if not ok]
        if bad:
            print(f"[Rule ENUM-PARITY] SELF-TEST FAIL ({len(bad)} 项): {bad}")
            return 1
        print(f"[Rule ENUM-PARITY] SELF-TEST PASS ({len(checks)} 项断言全绿)")
        return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true", help="临时双面样本红绿自证后退出")
    parser.add_argument(
        "--family",
        action="append",
        default=[],
        help="只对账指定家族（可多次）；默认全表",
    )
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    families = FAMILIES
    if args.family:
        unknown = [f for f in args.family if f not in FAMILIES]
        if unknown:
            print(f"[Rule ENUM-PARITY] FAIL - 未知家族: {unknown}（可用: {sorted(FAMILIES)}）")
            return 1
        families = {f: FAMILIES[f] for f in args.family}

    findings = run_checks(BACKEND_ROOT, MOBILE_ROOT, families, KNOWN_DRIFT, TODAY)

    fail = 0
    warn = 0
    exempt = 0
    for f in findings:
        if f.exempt:
            exempt += 1
            print(f"[Rule ENUM-PARITY] KNOWN-DRIFT {f.family}: {f.message}  [豁免: {f.exempt}]")
        elif f.code == "OK":
            print(f"[Rule ENUM-PARITY] {f.message}")
        else:
            print(f"[Rule ENUM-PARITY] {f.severity} {f.code} {f.family}: {f.message}")
        if f.severity == "FAIL" and not f.exempt:
            fail += 1
        elif f.severity == "WARN":
            warn += 1

    unmapped = inventory_unmapped_backend_enums(BACKEND_ROOT)
    if unmapped and not args.family:
        judged = [x for x in unmapped if x[0] in BACKEND_ONLY]
        undecided = [f"{name} ({rel})" for name, rel in unmapped if name not in BACKEND_ONLY]
        if judged:
            print(
                f"[Rule ENUM-PARITY] INFO 已判定 backend-only（无 wire 下发面，不进映射表"
                f"——判定证据见脚本 BACKEND_ONLY 清单）: {len(judged)} 族 "
                f"{[name for name, _ in judged]}"
            )
        if undecided:
            print(
                f"[Rule ENUM-PARITY] INFO 未进映射表的 backend StrEnum（不判失败，扩表候选"
                f"——需逐族判定 dual/passthrough/backend-only）: {undecided}"
            )

    total = len(findings)
    if fail:
        print(f"[Rule ENUM-PARITY] FAIL - {total} 条结果：FAIL={fail} WARN={warn} 豁免={exempt}")
        return 1
    print(
        f"[Rule ENUM-PARITY] PASS - {total} 条结果：FAIL=0 WARN={warn} 豁免={exempt}"
        f"（豁免命中已显式列出，修复落地后删除 KNOWN_DRIFT 条目）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
