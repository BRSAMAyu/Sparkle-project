# W558 本地集成栈独立审计报告（第一轮·猎缺）

- 审查者：wt558（双轮审查机制·第一轮）；日期 2026-09-27
- 审查对象：主仓 `origin/main..HEAD` 本地未推 commit 集 64 个（merge-base = origin/main HEAD `cfaefe63`，栈顶工作树基线 `cbba2133`，其后 3 个为 docs(fleet) 协调提交）
- 方法：只读审计，零产品码改动；全量 diff 通览 + 逐面抽查 + 守卫实跑
- 量级：165 文件 +5078/−6917；非 docs/v3 代码提交 25 个、代码文件 162 个；多卡触碰文件 16 个

## 面一：跨卡交互抽查（5 对深核，全部自洽）

同文件被 ≥2 卡触碰的 16 个文件中取 5 组最可疑对，做逻辑面（非 textual）复核：

1. **`backend/app/orchestration/persistence_layer.py`（wt543 FIX-264 × wt544 FIX-258）**：f885ccb4 在 `_notify_pending_milestone_proposals`（现 :310-335）做 proto metadata 全值 `str()` 缺省；52fbed29 在 `_persist_assistant_message`（现 :89-100）置 `origin=MessageOrigin.DEMO/LLM`。两改动区域不相交、语义独立；写侧 origin 判据（落库时刻 `llm_service.demo_mode`）与读侧过滤判据同源，无矛盾。**自洽**。
2. **`backend/app/services/memory_inferred_write_lane.py`（wt536 mypy 批四 b53d0098 × wt544 FIX-258）**：demo 过滤位于 `process_chat_turn`（:261）入口 :279-286 单点；`enqueue_from_chat_turn`（:186）与 `enqueue_from_session`（:213）均经 `_run_background`（:240-258）汇入该入口，无旁路。「全部生产调用方汇入」声明与代码结构核实一致。**自洽**。
3. **`backend/app/services/guest_seed_service.py`（wt537 FIX-257 2b32d728 × wt544 FIX-258）**：257 的转正清洗作用于统计四表（`_cleanup_guest_seed_statistics` :3903 + `_SEED_NODE_MASTERY_SIGNATURES` 指纹 :1646，宁漏勿误删方向）；258 的 guest 种子聊天行置 `origin='demo'`（:3854-3856）且行内注明「内容保留按 257 裁决」。两卡对同一批种子数据采取互补处置（统计清洗/聊天标记保留），互相引用口径一致。**自洽**。
4. **`mobile/lib/shared/entities/achievement_model.dart` + `.g.dart`（wt539 FIX-259 × wt542 FIX-260）**：合并态 AchievementType 含 planning+unknown、StreakDayStatus 含 weak+unknown（:24-97）；`.g.dart` 枚举 map 与 `$enumDecode unknownValue` 兜底逐值同步（photon_model.g.dart、community_model.g.dart 同族核验，均为规范生成器输出形态，见面三）。**自洽**。
5. **`mobile/lib/l10n/` 四向（l10n 批五 764d5ce7 × 批六 c2129226 × FIX-259 786e2a4f × FIX-269/270/271 86900310）**：HEAD 处 en/zh arb 10129 键零差、`app_localizations{,_en,_zh}.dart` getter 8740 三文件精确一致（含枚举修复新增键）。arb 键 10129 对 gen getter 8740 的 1389 差为**基线既有**（merge-base 为 1472，本栈净收敛 −83，方向与 FIX-210 死键收割一致），非本栈引入。**自洽**。
6. 附核两处：`backend/app/services/achievement_engine.py`（wt539 SAVEPOINT × wt547 mypy 批五）合并态 `begin_nested` 与 Coroutine 契约收紧互不干扰、`stmt_sqlite` 命名一致（:302-307）；gateway `schema.sql`/`models.go`（FIX-258 origin 列 :1760 / Origin 字段 :2579 × FIX-259 StreakdaystatusWeak :1392）两卡增量并存，与迁移 `f258_20260925`、`wt539_20260926` 对应。**自洽**。
7. 卡面提及的「BaseTool locale 参数 × demo origin 写侧」：locale 契约落点是 `executor.py:1008` `_accepts_kwarg(tool.execute, "locale")` 探测后传参（兼容未声明工具），18 个 tool execute 签名带 `locale: str = "en"`（backend/app/tools/）；与 demo origin 写侧无共享文件、无交互面。**无交互风险**。

## 面二：台账完整性

