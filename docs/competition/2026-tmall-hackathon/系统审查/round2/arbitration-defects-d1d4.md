# 数据飞轮专项（三）：仲裁缺陷 D1-D4 修复记录

- 基线：f39fb64b（wt5 worktree，2026-09-19）
- 性质：缺陷修复 + 红绿回归，上游输入为 [data-flywheel-arbitration-audit.md](data-flywheel-arbitration-audit.md)（D1-D4 定位）
- 变更快照：同目录 `arbitration-defects-d1d4.patch`（未 commit，仅 worktree 产出）
- 主仓进程/DB 只读；全部验证在 wt5 worktree 内完成

---

## 0. 一句话结论

D1 死门（topic 对 sha1 十六进制做子串匹配，数学上永不命中）与 D2 兜底过宽（未知 lane 判最高优先级）按审计定位修复；D3 做**最小止血**——profile 域不再静默遮蔽 memory_preferences，双源并存进 pack 由 rank/预算竞争，双源键显式登记进 metadata 供审计；D4 经代码复核**修正审计结论**（消费者其实存在且已排程，真实缺口是 `7d` 策略未登记 + `due_at+7d` 无消费者），补齐前者、后者标注 V3 待办。全部修复先红后绿；邻域回归 1173 passed，另 6 个失败经基线比对确认为本 worktree 预先存在的环境性红（与本专项无关）。

---

## 1. D1（死门）：has_unresolved_conflict 永不命中

### 根因

`ConflictResolverService.has_unresolved_conflict`（conflict_resolver_service.py 原 :85-102）把技能激活条件产出的人类可读 `topic_keys`（如「早睡」「复习」）与 `UnresolvedConflict.conflict_key` 做双向子串匹配。而 `conflict_key = semantic_key = sha1(规范化句子).hexdigest()`（memory_inferred_write_lane.py:337，40 位十六进制）——子串匹配在数学上不可能命中，`skill_selection_service.py:53` 的「未决分歧屏蔽技能激活」恒为 False。既有单测 `test_skill_selection_blocks_on_unresolved_conflict` 之所以一直绿，是因为它直接把 `conflict_key` 播种成人类可读的 `"exam-plan"`——恰好绕开了生产形态，掩盖了死门。

### 修复（对齐比较语义）

`app/services/conflict_resolver_service.py`：

1. `topic_keys`（人类可读）：与行内**可读范围**做归一化双向包含比对——`left_summary` / `right_summary`，以及 `left_payload` / `right_payload` 内的 `semantic_key` 字段（payload 中的 semantic_key 参与精确语义比对与 topic 比对均可作为 haystack）。冲突行的摘要本身就是人类可读文本，topic 对齐摘要即「topic 解码」。
2. 新增可选参数 `semantic_keys`：与 `conflict_key`（=semantic_key）及 payload 内 semantic_key **精确比对**，供未来调用方能直接给语义键时走「semantic_key 对 semantic_key」。
3. 接口向后兼容：`skill_selection_service` 调用点无需改动。

### 红绿证据

- 红（修复前）：`test_has_unresolved_conflict_matches_topics_against_readable_scope` 断言 `topic_keys=("早睡",)` 命中 sha1 形态冲突行 → `assert False is True`；`test_skill_selection_blocks_on_unresolved_conflict_with_production_hash_key` 断言技能被拦 → 实际技能照常激活（score=1.0）。
- 绿（修复后）：上述测试 + `test_has_unresolved_conflict_matches_semantic_keys_exactly`（语义键精确命中/未命中）+ `test_same_key_tie_candidates_surface_to_unresolved_conflicts_and_block_topic`（同 key 平级候选 → 落 `unresolved_conflicts` 表 pending_user → topic 门命中拦截；不相关 topic 不误拦）全部通过。

### 任务书要求的「两条同 key 不同置信候选」专项用例

`test_same_key_candidates_with_different_confidence_arbitrate_and_audit`：同 semantic_key、同 lane、置信 0.55 vs 0.92 的两条候选——按 Stage20 既有语义，不同置信走**确定性裁决**（accept-with-override：胜者落库、输者 `retracted_at` 撤回、`ConflictResolutionRecord` 审计行落库、`conflict_key` 全程可追溯），不进 pending_user 队列（该断言显式写入测试，固化语义）；「落 unresolved_conflicts 表」的是同 key **平级平信**的 tie 路径（见上）。两条路径合起来覆盖任务书要求的「检出冲突并落表」全链。

---

## 2. D2（兜底过宽）：未知 source_lane 判最高优先级

### 根因

`_priority` 的 fallback 分支把一切未登记 lane 返回 `explicit(4)`（最高档）。代码库中真实存在的 `aurora_calibration_receipt` lane（aurora/runtime_v1/correction_feedback.py:427）因此能压过 `direct_capture` 的用户直接声明；任何未来新 lane 同理。注意旧实现里 `direct_capture` 本身也未显式登记——它「碰巧」靠同一个 fallback 落在 4 档，修复时必须显式登记以免误降级。

