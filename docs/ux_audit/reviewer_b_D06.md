# Reviewer B — D06: 长期用户（30天+）体验——记忆/归档/推送是否退化
Timestamp: 2026-04-26T01:30:00+08:00
Chain Index: 19 (Round 3 — D-chain audit)

## Chain Flow Summary
用户使用 30+ 天后涉及 4 条退化链路：(1) EpisodicMemory 表持续增长，`list_recent_episodic` 默认只返回 10 条（`memory_service.py:631`）；(2) 学习档案归档在 `ExamSprintReviewService` 中通过 `MAX_ARCHIVE_ENTRIES = 10` 截断（line 1043-1044）；(3) 周报叙事由 `_compose_weekly_narrative_sentences` 生成，句式固定（"最大的进步："/"下周目标："），不参考历史叙事；（4）推送通知中间隔重复提醒标题固定为"Aurora 复习提醒"，内容模板仅替换变量名。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`backend/app/services/exam_sprint_review_service.py:61,1043-1044`**: `MAX_ARCHIVE_ENTRIES = 10` 硬截断归档，旧冲刺数据永久丢失。`entries = entries[-self.MAX_ARCHIVE_ENTRIES:]` 保留最近 10 条，超出部分直接丢弃。Expected: 用户能查看所有历史冲刺记录，或至少有分页/展开机制。Actual: 使用 7 天冲刺的用户约 70 天后（10 个冲刺），最早的冲刺数据从档案中消失。用户无法回顾早期学习历程。无导出机制、无警告提示。Evidence: line 61 `MAX_ARCHIVE_ENTRIES = 10`，line 1044 `entries = entries[-self.MAX_ARCHIVE_ENTRIES:]`。

**`backend/app/services/progress_narrative_service.py:916-936`**: `_compose_weekly_narrative_sentences` 使用固定句式模板，不参考之前周的叙事内容。`highlights` 是当周实时数据但框架句式（"最大的进步："/"下周目标："）每周相同。Expected: 连续使用多周后叙事风格有变化，不重复上周的表达。Actual: 第 4 周和第 12 周的叙事结构完全一致——"最大的进步：X 的掌握度从 Y% 提升到了 Z%。下周目标：..."。No deduplication logic against previous narratives（grep 确认零匹配）。

## Minor Issues 🟢
**`backend/app/services/memory_service.py:610-633`**: `list_recent_episodic` 默认返回最近 10 条，DB 中 EpisodicMemory 无上限无驱逐。注释 `# TRACKED(TD-008)` 提到 per-session rate limits 但未实现。30+ 天后 DB 中可能有数百条记录，API 只返回最近 10 条不影响功能但增加存储负担。

**`backend/app/services/notification_center_service.py:80-85`**: 间隔重复提醒标题固定 "Aurora 复习提醒"，内容模板仅替换 `display_name`、`interval_days`、`mastery`、`estimated_minutes` 四个变量。框架句式不变。但每日冲刺提醒（`celery_tasks.py:1372-1376`）含完成率和任务名，个性化程度更高。对频繁收到复习提醒的用户（如 10+ 个 Galaxy 节点），消息结构高度重复。

## Working Well ✅
- **`backend/app/core/celery_tasks.py:1372-1376`**: 每日冲刺提醒使用动态数据（subject、days_left、completion_percent、primary_task_title），个性化较好。
- **`celery_tasks.py:1348-1365`**: 重复提醒抑制逻辑（`duplicate_recent` check），防止同一天多次推送。
- **`notification_center_service.py:130-154`**: `has_recent_spaced_repetition_reminder` 按节点去重，`SPACED_REPETITION_MIN_COOLDOWN_DAYS` 控制冷却期，不会对同一节点频繁推送。
- **`progress_narrative_service.py:304-328`**: 空数据和无学习活动场景有专门的占位文案，不会返回空白叙事。
- **`memory_service.py:618-623`**: 正确过滤 deleted/archived/retracted/revoked 状态的记忆，不会返回无效数据。

## Files Examined
- `backend/app/services/memory_service.py` (lines 608-684)
- `backend/app/services/exam_sprint_review_service.py` (lines 55-70, 1035-1060)
- `backend/app/services/progress_narrative_service.py` (lines 295-328, 910-948)
- `backend/app/services/notification_center_service.py` (lines 70-128, 130-155)
- `backend/app/core/celery_tasks.py` (lines 1289-1397)

## Confidence: High — 所有 4 条退化链路已通过代码行号确认。
