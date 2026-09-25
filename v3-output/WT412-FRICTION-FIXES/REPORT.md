# WT412 · A-08 行为缺陷修复组 REPORT（V3-FIX-49 / FIX-50 / FIX-51 + FIX-59）

- base SHA：`b5e8dedd`（worktree `wt412-friction-fixes`，分支 `wt412-friction-fixes`）
- final SHA：见单提交（DYNAMIC_ISSUES 状态行的 FIXED@ 引用本 REPORT 所在提交的前一提交）
- 修复对象：A-08（wt393）四臂消融 §5 反例 1/2/3 + Q-03 视觉审查 FIX-59
- 反例数据真源：`v3-output/WT393-A08-ABLATION/{REPORT.md §5, raw/*.jsonl}`（未改动）
- 修复后全人口四臂复跑产物：本目录 `a08-post-fix/`（raw×4 + summary.json + EVAL_RESULTS.md，复跑命令同 A-08 runner `--out-dir` 指向本目录）
- 模型 judge：0 次（全链确定性服务）；评估侧产品代码零 mock

## 1. 逐项处置（红→绿）

### V3-FIX-50（P1）B1 平权 tie —— 引擎层，`backend/app/aurora/friction_diagnosis.py`

- **实证先于修复**：现行代码的 argmax/后验排序已是 `(−score, type)` 字母序
  （`_argmax_type`/`_posterior_from_scores`），跨 5 个 `PYTHONHASHSEED`（0/1/2/3/42）
  探针输出完全一致——**卡片所述「tie-break=frozenset 迭代序（PYTHONHASHSEED 相关）」
  的机制描述对本栈已过时**（A-08 评估侧 `PYTHONHASHSEED=0` 补丁把该面侧写规避了）。
  但缺陷本体真实：宽分支零事实 → 10 路平权 → argmax 落**字母序偶然型**
  （raw 反例：p06 time 真值段恒落 dependency×3 → 纠正环；p06 dependency 段反被
  同一偶然蒙对）。
- **①（择优采纳）：B1 exact-tie 降级**。预算尽 best-guess 仅当领先幅度
  `> TIE_DISCRIMINATION_EPSILON`（1e-9）才按 argmax 行动；exact tie（margin=0，
  证据对行动零约束）→ `no_action` + 空提名 + `insufficient_context`，新封闭
  reason 码 `B3.budget_exhausted_tie_no_action`（B2「不假诊断」同律）。
  **弃②（种子偏置收窄）理由**：零事实下任何固定偏置对真值仍是任意的——它只
  会把「字母序偶然」换成「偏置设计者偶然」，且改动分支变换会波及 IG 选问与
  全部四臂的证据数学（S2 带、决策敏感判定），为单一出口动全局模型不成比例。
  ①是外科手术式：只动「平权且预算尽」这一个出口，非 tie 的 B1 best-guess
  行为不变（有红绿双测试锁）。③字母序契约：docstring 显式声明 + 子进程换
  seed（0/31337）输出逐字段一致测试锁死。
- 纪律面：`FRICTION_DIAGNOSIS_VERSION` v1_1→v1_2；`FRICTION_DIAGNOSIS_REASONS`
  扩 B3 + sufficiency 指纹重算（测试 `FROZEN_SUFFICIENCY_FINGERPRINT` 同步更新，
  词面/问题库/证据面三指纹不变）——扩面 bump 纪律履行，非删断言换绿。
- 红测：`tests/unit/test_a03_friction_diagnosis.py::TestB1TieExitContract`
  （exact-tie 降级 / 非 tie 不变 / 字母序契约 / 跨进程锁，修前 5 红）。

### V3-FIX-49（P1）wiring 无门全量触发 —— chat 装配层，`backend/app/services/friction_chat_wiring.py`

- **门设计：fresh 出口词牌门（降噪不关死）**。orchestrator 对每条非工具消息
  无门调用 `process_turn`；raw 反例两条机制——①零证据普通消息恒触发 U1 根
  分裂澄清问（no_experience 臂 25/25）；②stale spine（48h 窗口内）单独驱动
  S1 直出建议 / Q1 追问（full 臂 21/25）。门契约：**fresh 轮 ask/act 出面必须
  携带正向摩擦自报词牌**（引擎注记 `utterance_matches` 非空），否则静默
  `no_action`，`annotations.wiring_gate` 记门原因（`silent_unknown_no_friction_evidence`
  / `silent_no_utterance_wordmark`）可审计。
