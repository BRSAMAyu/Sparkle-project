# GAIN-FIX 交付报告 — 消融盘点揭出的三处污染/幻觉/坏开关修复

- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt205`（基线 `80f5db3d`，未 commit / 未 push）
- 修复依据：主仓 `v3-output/GAIN-EVAL/REPORT.md` §5 红旗 3 / 4 / 6（=本卡红旗 1 / 2 / 3）
- 法源：FLEET-BRIEF 四.4「诚实性：空数据返回诚实空态，不造默认值」+ 用户令「发现污染/幻觉即修」
- 交付物：本报告 + `v3-output/GAIN-FIX/changes.patch`（6 改 + 1 新测试文件，零凭据）

---

## ① 三红旗修法（对照红旗原文）

### 红旗 1（捏造状态，最重）—「零数据用户的 prompt 被注入捏造痛点 Recent error pressure remains elevated.」

**根因链**：`error_book_service.get_review_stats()` 对零错题用户也恒返全零**非空** dict（`total_errors:0,...`）→ `ProfileContext.error_summary` 真值判断通过 → `user_insight_compiler._apply_error_signals` 无条件生成 `pain:error_summary` 痛点条目（硬编码英文状态断言 label）→ 经 `UserInsightState.to_inline_snapshot()` 渲成 `- 痛点: Recent error pressure remains elevated.` → `prompts.py` 【画像快照】节注入零数据用户 prompt。

**修法（注入面按真实数据门控）**：`_apply_error_signals` 中该痛点只在存在**实际错题压力**时生成（`total_errors>0 或 need_review_count>0 或 due_for_review>0 或 subject_distribution 非空`）；全零快照不再生成痛点条目。`error_summary` 信号（计数字段）对全零快照仍保留——`累计错题 0` 是真实计数（诚实零值），不是捏造，保持原渲染面不动。**绝不无中生有；有数据时照常注入（阳性对照验证，见 ③）**。

**红证（修前可复现）**：零数据用户经生产装配链（`get_user_context` USE_CONTEXT_PACK=True → `build_system_prompt`）prompt 含该捏造句式（【近期痛点】`累计错题 0` + 【画像快照】`痛点: Recent error pressure remains elevated.`）。修后：捏造句式消失，诚实零计数保留。

### 红旗 2（M-05 回灌违背）—「prompts.py:3784 画像证据摘要回灌面把预算裁剪掉的 goal 标题/偏好值带回 prompt」

**根因**：`context_pack.py` 的 `metadata.evidence_summary`（top-evidence 观测面）由**预算裁剪前**的 source records 构建，此前只按 M-05 selfcheck 内部档 id 过滤（`memory_selfcheck_internal_ids`），**预算维度有缺口**；`prompts.py` 【画像证据摘要】在 `active_goals+episodic_memories` 皆空（=预算裁光）时反而把该摘要的 goal 标题/事件摘要/偏好 key+score 渲进 prompt——被裁掉的正文经 metadata 回灌，违背 M-05「无正文回灌」裁决。

**修法（回灌面与预算裁剪口径对齐 + 摘要源同口径，双端钉死）**：
1. `context_pack.py`：`evidence_summary` 源记录一律收敛到最终 `trimmed_*`（=预算+focus+selfcheck 后的 surfaced 集）——preferences 按 surfaced key、goals/episodic 按 surfaced id 过滤（原 selfcheck-internal 过滤被 surfaced 过滤严格覆盖，故收敛为单一口径）。被裁掉的条目从源头不进摘要。
2. `prompts.py`：【画像证据摘要】渲染面前同样做交集（偏好 key ∈ `normalized["preferences"]`；goal/episodic id ∈ 注入面 payload id），且**全空时不落节头**（诚实空态，顺带修掉修前「空 evidence 也渲染光秃节头」的小缺陷）。

**红证（修前可复现）**：播种 1 goal + 1 episodic，预算 `{"goals":0,"episodic":0,...}` 强制裁剪 → pack 注入面 `active_goals==[]` 但 `metadata.evidence_summary.goals` 仍含完整标题，`format_user_context` 产物含 `目标证据(Top 3): - 绝密目标XQZ-91...`。修后：被裁剪内容在 metadata 与最终 prompt 双面均不出现。

### 红旗 3（总开关半坏）—「chat.py:1014 legacy 路径引用不存在的 Plan.is_completed 属性」

**根因**：`USE_CONTEXT_PACK=False` legacy 分支的 context 组装在 `not Plan.is_completed` 处即 AttributeError（`Plan` 模型无该列），被外层 `except Exception`（:1047）静默吞掉——**plans/knowledge_stats 两段整体丢失**，总开关处于「半坏」态。深挖发现同块共 **5 处**幽灵属性引用（报告红旗只点了第一处炸点）：

| 位置 | 幽灵属性 | 对齐后（查 models 实证） |
|---|---|---|
| plans 查询 | `Plan.is_completed` | `Plan.is_active.is_(True)` + `Plan.not_deleted_filter()`（对齐全仓活跃计划口径：aurora runtime PlanScope / celery_tasks 同款谓词） |
| active_plans 映射 | `plan.title` | `plan.name`（输出 dict key 仍为 `title`，下游【活跃计划】渲染契约零破坏） |
| active_plans 映射 | `plan.plan_type` | `plan.type` |
| recent_tasks 映射 | `task.task_type` | `task.type` |
| knowledge_stats | `n.mastery_level`（×2 处） | `n.mastery_score`（`UserNodeStatus` 真实列） |

**红证（修前可复现）**：零数据用户 legacy 分支返回 `knowledge_stats=={}`（默认值——真实装配从未发生），`hasattr` 证实 5 个属性全部不存在。修后：legacy 分支走通，`knowledge_stats=={'total_nodes':0,...}`（诚实零），有数据用户 active_plans 正确映射（守卫测试含 Plan 落库正例）。

---

## ② 同型扫描（「无数据也注入」捏造面）

扫描范围：`user_insight_compiler.py` 全部 label 字面量（241/251/261/279/290/299/438/456/477/626/662/682）、`to_inline_snapshot`（全部条目均 `if label` 门控）、`learning_state_fragment.py`（仅渲染真实计数）、`situation_brief.py`（`_recent_pain_points` 渲染真实计数；freshest_items 拼接有数据才加）、`aurora_control_surface_service.py:341-353`（门控非空）、`user_insight_transparency_service` / `insight_prediction_service`（只取真实列表长度）、全 app `remains/elevated/is struggling/tends to` 类断言句式扫描（命中均为注释/文档，非注入面）。

**结论**：同族唯一「无数据也注入」的**状态断言型**捏造面即红旗 1 已修；其余同族注入行全部按真实数据在场门控或渲染诚实零计数，无需同修。

**登记备查**：GAIN-EVAL §5 红旗 5（`prompts.py:4479-4484` canonical insight goals 可回填 `active_goals`，画像/记忆边界交叉）——数据源自编译后的真实 insight state，**非捏造**，属边界归属问题且 C-PROF 消融同样覆盖，不在本卡「污染/幻觉」令内，留主会话裁决（本次未动）。

---

## ③ 实现清单（diff 面）

| 文件 | 改动 |
|---|---|
| `backend/app/services/user_insight_compiler.py` | `_apply_error_signals`：错题痛点按真实压力门控（红旗 1） |
| `backend/app/core/context_pack.py` | `evidence_summary` 源记录收敛到 surfaced 集（红旗 2 源端）；移除失效的 `memory_selfcheck_internal_ids` 中转变量（其唯一读点被 surfaced 过滤取代） |
| `backend/app/orchestration/prompts.py` | 【画像证据摘要】交集化渲染 + 空态不落节头（红旗 2 注入端） |
| `backend/app/api/v1/chat.py` | legacy 分支 5 处属性名对齐真实列（红旗 3） |
| `backend/tests/unit/services/test_user_insight_compiler.py` | +2 守卫：零错题无捏造痛点（含 error_summary 零值信号保留断言）/ 有错题痛点照常（阳性对照） |
| `backend/tests/unit/test_context_pack.py` | +2 守卫：整体裁剪不回灌（metadata+prompt 双面+空态无节头）/ 部分裁剪 evidence ⊆ 注入面 |
| `backend/tests/api/test_chat_legacy_user_context.py` | 新文件 +2 守卫：legacy 零数据走通（knowledge_stats 真实装配）/ Plan 落库正例映射（name/type/is_active 真实列） |

**阳性对照（门控不误伤，/tmp 脚本实证）**：有错题用户痛点标签仍在 inline snapshot；部分裁剪时 `evidence_summary.goals == ['在场目标KEEP-1']` ⊆ 注入面——修的是「对齐」不是「杀观测面」。

---

## ④ 冲突面声明

| 邻卡 | 面域 | 交叠判定 |
|---|---|---|
| wt200（只读实测） | 实测/验收面 | 本卡改动全部在 `backend/app/{services,core,orchestration,api}` + `backend/tests`，wt200 为只读实测、零树变更——**零重叠** |
| wt204（mobile SPEC） | `mobile/` | 本卡零 mobile 文件——**零重叠** |
| GAIN-EVAL 资产（wt198 已合入） | `backend/tests/northstar_eval/` | **零改动**（dry-run 复跑全绿为证）；本卡新测试文件在 `tests/unit`、`tests/api`，无同名新文件风险 |

---

## ⑤ 收工核查

- [x] 每项红旗先红证后修：修前 /tmp 红证脚本三项全 True（红旗在燃），修后复跑 ALL GREEN；红证/阳性对照脚本在 `/tmp`（收工自清，证据摘录已入本报告）
- [x] GAIN-EVAL 资产装配面零破坏：`test_gain_ab.py` 5 passed；全量 dry-run `20 场景 × 4 臂真实装配链装配 OK；开关探针 {'D-VEC': True, 'G-GALAXY': True}；消融接线断言全绿`（修后两轮复跑）
- [x] 回归对比法零新增：基线克隆（`/tmp/gainfix-baseline` @ 80f5db3d）对照——`test_user_insight_compiler.py` 的 `recurring_windows` 失败与 `test_context_pack.py` 的 2 条 ruff（I001/UP017）**基线即红**，非本卡引入；其余定向全绿（context_pack+sources+selfcheck_wiring 18 passed；prompt 三件套+context_pack 31 passed；snapshot cache/invalidation/situation_brief 57 passed；本卡守卫 6 passed）
- [x] lint：改动文件 `ruff check` All checks passed（`ruff format` 的 would-reformat 4 文件基线同样 drift，未触碰存量行）；新增/改动 hunk format 合规（120 列）
- [x] 修改仅在本 worktree；主仓只读（`backend/app/gen` 为 gitignored 生成物，进程内验证期间从主仓 symlink 进 worktree，收工已移除；主仓零写入）
- [x] 未 commit / 未 push；交付物 = 本报告 + `changes.patch`（不含 v3-output 自身、不含 gen symlink）；零凭据
- [x] /tmp 产物（红证/阳性脚本、dry-run 输出、基线克隆）已清；无独立端口进程/模拟器/浏览器（全 LIGHT 任务，测试均带 --timeout、定向不宽扫）
