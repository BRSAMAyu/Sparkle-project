# 数据飞轮专项：全仓冲突仲裁机制现状盘点（V3 规划输入）

- 基线：d4338948（wt5 worktree，2026-09-19）
- 性质：审计 + 方案，**不含代码变更**
- 核心命题（项目方原话）：生产环境用户数据复杂且矛盾（今天说要早睡明天熬夜求助；上周喜欢 A 这周喜欢 B），**不同模块对同一用户给出矛盾结论时最终以哪个为准、如何仲裁**。
- 主仓 DB 只读查证时间：2026-09-19（sparkle_db 容器，psql 只读 SELECT）

---

## 0. 一句话结论

系统中存在 **8 套互不连通的"准仲裁"机制**（Stage20 确定性裁决器、读时软仲裁器、五层跨层裁决器、画像真相编译器、洞察矛盾探测器、纠错降权链、rank_items 加权排序、prompt 文本规则），但：① 唯一的**写侧硬仲裁器**（Stage20）从未在实战中产生过一条记录（DB 中 conflict_resolution_records = 0）；② 真正每天在生效的仲裁是 **rank_items 排序 + profile 域静默遮蔽 + 预算截断 + 三处口径不一的 prompt 文本规则**——全部是"影响注入顺序/可见性"的隐式仲裁，**没有任何一处对矛盾结论做显式裁决并向用户求证**。V3 需要的不是再造一个裁决器，而是把已有 8 套机制收敛到一个统一裁决点。

---

## 1. 写入侧盘点：谁在产生"用户结论"

### 1.1 全模块矩阵

