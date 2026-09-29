# V4-U02 · R2 独立审查 receipt（二审 + 一审 FAIL 返修复审）

- 审查人：wtU02R2（未参与 U02 实现、一审与返修的独立会话）
- 日期：2026-09-29
- 审查对象：`agent/v4/u02` @ `1384a1fe`（返修）+ `f4a1b30b`（注记），覆盖一审对象 `4d23cb8a`+`bc507e32` 与一审 receipt `10acec52`（FAIL：B-1/B-2）
- 审查方式：只读审查 + 亲放独立端到端探针（后端直调，用后即删，`git status` 核干净）+ 亲放三枚 mutation 探针（逐一还原）+ 亲跑全部回归数字与合并落差
- **裁决：PASS（一审 B-1/B-2 均彻底关闭；三条验收端到端成立；无新增阻断，3 条非阻断观察见 §5）**

---

## 0. 裁决摘要

一审两阻断的返修方向正确、落地彻底：B-1 以「客户端取词表内值 + 词表镜像常量 + 穿透 fake 的真仓库契约测试」关闭，本审查以**独立后端直调探针**证实 `source='task'` 全链路真通（创建→权威 diff→同键恰一次→approve 落账→任务字段真实变更→receipt 本体），且 `recovery_sheet` 词表外 400 面复现（服务端行为与一审诊断一致）；B-2 以「每次提案意图一盐（显式取消成功后轮换）+ buildAdjustment 终态重放 fail-closed 守卫」双防线关闭，取消后重建正测、终态反钉、失败重试同键三测齐备且 mutation 亲证咬合。一审确认的立面（回执门时序钉/两写分离/零 toast）经返修后复放探针确认未被破坏。全部回归数字亲跑复核，合并落差结构化核零冲突。

## 1. B-1 返修复核（首靶）——**彻底关闭**

### 1.1 词表镜像常量与真源一致性（亲验逐值比对）

| 镜像（客户端） | 真源（backend `app/core/action_command.py`） | 判定 |
|---|---|---|
| `kProposalSourceVocabularyMirror` = {chat, task, aurora, system, api}（`action_proposal_repository.dart:22-28`） | `ProposalSource` :91-99 同 5 值 | **逐值一致** |
| `kActionCommandTypeVocabularyMirror` = {task.update_status, task.update_fields, task.create_batch}（:11-15） | `ActionCommandType` :101-111 同 3 值 | **逐值一致** |
| `_kTerminalProposalStatuses` = {CANCELLED, REJECTED, EXPIRED}（`recovery_calibration_provider.dart:71-75`） | `ProposalStatus` :65-76 终态封闭（PENDING 唯一非终态；COMMITTED 走回执门） | **子集正确**（COMMITTED/PENDING 恰当排除） |

实际发送值 `_kAdjustmentProposalSource = 'task'`（:32）经 payload 钉（`recovery_calibration_test.dart:1080`）与路由 schema `max_length=16` 钉（:1088）双钉。

### 1.2 source='task' 端到端探针（R2 独立亲放，非转述返修记录）

本机 sqlite 测试库直调 `ActionCommandService`（wtU02 backend 代码 = 本分支，backend 零 diff；venv 复用主检出；临时探针文件用后已删，`git status` 干净）。**4/4 过**：

1. 词表实测：`ProposalSource values: ['chat', 'task', 'aurora', 'system', 'api']`（5 值）；
2. **负探针**（一审 400 面复现）：`source='recovery_sheet'` → `ValueError: unknown proposal source 'recovery_sheet' (closed vocabulary)`——证实一审诊断与返修必要性；
3. **正探针**（全链路）：`source='task'` + `task.update_fields{estimated_minutes: 40→15}` → `created=True` / `status=PENDING` / `source` 落库 `task` / **服务端权威 diff**（`changed_fields=['estimated_minutes']`，before 30→after 15）；**同键重放** `created=False` 同提案 id（X-09 恰一次）；`approve` → `COMMITTED` + 完整 receipt 本体（`receipt_id`/`diff`/`effects`/`version_token_after`）+ **`task.estimated_minutes` 真实变为 15**。
4. **B-2 服务端语义探针**（见 §2.4）。

结论：卡目标「可读 action diff + 实际 committed 回执」对真实后端**端到端可达**（一审 B-1 的「每次必 400」不复存在）。

### 1.3 镜像常量「防再犯」机制裁决：**活钉**（对 B-1 同型回归），残余缺口已声明且被兜底

