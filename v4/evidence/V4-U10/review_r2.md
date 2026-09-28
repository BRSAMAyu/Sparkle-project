# V4-U10 二审 receipt（R2 = wtU10R2，未参与实现与一审/整改）

- 审查对象：分支 `agent/v4/u10` @ `24d8be9c`（实现 `b5e04e57` → 一审 receipt `03f1d8f1` → 整改 `24d8be9c`；base=main@`331740ff`，merge-base 已核）
- 审查方式：只读审查 + 审查者自有 mutation（亲做 2 个，跑完即还原、未入 commit）+ 自有对抗探针（临时 pytest 文件，跑完即删、未入 commit）+ 全量复跑
- 环境：`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`（worktree 无 .env，与 run_manifest 一致）；Flutter 3.41.3 stable / go test 13 包 / python3.11
- 卡面：高风险 · 独立审查 2 位（R1+R2 本文）；本审聚焦整改复核与对抗，与 R1 互补

## 总裁决：PASS（APPROVE）

一审 F-1 整改（a 案）**成立且经审查者亲做 mutation 验证可失败**；一审 F-2/F-3/F-4/N-5/N-6 全部落定且证据同步；卡面三验收维持成立（R1 亲跑 + 本审对抗无翻案）；**零答案泄漏红线在整改新增门之后经序列攻击对抗仍成立（fail-closed）**。无新增 CHALLENGE。建议协调面销账 `DONE_REVIEWED`（集成时按 §7 对最新集成 SHA 重跑合并面）。

---

## 一、F-1 整改复核（最重靶）——成立，两面均可失败钉死

a 案落点核实（代码读核，非采信声明）：

- **GET 读模型位置门**：`build_goal_journey` 的 `check_view` 仅在 `check_authority` 齐备且 `scaffold.stage == SCAFFOLD_STAGE_INDEPENDENT_CHECK` 时携带 `{"question": ...}`；非检验段 `view.check=None` 且**不误报警示**（权威在、只是未到段 → 无 `check_authority_missing`/`check_question_missing`）。到段但题面缺失 → 诚实降级 `check_question_missing`（learning_journey_service.py:188-199）。
- **判分面 stage 门**：`grade_check` 先于判分执行 `scaffold.stage != SCAFFOLD_STAGE_INDEPENDENT_CHECK → HOLD.scaffold_not_at_check`（graded=False、correct=None），**correct 裁决结构上不可得**；缺权威 ≠ 位置不对 → 专属 `HOLD.check_authority_missing`（learning_journey_service.py:362-384）。
- **REST 契约面**：`GET /learning-journey/tasks/{id}` 与 `POST .../check/submit` 均走服务层同一门（api 层无旁路）；`enter_check` 仍是唯一写路径（I07 `apply_scaffold_decision` 写回 guide_json 策略块，零迁移）。

### Mutation（审查者亲做，撤门 → 新测试红）

| mutation | 改动 | 结果 |
|---|---|---|
| M1：撤 GET 位置门 | `elif scaffold.stage == ...` → `elif True` | **2 failed**：`test_get_journey_check_face_gated_by_scaffold_position`（service）+ `test_check_face_and_grading_gated_until_check_stage`（API 契约面断 `view.check is None` 红）。32 其余绿 |
| M2：撤判分 stage 门 | `if scaffold.stage != ...` → `if False and ...` | **3 failed**：service 两反例 + API 同名钉死——example 段提交正确答案实际拿到 `graded=True`（绕证据门的 correct 裁决可得），测试红在刀口上 |

两次 mutation 均被整改新增的 +5 测（core 19/service 11/api 4 = 34，其中 +5 全一正一反）捕获后还原工作区。门不是摆设，钉死测试真实可失败。

### 对抗（审查者自有探针 4 支，全过）

