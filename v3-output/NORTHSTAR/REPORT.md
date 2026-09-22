# NORTHSTAR REPORT · 北极星场景 Worker 交付报告

- **Task**: 北极星场景 · 「只剩一周准备期末考试，Sparkle 学习效果最好、拿分最高」——剧本 + 评估框架 + 增益证明清单 + 评估 runner 骨架
- **Worktree**: wt81（全部改动仅在本 worktree；主仓只读；未 commit / 未 push）
- **产物目录**: `v3-output/NORTHSTAR/`

## 1. 交付物

| 文件 | 内容 |
|---|---|
| `SCENARIO.md` | 7 天离散数学期末冲刺 spec case：Day0 摸底 42 分 + 24 考纲节点映射 → 每日五段循环（自适应计划/新学/自测/错题沉淀/复习复盘）→ Day7 全真模拟考 → Day10 遗忘率重测。每步含用户动作/系统行为/可测检查点，附系统行为→仓库真实服务锚点表（exam_sprint_* / galaxy / knowledge / memory_* / profile / north_star_metrics） |
| `EVAL_FRAMEWORK.md` | 9 个代理指标（M1 同卷提分 / M2 单位小时提分 / M3 遗忘率 / M4 加权覆盖 / M5 复习命中 / M6 遗漏点率 / M7 认知负担 / M8 校准误差 / M9 过考概率轨迹）+ 三臂对照协议（Sparkle vs 裸 GPT vs 裸 DeepSeek，同状态等时间，N-of-1 交叉 ABBA 主档）+ 判定/证据规则（模型自评不作唯一证据） |
| `GAIN_PROOFS.md` | 13 个增益靶子（GP-01..GP-13，覆盖星图/向量/记忆/画像 × 有效/无效/有害三态机检定义 + 观测键 + 差分方法），含北极星级一票否决项（GP-03/04/07/11） |
| `changes.patch` | runner 骨架代码改动（7 文件，+1206 行）：`backend/tests/northstar_eval/`（已 `git add -N`，diff 导出；未 commit） |
| `REPORT.md` | 本文件 |

## 2. Runner 骨架（backend/tests/northstar_eval/）

复刻 Q-01（`tests/v3_scenario_eval/`）模式 + 借鉴 M-09 paired 双臂思想：

| 文件 | 职责 |
|---|---|
| `journey_schema.py` | 冻结 schema `northstar-journey.v1`（九字段）+ arm 三值词表 + checkpoint 词表（CP-00..CP-99）+ JSONL 装载校验 + NS-001 spec case 程序化构造（24 节点权重合计恰 1.0） |
| `simulator.py` | 三臂确定性旅程推演（`ARM_PRIORS` 假设先验显式声明）；Day0 诊断 → 学习/quiz/错题/复习/遗忘衰减 → Day7 加权模拟考 → +3 天重测 |
| `metrics.py` | EVAL_FRAMEWORK §1 指标的机检实现（gain / per-hour / forgetting / coverage / review hit / sync / adaptive / calibration） |
| `grading.py` | checkpoint 逐项 checker 注册表 + 诚实聚合（unsupported 永不计 PASS，复用 Q-01 硬线） |
| `runner.py` | CLI（`--spec-case / --journeys / --out / --seed`）+ 稳定结果 JSON `sparkle.northstar.journey-results.v1` + evidence 落盘 + mock-only provider 红线（真 provider 直接拒绝） |
| `test_northstar_eval_gate.py` | 12 个冒烟断言 |

复现（backend/ 下，`SECRET_KEY=test`）：

```bash
/opt/homebrew/bin/python3.11 -m pytest tests/northstar_eval -q        # 12 passed
/opt/homebrew/bin/python3.11 -m tests.northstar_eval.runner --spec-case
```

冒烟结果（真实 LLM 0 次，纯 stdlib，无 DB 依赖）：spec case 三臂全出；
sparkle 臂（假设先验下）42→66.99（ΔS≈+25）、η≈1.30 分/h、F≈2.2%、加权覆盖 0.82、
复习命中 1.0；对照臂 ΔS≈+7、覆盖/复习/错题同步全 0（结构性缺账本）；臂间 delta 方向
与 EVAL_FRAMEWORK 结构性论证一致。同 seed 逐字节一致，跨 seed 判定稳定、指标可见 seed 生效。

## 3. 回执数字

- **剧本检查点数**：11（CP-00..CP-08 确定性 9 + CP-98 真人量表 / CP-99 真墙钟 honest-unsupported 2；另有逐日采集项）
- **指标数**：9（M1..M9）
- **增益靶子数**：13（GP-01..GP-13）
- **runner 骨架**：7 文件 +1206 行；12 冒烟（含空场景冒烟 ×2、3 seed 确定性钉面、mock-only 红线）

## 4. 诚实申报（必读）

1. **推演不是证据**：simulator 的臂间差异来自显式声明的假设先验（`ARM_PRIORS`），只用于打通测量管线；每一轮结果 JSON 都携带 `prior_disclosure` 与 `verdict_semantics` 防误读。增益证据只能来自 EVAL_FRAMEWORK §2 三臂对照协议的真实执行。
2. **API 级推演永远 verdict=unsupported**：因 CP-98（真人自报）/CP-99（真墙钟）在 grading 中诚实降级，且按 Q-01 硬线任一 unsupported 即 case unsupported——这正是「能跑≠有用」的机检表达：骨架本身不可能绿，北极星达成只能由 C 线真实闭环测试宣布。
3. **阈值是定标假设**：M1 的 +15（MDE）、M3 的 0.2 等为工程判断，非功效分析产物；C 线首轮实测后必须重估（EVAL_FRAMEWORK §5 已登记此义务）。
4. **骨架简化**：simulator 的形成性 quiz 按考纲比例抽样（SCENARIO 剧本的「当日 70%+历史 30%」抽样在骨架中未逐日建模）；difficulty 字段为 spec 形状字段，推演未消费。两处均已注释声明，C 线接入真实自适应难度分层时补齐。
5. **spec case 内 quiz/模拟考分数轨迹为推演值**，与 SCENARIO.md 的每日目标带（人工判读用）不是同一口径；SCENARIO 目标带留给真人实测。
6. **git 状态**：`backend/tests/northstar_eval/` 处于 intent-to-add（`git add -N`），patch 已导出；未 commit、未 push；主仓零触碰。`v3-output/NORTHSTAR/*.md` 与 patch 为 untracked 交付物。

## 5. C 线闭环测试接口（留给后续）

- 靶子清单：GAIN_PROOFS §5 矩阵即执行核对单；每个靶子的观测键已与 runner observations 对齐；
- 差分方法：GP-07 用 M-09 的 paired no-history 臂（`tests/memory_eval/` 可直接复用）；GP-04 真料/盲选双臂；GP-11 画像开/关 ablation；
- 机制前置证据已存在：M-09 门禁当前 RED（20 个已登记产品 bug 签名）——GP-08 的「superseded 旧值复活」靶子在真实链路上有已知活性 bug 支撑，C 线应优先复测；
- 判卷/演示账号：确定性判卷走 exam_sprint diagnostic grader；演示账号走 `LOCAL_SMOKE_USERNAME` 体系（`backend/scripts/seed_demo_user.py`）。