| # | 模块 | 存储 | 写入方（真实调用链） | 置信度语义 | 时间衰减 | 冲突防御 |
|---|------|------|----------------------|-----------|---------|---------|
| 1 | 情景记忆 L1 `episodic_memories` | `EpisodicMemory`（models/memory.py:77） | ① direct_capture：`MemoryService.create_episodic_memory`（memory_service.py:724，默认 lane）② inferred_extraction：`MemoryInferredWriteLaneService`（规则启发式，memory_inferred_write_lane.py:302-322）③ llm_extractor：`LlmExtractorService`（llm_extractor_service.py:167）④ working memory 固化：`WorkingMemoryConsolidationService`（:159）⑤ 任务反思：task_reflection_service.py:770/1024 | `confidence`（0-1；规则 lane 加性启发式 0.72 起步封顶 0.95；入库门槛 `MEMORY_INFERRED_MIN_CONFIDENCE=0.9`）+ `evidence_score`（evidence_scoring.compute_score，由 evidence_refs 计算）+ `importance_score`（写入时=confidence）+ `correction_count` | `decay_policy` 标签（7d/30d/due_at+7d）挂在 tags，**无消费者按期执行物理衰减**（decay_service.py 只衰减知识掌握度，不衰减记忆） | semantic_key 去重（`_is_duplicate`）+ Stage20 仲裁（仅 inferred lane 接入） |
| 2 | 偏好 `memory_preferences` | `MemoryPreference`（版本链 version + replaced_by_id，models/memory.py:15） | `MemoryService.upsert_preference`（:90，PREFERENCE_KEYS 白名单）；`ProfileWriteService.update_inferred_preference` 镜像写历史（profile_write_service.py:206-217） | `evidence_score` + `confidence` + `correction_count`；版本链 write 语义 = **最新版本无条件胜出**（upsert 直接建新版本） | 无显式衰减；读侧 `PREFERENCE_STALE_DAYS=180` 仅把 freshness 打 5 折（context_ranker.py:28,48-53） | 版本链去重；retracted_at 过滤 |
| 3 | 目标 `memory_goals` | `MemoryGoal`（models/memory.py:44） | `MemoryService.create_goal/update_goal` | `evidence_score` + `correction_count` + `expires_at` | expires_at 过期读侧降 freshness 0.5 | 无 semantic key；靠标题文本对比 |
| 4 | 画像偏好域 `user_preferences_center` | `UserPreferencesCenter`（explicit/inferred 两个 JSONB + version OCC；单行/用户） | 显式：`ProfileWriteService.set_explicit_preference`；推断：`update_inferred_preference`（:159）——**explicit 非默认值时推断写被丢弃**（:183-188，write 侧显式>推断守卫）；用户纠正 lane：`ProfileInsightControlService.apply_control`（profile_insight_control_service.py:69，wrong/used_to_be_true/exam_mode_only/reset_override 四动作） | **无置信度列**；inferred 的置信度塞在 dict 内键（如 `error_correction_rate_confidence`）；`INFERRED_META` 注册可调键 | `inferred_preference_decay_service.py` 存在但为独立路径；center 内 inferred 无自动衰减 | write 侧 explicit 守卫（仅本域内）；与 #2 之间**无写侧协调** |
| 5 | 五层用户模型 | `LayeredLearningContract`（five_layer_learning_contract.py:103）+ 各层 governance state | `OutcomePromotionGovernor` / `UserStrategyStateService` / `CompanionStateService`（layer_conflict_resolver.py 被三者引用） | `PromotionThreshold`：min_confidence、min_matching_revisions、min_distinct_sessions、requires_measurable_effect、**block_on_conflict**、review_window_days、expiry_days | review/expiry → `stale`/`review_due`（LayerConflictResolver.stale_items_from_governance） | `LayerConflictReport` + 状态机（active/blocked/demoted/stale） |
| 6 | Spine 模型 claims | StateRegister（Redis，aurora_state_snapshots 快照）+ `insight_claims` 表（**空表，0 行**） | `SpineOrchestrator.on_*` 事件族（spine_orchestrator.py）：quiz 0.4-0.85、文件 0.75/0.45、聊天信号 0.7-0.82、伙伴观察 0.75；`add_counter_evidence`（:2408） | 每 entry 带 confidence + counter_evidence 列表；6-state band 分档（conf≥0.6 高置信 / ≥0.4 中 / 其余低，:471-472）；`stale_state` 守卫 | band 有 cooling_down；`stale_state` 状态键 | 同 state_key 反证降信；**同 key 异 value 并存时无裁决，全部并列进 active_claims** |
| 7 | Aurora 写管道 claims | Redis claims（TTL 24h）+ temporary state（TTL 24h，write_pipeline.py:33-37） | `AuroraWritePipeline`（aurora/runtime_v1/write_pipeline.py）：observed→candidate(≥0.7)→trial(7d)→confirmed / revoked | `CANDIDATE_CONFIDENCE_THRESHOLD=0.7`、`MIN_EXAM_SPRINT_EVIDENCE=2` | `TRIAL_WINDOW_DAYS=7`、claim TTL 24h | 状态门 + TTL 天然过期 |
| 8 | 认知洞察 `cognitive_insights` 路径 | `UserInsightState`（投影态，不独立落库）+ `insight_claims`/`probe_outcomes`（**均 0 行**） | `UserInsightAnalysisService.analyze`（user_insight_analysis_service.py:59）规则生成；`ProfileTruthCompiler`（profile_truth_compiler.py:15）把 canonical 画像编译为洞察 | `signal_evidence[].confidence` + freshness 三档（<0.55 或 freshness=low → stale，:262-286）；hypothesis 分 promoted/provisional/watch（:386-395） | freshness 分档 + confidence_decay posture | **只探测不裁决**：`_build_contradictions`（:294-367）产出 3 类矛盾 → `active_contradictions` → contradiction_map |
| 9 | 贝叶斯信念态（数据飞轮底座） | `BeliefState`（内存/快照，services/evidence/belief_state.py:149） | `FusionEngine` ← UnifiedEvidence（任务结果/对话抽取，outcome_evidence_adapter / conversational_extractor） | 1D Kalman：confidence→观测方差 (1-c)²，按精度加权融合（:101-146）；`belief_confidence = 1 - variance/0.25` | uncertainty 半衰期 12h，mean 向中性 0.5 回归强度 0.35（:71-98）——**全仓唯一的数学化矛盾融合**，但服务于 routing bandit，不产出面向用户的"结论" |
| 10 | state_aggregator | `UserStateV1` 只读聚合（state_aggregator/service.py:66） | 无写（Stage 18 明确 read-only） | 各字段 TTL 30s~24h（FIELD_TTLS_SECONDS） | TTL 即新鲜度 | 不裁决，透传上游 |

