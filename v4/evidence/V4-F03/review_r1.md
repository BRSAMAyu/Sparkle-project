# V4-F03 · 独立审查 receipt（一审 · wtF03R1）

- **审查者**：wtF03R1（独立会话，未参与 F03 实现）
- **审查对象**：分支 `agent/v4/f03`，commit `13ba9e76`，base `71553984`（diff 16 文件，+2361/-5）
- **日期**：2026-09-28（本机 macOS arm64；纯 Python/Dart 变更，无 cgo/平台面）
- **卡风险级**：high（需 2 位独立审查；本 receipt 为第一审）

---

## 总裁决：**PASS**（一审合格，附 1 条数字勘误 + 2 条建议 + 2 条注记，均非阻塞）

三条卡验收全部独立复核成立（每面正反测试实跑通过 + 机制面逐一核对）；D01 二审 C-1/C-2 属本卡卡面且确已闭合；预登记挑战点①-⑤逐一独立下判（见下）；红线全量核对零触碰。等待第二位独立审查（高风险双审），`review_receipt.json` 维持 PENDING 至双审落账。

---

## 一、三条验收逐核（全部独立复核成立）

### 验收① 无 committed 回执不触发成功；同 event 重播不重复震/音 — **PASS**

- **backend 链（X-03 回执→投影→事件）反例面实跑**：PENDING（`not_terminal_no_receipt`）、状态谎报 COMMITTED 无 receipt 本体（`no_authoritative_receipt`）、回执体 status 不自洽（同上）、user_cancelled/user_rejected（`user_action_terminal_skip`，契约 §6 零事件）、version 全链缺失（`subject_version_missing`，不猜版本）、subject 缺失 create 型（`subject_unanchorable`，不造泛化成功）——6 条拒绝路径全部有测试且断言 `event is None`。I2 双门（status=COMMITTED **且** receipt 本体 receipt_id+status 自洽）为投影前强制，结构性不可绕。
- **mobile 链**：解析层 E1 门（state_confirmed 无 receipt_ref / committed 带 error → `tryParse` 返 null → `ignoredInvalid`，零感官、计数可观测）；重放实测：同 event_id present 两次，sink 调用数恒 `['success']`（不重复震/音）、`replaySuppressed` 无庆祝徽章、**copy 仍恢复**（MOTION「文本状态仍恢复」口径）。去重键 = D01 内容寻址 `event_id`（`sha256(receipt_ref+kind+version_token)` 派生，时间不进身份——`replay_action_receipt` 跨时点重算恒同 id 有测试）。

### 验收② 仅保存记忆不显示任务修改完成；证据登记不叫精通 — **PASS（双侧机制核成立）**

- **backend 文案路由（结构性）**：`SUCCESS_FACE_SUBJECT_TYPES={task,goal,plan}` 封闭集；`COMMITTED_COPY_KEY_BY_SUBJECT["memory"]="memory.saved"`（「记忆已保存」），memory 路由**结构性拿不到**任务成功文案与三模态（`_SUCCESS_MODALITIES` 仅 success_face subject 开放，memory committed 恒 `[visual]`）；`project_feedback_receipt` 通用面调用方**不可指定成功文案**（封闭路由 `outcome://`+progress_delta → `evidence.registered`「证据已登记」）。全表 17 键禁词扫描（精通/已掌握/掌握度/mastery/mastered 零命中，测试钉死）。
- **mobile 分层路由（同构）**：路由顺序 replay 抑制 → 失败面 → 中性 kind → version 校验 → subject 分层；memory committed → `presentHighlight`（visualState=null、celebrates=false、playsSuccessCue=false、selection 轻触一次——实测 sink 恒 `['selection']`）；成功面孔仅 {task,goal,plan}；禁词扫描 + `kSuccessFaceSubjectTypes` 集合断言钉死。I07 锁面不越（无 mastery 机制实现，仅呈现纪律）。

### 验收③ 断网未知态仍可查，不渲染绿色成功 — **PASS**

