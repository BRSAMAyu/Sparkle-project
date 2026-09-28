# V4-F03 · 独立审查 receipt（二审 · wtF03R2）

- **审查者**：wtF03R2（独立会话，未参与 F03 实现与一审）
- **审查对象**：分支 `agent/v4/f03`，实现 commit `13ba9e76`，一审 receipt commit `86e2189d`（读取作输入，独立下判）
- **日期**：2026-09-28（本机 macOS arm64；纯 Python/Dart 变更，无 cgo/平台面）
- **卡风险级**：high（双审）——本 receipt 为第二审，靶面与一审互补：**对抗面 + 跨端一致性 + 随账勘误**

---

## 总裁决：**PASS**（二审通过；CHALLENGED 4 项全部非阻塞，见 §六）

三条卡验收经对抗面重压后全部成立；一审结论无推翻项。C-1 遗留勘误独立确认并随账；跨端 17 键逐字亲比一致并给出可落地的 sha256 守卫裁决；memory 域路由、unknown 断网面、D01 C-1/C-2 挂点逐一源码亲核 + 亲测；复跑全绿。`review_receipt.json` 仍留 PENDING，由实现方/协调方按双审流程落账（本审不改一审与实现自证文件）。

---

## 一、靶 1｜一审 C-1 勘误随账确认（独立复核，不动一审 receipt）

| 一审 C-1 项 | 实现自报 | 本审独立实测 | 判定 |
|---|---|---|---|
| X-03 服务测试数 | 「32 测」（run_manifest command 3 / diff 文档 / tasks.json evidence_summary） | `pytest --collect-only tests/unit/test_action_command_service.py` → **29 collected** | **勘误确认：29** |
| 改动 3 文件行数 | 「+31/-1」（diff_or_evidence_only.md） | `git diff --numstat 71553984..13ba9e76`：action_proposals +8、action_command_service +11、intervention_record_service +11/-1 → **+30/-1** | **勘误确认：+30/-1** |
| 聚合数 | 98 回归 / 144 回归 / 161 全量 | 本审复跑 161 passed（17+144；144 = 29+16+31+13+9+46） | **为真**（误的只是拆分数） |

**随账新增小误（同类别，C-1'）**：`run_manifest.json` locks.note 与 commit message 均写 `action_command_service.py +12`，numstat 实测 **+11**。数字类、非行为性，随本 receipt 记录，请实现方销账落账时一并勘误；本审不代改实现自证文件。

## 二、靶 2｜对抗面亲测（一次性测试亲跑，跑毕即删未入库）

自写 backend 6 测 + mobile 10 测（`pytest` via 主检出 venv 解释器 + worktree 代码；`flutter test`），**16/16 全过**：

### a) 重放风暴（同 event 快速 10 次投递）
- **backend**：同一 committed 回执 10 次快速重放（issued_at 逐次递增）→ 10 次 `event_id` 恒一、`dedupe_key` 恒一、`event_id == derive_experience_event_id(dedupe_key)` 恒成立；FakeEventBus 收到 10 次发布（发布面不去重——去重责任在消费方，与 B05 §3 口径一致，设计如此）。
- **mobile**：同 event 连投 10 次并每次 `emitSensory` → sink 调用恒 `['success']` 一次；末次 action=`replaySuppressed`、`celebrates=false`、copy 仍「任务已更新」（文本状态仍恢复）。风暴内混入异 id（task/goal/plan 各一 + 重播）→ 三个异 id 各庆祝一次、重播被吞（去重键粒度 = event_id，正确）。

### b) 乱序（成功先到、回执后到/永不到）
- **回执永不到**：status=COMMITTED 而 receipt 缺失 → `no_authoritative_receipt` 拒绝——成功事件**不存在**（不是延迟）；mobile 侧解析 E1 门同构。结构性成立。
- **先 PENDING 后回执**：先投拒绝（`not_terminal_no_receipt`），回执到达后投影成立，身份与投递顺序无关（内容寻址）；乱序重投恒同 id。
- **mobile 乱序**：成功事件先到而当前版本未知（断网）→ `presentUnknown`（unknown 徽章、零声/触）；版本后对上再投同 id → `replaySuppressed`（**不补庆祝**，copy 仍恢复）——保守方向，与一审 N1 一致，亲测确认。乱序不丢失败面：unknown 前后的失败事件（异 id）照常 `presentFailure` + 警示触一次。

### c) 版本回退攻击（旧 version 事件在新对象上投递）
- **backend**：对象已前进后重放旧 committed 行 → 事件恒携带回执链旧 token（backend 锚定回执链，不持有"当前对象版本"读数——当前版本判定权在消费方，分层正确）；**篡改 version token 即改 dedupe 内容 → 新 id**，无法冒充旧身份（内容寻址抗改票）。
- **mobile**：旧 version 事件砸在 v9 对象上 → `staleVersionSuppressed`、零庆祝零感官；同 id 旧事件在版本前进后重投 → replay 抑制先于 version 校验（N1 亲测复核）。
- **信任边界（亲测文档化，非缺陷）**：换新 id + 伪称当前 version 的伪造事件会被 `presentSuccess`——mobile 不验内容寻址签名（derive 函数在 backend 侧），事件真实性由认证传输面承担。**version 校验防的是过期重放，不是伪造**。当前事件仅源于本方 backend 且 WS frame 未落，风险不成立；登记 N3（§六）供 F04 接线时守门。