**要点**：置信度语义至少有 6 种不同量纲（0-1 float、evidence_score、版本号、六态带、governance 阈值、Kalman 方差），**没有任何跨模块可比性定义**。时间衰减只在 #9（数学化）和 #5/#7（窗口/过期）真实生效；#1 的 decay_policy 是"贴了标签没人执行"的摆设。

### 1.2 "今天早睡明天熬夜"在这个矩阵里的真实走向

- "我要早睡" → direct_capture/inferred 写入 episodic_memories（confidence≥0.9 才入库，semantic_key=sha1(规范化句子)）。
- 当晚 23:40 求助 → conversational_extractor 抽取证据 → BeliefState 的峰值时段 belief 被 Kalman 更新推向深夜；spine chat 信号可能写入 `peak_focus_hours` 类 state；insight 侧 `peak_focus_hours` 观测集更新。
- **没有任何机制把这两者对撞**：`study_time_preference`（center 域）与 `peak_focus_hours`（观测域）的矛盾只有 `UserInsightAnalysisService._build_contradictions` 的规则 `conflict:time_preference_vs_observed_peak_hours`（:297-321）会探测到——产出一条 contradiction 记录注入 situation_brief 的"洞察冲突"行（situation_brief.py:1306），**然后呢？没有然后**。不回写、不求证、不降权、不阻断。

---

## 2. 冲突处理现状：八套机制的精确能力边界

### 2.1 ConflictResolverService（Stage 20，conflict_resolver_service.py）——唯一的写侧硬仲裁器

- **范围**：仅 `episodic_memories` 同 `semantic_key`（`load_conflicting_records` :68）。preferences/goals/profile/spine/insights 全部不在裁决域内。
- **裁决规则**（`_compare_candidate_to_record` :374）：lane 优先级 `working_memory(1) < llm_extractor(2) < inferred_extraction(3) < explicit(4)`；同级比 confidence → 比 occurred_at；全平 → tie。
- **三种裁决动作**：`accept`（新记录入库 + 输者置 retracted_at）、`reject`（高优先级在场，拒绝写入）、`surface_to_user`（tie → 建 `UnresolvedConflict(status=pending_user)`，由 `/memory/unresolved-conflicts/{id}/arbitrate` API 让用户选 left/right/none；选后输者撤回、胜者落库、全程写 `ConflictResolutionRecord` 审计）。
- **接入点**：唯一接入 `MemoryInferredWriteLaneService.write_candidate_to_l1`（memory_inferred_write_lane.py:521-559）。direct_capture / llm_extractor / working memory 固化**均不经过它**。有 shadow mode（`SPARKLE_CONFLICT_RESOLVER_SHADOW_MODE`，默认 False=live）。
- **下游消费**：`has_unresolved_conflict` 被 skill_selection_service.py:53 消费（存在未决分歧时屏蔽技能激活）；user_strategy_state_service / companion_state_service / outcome_promotion_governor 也引用。
- **实战记录：0**。DB 查证 `conflict_resolution_records = 0`、`unresolved_conflicts = 0`。原因：a) 入库门槛 0.9 已把冲突候选挡在门外；b) semantic_key 是句子规范化后的 sha1，同一事实换个说法就是新 key，撞 key 概率极低；c) 只有 inferred lane 接入。

### 2.2 MemoryConflictResolver（读时软仲裁，memory_conflict_resolver.py）

- `resolve_preferences`：同 key 多版本按 `(evidence_score, updated_at, confidence)` 择 winner，**可以复活被版本链替换的旧版本**（旧版本 evidence_score 更高时）——与 `upsert_preference` 的"最新版本无条件胜出"写语义直接矛盾（两套语义打架，谁赢取决于 feature flag `ENABLE_MEMORY_CONFLICT_RESOLUTION`，默认 True → 读时 evidence 赢，写时 latest 赢）。
- `resolve_goals`：同标题 + target_date 重叠（任一为 None 视为重叠，:54-57）→ dedupe。`_goal_overlap` 的 None=True 规则会把无日期目标一律判为互相重叠。
- `resolve_episodic`：摘要前 40 归一化字符相同或词重叠 ≥0.8 视为重复 → 抑制后到者。
- `resolve_cross_type`：goal 标题出现在 episodic summary 里 → 按 evidence_score 择一（跨类型文本包含判定，误杀率高）。
- **产出物**：全部是 `ConflictNote`（winners/suppressed），进 `pack.metadata["conflicts"]`（context_pack.py:1487-1488）——**纯遥测，不渲染进 prompt，不回写 DB，不通知用户**。