- **客户端自伤路径（B-1 原型）→ 活钉**：mutation 亲放——`_kAdjustmentProposalSource` 拨回 `'recovery_sheet'` → 契约穿透测红（`recovery_calibration_test.dart:1080` source 钉）→ 还原绿。任何人再引入词表外值，测试必红。
- **服务端词表 bump 而镜像不随动**：无害静默——客户端只消费 `'task'`（服务端 enum 稳定值），镜像缺新值不产生任何错误行为；未来开发者在镜像外取服务端新值时 `contains` 断言红，**强制一次显式的镜像同步决策**（活钉行为而非死键）。
- **残余缺口（非阻断）**：镜像与真源无跨仓自动同步测试；「镜像与 source 同时改坏」（镜像内私加服务端没有的值）客户端测试不可见。兜底：镜像注释明示冻结纪律与 X-03 owner 归属 + 服务端 enum 单一真源 + X-04 e2e（`source=ProposalSource.TASK` 全链，`test_x04_action_flow.py:438-450`）+ 本次独立探针。
- **顺带发现（X-03 owner 的一行加固建议，非本卡义务）**：服务端 `test_vocabularies_frozen`（`test_action_command_service.py:627-639`）钉了 ProposalStatus/ActionCommandType/TERMINAL_REASON 但**未含 ProposalSource**——建议 owner 补一行冻结断言，使服务端词表 bump 也必过冻结测。

## 2. B-2 返修复核——**彻底关闭**

### 2.1 取消后重建正测（亲跑绿）

「取消后重建同值提案——新键、新对照可用、确认落账走出死端」（`recovery_calibration_test.dart:1126-1204`）：fake opt-in 服务端幂等镜像（同键 create 原样重放首响 + cancel 终态封闭），断言链 = 第二次 create 的幂等键 ≠ 第一次（:1187-1191）∧ 新对照 `40 → 15` 可渲染 ∧ 确认后回执 `r-after-cancel` 到场走出死端。旧实现（同会话同键）在此必红。

### 2.2 终态重放守卫反钉（亲跑绿）

「create 重放命中终态投影 → 不渲染死对照，如实报错留在调整相」（:1206-1240）：CANCELLED 投影下死对照 findsNothing + 成功视觉三重 findsNothing + `没有连上` 如实一行在场 + 停留调整相（输入不清）+ 确认钮结构性缺席。

### 2.3 失败重试同键（X-09 恰一次不退化，亲跑绿）

「创建失败后的重试复用同键」（:1242-1284）：网络失败 → 重试 `idempotency_key[1] == idempotency_key[0]`——换键只发生在终态后，重试语义未受伤。

### 2.4 服务端侧边界探针（R2 独立亲放）

cancel（终态 user_cancelled）→ **同键**重建：服务端原样重放 CANCELLED、`created=False`——死端语义在服务端侧复现（客户端守卫正是防御此面）；**换键**重建：`created=True` 全新 PENDING；连续 **3 轮 cancel→换键循环** 全部真新建（多次取消循环边界覆盖；409 后重调链与之同构：`reAdjustAfterConflict` 取消成功才换键，取消失败留 conflict 相不换键——重试 cancel 复用 proposalId 基 cancel 键，与 create 盐无关，安全）。

### 2.5 mutation 亲放

注释 `cancelAdjustment` 内 `_rotateCreateKeySalt()` → 正测红，实捕 `Expected: not 'u02:t1:est:15:1790641542115356' / Actual: 'u02:t1:est:15:1790641542115356'`（同键复用被键差异断言咬住）→ 还原绿。防线纵深：即便未来某路径漏 rotate，`buildAdjustment` 终态守卫（provider :367-375）在 create 返回侧兜底（换键 + 如实报错，不渲染死对照）。

## 3. 一审 FAIL 两阻断消解判定（含边界）

- **B-1：彻底关闭**。词表内值 + 镜像一致 + 穿透测 + 独立端到端探针全通（§1）。边界：payload 钉同层迁移到真仓库 HTTP 边界（widget 级 fake 钉不再覆盖 source——契约归位到能看见 HTTP 的层，正确）。
- **B-2：彻底关闭**。双防线（意图盐轮换 + 终态重放守卫）+ 三测（正/反/恰一次）+ mutation 亲证 + 服务端边界探针（§2）。边界：多次取消循环 ✓；409 取消失败不换键（cancel 键 proposalId 基，重试安全）✓；漏 rotate 时守卫兜底 ✓。

## 4. 立面维持 + 回归与数字（全部亲跑）

