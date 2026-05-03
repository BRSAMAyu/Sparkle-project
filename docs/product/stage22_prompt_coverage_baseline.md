# Stage 22 Prompt Coverage Baseline

- audited_at: 1777776712.2806776
- audited_fields: 13
- covered_fields: 12
- coverage_ratio: 0.923
- baseline_interpretation: PASS

## Covered

- ✅ `error_summary` — 近期痛点中的错题摘要 (rendered)
- ✅ `recent_errors` — 近期痛点中的错题样本 (rendered)
- ✅ `recent_mastery_changes` — 近期进展中的掌握度变化 (rendered)
- ✅ `active_tasks` — 待办任务 / next_actions (rendered)
- ✅ `active_goals` — 当前目标 (rendered)
- ✅ `episodic_memories` — 近期相关记忆 (rendered)
- ✅ `preferences` — 学习偏好 (rendered)
- ✅ `social_context` — 社交上下文渲染器 (rendered)
- ✅ `profile_context` — 通过知识/画像快照间接可见 (rendered)
- 🔄 `community_context` — 仅在社区摘要链路命中时可见 (conditional)
- ✅ `knowledge_summary` — 知识薄弱点 / 画像摘要 (rendered)
- ✅ `focus_stats` — 专注统计 (rendered)

## Gaps

- ❌ `engagement_metrics` — 行为分析摘要