### 2.3 LayerConflictResolver（五层跨层，layer_conflict_resolver.py）

- 跨 session/episode/profile 层同 learning_key 的 direction 冲突：打分 = `repeated_evidence*0.45 + confidence*0.35 + freshness*0.2`，episode 层在上下文中 +0.6，profile 层 +0.05（`_pick_winner` :193-212）；`constitutional_override=True` 直接赢。
- 产出 `LayerConflictReport`（winner + blocked_layers + required_action="demote_or_review"），被 outcome_promotion_governor（晋升闸）、user_strategy_state_service、companion_state_service 消费；`PromotionThreshold.block_on_conflict` 可阻断带冲突结论晋升。**这是五层域内最接近"仲裁"的机制，但只覆盖五层 validated_learnings，不与 #1/#2/#4 的结论互通。**

### 2.4 ProfileTruthCompiler（画像矛盾探测，profile_truth_compiler.py:178-204）

- 4 条规则：难度要求 vs 启动困难、push 诉求 vs recovery 状态、自报掌握度 vs 画像掌握度、极限节奏 vs 可用容量。产出 contradiction（id/severity/evidence），消费于 observability_logger（:330-347）与 validation_engine（:430-449）→ **进决策上下文，不裁决**。

### 2.5 UserInsightAnalysisService（洞察矛盾，user_insight_analysis_service.py:294-367）

- 3 条规则：声明学习时段 vs 观测峰值小时（**就是"早睡 vs 熬夜"场景的探测器**）、declared daily_cap vs 当前 deadline/overload 压力、concise 回复 vs deep 收藏行为。
- 产出 → `state.active_contradictions` → `contradiction_map` → situation_brief 渲染"洞察冲突：…"（:1300-1306）→ **LLM 看得到，系统不处理**。

### 2.6 纠错降权链（correction_count / retracted_at / revoked_at 的完整语义）

| 字段/动作 | 触发者 | 语义 | 代码位置 |
|---|---|---|---|
| `correction_count += 1` | 用户纠错 API `/memory/correct`（reject/lower_confidence）、引用反馈 `/memory/reference-outcome`（corrected/denied） | 用户否认/纠错次数；rank_items 中每 0.1 权重惩罚、封顶 0.5（context_ranker.py:64-67）；claim_status 变 `user_corrected`（context_pack.py:313-327） | memory_service.py:1097 |
| `retracted_at` | 用户 `/memory/retract`、`/memory/correct` reject、Stage20 accept 输者、用户仲裁输者 | 直接捕获类记录的软撤回；读路径全部过滤 | memory_service.py:1231-1257 |
| `revoked_at` | 同上，但 `source_lane == inferred_extraction` 专用；`revoke_inferred_memories`（admin kill switch 批量） | 推断记录的撤销（与直接记录区分审计） | memory_service.py:1242-1244 |
| confidence -0.1 | `lower_confidence` 纠错、reference-outcome corrected/denied | `CONFIDENCE_DECREMENT=0.1`（memory_service.py:48） | memory_service.py:1086-1093 |
| confidence +0.03 / evidence +0.02 | reference-outcome accepted | 引用被用户接受的正反馈 | memory_service.py:1187-1191 |
| StateEntry confidence ± | Aurora correction_feedback：disconfirm -0.15 / confirm +0.05 | spine/aurora 域的用户确认/否认 | aurora/runtime_v1/correction_feedback.py:8-14 |
| 画像纠正 lane | 聊天内工具 `apply_profile_correction`（growth_strategy_tools.py:414）→ `ProfileInsightControlService.apply_control` | wrong（覆盖/删除推断）、used_to_be_true（删除）、exam_mode_only（**范围化限定**）、reset_override；写 explicit 覆盖 + insight_scope_overrides + MemoryCorrection 审计 | profile_insight_control_service.py:69-196 |

