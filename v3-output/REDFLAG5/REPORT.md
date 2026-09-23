# REDFLAG5 裁决报告 — goals 跨通道回填的边界归属（裁决 = 合法，钉防劣化）

- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt209`（基线 `490acf7a`，未 commit / 未 push）
- 裁决对象：主仓 `v3-output/GAIN-EVAL/REPORT.md` §5 红旗 5（画像面跨通道注入 goals）——wt205 同型扫描判「边界归属非捏造，登记备查留裁决」（`v3-output/GAIN-FIX/REPORT.md` §2），本卡把这个悬而未决的边界裁掉
- 交付物：本报告 + `v3-output/REDFLAG5/changes.patch`（**1 个新守卫测试文件，零产品代码改动**，零凭据）
- 验证：定向对比法零新增失败 + 三变异红证全红 + GAIN-EVAL 资产套件复跑全绿

---

## ① 回填链路事实（file:line，基线 490acf7a）

**注入点**（GAIN-EVAL 引 `prompts.py:4479-4484` @wt198 基线；GAIN-FIX 合入后同块现为）：
`backend/app/orchestration/prompts.py:4501-4507`（`_normalize_user_context` 内「Canonical insight state enrichment」段）

```python
# Goals from compiled state, only if not already provided
if not normalized.get("active_goals") and canonical_insight.goals:
    normalized["active_goals"] = [
        {"title": str(g.get("label") or g.get("type") or ""), "status": "active"}
        for g in canonical_insight.goals[:3]
        if isinstance(g, dict)
    ]