- **不关死的证据**：回答闭环（answer_replay）不设门；带词牌诊断全链照常
  （问询/建议/patch 重排均不变）；旅程面（用户主动「我卡住了」）不经过本服务。
  门放在装配层而非引擎层——旅程面 U1 根分裂问（J-05 产品语义）保持原样。
- 红测：`tests/services/test_friction_chat_wiring.py::TestFrictionWiringTriggerGate`
  （stale-spine 静默 / 零证据静默 / 词牌问询照常 / 词牌 act 照常 / 回放不设门，
  修前 2 红 3 绿）。
- **门定位说明**：任务卡原文「词牌/spine 预筛或置信门」——纯词牌预筛会误杀
  8 个弱词牌真卡点表达（A-08 persona 词表实证：clarity/time/dependency/choice/
  plan_drift/social/tooling 弱档无一命中词牌库），故采用**出口门**（诊断照跑、
  出面设限），既杀对照侵入又保弱词牌段的问询收敛通道。

### V3-FIX-51（P2）决策两面守卫不对称 —— 契约声明路线，`backend/app/services/stuck_journey_service.py`

- **择优：契约声明（卡片处置第二选项）**，弃「旅程出口过 A-02 evaluate」：
  journey 能力面映射的完备性是产品级裁决（旅程提名由客户端动作面执行，各面
  各有守卫；引擎侧任意圈定能力集会制造假排除），任务面明示该风险。
- 落地三件：①模块常量 `JOURNEY_INTERVENTION_DELIVERY = "recommendation"`；
  ②`main_intervention` 载荷恒带 `delivery` 字段（类型面声明）；③模块 docstring
  登记差异语义（chat 面 = 过 A-02 守卫的执行决策；旅程提名 = 建议非执行，
  差异合法、登记非静默）。测试锁：`tests/api/test_stuck_journey_api.py::
  test_main_intervention_declares_recommendation_delivery`（start/answer 两出口
  + 常量值，修前红）。

### FIX-59（P2）连胜详情文案窗矛盾 —— `mobile/lib/features/achievement/presentation/screens/streak_details_screen.dart`

- 根因：`streakInsightBanner` 模板硬编码「过去7天」而 `totalCheckins` 是 90 天
  历史日历的完成天数（demo 档渲染「过去7天你有70天完成了任务」）。
- 修法：模板窗参化（zh/en arb 加 `windowDays` 占位，gen-l10n 重生成）；概览句
  窗口值与完成数**同源**（都取 `historyState.days`）；历史未加载（空日历）不
  渲染可能为假的概览句（加载态显示 0 完成数同样是断言）。
- 红测：`mobile/test/.../streak_details_screen_test.dart`（90 天窗 70 完成 /
  30 天窗 12 完成 / 空日历三测，**修前实测 0 过 3 红**——stash 修复后复跑证红）。

## 2. A-08 主结论不回退证明（全人口四臂复跑，PYTHONHASHSEED=0）

分解复跑设计：gate-only（B3 临时置 -1 禁用）隔离 FIX-49 门的影响；gate+B3 为
最终态（`a08-post-fix/`）。

| 臂 | 指标 | 修前（WT393） | gate-only | 最终（gate+B3） |
|---|---|---|---|---|
| full | accuracy | 0.65 | **0.65** | 0.45 |
| full | 对照侵入 | 21（84%） | **0** | **0** |
| full | 效用 | −16.2 | **−3.6** | −9.2 |
| no_memory | accuracy / 侵入 / 效用 | 0.55 / 21 / −21.4 | **0.55 / 0 / −8.8** | 0.55 / 0 / 0.0 |
| no_experience | accuracy / 侵入 / 效用 | 0.65 / 25 / −19.05 | **0.65 / 0 / −3.6** | 0.45 / 0 / −9.2 |
| fixed_policy | accuracy / 侵入 / 效用 | 0.30 / 0 / −24.8 | 0.30 / 0 / −24.8 | 0.30 / 0 / −24.8 |