- `resolveUnknownDisplayState()` → `PixelRunState.unknown`（`PixelStateSpec.forState(unknown).celebrates == false` 有断言）；committed 事件 + `currentSubjectVersionToken==null`（断网/未对账）→ `presentUnknown`（unknown 徽章 + 零声/触实测）；版本不符 → `staleVersionSuppressed`（零庆祝，仅中性文本）。
- **绝不借 PixelSuccessBadge 有组件级反例（判别力有正例控制组）**：unknown/failed/conflict 三决策的组件树中 `find.byType(PixelSuccessBadge) findsNothing` + 语义标签可查（「结果未知」「失败」「版本冲突」）；正例（success 决策 → findsOneWidget）证明断言非恒假。视觉路径唯一经 F02 `PixelStateBadge` 族。
- **断网态数据可达性声明核**：unknown 面为纯本地语义（无网络对账仍可渲染 unknown 徽章 + 文案 + 读屏标签），适配器不依赖网络可达；真机断网实测属 DEVICE_UNVERIFIED（limitations #6 如实登记，MOTION 纪律原文），不阻止本审通过。

## 二、D01 C-1/C-2 落地核 — **均闭合（真实生产调用方）**

- **C-1**：三个挂点经源码逐一定位——(a) `approve` 成功路径：`db.commit()`+`refresh()` 之后、`return` 之前调 `project_action_receipt_safe`（真实生产 commit 链路）；(b) `expire_stale_proposals`：批量 `_terminalize`+commit 后逐行挂点（真实清扫路径）；(c) API `approve_proposal` 错误面：`except ActionCommandError` 内 `project_action_error_by_id_safe`（HTTP 映射原样进行，挂点只增呈现）。**INVALID_COMMAND fail-loud 生产可达且有测试**：`project_error_state(ACTION_INVALID_COMMAND)` → `ExperienceProjectionRefused` 上抛（测试断言 `pytest.raises`）；韧性壳 `project_action_error_safe` 把 fail-loud 转 `None` + 稳定前缀 warning（不静默吞，测试断言 `swallowed is None`，且直呼路径的 raises 测试证明 fail-loud 语义本身未被壳吞——两层都有测试钉住）。
- **C-2**：`mark_seen` 挂点改为捕获 `record_rendered_exposure_safe` 返回值，`not projected` → `logger.warning("experience_presentation.degraded record=… decision=… reason=…")` 稳定前缀可 grep；测试用真实 `InterventionRecordService` 生命周期 + 删 `InterventionLifecycleEvent` 行模拟回执缺失，loguru sink 捕获断言前缀 + `no_authoritative_receipt` 双命中；SEEN 转场不受影响。None 返回（壳内异常路径）有守卫不误报。

## 三、预登记挑战点①-⑤逐一独立下判

### ① 懒转/双投影 dedupe 身份恒一 — **成立（审查者独立实测，非采信自报）**

实现自身 17 测中**无**双路径同 id 测试（仅同路径 replay 恒同）。本审查自写一次性测试实测（跑毕即删，不入库）：路径 A = `approve` 已过期 PENDING proposal → 服务懒转 EXPIRED + `ProposalExpiredError`(error_code=ACTION_EXPIRED) → API 错误面挂点 `project_action_error_by_id_safe`；路径 B = 同一行走 sweep 终态面 `project_action_receipt`。**实测结果：`event_id_A == event_id_B` 且 `dedupe_key` 相同**（内容寻址 `action_command://{id}`+`terminal_failed`+version 恒同，与投影路径无关）；sweep 服务路径（`expire_stale_proposals` 真实调用）亦验证。**判定：身份恒一成立。** 建议（非阻塞）：把双路径同 id 断言补进回归套件（我的实测已钉一次，但不随本分支留档）。

### ② mobile/backend copy 表镜像 — **缺口确认属实；判定可接受，建议后续强化**