1. **序列攻击「到段前后各一次请求」**：有证据 → enter 推进到检验段（题面被攻击者缓存）→ 外部写手把 guide_json stage 回退 attempt（模拟任何回退向量）→ 后续请求：GET `view.check=None`、submit 正确答案 → `HOLD.scaffold_not_at_check`、correct=None。**缓存题面换不到裁决，fail-closed**；同请求序列再 enter → 证据门重新放行（不误伤正常旅程）。注意：门读的是提交时点落库状态（探针曾因 JSON 列原位改不触发 UPDATE 而"攻击无效"，整体重赋值落库后门照样拦——即门对真实持久化状态生效）。
2. **stage 竞态（双击 enter）**：两次连续 enter——首次 `persisted=True` 推进，二次幂等到段 `persisted=False` 不再写、题面稳定；无回退、无双重写。链终点稳定面判分照常。
3. **无证据重复 enter ×3**：stage 原地不动（example）、永不落检验段、GET 始终无题面——竞态前提（stage 未经门前进）不成立；`next_scaffold_step` 转移表只前进不回退（import 期对齐断言 + R1 已核）。
4. **同请求快照一致性**：位置门与判分权威取自同一行 `_resolve_scaffold` 快照（单 SELECT 单行，请求内无 TOCTOU）；到段但权威不完整（有题无答案）→ GET 出题面（题面非答案材料）+ submit → `HOLD.check_ungradeable`，不猜不伪造。

跨用户/404 语义、出口泄漏探针、解析诚实构造不变量本审复核与 R1 一致，无翻案。

## 二、词表 bump 纪律复核——成立

- **4→6 与 v1→v2**：`CHECK_VERDICT_REASONS` 现 6 成员（+`HOLD.check_authority_missing`、+`HOLD.check_ungradeable`）；`LEARNING_JOURNEY_SCHEMA_VERSION = "learning_journey.v2"`；bump 随 R1 N-5 预授权的冻结集更新流程走（v1 未外发——全仓 grep 无任何 `learning_journey.v1` 消费/留存，v1 字样仅存在于异名契约 `hybrid_journey.v1`/`stuck_journey.v1`/`northstar-journey.v1`，不混淆）。声明如实。
- **冻结钉死锚定**：`test_check_verdict_reasons_vocabulary_frozen` 集合相等断言 6 成员 + 前缀纪律（HOLD.* 不承载裁决、OK.* 只在 graded=True）+ v2 钉死；移动端 `learning_journey_models_test.dart` 亦锚 `learning_journey.v2`。
- **全仓引用同步 grep**：`learning_journey.v2` 字样命中 core 定义、router.py 注释、gateway proxy_routes.go 注释、BA-ROUTES ledger 注释、Dart models/badge 注释、双端钉死测试、证据五件套——**零 stale**。verdict reason 字面量全仓盘点：服务层出口只发词表内成员（enter 的 `view.scaffold.reason` 为 I07 脚手架决策词表另一面，如 `OK.independent_check_reached`，与裁决词表分野清晰，无混用）。

## 三、数字口径复核（R1 F-2/F-3 勘误）——逐类全验，exact match

对 `331740ff..HEAD` 实测 `--numstat`：40 行（38 文本 + 2 二进制）**+5121/-96** ✓。diff doc §4 五类分解逐一复算：

| 类 | 声称 | 实测 | 判 |
|---|---|---|---|
| 生产面（backend app 4 + gateway 1 + BA-ROUTES 1 + 移动 lib 非 l10n 11） | 17 文件 +2329 | 17 文件 +2329 | ✓ exact |
| 测试面（后端 3 + 网关 1 + 移动 4） | 8 文件 +1727 | 8 文件 +1727 | ✓ exact |
| l10n（arb 2 + 生成 3） | 5 文件 +483（-92） | +483/-92 | ✓ exact |
| 证据（7 文本 + 2 png 二进制） | +578 | +578 | ✓ exact |
| tasks.json | +4/-4 | +4/-4 | ✓ exact |

F-2 移动回归 71（10+4+29+28）勘误在 run_manifest/test_results/review_receipt 三处同步且注因，全仓无残留「75 passed」活口径（review_r1.md/diff doc §7 中的 75 为勘误注记本身，属正当历史记录）。

## 四、复跑（全部亲跑）