- **FIX-49 门零回退且净增益**：gate-only 下 full vs fixed = **0.65 vs 0.30 分毫
  不动**，四臂对照侵入 84–100% → 0，full 效用 −16.2 → −3.6（去除侵入罚项）。
  「full 显著优于固定模板」主结论保全且增强。
- **A-08 契约锁**：`tests/unit/test_a08_aurora_ablation_contract.py` **13/13 绿**
  （最终代码上）。
- **FIX-50① B3 的代价（如实，不粉饰）**：full/no_memory/no_experience 的
  accuracy 变化全部来自 B3 移除「平权 tie 的字母序偶然蒙对」——修前 5 个
  journey 面解决段（p05-d0/d6、p06-d4、p09-d0、p10-d0）里 4 个是窄分支
  （no_direction 4 类）平权偶然落 choice→reflect 恰为 goal_drift/choice 主提名、
  1 个是宽分支偶然落 dependency（p06-d4）。引擎行为从「猜」改「不猜」，评估
  结果模型对幸运猜中的奖励随之消失——这是卡片处置①的**预期代价**，不是回退。
  契约 13 测锁的协议结构全部保全。
- **新发现（V3-FIX-97 登记）**：B3 诚实 no_action 暴露纠正通道的结构性输入
  依赖——纠正只在「旅程面错位行动」后可提（产品语义：对被提名的成因说
  「不是这个原因」），诚实不猜 = 无从纠正，full 臂纠正记忆回路在此时间线被
  饿死（memory 净收益 ±0.10 → 修后 −0.10，full 0.45 vs no_memory 0.55）。
  需产品裁决：无行动出口是否提供第二入口（如「都不对，其实是…」自由纠正）。

## 3. 质量门

- 邻域 pytest：A-02/A-03/A-04/A-06 + action_allocation + policy_patch + lifecycle
  + J-05 迁移 + journey API + wiring + A-08 契约 = **564 passed, 0 failed**。
- 冷 mypy：`mypy app services` = **1103 errors = `quality/mypy_baseline.txt` 值
  （1103），零漂移**（协调方提示基线文件可能滞后实际栈 1102；本机实测 1103，
  与基线文件一致，未动基线文件）。
- ruff：改动面 6 文件 All checks passed。
- 守卫：`bash scripts/run_all_rule_guards.sh` = **84/84 exit 0**（gen symlink 接
  主仓按 A-08 先例）。
- mobile：`flutter test streak_details_screen_test.dart` 3/3 绿；`flutter analyze`
  **0 error**，本卡改动文件（streak_details_screen.dart / 新测试 / l10n 生成物）
  零新增条目（全量 info 计数随主仓其他 worker 合并自然漂移，非本卡引入）。

## 4. 改动文件清单

- `backend/app/aurora/friction_diagnosis.py`（v1_2：B3 + 字母序契约 + TIE_DISCRIMINATION_EPSILON）
- `backend/app/services/friction_chat_wiring.py`（v2：fresh 出口词牌门）
- `backend/app/services/stuck_journey_service.py`（FIX-51 交付契约）
- `backend/tests/unit/test_a03_friction_diagnosis.py`（TestB1TieExitContract + 指纹/词表同步）
- `backend/tests/services/test_friction_chat_wiring.py`（TestFrictionWiringTriggerGate）
- `backend/tests/api/test_stuck_journey_api.py`（FIX-51 契约锁）
- `mobile/lib/l10n/app_zh.arb` / `app_en.arb` + `lib/l10n/app_localizations*.dart`（gen-l10n 重生成）
- `mobile/lib/features/achievement/presentation/screens/streak_details_screen.dart`
- `mobile/test/features/achievement/presentation/screens/streak_details_screen_test.dart`（新增）
- `v3-output/WT412-FRICTION-FIXES/`（本 REPORT + a08-post-fix/）
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（49/50/51/59 OPEN→FIXED + V3-FIX-97 登记，随后续提交）