**要点**：纠错链是全仓最完整的"用户意志 > 系统推断"通路，且 `exam_mode_only` 已经隐含"结论要带 scope"的正确直觉。但它只覆盖三类 memory 表和 center 域的已注册键，**spine claims、五层 learnings、洞察 hypotheses 不接受用户纠正**（它们有自己的 confirm/deny 芯片，但改的是 confidence 数值，不产生结论级撤销）。

### 2.7 rank_items——每天真正在生效的隐式仲裁器（core/context_ranker.py）

权重（:18-27）：`evidence 0.40 + freshness 0.20 + correction惩罚 0.12 + confidence 0.12 + goal_linkage 0.10 + importance 0.06 + relevance 0.20`。可被 `MemoryRankPolicyService` 按 intent/user 覆写。

- 它**只影响注入顺序和预算裁剪**：分数低的在 token 预算不足时被 `_trim_ranked_list` **静默丢出 prompt**（context_pack.py:185-209）——这是生产环境最高频的"事实仲裁"：预算压力下谁分高谁见 LLM，谁分低谁消失，无审计、无冲突记录。
- 矛盾双方分数接近时**同时入选**，以相邻条目呈现给 LLM（见 §3）。
- semantic gating 再叠加一层：`final = rank*0.6 + cosine*0.4`，阈值过滤 + top_k（context_pack.py:1032-1057）——第二重静默淘汰。

### 2.8 prompt 文本规则（散落的第三类仲裁）

| 位置 | 规则原文 | 仲裁语义 |
|---|---|---|
| prompts.py:483（CORE_PRINCIPLES_SECTION） | "如果用户明确表达与画像不一致的偏好或信息，以当前声明为准；若涉及核心偏好（深度/探索）且历史证据分数≥0.7，则进行一次温和确认" | **当前声明 > 画像；高证据核心偏好 → 求证一次**。全仓唯一的全局文本仲裁规则，但只在 core 聊天 prompt，其他 mode/agent 不一定继承 |
| prompts.py:4009 | 胶囊偏好"当前请求冲突时，以当前请求为准" | 局部域：当前请求 > 收藏信号 |
| prompts.py:372 | "若与更高优先级指令冲突，以更高优先级为准" | 压缩层：指令优先级声明 |
| prompts.py:1038/1047 | "[冲突处理] 若与其他指令冲突，优先执行本节" | 分节声明自保 |
| prompts.py:3836 | "不确定记忆: confidence < 0.70 时用试探语气，并优先轻量确认；用户否认后停止引用该记忆" | 低置信 → 试探 + 轻量确认 |

**口径不统一**：483 行说"核心偏好且证据≥0.7 要确认"，3836 行说"confidence<0.7 要确认"——阈值一样方向相反（一个是对声明求证、一个是对记忆求证），LLM 需要自行脑补优先级。

---

## 3. 读出侧现状：矛盾内容如何呈现（实际案例）

### 3.1 案例 A（DB 实证）：偏好双源并存，profile 域静默获胜

context_pack.py:1368-1378：

```python
profile_prefs = await self.preference_service.get_preferences(user_id)
profile_keys = set((profile_prefs.inferred or {}).keys())
explicit_profile_prefs = dict(profile_prefs.explicit or {})
for key, value in explicit_profile_prefs.items():
    default_value = PreferenceService.DEFAULT_EXPLICIT.get(key, object())
    if key not in PreferenceService.DEFAULT_EXPLICIT or value != default_value:
        profile_keys.add(key)
if profile_keys:
    ranked_preferences = [e for e in ranked_preferences if e.item.pref_key not in profile_keys]
    preferences = {k: v for k, v in preferences.items() if k not in profile_keys}
```