### 附带对抗
- **memory 恶意模态**：memory 事件恶意携带 `[visual,audio,haptic]` → mobile 路由仍剥离为 `presentHighlight`（高亮+轻触一次、零成功声/触、`celebrates=false`）——subject 分层在模态字段之上，纵深成立；backend 侧 memory committed 投影实测恒 `[visual]` + `memory.saved`。
- **表外 copyKey**：`mastery.unlocked` → copy 空串（不拼自由文本，呈现层无词可拼）。
- **N2 复核**：sweep 的 `expired` 事件与用户再 approve 的 `not_pending` 事件实测异 id——两个不同失败事实，非 dedupe 违例（一审 N2 定性确认）。

## 三、靶 3｜跨端 copy 表 17 键逐字亲比 + 守卫裁决

- 程序化逐键比对（backend 直接 import `EXPERIENCE_COPY_TABLE`；mobile 正则解析 `kExperienceCopyTable` 字面量）：**键集相等（17/17）、文案逐字相等、无重复键、声明顺序一致**；`memory.saved`=「记忆已保存」、`evidence.registered`=「证据已登记」双侧钉死键一致。
- 双侧 canonical JSON（`sort_keys` + 紧凑分隔符）sha256 **恒同**：
  `949757daf0b81e7c31bad47f5ad4a47d6aa559270fd614ecafe6bf431862b200`
- **漂移面确认**（与一审②一致）：17 键中 15 键单侧改内容不红；backend 增/删键时 mobile 仅键数断言可红（单向部分红）。
- **裁决（靶面要求）：守卫增量值得落，推荐最小形态 = 双侧 sha256 互钉**——每侧测试固化对侧表 canonical sha256（即上行哈希值，可直接粘贴），任何单侧内容/键集改动即双侧红；契约性改文案时同步更新两常量（同 repo，成本 ≈ 10 行）。**非阻塞**：当前表冻结 v1 + 扩展=契约变更 + 双审在途，漂移风险有界；建议随本分支销账后小增量提交落地，或并入一审 R2 的后续卡作为生成式单一真源落地前的过渡守卫。本审不代落实现代码。

## 四、靶 4/5｜memory 域路由与 unknown/断网面

- **memory 恒 [visual] 声明**：backend 投影亲测成立（§二附带）；mobile 构造 memory 事件走路由亲测成立（`presentHighlight`、无成功徽章/声/触）。`EXPERIENCE_RECEIPT_REF_SCHEMES` 六元封闭集亲核确无 `memory://`——memory 生产回执暂不可投影（limitations #4 如实）；mobile 路由已就绪，scheme bump 即插即用。
- **evidence.registered「证据已登记」**：双侧逐字一致（§三逐比确认）+ backend `outcome://`+progress_delta 路由亲测 + mobile 中性呈现亲测（`presentNeutral`、零庆祝）。「登记 ≠ 精通」双侧成立。
- **断网 unknown 数据可达性**：适配器 import 面亲核（foundation / pixel_state / experience_event / sensory_feedback_service——后者为本地 haptic/audio，无网络面）；`resolveUnknownDisplayState()` 纯本地、`present()` 在 token=null 时纯本地决策，unknown 徽章 + 文案 + 读屏标签渲染不依赖网络可达——声明成立（真机听感/震感仍 DEVICE_UNVERIFIED，limitations #6 口径）。
- **重试语义**：恢复后同 event 重投 → `replaySuppressed`（copy 恢复、不补庆祝）——会话内保守不双响；`reset()` 可清。跨会话持久去重未夹带（limitations #4/#7 与一审④口径如实）。

## 五、靶 6/7｜D01 C-1/C-2 挂点源码亲核 + 复跑

### 三挂点生产可达性（worktree 源码行号亲核，非仅 diff）
1. **approve 成功链**：`action_command_service.py:386` —— `db.commit()`+`refresh()` 之后、`return ProposalMutationResult` 之前，`project_action_receipt_safe(self.db, None, proposal)`（真实 commit 链路）；
2. **过期清扫**：`action_command_service.py:531` —— `expire_stale_proposals` 批量 `_terminalize`+commit 后逐行挂点；
3. **API 错误面**：`action_proposals.py:248` —— `except ActionCommandError` 内 `project_action_error_by_id_safe`，HTTP 映射原样进行。
   `cancel_proposal`（:260）/`reject_proposal`（:281）亲核**无挂点**（契约 §6 用户亲自操作零事件，limitations #8 如实）。三挂点 `event_bus` 实参均 `None`（投影成立、发布跳过——与 D01 生产 mark_seen 形态同构，limitations #3 如实）。INVALID_COMMAND fail-loud：直呼路径 `pytest.raises` + 韧性壳转 warning+None（`swallowed is None` 断言）双层钉住，fail-loud 语义未被壳吞。
