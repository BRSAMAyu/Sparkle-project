# V4-P01 一审 receipt（wtP01R1）

- 审查会话：wtP01R1（未参与实现）；审查对象：`agent/v4/p01` 实现 `d0bd8d45` + 证据 `569705be`，基线 `17c14cea`。
- 审查日期：2026-09-29。方法：只读审查 + 本机亲跑（共享主检出 venv，`SECRET_KEY` 环境变量注入；临时探针用后即删）。
- **裁决：APPROVE_WITH_CONDITIONS**（两条收口条件 C-1/C-2，见文末；不动实现提交本身）。

## 一、亲证通过面（每条带可复现命令/行号锚）

| # | 结论 | 锚 |
|---|---|---|
| V1 | 工作树干净，与实现提交零漂移 | `git diff d0bd8d45 --stat -- backend/` 空 |
| V2 | CH-5 复原完整性：8/8 文件 sha256 与 run_manifest 逐一相符 | `shasum -a 256` 八文件 == `artifacts_sha256`；`unified_budget.py` = `389c9b8c…fcb4` |
| V3 | M1 突变亲放：subject 抑制分支短路 → 2 反例钉齐红；`git checkout` 还原后 sha256 复原 + 17 绿 | `pytest tests/aurora/test_proactive_unified_budget.py::test_cross_channel_rejection_blocks_spine_nail tests/unit/test_p01_budget_channel_wiring.py::test_spine_recall_blocked_after_nudge_rejection_nail` → `2 failed`；还原后 `17 passed` |
| V4 | 17 新测亲跑绿 | `pytest tests/aurora/test_proactive_unified_budget.py tests/unit/test_p01_budget_channel_wiring.py -q` → `17 passed` |
| V5 | 受影响面全量回归亲跑复现：1219 passed 零失败 | 11 文件同命令 → `1219 passed in 194.83s` |
| V6 | mypy 33/31 零新增亲证：head 六入口文件各 `33 errors in 31 files`，base 临时 worktree 同命令 `celery_tasks.py` 同为 33/31 | base 对照 worktree（已删）亲测；错误全在传递导入既有文件 |
| V7 | ruff 7 文件 `All checks passed!`；black 3 新文件零漂移 | 亲跑 |
| V8 | merge 干净：vs main `c94afbe4`（merge-base 17c14cea）merge-tree 0 冲突标记；双侧唯一重叠 `v4/04_tasks/tasks.json`（舰队状态文件，预期）；main 侧零触碰 aurora/proactive 族/celery_tasks/proactive_suggestion_service/notification_center（`git diff --name-only` 空清单） | `git merge-tree $(git merge-base main agent/v4/p01) main agent/v4/p01` |
| V9 | 「spine 渠道此前不过 quiet、不占日预算、不认拒绝」属实：base `recall_notification_task` 任务体无任何 burden/quiet/suppression 调用 | `git show 17c14cea:backend/app/core/celery_tasks.py`（基线 spine 体 grep 零命中；对照 base nudge 体 2159/2183 行内联 P-03/P-06） |
| V10 | 统一日预算真实成立：`daily_count` 计**全类型** Notification 行（用户本地日界）——spine 发送计入并受共享 cap 约束 | `notification_settings.py:264-289`（无 type 过滤的 count 查询） |
| V11 | 「被抑制不消耗 spine 冷却」属实：闸门在 `get_spine_orchestrator` 之前 return；`record_sent_async` 在 `build_recall_notification` 内部（spine_orchestrator.py:1323） | 控制流亲读 + 任务级 `assert_not_awaited` 双钉（wiring 测试） |
| V12 | tasks.json 证据编辑外科（仅 V4-P01 条目 +9/-3） | `git show 569705be -- v4/04_tasks/tasks.json` |
| V13 | CH-4 并存语义自洽：muted 不被冷却降级 / 冷却不叠加顺延 / 到期可刷新 / 静音单向升级 | `proactive_suggestion_service.py` `_merge` 闭包逐分支亲读 + `test_record_resolves_task_plan_and_never_stacks` |
| V14 | OpenAPI 契约/BA-ROUTES/event_registry/proto 零改动声明与 diff 一致 | `git show d0bd8d45 --stat`（8 文件全在 backend/，无 proto/迁移/event_registry） |

## 二、预登记挑战 CH-1..CH-5 逐项裁决