DB 查证（2026-09-19）：**7 个用户**的 `error_correction_rate`、`error_density_score` 同时存在于 `memory_preferences`（带 evidence_score/confidence/版本的完整记录）和 `user_preferences_center.inferred`（无置信度列的分析值）；2 个用户的 `depth_preference` 同 key 存在于 center 的 explicit 和 inferred 两处。运行结果：**只要 center.inferred 有这个键（无论置信度多低、多旧），memory_preferences 的证据化记录直接从 prompt 消失**——profile 无条件赢、inferred 也赢、无冲突记录、用户无感知。这是"两份偏好谁赢"的实锤答案：**center 赢，静默赢**。

### 3.2 案例 B：矛盾记忆原样并列进 prompt

context pack 产出的 episodic_memories（含 source_label"你告诉我的/从对话里推断的/从任务完成情况推断的"、confidence、user_confirmed、correction_actions）经 prompts.py:3780-3948 渲染为 `## 相关记忆` / `## 跨会话记忆` 段：每条 `[时间/主体/来源] 内容 + confidence + user_confirmed`，**逐条并列、不合并、不标注互斥**。若"周一说我决定早睡"与"周四熬夜求助"都入库（semantic_key 不同必然都入库），prompt 里就是两条并列事实，如何调和完全交给 LLM 现场发挥。唯一的辅助是 `<0.70 → confirmation_hint: 需要轻量确认`。

### 3.3 案例 C：矛盾洞察只做提示

`situation_brief.py:1306`：`- 洞察冲突: {contradictions[:2] 拼接}` ——把"声明时段 vs 观测峰值不符"作为一行提示塞进决策上下文。系统层面无后续动作（不阻断、不求证、不落库）。

### 3.4 案例 D：预算截断 = 静默仲裁

`ContextBudgetManager`（context_pack.py:791-943）五源配额（对话 40%/文档 25%/知识 15%/任务错误 10%/认知 10%）；`_trim_ranked_list` 分数最低者先丢。同主题新旧两条矛盾记忆，旧的那条 freshness 低分低，**大概率根本进不了 prompt**——用户视角是"它忘了"，系统视角是"它仲裁了（没记录的那种）"。

---

## 4. 主仓 DB 只读查证（2026-09-19）

| 表 | 数量 | 关键发现 |
|---|---|---|
| episodic_memories | 152 | direct 130 / inferred 22 / llm_extractor 0；semantic_key 143；retracted 0 / revoked 0 / correction_count>0 为 0 |
| memory_preferences | 56 行 / 9 keys | 1 条 retracted、1 条 corrected；同 key 多版本 = 版本链正常 |
| memory_goals | 7 | — |
| **conflict_resolution_records** | **0** | **Stage20 仲裁器从未实战触发** |
| **unresolved_conflicts** | **0**（pending_user 0） | **从没有过一次"向用户求证"事件** |
| memory_corrections | 1 | 纠错链几乎未被使用 |
| **insight_claims / probe_outcomes** | **0 / 0** | 结论-求证闭环的表建好了，链路从未跑通 |
| user_preferences_center | 187 用户 | explicit 全量默认 14 键；inferred：error_correction_rate / error_density_score（7 用户）、depth_preference（2 用户，与 explicit 同 key 并存） |
| 同 semantic_key 多活跃记录 | 0 组 | 写侧去重有效（也说明撞 key 概率低 → Stage20 无米下锅） |

**结论**：仲裁机制的"机器"都在，"里程表"全是 0。当前系统从未向任何用户提出过一次矛盾求证——这正是 V3 命题的现状基线。

---

## 5. 发现的缺陷（语义级，均非 500 类；V3 一并处理）

> 本轮按"审计为主、不顺手改语义"原则未附 patch；请求路径上未发现矛盾数据导致的 500（所有读路径对 retracted/revoked/deleted 均有过滤，payload 解析均有防御）。相关单元测试基线绿：`test_conflict_resolver_service / test_memory_conflict_resolver / test_layer_conflict_resolver / test_context_ranker` 12 passed。