```

**生产链路**：`build_system_prompt`（prompts.py:993）→ `_render_user_context_content`（:3426）→ `_normalize_user_context`（:3433）→ 回填（:4502）→【当前目标】渲染（:3603-3608）。canonical_insight 取值序 `context["user_insight_state"]` / `profile_context.user_insight_state`（prompts.py:2759-2803）。注意：陪伴人格节的 `当前目标:` 行（:2041-2046、:2143-2145）读**原始** context 的 active_goals，不经本次回填（该行另有 plan_context.goal 兜底）——双面非对称是既有事实，非本卡缺陷面。

**回填源（画像编译态通道）**：`UserInsightState.goals` 仅由 `user_insight_compiler.py` 四个产出点写入，全部来自真实记录事实：

| 产出点 | goal id | 事实源 | source 标注 |
|---|---|---|---|
| `_build_base_state` :237-244 | goal:primary | profile preferences `learning_goal_type`/`goal_type`（用户声明） | preferences |
| `_build_base_state` :247-255 | goal:exam_window | preferences `exam_urgency.days_left` | preferences |
| `_build_base_state` :257-264 | goal:active_subjects | knowledge_summary `active_learning_subjects`（无声明时回退） | knowledge_summary |
| `_apply_calendar_signals` :678-686 | goal:exam_pressure | 日历 exam_urgency（真实日程） | exam_urgency |

零事实用户 → `goals==[]`（:899 源端就登记 goal_shape 不确定性）→ 回填条件 `and canonical_insight.goals` 不触发 → 诚实空态。**同通道画像面本就含目标**：`to_inline_snapshot`（user_insight_state.py:185-189）无条件把前 2 条 goals 渲成【画像快照】的 `- 目标: {label}` 行——目标事实进 prompt 是画像面设计本义，非该回填块独创。

**主通道（回填让位方）**：`active_goals` 有两个生产者——(1) stage34 装配：`context_builder.py:659-662,722`，`PlanService.list_active(limit=3)` 取 **Plan 业务真值行**（非 MemoryGoal）；(2) pack 面：`context_pack.py:1403`（`memory_service.list_active_goals` → MemoryGoal 行）→ M-03 预筛（:1422-1426）→ rank/预算裁剪 → `trimmed_goals`（:1916）→ `ContextPack.to_prompt_context()`（:1263）。回填仅在两主通道产出皆空时触发。

**与 wt205 修复面的交互（已核，无回灌协同）**：【画像证据摘要】（prompts.py:3784-3839）仅在 `not active_goals and not episodic_memories` 时落节，且 goal 证据按 surfaced id 交集过滤（:3809-3813）——回填条目无 `id` 字段、回填触发即令该节整体不落：两个方向都堵死了「被裁正文经 metadata 复活」的协同面。

**类别权威**：`context_sources.py:33-37`「state —— 业务真值投影：plan/goal/task…**Goal 属 Current State（USER_WORLD_MODEL §1），虽存储在 MemoryGoal 表——类别按语义对象，不按表名**」；:92-95 `item_type "goal" → "state"`；:130 `active_goals → state`；:122-127 profile/preferences（payload 面）→ state。:172-175 `LATE_STAGE_WRITERS` 是 provenance 标注（「不是冲突断言」），非通道排他律。

---

## ② 裁决链全文（事实 → 规则 → 结论）

**命运选项**：(a) 合法（裁决文档 + 守卫钉死）；(b) 违规（照 wt205 红旗 2 双端钉修）；(c) 部分合法（拆面处置）。

**事实**（见 ①）：回填内容源 = 编译态真实用户事实（声明 goal 类型/考期/在学科目/日历考窗），未过记忆闸、不在任何预算池里、零数据时不触发；目标语义在项目自己的四类权威里属 state（Current State）；【画像快照】本就渲染目标行。

**规则对照**：

1. **M-05「降档条目正文不回灌」**（M-05 REPORT §4；wt205 红旗 2 修法）——辖域是**记忆闸（M-03 预筛/M-05 selfcheck/预算裁剪）降档的 memory 记录**不得经同装配系的侧通道（metadata/evidence_summary）复活。回填内容从未进过记忆闸、从未被裁——不存在「被裁正文复活」，源记录亦不同存储（ProfileContext/preferences vs MemoryGoal 行）。查询相关度降档是**记忆召回纪律**（可召回可不出口），对 state 通道的恒在场真值投影本就不适用（USER_WORLD_MODEL：state=当前真值，非按查询召回）。**不违背**。
2. **FLEET-BRIEF 四.4 诚实性**——零数据回填不触发（守卫 2/3 钉死），有数据时每条 goal 都有真实记录出处（守卫 1 钉死 source 封闭词表），无默认值、无捏造状态。**不违背**（且正向服务诚实性：人格节指示「视为已知上下文，不要反复问你的目标是什么」（:2087、:2111），声明过 goal 事实的用户若因无 Plan/MemoryGoal 行而【当前目标】恒空，反而诱导模型反复追问已知信息）。
3. **FLEET-BRIEF 四.1 口径单一事实源**——回填消费的是唯一权威编译态 `UserInsightState`（C-02/SPEC 链认定的 canonical state），非自算新聚合。**不违背**。
4. **四类边界（C-02/USER_WORLD_MODEL「四类对象不可混」）**——画像通道与 goals 槽在四类分类法里**同为 state**（见 ① 类别权威），红旗 5 的「画像与记忆边界交叉」框架在项目自己的类别权威下不成立：goal 的「memory 归属」只是存储表名（context_sources.py:36-37 明文「类别按语义对象，不按表名」）。**无边界穿越**。
5. **价值增量红线**（FLEET-BRIEF 四.3）——纯 prompt 装配面，免费闭环行为零变化；无光子/会员面。**不适用/不触碰**。
6. **预算纪律**——回填 `[:3]` 硬截断 + 渲染面 goal_limit 截断（:3606）+ 快照面自带 1200 字符预算（user_insight_state.py:174）；它不绕过任何裁过**该内容**的预算（该内容不在被裁池）。**无绕行**。

**结论**：**(a) 合法**——goal 是一等用户事实（Current State），画像编译态回填 = 画像面本义（快照面本就含目标行）的 fallback-only 延伸；对 M-05、诚实性、口径、四类边界、价值增量五条红线均无违背。**残余风险 = 未来劣化**（有人在编译器加无出处的推断型 goal、或零数据时造默认目标、或改成覆盖主通道）——以 3 条不变量守卫钉死（见 ③），任一变红即回裁决。不修产品代码：本卡零 diff 面于 `backend/app/**`。

---

## ③ 实现/守卫清单

**唯一交付文件**：`backend/tests/unit/test_goal_backfill_boundary.py`（新增，6 守卫，ruff check + format(120) 全绿）。零产品代码改动（`git status` 可证：仅 1 个 untracked 测试文件）。

| 守卫 | 钉死的不变量 | 红证（变异试验，单文件改→红→`git checkout --` 还原） |
|---|---|---|
| `test_compiler_goal_emitters_carry_real_fact_provenance_ast_pin` | 编译器 goal 产出点冻结为 4、每点必带 `source ∈ {preferences, knowledge_summary, exam_urgency}` + label/type 键（AST 钉，M-05 wiring 同法）——**「goal 回填只能来自真实 goal 记录」的核心钉** | MUTATION-B：删 goal:primary 的 `source` 键 → **2 failed**（AST 钉+行为钉同红）→ 已还原 |
| `test_base_state_goal_sources_behavioral_pin` | `_build_base_state` 三种画像输入：声明事实→2 条带出处；回退事实→knowledge_summary 出处；零事实→`goals==[]`（源端诚实空） | 同上（MUTATION-B 双杀） |
| `test_backfill_zero_data_user_honest_empty_no_default_goal` | 零数据用户不回填、prompt 无【当前目标】/`当前目标:`（红旗 1 同型捏造的 tripwire） | MUTATION-A：注入默认目标 `期末备考冲刺` → **1 failed**（`'active_goals' not in {...}` 精确报红）→ 已还原 |
| `test_backfill_never_overrides_primary_channel_payload` | 主通道（stage34 全形状含 id/progress/target_date）在场时回填绝不覆盖/合并 | MUTATION-C：删 fallback-only 条件 → **1 failed** → 已还原 |
| `test_backfill_entries_bounded_to_compiled_labels` | 回填标题 ⊆ 编译态 label/type 投影、`[:3]` 截断、status 恒 active、无 id（不冒充 MemoryGoal 记录） | 纯断言面（内容边界由 MUTATION-B/C 间接红证） |
| `test_backfilled_goal_renders_current_goal_section_positive_control` | 阳性对照：有真实 goal 事实的零 Plan 用户【当前目标】照常落节（防未来误杀合法画像面） | —（对照面） |

---

## ④ 冲突面声明

| 邻卡 | 面域 | 与本卡交叠判定 |
|---|---|---|
| wt206（chat session 面） | chat session 装配/会话面 | 本卡仅**新增** `backend/tests/unit/test_goal_backfill_boundary.py`，零产品代码改动、零 session 面文件——**零重叠**（仅同目录新增文件，无同名风险：文件名为本卡专名） |
| wt207（onboarding/趋势/光子） | onboarding/趋势/光子服务与测试 | 本卡不触 onboarding/光子任何面——**零重叠** |
| wt208（纯巡检） | 只读巡检 | 本卡树变更仅 1 个新测试文件，巡检只读——**零重叠** |
| wt205 已合入面（基线 490acf7a 在案） | `prompts.py` 证据摘要交集、`context_pack.py` surfaced 收敛、`user_insight_compiler.py` 错题痛点门控、`chat.py` legacy 对齐 | 本卡**只读消费**这些模块（AST 扫描 + 进程内行为验证），不改其一行；已核回填与 wt205 证据摘要修复面无回灌协同（见 ①）；`test_user_insight_compiler.py`、`test_context_pack.py` 均未触碰，复跑绿 |
| GAIN-EVAL 资产（wt198 已合入） | `backend/tests/northstar_eval/` | 零改动；`test_gain_ab.py` 复跑 **5 passed**（真实装配链含本回填路径，间接证明裁决后装配面零漂移） |

---

## ⑤ 收工核查

- [x] 裁决链写全（事实→规则→结论，五条规则逐一对照）；命运选项 (a)/(b)/(c) 明确选 (a) 并说明 (b)/(c) 不成立的判定点
- [x] 守卫 6 全绿；三变异红证全红且逐一 `git checkout --` 还原（单文件粒度，符合并发验收工作树安全纪律）；`git status` = 仅 1 个 untracked 测试文件
- [x] 对比法零新增：基线克隆（`/tmp/redflag5-baseline` @ 490acf7a）同套件 36 passed + 1 failed（`recurring_windows`，wt205 报告已登记的基线即红）↔ 本树 42 passed + **同一 1 failed**——失败集逐条一致，零新增
- [x] 定向不宽扫：只跑 5 个相关域测试文件 + GAIN-EVAL 资产套件，全部带 `--timeout`，SECRET_KEY=test 进程内哑值，零真实 LLM 调用
- [x] lint：新文件 `ruff check` All checks passed + `ruff format(120)` 合规
- [x] 修改仅在本 worktree；主仓只读（`backend/app/gen` 为 gitignored 生成物，从主仓 symlink 进 worktree，收工移除；主仓零写入）
- [x] 未 commit / 未 push；交付物 = 本报告 + `changes.patch`（不含 v3-output 自身）；零凭据
- [x] /tmp 产物（`/tmp/redflag5-baseline` 基线克隆）收工自清；无独立端口进程/模拟器/浏览器/Gradle（全 LIGHT 任务）