- **FIXED@sha 存在性：134/134 全部真实存在**（`git cat-file -t` 逐个核验，含本栈新引用 b051ce99/934b076b/63ebb36b/37f1d69a 等）。
- **编号占用**：行级最大号 **V3-FIX-274**，275 起空闲（grep 验证 275/276 零占用）。
- **吞行/粘连残留（真问题，基线既有）**：4 行各粘连 2 个完整行——:171（201+179）、:176（214+179）、:191（239+221）、:192（220+231）；连同 :203/204 的 **V3-FIX-233 双行**（陈旧 OPEN 行 + 权威 FIXED@5caa5355 行并存），合计重号 179×3、221×2、233×2；**231 仅以粘连体存在**（行首锚定解析会漏计）。行首锚定 vs 全文含粘连体行首数 193 vs 196。**全部 4 处粘连与 233 双行在 origin/main 基线逐字节同在（预存在，非本栈引入）**；wt551 的 `scripts/devtools/ledger_union_merge.py`（FIX-268）固化了「不再产生」的根修，但**未回扫修复存量**。粘连还造成注记错位：232→239 重编注记落在 221 行单元格内（应属 239 行）。
- **表结构缺陷（真问题，本栈新增）**：本栈新增 12 行（263-274）中 **8 行管道数错**——263=11 管（多 3）、266/267/269/270/271/272/274=7 管（缺 1，表头 7 列需 8 管）；markdown 渲染列错位、按管解析的自动化错读。258 行既有 `|集成重编号：...）` 缺左括号形态（基线同形，本栈就地改状态未顺带修）。210/246/257/258 就地改动、264/265/268/273 新行结构正确。
- **重编号注记链：自洽**。抽样 12+ 条均可追溯（108←110、152←145、186/188/189←182/184/185、193←191、237←226、239←232、250←244、251←245、256←247、258←256、259/260←256/257、263←257、267←265、268←266、269/270/271←266/267/268、272←264、274←267）；守卫脚本内引用随重编号同步改（cb3a80a7 将 ENUM-PARITY KNOWN_DRIFT fix 引用 266/267/268→269/270/271，与台账行一致）。空号段（71-76、82-107、122-139 等）与「预留/顺延/撞号先到先得」注记链吻合，无无法解释的跳号。
- 化石级小瑕疵：`FIXED@V3-FIX-3536`（:40/:41）实为 3c2ca32c「FIX-35+36」双修引用丢失分隔符，非吞行，两行均在且各自闭账。

## 面三：遗留物扫描

- **运行时产物/临时文件：零**。全量 diff 无 .log/.tmp/.pyc/.bak/.orig/.rej/DS_Store/__pycache__/.env/scratch 命中；v3-output/、data/ 目录零触碰。
- **生成物手改：零**。3 个 .g.dart 变更（achievement/photon/community）均为规范生成器输出形态：`$enumDecode(..., unknownValue:)` 参数、枚举 map 增项、hive adapter case 增项，与 .dart 源逐值对应（MessageType broadcast=11/unknown=12、GroupType official+unknown、PhotonTransactionType grant_bonus/contract_escrow/guest_seed+unknown）；`app_localizations*.dart` 三文件互相零漂移（见面一第 5 条）。gen/ 目录外无 .g.dart 手改痕迹。
- **debug 打印新增：1 处且合理**——`achievement_model.dart:136` debugPrint 为 FIX-260 未知成就类型降级 unknown 的显式告警（有标签、有 FIX 引用）。backend/app 新增 `print(` 零命中。l10n 两批（764d5ce7/1019 行、c2129226/5019 行）确证**纯删除零插入**。
- **CI 变更最小**：ci.yml 仅 pytest 行加 `--timeout=300 --timeout-method=thread`（cbba2133），与声明一致。
- `V3-FIX-XXX` 字符串命中为 ENUM-PARITY 守卫 `self_test()` 的豁免 fixture（scripts/guards/check_enum_value_set_parity.py:928），非残留。

## 面四：守卫口径