- **CH-1（subject-less scan 派发）——缺口真实、已如实声明、不阻塞**。事实亲证：`scan_recall_notifications` 以 `json.dumps({})` 空上下文派发全部 4 类触发（celery_tasks.py:3173 附近），生产主路径的 spine 请求无 subject 键 → subject 抑制、过期检查、effect 去重三面全旁路（探针亲证：空 refs 判定 `allowed`）。该路径抑制面缺口由共享 quiet+cap（V10）+ spine per-trigger Redis 冷却 + 30min 扫描去重承载。裁决：验收①在 scan 路径由**预算面而非抑制面**承载——不阻塞收口（闭合需 scan→detector→context 全链传参，属后续卡），但此口径须随卡片交接记录（见记录项 R1）。
- **CH-2（过期计划单侧 vs 双侧）——单侧裁决成立**。`_SUBJECT_EXPIRED_CHECKED_CHANNELS` 仅 spine（unified_budget.py:85）；nudge 渠道过期计划呈现是 J-07 rescope 校准流，属「有具体帮助时出现」的合法面，双侧阻断会杀死该流。卡句「不再被**另一渠道**补发」从 spine 视角读成立。不阻塞。
- **CH-3（24h 去重窗收紧 6–8h 冷却）——方向正确，不阻塞**。依据亲证：`_COOLDOWN_SECONDS` task_missed=8h、pre_exam_silence=6h（recall_notification.py:22-31）< 24h effect 窗。收紧只少发不多发，与「同一用户预算/只在有具体帮助时出现」同向；`PROACTIVE_PROMPT_EFFECT_WINDOW_HOURS` 旋钮在，时长语义留产品裁决（limitations#4 已声明）。
- **CH-4（muted 单向升级 × 一次 effect 并存）——语义自洽，过**。见 V13。
- **CH-5（突变复原）——过**。见 V2/V3；M2/M3 未重放（同法可信，M1 为最重靶已亲放）。

## 三、发现（按严重度）

### F1（最重靶缺陷，条件收口 C-1）：spine→nudge 方向跨渠道 subject 抑制在真实接线中结构性失效

- `recall_notification_task` 是 `recall_notification` 类型通知的**唯一**生产者（celery_tasks.py:3081，全仓 grep 亲证）；其 `NotificationCreate.data` 固定形状**不含** `plan_id`/`task_id`/`goal_id`——上下文键不落入 data，已盖信封里的 `subject` dict 也不被提取面读取。
- 后果：用户经 suggestion-action 对 spine 卡拒绝/静音时，`record_cross_channel_suppression(notification.data)` 提取零 subject。**临时探针亲证**（用后即删）：构造与任务逐字段一致的 spine data → `recorded == {}` → 同 plan 的 comeback nudge 随后 `allowed=True`。
- 证据测试缺口：`test_cross_channel_rejection_blocks_spine_nail` 反向半场（spine 静音→nudge 被拦）直接喂合成载荷 `{"task_id": TASK_ID, "plan_id": OTHER_PLAN_ID}`——真实 spine 通知永不携带该形状，service 层 task→plan 解析为真但 API→提取→写库一环被跳过，「反向亦然」的端到端主张不成立。
- 定性：验收①的双向对称仅 nudge→spine 方向端到端成立。修复小而局部（spine data 补 subject 键或提取面读信封 subject），故定条件收口而非 FAIL。

### F2（CH-1，记录不阻塞）：scan 主路径抑制面旁路

见 CH-1 裁决。验收①「过期计划不再被另一渠道补发」在 scan 派发路径上由预算面（quiet+cap+冷却）承载而非抑制面。

### F3（证据精度缺陷，勘误 C-2b，不影响零回归结论）：「基线 242」数字失实

- run_manifest/test_results/diff md 称基线命令（同 9 文件集）`242 passed`。base 临时 worktree 亲测：**同集收集 1202**（head 同集亦 1202）。
- 真实算术：1219 = 1202（同集）+ 17（新测），零回归结论**成立**（base=head 收集数相同 + 1219 全绿亲跑 V5）；但 242 作为「same set」分母不成立，须勘误。

### C-2a（rollback 语义失实，文档修正）

`PROACTIVE_UNIFIED_BUDGET_ENABLED=false` = 闸门 passthrough，但 comeback_nudge_task 已用闸门**替代** base 既有的内联 P-03+P-06 检查（base 2159/2183 行亲证）→ off 态下 nudge 渠道连**既有**类型抑制/负担检查一并失效（静音用户可再被打扰）。「off = 恢复各渠道既有行为」对 nudge 渠道不成立——它是全关紧急开关。措辞须改（或补 legacy 回退，非必需）。

### Minor（记录）

- quiet hours 经统一闸门无直接行为钉（两新测试文件均显式关断 quiet；闸门 quiet 与 daily_cap 共用同一 passthrough 代码行，`evaluate_burden` 自身 quiet 语义有专测且在 1219 集内）——低风险，留后续补钉。
- effect 去重按 channel 分键（`derive_prompt_key` 含 channel）：跨渠道同 subject 双发不属 effect 去重管辖（由抑制面+共享 cap 承载）——「多端一次 effect」按多设备口径成立，口径备注。