4. **C-2**：`intervention_record_service.py:173-175` —— 捕获 `record_rendered_exposure_safe` 返回值，`not projected` → 稳定前缀 `experience_presentation.degraded` warning（可 grep）；测试以真实生命周期 + 删回执行断言双命中。

### 复跑（本机独立执行，全部通过）

| 项 | 结果 |
|---|---|
| backend（17 新 + 6 回归文件 + 5 邻接文件，`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`） | **161 passed**（261.22s）＝ 17 新 + 144 回归 ✓ |
| mobile（`flutter test test/core/experience test/core/design test/app test/widget_test.dart`） | **+217 ~1 All tests passed**（exit 0）＝ 18+160+39 ✓（~1 = widget_test 既有 skip） |
| 四棘轮守卫（ui-tokens / typo-rhythm / spacing-rhythm / dl-spec） | 四守卫 **PASS**（ratchet holds） |
| ruff / black（F03 新增 3 + 改动 3 文件） | All checks passed / 3 files unchanged |
| `flutter analyze --no-pub lib/core/experience test/core/experience` | **No issues found!**（本审一次性对抗文件所报 9 条 info 随文件删除清零） |
| 对抗面一次性测试 | backend 6/6 + mobile 10/10（跑毕即删，工作树仅本 receipt 增量） |

环境注记：worktree `.venv` 无 pytest（与一审同），复跑用主检出 `sparkle-cosmos/backend/.venv` 解释器 + worktree 代码；mobile `pub get` 已在实现期还原 l10n，本审未触生成文件（`git status` 干净）。

## 六、CHALLENGED（4 项，全部非阻塞）

- **CH-1（勘误随账）**：靶 1 三项确认 + 新增 C-1'（`action_command_service.py +12` 实为 +11，run_manifest locks.note 与 commit message 同源）。请实现方销账落账时勘误，本审不代改。
- **CH-2（一审 R1 仍悬空）**：WS frame proto 增量（`ExperienceEventFrame`）经全量 grep 仍只在 F03 limitations #1 / progress_note / 一审 receipt 声明，tasks.json 无任务面承接、HUMAN_INBOX 无条目——**登记要求维持一审⑤(a)原判，移交协调方**；不因登记缺位降格本卡（与一审同口径）。
- **CH-3（守卫建议，靶 3 裁决）**：双侧 sha256 互钉测试值得落（哈希值已给出，见 §三），建议销账后小增量或并入 R2 后续卡；非阻塞。
- **CH-4（注记 N3，信任边界）**：mobile 适配器不验事件内容寻址签名——version 校验防过期重放、不防伪造（伪造面由认证传输承担，亲测文档化见 §二c）。WS frame 落地与 F04 接线时必须守门：事件只经认证 WS 通道、不新增未认证投递路径。

## 七、limitations 八条 + 一审移交项定性复核

- **八条逐核**：#1 WS frame 未落 proto（diff 零 proto 面）✓；#2 无屏幕消费方（grep 全库仅自身文件+测试）✓；#3 挂点 event_bus=None（源码亲核）✓；#4 无 memory:// scheme（封闭集亲核）✓；#5 create 型 unanchorable（有测试）✓；#6 声/触决策面（记录型 sink）✓；#7 中文单语 ✓；#8 仅 approve 错误面挂点（cancel/reject 亲核无挂点）✓。**八条如实，无夸大声明**。
- **R1（WS frame 登记）**：仍开放 → CH-2 移交协调方。
- **R2（copy 单一真源）**：本审 §三 给出过渡形态裁决 → CH-3。
- **N1（replay 先于 version 校验）**：亲测复核（§二b/c），保守方向确认；F04 接线时复核口径。
- **N2（not_pending/expired 异 id）**：backend 亲测复核成立（§二附带）。

## 八、结论

V4-F03 二审 **PASS**。三条验收在对抗面（重放风暴/乱序/版本回退）重压下全部成立；跨端 17 键逐字一致；memory 域路由、unknown 断网面、C-1/C-2 挂点生产可达性逐一亲核亲测成立；复跑全绿（backend 161 / mobile 217 / 四棘轮 / lint / analyze）；limitations 八条如实。C-1 勘误随账确认（含新发现 C-1'）；R1 登记仍悬空移交协调方。高风险卡双审面已齐，建议按流程由集成 SHA 复验落 DONE_REVIEWED；`review_receipt.json` 落账时请并入本 receipt §六 CH-1 勘误与 CH-2 移交项。

---
*wtF03R2 · 2026-09-28 · 审查用一次性测试（backend 6 + mobile 10）已删除，工作树仅本 receipt 增量；未 push。*