- **ENUM-PARITY 登记在案**：`scripts/rule_guard_manifest.tsv:90` 新增 `ENUM-PARITY → scripts/guards/check_enum_value_set_parity.py`，与 5bb44f32 交付一致；manifest 60 条与 scripts/guards/ 39 脚本逐一对照，**guards/ 零漏登、零空挂**。
- **实跑验证**：HEAD 处 `check_enum_value_set_parity.py` **PASS（65 族，FAIL=0 WARN=7 豁免=0）**——与 84243910/d79354e9/7f466be5「修复落地即删豁免」声明一致，剩余 WARN 均为 unknown 哨兵族 EP002（与 7f466be5 描述吻合）。附带发现：守卫自报 `MessageOrigin (app/models/chat.py)` 为未进映射表的扩表候选（FIX-258 新 enum 尚无 mobile 镜像，设计上暂无 wire 消费面，观察项不阻塞）。
- **CARD-DUAL-WRITE 现状如实**：manifest :71-72 注释停用（2026-09-18），理由经核实为真——`app/services/card_protocol/consistency_validator.py` 确不存在（card_protocol/ 目录 14 文件无此模块）。
- **quality 双基线一致**：`quality/mypy_baseline.txt` = **642**（批五声明值精确一致）；`flutter_analyze_allowlist.json` max_info=**378**、CASCADE_INVOCATIONS 预算 **188**，_comment 链完整记载批四 412→409（wt546，含「≥40 不可达」缺口说明）与批五 409→378（wt549，test/ 面 219→188、1 跳过原因）——与台账 266/274 行、commit 806ef4be/eaf86ca7 声明逐项吻合，只降不升无倒挂。
- 观察（基线既有）：scripts/ 根下 12 个 check_* 脚本（cors/coverage/dependency/duplicate/flutter_analyze_gate/migration_contracts/openapi/production_secrets/proto_contract/proto_deprecated_windows/secret_strength/tech_debt_budget）未见于 manifest 任何行（含 && 复合行），口径上属未登记守卫；非本栈引入，建议后续一并收编或注明运行入口。

## 面五：诚实性抽查（3 行，diff 静态核验）

1. **FIX-257 FIXED@afbfdef2**（2b32d728）：声称「四表 catalog 指纹+种子写入窗双闸」——实况：guest_seed_service +400 行含 `_SEED_NODE_MASTERY_SIGNATURES` 指纹（:1646）、`_cleanup_guest_seed_statistics`（:3903）、auth.py 挂钩 +15；新增测试 test_guest_upgrade_seed_statistics_cleanup.py 299 行 6 用例。**支撑**。
2. **FIX-264 FIXED@91f8e579**（f885ccb4）：声称「await 同步纯函数红→绿 + metadata str() 缺省」——实况：routing_parameter_proposal_service.py:200 直调（去 await，`_compute_proposed_value` 确为 :318 @staticmethod 纯函数）、persistence_layer.py:310-335 全值 str()；新增 test_routing_parameter_proposal_service.py（1 用例，与「1 passed」口径一致）+ test_persistence_layer_mixin.py:194 起三守卫带 V3-FIX-264 标记。**支撑**。
3. **FIX-272 FIXED@934b076b**（fb1ce66e）：声称「test-only，4 用例 _coerce_session_uuid 旧契约对齐 staticmethod 单参」——实况：fb1ce66e 仅触 2 个测试文件（+9/−4），rebinding 正是旧双参 lambda→staticmethod 单参；产品侧 `orchestrator.py:1503` 确为 `@staticmethod def _coerce_session_uuid(session_id: str)`，测试桩契约与产品签名吻合。**支撑**（注：本工作树无后端 venv，「4 用例转绿」未独立复跑，静态证据链完整）。
4. 加验 FIX-269/270/271 FIXED@b051ce99：三族枚举修复 + 3 个新 drift 测试文件在库 + 守卫豁免即删且实跑 PASS（见面四），链路闭环。**支撑**。

## 风险分级与建议

- **R1（建议修后推，台账债·本栈新增）**：8 个新登记行表结构坏（263/266/267/269-272/274 管道数错、258 缺左括号）。影响渲染与自动化解析；修复=纯 docs 单 commit 补管/补括号，零内容变更。→ 登记 **V3-FIX-275**。
- **R2（可推后修·基线既有）**：台账 4 处吞行粘连 + 233 双行 + 231 仅粘连体。union-merge 工具已根修「新增侧」，建议给工具加存量 repair 模式或一次性回扫（先备份逐行 diff 复核）。→ 登记 **V3-FIX-276**。
- **R3（观察，不阻塞）**：①MessageOrigin 未入 ENUM-PARITY 映射表（守卫自报扩表候选，待有 mobile 镜像面时扩表）；②scripts/ 根 12 个未登记守卫脚本收编；③arb 10129 vs gen 8740 的 1389 键差（基线既有、收敛中，是 FIX-210 后续粮仓）；④FIXED@V3-FIX-3536 分隔符化石；⑤本审计在无 venv 环境无法复跑测试套件，建议集成侧在 CI（attempt#2）落绿后推。
- **跨卡交互面：零缺陷**。5+2 组对全部自洽，无合并语义撕裂。

## 整栈健康度结论

**可推**。产品码面（迁移/枚举/demo origin/guest 清洗/mypy/l10n/CASCADE）五面审计零发现阻塞缺陷；唯一建议修后推的是台账 markdown 表结构（R1，纯文档、10 分钟级），不构成产品回滚/返工因素。若集成侧接受台账债随栈携带，直接推亦可——但 275/276 登记行本身要求先落（见台账新行）。
