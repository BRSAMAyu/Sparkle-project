# V4-U02 · R1 独立审查 receipt（一审）

- 审查人：wtU02R1（未参与 U02 实现的独立会话）
- 日期：2026-09-29
- 审查对象：`agent/v4/u02` @ `4d23cb8a`（实现）+ `bc507e32`（证据），基线 `a592159f`
- 审查方式：只读审查 + 亲放变异/时序探针（用后全部还原，工作树已核干净）+ 亲跑测试/守卫/合并落差
- **裁决：FAIL（列阻断证据见 B-1/B-2；客户端结构与测试纪律本身扎实，返修面窄且已定位）**

---

## 0. 裁决摘要

三条验收按字面（客户端语义层）均被可失败测试真实钉住（亲放三枚探针全数转红，见 §2），呈现纪律（零 AppFeedback.success、回执驱动成功相）亲验成立。**但**：本卡目标「可读 action diff 和实际 committed 回执」的唯一创建调用携带服务端封闭词表外的 `source` 值，对真实后端**每次必 400**（B-1，本审查用本 worktree 后端代码直接探针证实）——diff→确认→回执链路在真实环境不可达；且实现自述 R1-C4 的「source=recovery_sheet 可审计」被证伪。另有同会话取消后重建提案的幂等键重放死端（B-2，B-1 修复后即活化）。高风险卡 + 核心链路端到端不通 → 不能通过。

## 1. 亲跑验证（全部本机复现）

| 项 | 命令（cwd） | 结果 |
|---|---|---|
| recovery 全套 | `flutter test test/features/recovery`（mobile） | +27 全绿（18 行为 + 2 证据 + 7 既有） |
| 受影响回归 | `flutter test test/features/recovery test/features/home test/features/memory test/features/task test/shared/widgets/action_proposal test/unit/chat_provider_test.dart test/unit/chat_notifier_stream_test.dart` | +391 全绿；另 `test/performance/widget_bench_test.dart` 隔离 9/9 绿 → 合计 400，与自述一致 |
| 静态分析 | `flutter analyze` | No issues found! |
| 治理守卫 | `bash scripts/run_all_rule_guards.sh`（仓库根） | all rule guards passed (88 rules) |
| l10n 再生 | `flutter gen-l10n`（mobile） | 再生后 `git status lib/l10n` 零漂移；arb 键集 diff：新增 42 值键 + 6 占位元数据、**0 删除**（zh/en 与基线同构纯增量） |
| 计数分解 | `grep -c "testWidgets("` | 18 + 2 = 20 ✓ |
| RF-06/路由/后端零触碰 | `git diff a592159f 4d23cb8a --stat -- <faces/routes/backend/proto>` | 全空 ✓ |
| 合并落差 | `git merge-tree $(git merge-base HEAD dc38df74) HEAD dc38df74` | 双侧改动 6 文件（l10n×5 + tasks.json），**0 冲突标记**；recovery 族与 main 侧（S02 心跳）零重叠 |
| 成功反模式 | grep AppFeedback/SnackBar/ScaffoldMessenger 于改动生产文件 | 仅注释命中，**零调用** ✓（CH-R1/F03 终结声明成立） |

证据五件套交叉核：5 态语义树与代码/文案逐字一致（`u02_committed` 含回执号 `r-20260929-u02` 且成功面唯一；`u02_conflict` 零成功视觉；`u02_abstain` 纠正输入在场）。

## 2. 预登记 R1-C1~C6 独立下判