- 逐键核对：两侧 17 键、键名与文案**本次逐字一致**。键数断言双侧在（mobile `length==17`、backend 键集逐字面冻结）。
- **「改字不红」缺口确认**：仅 `memory.saved`/`evidence.registered` 两个文案双侧内容钉死；其余 15 键**单侧改内容不红**；backend 增/删键时 mobile 侧（仅计数断言）**不红**——双向漂移面均存在，预登记描述如实。
- **漂移风险评估**：当前低——表冻结 v1、卡面明文「扩展 = 契约变更」、改动必过审查；但长期无跨端单一真源仍是结构债。
- **建议**：后续卡做生成式单一真源——backend `experience_copy.py` 为源，`scripts/devtools/` 同步脚本渲染 Dart 常量 + 守卫比对（符合 REPOSITORY_STANDARDS devtools 位）；不阻塞本卡。

### ③ 失败事件不做 version 校验的口径 — **合理，接受**

不对称性方向正确：version 纪律的防御目标是「过期成功被当当前事实庆祝」（false success），失败是**已发生的权威事实**，version_conflict 文案本身即「对象已前进」的直陈；对失败做版本抑制反而可能吞掉用户必须知道的失败（更违背 MOTION/B05 失败模态纪律）。滥用面由三重既有机制 bounded：E2 互斥（失败永不混 committed 呈现）、event_id 去重（同失败只提示一次）、专用失败键（无成功视觉可能）。**判定：口径成立，预登记定性如实。**

### ④ replay 抑制会话级（重启后再响）的定性 — **如实，接受**

代码核实：`_seenEventIds` 为适配器实例内存集合，`reset()` 可清，App 重启即空——重启后同 event_id 再触发声/触属实，limitations #4 明文承认、未谎称跨会话持久。MOTION/B05 口径「恢复重放不重复音/震」指恢复流程内重放，本卡满足。跨会话持久去重需存储面（SharedPreferences/DB），未夹带属正确资源选择。**判定：定性如实。** 注记（N1）：F04 接线 + WS frame 落地时一并评估持久化必要性与 expires_at 面活了。

### ⑤ 「统一入口」闭合标准裁决请求 — **裁决：销账（适配器级闭合成立），附两项可追踪条件**

**独立裁决：F03 按「统一入口 = 适配器 + 消费语义 + 生产事件流」口径销账，不要求本卡内做单点屏幕接线增量。** 理由：

1. 卡面三条验收均为**管线行为性质**（无回执不成功/重播不重复/未知不绿），非「N 屏迁移」；三条已在适配器 + 徽章绑定级被可失败测试钉死。
2. MOTION「统一适配器」的最终态 = 屏幕逐面切换，其前置是**事件源**（WS `ExperienceEventFrame` proto 契约 commit）——按卡 path_policy「契约/迁移由单一 owner 单独合并」本就独立合并；在 frame 缺位下单点接线只能屏幕内造投影调用，反违 no-second-source 纪律。
3. 屏幕切换与 F04 mobile-shell 在航面强耦合，硬塞本卡会制造跨卡冲突面。
4. limitations #2 已如实声明「全部屏幕经适配器呈现」不可声明——无夸大。

**销账附条件（必须落账，非本审可自行闭合）**：
- (a) **WS frame proto 增量（`ExperienceEventFrame` oneof 挂 `WebSocketMessage`）当前只在 F03 limitations #1 与 tasks.json progress_note 声明，无任务面/协调态承接**——要求协调方将其登记进 fleet 可追踪面（后续卡或 HUMAN_INBOX），否则「单独移交」有悬空风险。本审不因该登记缺位降格 F03（禁触 proto 是本会话工程纪律，移交声明本身如实）。
- (b) F04 审查时必须核：屏幕切换经适配器、无第二发声/视觉路径、`replaySuppressed`/`presentUnknown` 语义不被绕。

## 四、复跑（审查者本机独立执行，全部通过）