| 项 | 命令（cwd） | 结果 |
|---|---|---|
| recovery 全套（含 B-1 穿透 2 + B-2 重建 3 新测） | `flutter test test/features/recovery`（mobile） | **+32 全绿**（一审 27 → 返修 32，增量恰为 +5） |
| 受影响面 | `flutter test test/features/recovery test/features/home test/features/memory test/features/task test/shared/widgets/action_proposal test/unit/chat_provider_test.dart test/unit/chat_notifier_stream_test.dart` | **+396 全绿**；`test/performance/widget_bench_test.dart` 隔离 **9/9** 绿 → 合计 405（一审 391+9=400 → +5 一致） |
| 静态分析 | `flutter analyze` | No issues found! |
| X-03 契约测（U14 面） | `pytest tests/unit/test_action_command_service.py tests/unit/test_action_proposals_api.py`（backend） | **45/45**，零回退 |
| 治理守卫 | `bash scripts/run_all_rule_guards.sh`（仓库根） | **all rule guards passed (88 rules)** |
| N-1 计数勘误核 | arb 键集 diff vs `a592159f` | 每侧 **+48 条目 = 42 值键 + 6 占位元数据，0 删除**，zh/en 同构——勘误准确（前称 45 已在证据三处更正） |
| 分支零越界 | `git diff a592159f HEAD --stat -- backend/ gateway/ proto/ …routes` | **全空**（30 文件全在 recovery/task 仓库面 + l10n + 测试 + 证据；RF-06 三面零触碰沿袭） |
| 零 toast | grep AppFeedback/SnackBar/ScaffoldMessenger 于改动生产文件 | 零代码调用（仅注释提及）✓ |
| 合并落差 vs `f59ffe56` | `git merge-tree --write-tree HEAD f59ffe56` | **NO-CONFLICT**（注：三段式 merge-tree 输出中 2 处 `<<<<<<<` 字样为证据 md 引用的 grep 命令文本，非冲突 hunk；6 个双侧共touch 文件逐文件核 0 真冲突；双侧交集仅 l10n×5 + tasks.json，recovery 族与 main 侧零交集） |
| 合并落差 vs `origin/main`（c5978b29） | `git merge-tree --write-tree HEAD origin/main` | **NO-CONFLICT** |
| 立面探针复放 | 短路 `_parseProjection` 回执检查（一审 C2 同法） | 「committed 但回执缺席 → 诚实 unknown」反例**红**→ 还原绿——返修未破坏回执门；两写分离/时序钉在 32 绿套件内 |

证据五件套：5 态语义树 spot 复核（`u02_committed` 含回执号 `r-20260929-u02`；`u02_conflict` 零成功视觉命中 0）；UI 渲染面返修零变更，截图/语义树继续有效。`review_receipt.json` R1-C4 证伪自述已如实更正（【一审 B-1 证伪并返修】），`limitations.md` 盐语义更新，一审 receipt 未动——返修纪律合格。

## 5. 非阻断观察（登记不阻断）

- **O-1** `buildAdjustment` 若 create 重放命中 **COMMITTED** 投影（不在终态守卫词表内）会进 diffReview 渲染旧 diff。实际不可达：committed 后本控制器无回调整相入口，重开 sheet 即新控制器新盐；且该路径下 approve 走服务端幂等重放返还原 receipt，无双写无假成功。留观即可。
- **O-2** 服务端 `test_vocabularies_frozen` 未含 `ProposalSource` 冻结断言（§1.3）——建议 X-03 契约 owner 一行补钉，不属本卡。
- **O-3** 词表镜像与真源无跨仓自动同步（§1.3 残余缺口）——由活钉 contains 断言 + 单一消费值 `'task'` + X-04 e2e 兜底，可接受。

## 6. 验收三条（R2 终审）

1. 「三宿主同语义，abstain 仍可输入纠正」——成立（3 正测 + 2 反例钉，32 绿内）。
2. 「保存偏好≠改任务；取消不改变原行动」——成立（结构分离 + 零 toast + 取消两拍零写）。
3. 「unknown/版本冲突可恢复，回执之后才成功反馈」——**端到端成立**（一审「客户端语义成立但整链不可达」的保留已消解：source='task' 独立探针证实创建→diff→确认→落账→回执全链真通；409/unknown 出口与回执门经 mutation 亲证）。

——以上每条结论均给出文件行号锚或可复现命令。所有探针（后端直调 pytest ×1 文件、mutation ×3）用后已删/还原，写入本 receipt 前 `git status` 干净。本 receipt 不动实现、不 push。