- **C1 两写路径结构分离：成立**。`savePreference`（`recovery_calibration_provider.dart:285-314`）方法体仅 `apiClient.post(understandingSnapshotCorrections)`，无任何 repository/proposal 引用；反向 `buildAdjustment`/`confirmAdjustment` 只触 proposal 仓库，测试钉 `api.posts isEmpty`。**亲放变异探针**（在 `savePreference` 注入 `createAdjustmentProposal` 调用）→「保存偏好≠改任务」钉即红（+0 -1）。测试与结构双保险确认。
- **C2 回执门双条件：成立**。`_parseProjection`（:524-543）要求 `status==COMMITTED` **且** receipt 非空，否则 unknown。**亲放变异探针**（短路 receipt 检查只看 status）→「committed 但回执缺席→诚实 unknown」钉即红。
- **C3 abstain 恒可达：成立**。校准区在 `StuckJourneySheetBody.build` Column 尾部**无条件挂载**（sheet diff 可证，loading/error/ready 皆在场）；控制器不读 `payload` 决定渲染（journey 仅喂偏好 claim，null 安全）；abstain 载荷 + 旅程错误态两枚反例钉在套件内绿。
- **C4 客户端直连 X-03 非第二权威：架构上成立，事实自述证伪 → 见 B-1**。授权语义确在服务端（`CreateProposalRequest` 拒收客户端授权字段、`execute_if_authorized` 未用、`TASK_FIELD_WHITELIST`/`validate_subject` 均服务端），非第二权威；**但** `source: 'recovery_sheet'` 不在服务端封闭词表内（详见 B-1），R1-C4 预登记答案「source=recovery_sheet 可审计」不成立。
- **C5 409 取消竞态：成立**。`reAdjustAfterConflict` 取消失败留在 conflict 相（catch 分支 ：454-461）；双重落账由服务端结构性拦截：`validate_subject`（`task_commands.py:194-205`）approve 关键段内 `with_for_update` 重读 subject 比对版本 token（:119-124 TOCTOU 返修注记），stale 即 VersionConflictError→409。
- **C6 fake 契约真实性：部分成立**。响应侧投影逐字段对齐真实现（`proposal_projection` :603-634 的 proposal_id/status/diff/summary/receipt；`build_diff` :251-268 的 before/after/changed_fields；receipt 含 receipt_id）；请求侧契约**未核**——恰是 B-1/B-2 漏网之处（fake 不经 HTTP）。

## 3. 阻断证据

### B-1（阻断）`source: 'recovery_sheet'` 被服务端封闭词表拒绝——「仅本次」链路真实环境必 400

- 客户端：`action_proposal_repository.dart:33-46`（本卡新增）POST `/action-proposals` 携带 `'source': 'recovery_sheet'`；payload 钉测试将其钉死（`recovery_calibration_test.dart:581-591` 一带断言 payload 含该 source——修复时须同步改钉）。
- 服务端（本分支基线代码，本卡零触碰）：`backend/app/core/action_command.py:91-99` `ProposalSource` 封闭词表 = `{chat, task, aurora, system, api}`；`backend/app/services/action_command_service.py:148-149` `if source not in {s.value for s in ProposalSource}: raise ValueError("unknown proposal source ... (closed vocabulary)")`；`backend/app/api/v1/action_proposals.py:59` schema 仅 `max_length=16`（'recovery_sheet'=14 过 schema），ValueError → 路由 400（同文件 except ValueError 分支）。
- **亲放探针**（本 worktree 后端 venv 直调服务，source 检查先于任何 DB 访问）：
  ```
  ProposalSource values: ['chat', 'task', 'aurora', 'system', 'api']
  ValueError raised: unknown proposal source 'recovery_sheet' (closed vocabulary)
  ```
- 后果：真实环境中 `buildAdjustment` 每次收 400 → 走「网络失败」瞬态错误行（无假成功，此点诚实），但 diffReview/确认/回执/409 恢复全部不可达——卡目标（可读 action diff + 实际 committed 回执）端到端不成立。全套测试用 fake 仓库，请求侧契约不可见。
- 定性：实现自述「source=recovery_sheet 可审计」为不实声明（非假成功、非 Mock 冒充，属契约未核）；按 path_policy「契约由单一 owner 单独合并」，返修二选一：(a) 客户端改用词表内 source 并修正 payload 钉与证据自述；(b) 由 X-03 契约 owner 单独卡面登记 `recovery_sheet` 词表项后再合并本卡消费。R2 前必须落地其一。