### 修复

- `KNOWN_SOURCE_LANES` 显式登记表：`direct_capture`/`user_confirmed`→explicit(4)，`llm_extractor`/`llm_extraction`→llm(2)，`inferred_extraction`→rule(3)，`working_memory`→working_memory(1)。
- 未登记 lane 一律落新增最低档 `unknown(0)`，并打 `logger.warning`（每 lane 每进程一次），提示在登记表补注册。
- 新增约定：新增 lane 必须同步登记 `KNOWN_SOURCE_LANES`。

### 红绿证据

- 红：`test_unknown_lane_falls_to_lowest_priority_and_loses_to_direct_capture` 断言 `_priority("aurora_calibration_receipt") == 0` → 实际 `4 == 0` 失败；同测试中「未知 lane 候选 vs direct_capture 在场记录」断言 `reject` → 实际 tie。
- 绿：该测试 + `test_known_lanes_keep_registered_priorities`（六个已知 lane 档位回归护栏）通过；Stage20 既有 accept/reject/surface 全链测试无回归。

---

## 3. D3（双语义打架）：最小止血——profile 域静默遮蔽改双源并存

### 范围说明

审计 D3 指出「写侧 latest-wins vs 读侧 evidence-wins」两套语义并存；其中**每天实际产生用户可见伤害**的是 context_pack.py :1368-1378：只要 `user_preferences_center`（explicit 非默认或 inferred）含某 key，`memory_preferences` 的证据化记录就被从 `ranked_preferences`/`preferences`/`pref_scores` 三处静默剔除——center 无条件赢、inferred 也赢、无冲突记录、用户无感知（审计案例 A，DB 实证 7 个用户命中）。本次按任务书只做该处止血；版本链写/读语义统一属 V3（见审计 §6.2 步骤 4）。

### 修复

`app/core/context_pack.py`：删除三处剔除，改为：

- memory_preferences 记录**保留**在 ranked 流中，与 profile 域并存进 pack，由既有 rank 加权 + token 预算竞争裁决（center 域数值本身仍经其自有链路注入 prompt，两条来源同时可见，不再先验吃掉一方）；
- 与 center 域同 key 的记忆偏好键排序后写入 `metadata["preference_dual_source_keys"]`，双源并存显式可审计——不为冲突做静默裁决，也不添噪声（无重叠时不写该键）；
- 显式默认值仍不算 profile 域占有（原 explicit 非默认判定逻辑保留）。

### 红绿证据

- 红：`test_context_pack_keeps_memory_preferences_alongside_profile_domain`（memory 侧 `error_correction_rate` + center.inferred 同 key）→ 修复前 `pack.preferences == {}`（证据化记录被整体吃掉，复现审计案例 A）。
- 绿：修复后该键以 memory 侧证据化值进 pack、`preference_dual_source_keys == ["error_correction_rate"]`、`token_usage <= budgets`；`test_context_pack_no_dual_source_note_without_overlap` 保证默认 explicit 值/无重叠时不产生标注。context_pack 预算行为回归：`test_context_pack_budget_trimming` / `test_context_budget_manager` / `test_context_budget_scheduler` 全部通过。

---

## 4. D4（decay_policy 摆设）：审计结论修正 + 最小补齐

### 审计修正（重要）

审计称「episodic decay_policy 标签无任何消费者执行」。经代码复核（基线 f39fb64b），该结论**不完全成立**：

- `apply_memory_decay`（celery_tasks.py，自初始提交 1722e6dc 即存在）**就是** decay_policy 的消费者：按策略半衰期衰减 `importance_score`、低于阈值归档，且已注册 beat 排程（celery_app.py `memory-decay`，每日 03:30，batch 200）。
- 真实缺口收窄为两条：① 策略表只含 `30d/60d/90d`，`MemoryInferredWriteLaneService` 写入的 **`7d`（时敏记忆）不在表内**，从未被衰减（memory_inferred_write_lane.py:323）；② **`due_at+7d`（承诺类）**无消费者（llm_extractor_service.py:158-159 只把自己的 due_at+7d 归一成 30d，lane 直写的不归一）。

### 处理（最小代价）

- 衰减核心从 celery 任务体提取为 `app/services/memory_jobs.apply_episodic_decay_policies(db, *, now, batch_size)`（策略表 `EPISODIC_DECAY_POLICIES` 同址可查），celery 任务委托之——使其可单测、可复用（审计 §5 建议的「复用 memory_jobs 调度骨架」落点）。
- 补齐 `7d` 策略（half-life 7d，archive 阈值 0.15）——一行策略项，复用既有半衰期机制，关掉时敏记忆永不衰减的缺口。
- `due_at+7d` 需按 due_at 触发的调度语义，属真执行器工程——在策略表注释与 celery docstring 双处标注 **V3 数据飞轮待办**，本期不动。