## 四、验收三条裁决

1. **拒绝/静音/过期计划不再被另一渠道补发——条件性成立**。nudge→spine 方向 + 过期/缺失 spine 侧端到端成立且有反例钉+突变演示（V3）；spine→nudge 方向 F1 失效、scan 路径 F2 旁路。
2. **回归不视为必须打扰，不改变主题推断情绪——成立**。cap=0 时 comeback 同级被拦（`test_regression_comeback_not_privileged_nail`，闸门无任何渠道豁免分支亲读）；情绪输入面零写入钉（`test_gate_writes_no_emotion_signals`）；口径与 limitations#5 一致。
3. **同一提示多端一次 effect，预算与因果来源可追——成立**。prompt_key 多端去重闸门级+任务级账本匹配双钉；信封与 cap 计数出自同一 `evaluate_burden` 裁决、随 Notification 行同源落库（V10/V11）。

## 五、裁决与条件

**APPROVE_WITH_CONDITIONS**——实现架构（组合层零新真源、固定顺序闸门、fail-closed、有界 metrics、反例钉+突变演示）与证据纪律达标，零回归亲证；以下条件闭环后收口：

- **C-1（行为，必须）**：spine 放行路径把 subject 键带进 `Notification.data`（`parsed_context` 的 plan_id/task_id 直落 data，或让 `subject_refs_from_payload` 读已盖信封的 `subject` dict，二者取一），使 spine 卡的拒绝/静音真实产生 subject 抑制；补一条经**真实 data 形状**的端到端反例钉（spine 卡拒绝 → 对侧渠道闸门红）。
- **C-2（文档，必须）**：a) rollback 措辞改为「全关紧急开关：off 时 nudge 渠道既有 P-03/P-06 检查一并失效」；b) 勘误三份证据文件「基线 242」→ 同集 1202（1219=1202+17）。
- **记录项（不阻塞）**：R1) F2 scan 路径抑制面旁路口径随卡片交接；R2) CH-2/CH-3 裁决与 quiet 直钉缺口留档；R3) FIX-48 仍 OPEN（limitations#3 如实，属语义裁决非本卡）。

审查探针文件已删除；本 receipt 为审查会话唯一新增物。未 push、未动实现提交。

---

## 整改注记（2026-09-29，wtP01 整改会话追加；上文审查内容零改动）

- **整改 commit**：`4d80c4c5`（agent/v4/p01，`fix(v4): P01 一审 C-1 spine→nudge 抑制接线+C-2a/b 文档`；实现主逻辑仅动 C-1 修复面，本 receipt 原文零改动）。
- **C-1 闭环（F1）**：生产者侧 `recall_notification_task` 放行路径把上下文 subject 键（plan_id/task_id/goal_id）直落 `Notification.data`（gate/envelope/data 三处同源自 `subject_refs_from_payload(parsed_context)`）+ 提取面 `subject_refs_from_payload` 兼读预算信封 `proactive_budget.subject`（顶层键后读优先；损坏形状不炸）——两半场互为双保险，各配独立钉（wiring 测试 spine data 键钉 / 闸门测试信封提取钉）。F1 指出的「反向半场合成载荷跳过 API→提取→写库」由新端到端 `backend/tests/api/test_p01_cross_channel_suppression_e2e.py` 闭合：真实任务产形（任务体外呼 mock）→ 真实 `NotificationService.create` 落库 → 真实 `record_suggestion_action` handler → 提取 → P-03 写库读回 → 统一闸门判定，双向矩阵（spine 静音→同 plan nudge 拦 `cross_channel_suppressed`；nudge 拒绝→同 subject spine 拦）全绿；摘 C-1 修复突变 3 failed（方向一端到端 + 两半场钉）→ 还原 19 passed。
- **C-2a 闭环**：rollback 口径改为「全关紧急开关：off 时 nudge 渠道既有 P-03/P-06 检查一并失效」——config.py 旋钮注释 / unified_budget.py docstring 与步骤 0 注释 / limitations#10 / diff_or_evidence_only.md / `test_knob_off_passthrough` docstring 五处同步。
- **C-2b 闭环**：run_manifest.json / test_results.json / diff_or_evidence_only.md 三份证据文件「基线 242」→ 同集 1202（1219=1202+17）订正，勘误注记留痕。
- **整改验收证据**：原 11 文件集复跑 1219 passed 零失败（184.55s）；含新端到端文件 1221 passed；mypy 六入口 33/31 与一审基线同数（棘轮 ≤77 未触）；ruff 全过、black 零新增漂移（celery_tasks 14 hunks 为 base 既有同 hunk 集）；OpenAPI 契约 3 passed 零漂移（data 面非路由面）；CH-1 scan 路径抑制面缺口维持 limitations#1 如实登记不扩面（R1 记录项保持）。