| 套件 | 声称 | 实测 | 判 |
|---|---|---|---|
| 后端本卡 34 | core 19 + service 11 + api 4 | **34 passed**（6.6s） | ✓ |
| 后端合并 127（34 + I07 31 + I08 24 + D02 38） | 127 | **127 passed**（78.3s） | ✓ |
| 网关 | 2 测 + go test ./... | **2 PASS + 13 包全 ok** | ✓ |
| 移动 learning | 31 | **31 passed** | ✓ |
| 移动回归 router smoke + deep-link | 10 + 4 | **14 passed**（`test/app/router_smoke_test.dart` + `router_deep_link_test.dart`；注：审查者首跑误用 `test/router` 路径致 1 项"失败"为审查者自身路径伪影，改正后全绿） | ✓ |
| 移动回归 shell + error_book | 29 + 28 | **57 passed** | ✓ |
| 治理守卫 | 88 rules | **all rule guards passed (88 rules)** | ✓ |
| ruff（本卡 6 文件）/ black（3 生产文件） | 全过 | All checks passed / 3 files unchanged | ✓ |
| mypy（3 生产文件） | 0 error | **3 文件自身 0 error**（传递导入噪声 30 处均在本卡 diff 外的既有文件，非本卡引入） | ✓ |
| flutter analyze（4 目标 + 全仓） | No issues | **No issues found**（两者） | ✓ |

## 五、limitations 10 条如实性 + N-7

- 逐条复核：#1 单键判分（`_extract_expected_answers` 只读 `answer`，属实）、#2 揭示面未做（feedback 封闭短语，属实）、#3 review_count>0 口径（代码属实）、#4 bare-group 未联调（gateway registerREST 裸组属实、NOT_RUN 未伪造）、#5 知识节点链路（属实）、#6 badge 呈现面未接深链（`onOpenFragment` 可空回调，属实）、#7 宿主渲染非真机（U02TestFonts 先例口径属实）、#8 correct 双语义 + N-6 release 口径（models.dart 注释逐字如实：assert debug/test 生效、release 跳过、真实防线=服务端探针权威+运行时兜底）、#9 V3 零触碰（diff 全量核对无 V3 行为文件）、**#10 词表 bump 登记（4→6 + v1→v2 + v1 未外发 + 冻结钉死，与实现一致）**。10/10 如实，无缺漏新发现。
- **N-7**：diff doc §7 表行「按 R1 裁决记录备查不改代码」在案；`fromLaunch` 起飞前失败形态与 R1 记述一致。处置符合一审裁决。

## 六、红线面复核（整改后无回退）

- 五 Tab 只增不改、RF-06 三高危冲突面零触碰、tasks.json 仅 U10 状态行——对 `331740ff` 全量 diff 复核维持 R1 结论；整改 commit 未触碰路由/导航面。
- 零答案泄漏：GET 门收窄后题面出口只有「到段后的 `view.check.question`」与「enter 放行的 `view.question`」两处，均经 `redact_for_client` + `assert_client_payload_clean` 出口探针；判分面经本审 M2/序列攻击双向验证 correct 裁决不可绕证据门获得。

## 七、合并落差预判

- base=`331740ff`；main 现已前进至 `3b96039f`（F05 销账、CI39 词表钉、U03 等共 135 文件）。与 U10 diff 交集**仅 `v4/04_tasks/tasks.json`**，且两侧改的是不同卡片条目的不同 hunk（U10 状态行 ~L2362 vs main 的 F03/F05/D04 条目）——即便文本冲突也是行级易解，无生产代码冲突；CI39 event vocabulary（40→41）不触 U10 面。
- **集成 SHA 复验要求**：合并时点对最新集成 SHA 重跑合并面（后端 127 合并 + 移动 31/71 + 守卫 88 + go test）后再销账（与 R1 §4 同口径）。

## 八、裁决汇总

- F-1 整改（a 案）：**成立**——两面门落位、+5 测真实可失败（M1/M2 mutation 红）、对抗 4 支全 fail-closed、REST 面无旁路。
- F-2/F-3/F-4/N-5/N-6/N-7：**全部落定且证据同步**；数字口径五类 exact match。
- 词表 bump 纪律：**成立**（6 成员冻结钉死 + v2 全仓同步 + v1 零残留）。
- 卡面三验收 + 零答案红线：**维持成立**（R1 亲跑 + 本审对抗无翻案）。
- 复跑全绿（ §4，含 2 处审查者自身路径/环境伪影的如实注记）。
- 无新增 CHALLENGE；**PASS**。R1 + R2 = 高风险卡 2 位独立审查齐备，可销账。

—— wtU10R2 · 2026-09-29