### B-2（阻断，B-1 修复后即活化）同会话取消/重调后重建提案复用幂等键 → 服务端重放 CANCELLED 提案 → 静默死端

- 客户端幂等键 `'u02:$taskId:est:$minutes:$_createKeySalt'`（:336）：salt 为控制器构造时刻（每张 sheet 一次），同会话内「取消这份调整/不调了/409 按最新重调」后再建**同值**提案 = 同键。
- 服务端 `_resume_or_replay`（`action_command_service.py:674-710`）：existing 非 PENDING 或非 auto 直通时**原样重放**终态 proposal（`created=False`）。CANCELLED 投影返回后，客户端 `_Verdict.terminal` → `input` 相（:554-555）——用户被静默带回输入框，无 diff、无错误行、无任何如实反馈，且真实新建从未发生。
- 触发路径（同 sheet 会话内）：① diffReview「不调了」→ 重输同约束同分钟 → 再建；② 409 →「按最新状态重新调整」（显式取消）→ 步进回同值 → 再建。两者均为高概率路径。
- 现测试只钉「取消恰一次 + 零新增 create」，**未覆盖取消后再次 create**——反例缺位。返修要求：终态后重建须换键（如 salt 并入代数/时间片）或投影 status 非 PENDING 时如实呈现，并补「取消后重建得到可用 diff」正测一枚。

## 4. 非阻断发现（R2/返修随带）

- N-1 l10n 计数自述不精确：证据称「45 新键」，实测 arb 新增 **42 值键 + 6 占位元数据 = 48 条目**（0 删除，纯增量成立；zh/en 值键同步）。纯记账误差。
- N-2 输入长度无客户端上限 vs 服务端约束（summary≤2000 / correction≤1000 / claim≤600）：超长输入 4xx 落入瞬态错误行（诚实不崩），建议随 B-1 返修加 maxLength 或截断说明。
- N-3 非 409 的 4xx（如 B-1 的 400）与网络失败共用「没有连上」文案：永久性失败呈现为可重试瞬态，表述不精确（无假成功，不阻断）。
- N-4 全量三次「失败集不重合」自述本审查未复跑全量（三次整跑成本高）；但受影响面 400 + bench 隔离 9/9 + analyze + 88 守卫亲跑全绿，且失败归因（widget_bench 16ms 负载抖动）与隔离复跑证据自洽，采信为合理陈述不作阻断。

## 5. 验收三条逐条对证据裁决

1. 「三宿主同语义，abstain仍可输入纠正」——**客户端层面成立**（3 正测钉同组件/同标题/同输入键 + abstain/错误态两反例钉；语义树 `u02_abstain` 逐字可查）。
2. 「保存偏好≠改任务；取消不改变原行动」——**成立**（恰一次 POST routing_policy + proposal 三调用全空 + 成功徽章结构性缺席；取消两拍零写；C1 探针证明结构分离非仅测试守门）。
3. 「unknown/版本冲突可恢复，回执之后才成功反馈」——**客户端语义成立**（时序钉经亲放探针验证真实咬合；COMMITTED 无回执→unknown fail-closed；409 双出口）。**但**整链对真实后端不可达（B-1），故本卡整体不通过。

## 6. 返修清单（最小面）

1. B-1：source 词表二选一落地（客户端改值 + 改 payload 钉 + 修正 diff_or_evidence_only.md/review_receipt.json R1-C4 自述；或 X-03 契约 owner 单独登记词表项）。
2. B-2：终态后重建换键或终态如实呈现 + 补「取消后重建」正测。
3. N-1 证据计数勘误（42/48）随返修 commit 一并更正。
4. 探针残留：无（三枚探针已 `git checkout --` 还原，写入本 receipt 前 `git status` 干净）。

——以上每条结论均给出文件行号锚或可复现命令。本 receipt 不动实现、不 push。