- **D1（死门）**：`ConflictResolverService.has_unresolved_conflict`（conflict_resolver_service.py:85-102）用双向子串匹配 `topic_keys`（技能匹配产出的人类可读主题词）与 `conflict_key`（=semantic_key=sha1 十六进制串）——**数学上永不命中**，skill_selection_service.py:53 的"未决分歧屏蔽技能"逻辑恒为 False。修法方向：UnresolvedConflict 增加结构化 topic 列（hash + 原文 scope），或 conflict_key 双写（hash + topic）。
- **D2（优先级兜底过宽）**：`_priority` 的 fallback 把一切未知 source_lane 判为最高级 explicit(4)（:395-403）。已存在的 `aurora_calibration_receipt` lane（correction_feedback.py:427）或未来任何新 lane 都会压过 direct_capture。修法方向：显式登记已知 lane 表（direct_capture/user_confirmed=4…），未知 lane 落到最低档并告警。
- **D3（双语义打架）**：偏好裁决"写侧 latest-wins"（upsert_preference 版本链）vs"读侧 evidence-wins"（MemoryConflictResolver 可复活旧版本）并存，行为取决于 feature flag 组合。修法方向：二选一定为规范，另一侧降级为参考。
- **D4（decay 摆设）**：episodic `decay_policy` 标签无任何消费者执行衰减；memory 的时间衰减实际只发生在读侧 rank 的 freshness 项。V3 数据飞轮若依赖"遗忘曲线"，需要补一个真正的衰减 job（复用 memory_jobs 调度骨架）。

---

## 6. 方案建议（供 V3 直接采用）

### 6.1 仲裁原则建议（结论优先级草案）

对同一用户、同一**裁决维度**（建议维度 = 规范化主题键：睡眠时段/内容深度/反馈风格/目标…）的多源结论，按以下优先级：

1. **显式口令/直接陈述**（direct_capture + user_confirmed，"帮我记住/我要早睡"）——最高，但**带 scope**：时间性/情境性声明默认限定范围（复用 exam_mode_only 的 insight_scope_overrides 机制），"早睡"不覆盖"考试周熬夜"。
2. **用户纠正通道裁决**（User Correction lane 的 wrong/used_to_be_true + UnresolvedConflict 用户仲裁结果）——用户亲手做的选择是终局，写裁决审计。
3. **最近的强行为证据**（Kalman 高精度观测：小方差 + 新时间戳，如连续 N 天实际活跃时段）——行为不会说谎，但要给"声明型"一个求证窗口而非直接碾压。
4. **高置信历史推断**（confirmed/trial 期的 claims、五层 promoted learnings）。
5. **低置信推断/单次信号**——只允许以 hypothesis 形态存在，**禁止参与行为决策**，只能触发探测。

**兜底原则（V3 核心命题的直接回答）**：当 ≥2 个来源在裁决维度上冲突且最大分差低于阈值时，**不静默择一，向用户求证**——复用 `UnresolvedConflict(pending_user)` + Aurora band 的 `needs_confirm` 状态 + insight_claims/probe_outcomes（表已建、0 行）作为载体。任何静默裁决必须落 `ConflictResolutionRecord` 类审计行。

### 6.2 最小可行实现路径（全部复用现有资产）

| 步骤 | 做什么 | 复用什么 | 工作量级 |
|---|---|---|---|
| 1 | 裁决维度注册表：把 semantic_key 从"整句 sha1"升级为"维度键 + 内容键"双键 | 现有 semantic_key/evidence_token 列（新键写新列即可，不迁移旧数据） | 小 |
| 2 | 修 D1/D2：topic 结构化 + lane 显式登记 | ConflictResolverService 原函数 | 小 |
| 3 | 把 Stage20 裁决器接入 direct_capture 与 center 写路径（显式声明 vs 既有推断的撞点） | ConflictResolverService + ProfileWriteService.update_inferred_preference 的 explicit 守卫处 | 中 |
| 4 | context_pack 遮蔽规则（:1368-1378）改为显式规则表：center.explicit 非默认 > memory_preferences（高 evidence）> center.inferred（低置信时两者并列进 prompt 并打 claim_status 标签），冲突时写 unresolved | ContextPackBuilder + UnresolvedConflict | 中 |
| 5 | 打通 probe 闭环：`conflict:time_preference_vs_observed_peak_hours` 等 3+4 条既有矛盾规则探测到冲突时，写 insight_claims + 生成 probe（求证问题），probe_outcomes 回写后执行 winner 落库/loser 置 retracted | insight_claims/probe_outcomes 表（已建）、UserInsightAnalysisService、correction_feedback 的确认芯片交互模式 | 中 |
| 6 | 统一 prompt 仲裁指令：把 483/3836/4009 三处口径合并为一段"结论来源与冲突处理"标准节，注入所有 mode | CORE_PRINCIPLES_SECTION 编辑 | 小 |
| 7 | 裁决审计面板：conflict_resolution_records + unresolved_conflicts 已有 API（/memory/unresolved-conflicts），补管理端只读视图 | 现有 API | 小 |