| 项 | 命令要点 | 结果 |
|---|---|---|
| backend 全量 | `pytest`（17 新 + 6 文件回归 + 5 邻接文件） | **161 passed**（5:10s）＝ 17 新 + 144 回归 ✓ |
| mobile 全量 | `flutter test test/core/experience test/core/design test/app test/widget_test.dart` | **+217 ~1 All tests passed**＝ 18+160+39 ✓（~1 = widget_test 既有 skip） |
| 四棘轮守卫 | ui-tokens / typo-rhythm / spacing-rhythm / dl-spec | 四守卫 **PASS**（ratchet holds） |
| analyze | `flutter analyze --no-pub lib/core/experience test/core/experience` | **No issues found!** |
| ruff / black | F03 新增 3 + 改动 3 文件 | All checks passed / 3 files unchanged |
| 预登记①实测 | 一次性双路径身份测试（跑毕即删） | **passed**（`event_id_A == event_id_B`） |

环境注记：worktree `backend/.venv` 无 pytest（uv sync 因镜像源不可达），复跑使用主检出 `sparkle-cosmos/backend/.venv` 解释器 + worktree 代码（同一项目依赖面，纯 app 代码 diff，不影响结论）。

## 五、红线全量核 — **零触碰**

- **RF-06 冲突面**：`experience_readouts.py` 不在 diff ✓（B05 §7 理解条目面原样）；
- **五 Tab 路由**：mobile 改动全为新增文件（`lib/core/experience/` 2 + `test/core/experience/` 2），零既有文件修改，路由/壳未触 ✓；
- **proto 零触碰**：`proto/`、迁移、`*/gen/`、l10n、`.env` 均不在 diff ✓；`metrics.py`（D03/I04/I08 冲突面）不在 diff ✓；
- **WS frame 单独移交声明**：在案（limitations #1 + progress_note + diff 文档三处一致）——见 ⑤ 附条件 (a) 的登记要求；
- I07 hybrid-policy 锁面不越（未实现 mastery/deliverable，仅呈现纪律）✓；I1（事件无权限字段）结构保持 ✓；零模型调用、零 Mock 冒充 ✓。
- tasks.json 变更 = F03 状态机位（PENDING→in_progress/REVIEW_READY + evidence_summary/progress_note），符合卡制接力规范 ✓。

## 六、CHALLENGED / 勘误与建议（全部非阻塞）

- **C-1（勘误，需实现方落账）**：`run_manifest.json` command 3 拆分「action_command_service 32」**实为 29**（collect 实测 29；29+16+31+13+9=98 ✓）；`diff_or_evidence_only.md` 红线节「X-03 服务 32 测」同源；tasks.json `evidence_summary`「X-03 服务 32」同源。**聚合数（98 回归 / 144 回归 / 161 全量）经独立复跑核验为真**，误的只是单文件拆分数字。同文件「+31/-1 行」实为 `git diff --numstat` 实测 **+30/-1**（同类别小误）。请随二审落账时勘误。
- **R1（建议）**：WS frame proto 增量登记进 fleet 可追踪承接面（⑤ 附条件 a）。
- **R2（建议）**：copy 表生成式单一真源/守卫强化立后续卡（② 判词）。
- **N1（注记）**：mobile 路由顺序 replay 抑制先于 version 校验——首达即 unknown（断网）的事件，其后版本对上也不再庆祝（会话内保守不过庆）；保守方向正确，F04 接线时复核口径。
- **N2（注记）**：sweep 过期后用户再 approve → `not_pending` 事件与 sweep 的 `expired` 事件**不同 id**——语义正确（两个不同失败事实），非 dedupe 违例，登记备查。

## 七、结论

V4-F03 一审 **PASS**。三条验收可失败测试齐备且实跑通过、机制面（I2 双门/内容寻址身份/封闭路由/语义分层/unknown 唯一视觉路径）独立复核成立；C-1/C-2 真闭合；预登记①-⑤定性如实；红线零触碰。高风险卡等待第二位独立审查后，由集成 SHA 复验落 DONE_REVIEWED。

---
*wtF03R1 · 2026-09-28 · 审查用一次性测试已删除，工作树仅本 receipt 增量。*