### 红绿证据

- 红：`test_episodic_decay_policies_consume_7d_policy` 引入前 `ImportError`（函数不存在）。
- 绿：7d/60 天 0.8 分记录 → 衰减至 0.8×0.5^(60/7)≈0.002 且归档；7d/2 天 → 仅衰减；30d/10 天 → 仅衰减（既有 30d 行为不回归）；`due_at+7d` → 原样（待办固化）。

---

## 5. 回归与验证

| 套件 | 结果 |
|---|---|
| 核心邻域（conflict_resolver / memory_conflict_resolver / layer_conflict_resolver / context_ranker / inferred_write_lane_queue / context_pack×3 / skill_selection / memory_jobs） | 34 passed |
| memory 服务族（memory_service×4 / unresolved_conflicts_api / memory_api / past_session_ranking） | 18 passed |
| 扩展批一（context_budget×2 / context_focusing / rank_policy / preference_consumption / profile_write / inferred_chinese_commitment / naive_utc_write / memory_evolution / behavior_decay / inferred_preference_decay / conversation_memory_prompt） | 65 passed |
| 扩展批二（memory_revival×2 / daily_summary / eval / export / settings / working_memory_api / focus_memory / skill_store / skill_schema / skills_api） | 31 passed |
| 定向批三（signal_spine / aurora_write_pipeline / orchestrator_stream_queue / sprint_pack_loader / session_feedback / prompt_preference_scalar_render / tool_preference_router / predictive_productization） | 1043 passed |
| **新增本专项测试** | **10 个（先红后绿）** |

**worktree 预先存在的环境性红（与本专项无关，基线 stash 比对一致）**：

- `test_working_memory_consolidation.py` 3 个：kill switch 在本环境连不上 Redis（NOAUTH）fail-closed，`consolidation_enabled` 不 live → consolidated 恒空。主仓容器 Redis 带认证，单测进程无凭证。
- `test_memory_working_memory_api.py::test_working_memory_session_api_round_trip`、`test_skills_api.py::test_skills_api_crud_extract_and_share_flow`：同上，kill switch/Redis 认证依赖。
- `test_memory_settings_api.py::test_push_settings_get_and_update`：worktree .env 副本的推送默认值与用例期望不符（env 差异）。

**治理守卫**：`run_all_rule_guards.sh` 仅 K/Z/BG 三项失败，均为 worktree 产物（复制的 `app/gen/` 内 pb2 序列化了主仓绝对路径触发 `relative_to` 越界；Dart/Go 侧生成物未随 worktree 复制），与本次变更无关；与冲突审计直接相关的 **AE（conflict override 审计强制）PASS**，数据最小化覆盖 PASS，alembic 单头 PASS。主仓验证不受影响。

## 6. 变更清单

| 文件 | 变更 |
|---|---|
| `backend/app/services/conflict_resolver_service.py` | D1：has_unresolved_conflict 按 readable-scope/semantic-key 双语义对齐；D2：KNOWN_SOURCE_LANES 登记表 + unknown 最低档 + 一次性告警 |
| `backend/app/core/context_pack.py` | D3：profile 域遮蔽改双源并存 + `preference_dual_source_keys` 审计元数据 |
| `backend/app/services/memory_jobs.py` | D4：EPISODIC_DECAY_POLICIES + apply_episodic_decay_policies（含 7d；due_at+7d 标注 V3 待办） |
| `backend/app/core/celery_tasks.py` | D4：apply_memory_decay 委托提取后的核心函数，docstring 同步修正 |
| `backend/tests/unit/test_conflict_resolver_service.py` | +6 测试（D1×4 含不同置信/平级 tie 全链，D2×2） |
| `backend/tests/unit/test_skill_selection_service.py` | +1 生产形态 sha1 conflict_key 端到端死门回归 |
| `backend/tests/unit/test_context_pack.py` | +2 测试（双源并存/预算不破、无重叠无标注） |
| `backend/tests/unit/test_memory_jobs.py` | +1 测试（7d 衰减+归档、30d 不回归、due_at+7d 原样） |
| `docs/.../系统审查/README.md` | 本专项登记 |

## 7. 移交 V3 的后续（本专项不做）

1. 版本链「写 latest-wins vs 读 evidence-wins」二选一定规范（审计 D3 剩余半边，§6.2 步骤 4 的显式规则表 + 冲突登记）。
2. `due_at+7d` 承诺类衰减执行器（需 due_at 感知调度）。
3. 裁决维度注册表（semantic_key 升级「维度键 + 内容键」双键）、Stage20 接入 direct_capture 与 center 写路径、UnresolvedConflict 结构化 topic 列（Alembic 迁移，本期为零迁移止血）。
4. 冲突行 topic 匹配目前依赖摘要文本——摘要为空/纯符号的行匹配能力弱于结构化 topic 列方案，V3 迁移后可替换。