### 6.3 需要新增的裁决点清单（按模块）

| 模块 | 现状 | 需要新增的裁决点 |
|---|---|---|
| memory 写 lane（Stage20） | 仅 inferred lane + 整句 sha1 | direct_capture / llm_extractor / 固化链接入；维度键注册表；unknown-lane 兜底降档 |
| memory 读侧（MemoryConflictResolver） | evidence-wins 复活旧版本 | 与版本链语义二选一；ConflictNote 从遥测升级为可回写（用户可见"我们注意到你说法变了"） |
| 偏好双源（context_pack :1368） | center 静默遮蔽 memory | 显式规则表 + 冲突登记（§6.2 步骤 4）；inferred 需携带可比置信度（center.inferred 增加 confidence 结构） |
| 五层晋升（outcome_promotion_governor） | block_on_conflict 仅五层域内 | LayerConflictReport 接入统一冲突登记；跨域冲突（五层 vs memory vs center）晋升前总闸 |
| spine claims（StateRegister） | 同 key 异 value 并列进 active_claims，无裁决 | 同 state_key 多值活跃时：counter_evidence 达阈值 → 建 UnresolvedConflict/claim probe，而非并列展示 |
| profile center（ProfileWriteService） | write 侧 explicit 守卫已有 | 读侧 merge（_merge_preferences）显式化并记录 winner 原因；restore_inferred_backup 联动审计 |
| 认知洞察（UserInsightAnalysisService） | contradiction_map 只注入 situation_brief | 冲突 → insight_claims → probe_outcomes 闭环；resolved 后回写两侧（声明 scoped / 观测降权） |
| prompt 层 | 三处口径不一 | 统一"冲突处理"标准节 + 注入各 mode；LLM 只负责执行系统已裁决的结论，不再临场仲裁 |
| 信念态（BeliefState/FusionEngine） | 只服务 routing，不产结论 | 把 belief_confidence 暴露为裁决维度分之一（行为证据源的量化出口），并在裁决记录中引用 evidence_ids |

---

## 7. 参考文件索引（绝对路径省略仓库前缀 wt5/）

- backend/app/services/conflict_resolver_service.py（Stage20 硬仲裁器）
- backend/app/services/memory_conflict_resolver.py / layer_conflict_resolver.py
- backend/app/core/context_ranker.py / context_pack.py（隐式仲裁器 + 遮蔽规则）
- backend/app/services/memory_service.py（版本链/纠错/撤回语义）
- backend/app/services/memory_inferred_write_lane.py / llm_extractor_service.py / working_memory_consolidation_service.py（三条写 lane）
- backend/app/services/profile_write_service.py / profile_insight_control_service.py / personalization/preference_service.py（center 域 + 用户纠正 lane）
- backend/app/services/user_insight_analysis_service.py / profile_truth_compiler.py（矛盾探测）
- backend/app/services/five_layer_learning_contract.py / outcome_promotion_governor.py（五层晋升闸）
- backend/app/signals/spine_orchestrator.py / aurora/runtime_v1/write_pipeline.py / aurora/runtime_v1/correction_feedback.py（claims 生命周期）
- backend/app/services/evidence/belief_state.py / fusion_engine.py（贝叶斯信念融合）
- backend/app/orchestration/prompts.py（:483 / :3836 / :4009 文本仲裁规则；:3780-3948 记忆渲染）
- backend/app/api/v1/memory.py（:497-532 未决冲突 API）
- backend/app/aurora/ledger.py（claim 版本化账本）
