# V4-Q02 · diff_or_evidence_only（记忆效用四臂与新 holdout）

- 实现会话：wtQ02（worktree `../wtQ02`，分支 `agent/v4/q02`）
- 被评源 SHA：`a2b17f1c`（main 最新：I05 收口 / I 线 8 卡 / D 线 6 卡 / F 线 5 卡 / U 线 4 卡合并态）
- 状态：实现 + 运行完成，**待独立审查（2 位，风险 high）**；review_receipt.json 为 PENDING 占位
- 证据层：**L1_CONTROLLABLE_SERVICE_SIMULATION（零模型）**；L2 真模型层 **BLOCKED_EXPLICIT**（见下）

## 一句话

先冻结并复现原反例（B03 冻结行 `V3-NEG-A08-POSTFIX-NOMEMORY-BEATS-FULL`：A-08 修后 no_memory 11/20=0.55 反超 full 9/20=0.45），当前 SHA 上 **REPRODUCED**（sha256 六工件全对表 + 双路径重算逐数一致 + 当前 SHA 复跑聚合逐数全同、声明分歧类归一化后逐字节一致）；再按开发/独立 holdout 规则运行四臂（A=V3 现部署 / B=无可选历史 / C=V4 语义控制+全部合法历史 / D=V4 语义控制+效用筛选历史），30 dev + 120×2 seed holdout episode/臂、按 profile 簇配对 bootstrap 95% CI；选择面（D 门唯一集成面 context_pack）以 B03 CTX 族 9 场景跑真实装配面 oracle 全绿。**L1 效果门 FAIL：M11 形状点估计=精确 0（结构性），M12 未建立（CI 跨 0），冻结 utility 下记忆臂仍显著更差——产品 value=NOT_PASS**；L2 live 层因批量收费预算未授权 BLOCKED_EXPLICIT（零模型调用账目在案，未伪造）。

## 交付差量（全部新增；零产品代码改动；零迁移/proto/生成文件）

| 文件 | 变更 |
|---|---|
| `v4/evidence/V4-Q02/reproduce_counterexample.py` | **新增**反例复现脚本：①sha256 对表 B03 冻结行六工件；②冻结 raw 双路径复算（harness 权威 `summarize_arm` + 独立最小重算）episode 计数与冻结 utility（full=-9.2/no_memory=0.0）；③当前 SHA 复跑 A-08（full/no_memory，PYTHONHASHSEED=0，旗标部署默认）；④新 raw 对表冻结 raw（聚合全同 + 三类已声明分歧归一化后逐字节一致 + applied 归因只收窄不扩张方向检查） |
| `scripts/devtools/q02_run_four_arm_utility_eval.py` | **新增**四臂评测 runner：dev（15 profile×2=30/臂）→freeze（冻结清单：臂定义/判据/schema/零模型声明）→holdout（种子独立生成 30 profile×4=120/臂 ×2 seed）→analyze（冻结 utility + 配对 profile 簇 bootstrap 95% CI + 双 seed 敏感性 + C≡D 恒等实证）→surface2（选择面）。臂间旗标进程内切换、臂后恢复并断言泄漏 |
| `backend/tests/q02_surface2.py` | **新增**选择面评测模块（沿 `tests/q04_personal_redteam` 先例入 tests/）：真实 `ContextPackBuilder.build` + M-03 预筛 + I02 效用门，B03 配对集 CTX 族 9 场景 × 3 方式（gate_off/gate_on/no_history），oracle=不合法引用 0/必要记忆不可全拒（bypass 如实登记）/selected⊆input/precision N/A 纪律 |
| `v4/evidence/V4-Q02/run_manifest.json` | 命令/exit/环境/旗标/模型账目（0 调用）/L2 BLOCKED 取证/分母口径/工件 sha256 引用 |
| `v4/evidence/V4-Q02/test_results.json` | 复现判定 + 冻结清单 + 四臂全量数字与 CI + 选择面 9 场景 + 工程门（pytest 180 passed / mypy 59≤77 / ruff+black 新文件全清）+ 价值裁决 |
| `v4/evidence/V4-Q02/limitations.md` | 面边界与未证明事项如实申报 |
| `v4/evidence/V4-Q02/review_receipt.json` | PENDING 占位（high 风险待 2 位独立审查） |
| `.gitignore` | +`v4/evidence/V4-Q02/runs/`（运行生成物不入库；脚本+种子+sha256 保证可复现） |

## 原反例复现（卡目标第一条）——REPRODUCED

1. **冻结源完好**：B03 冻结行 `source_sha256` 六工件逐一重算全匹配（含 raw 四臂 jsonl）。
2. **重算逐数一致（双路径交叉）**：full=9/20（utility -9.2）、no_memory=11/20（utility 0.0）；harness 权威复算与独立最小重算两条路径与冻结行/summary.json 逐数一致；反超方向成立（Δ=+10pp）。
3. **当前 SHA 复跑**：`a2b17f1c` 上重跑 A-08 harness（V4 旗标全部部署默认）→ **聚合逐数全同**（9/20 vs 11/20、utility -9.2 vs 0.0、wrong 18/5、patch 漏斗 9 提案/7 确认同记录位）。
4. **记录级三类已声明分歧**（归一化后逐字节一致）：a) `friction_diagnosis_version` 注记 v1_2→v1_3（冻结后诊断引擎版本推进）；b) 随机 UUID 盐派生 id 面（decision_id/patch_id/goal/task id，逐 run 必然不同）；c) `applied_patch_ids` 归因收窄（I05 `4cac07ec` 把归因面对齐 FIX-67 scope 谓词——冻结 SHA 上 applied=未过滤全量 effective 集，属已修正的归因/可观测缺陷）：方向检查实证 fresh applied 回合 ⊆ frozen（8→2 / 10→4，零 fresh-only），决策行为与结局面零变化。

**结论：原反例在当前代码上原样成立**——V4 六线合并未扰动 V3 基线路径（行为面逐字节一致），也没有任何已合并机制在该层翻案负结果。

## 四臂 L1 结果（30 dev + 120×2 seed holdout episode/臂）

臂绑定（冻结清单 `runs/freeze_manifest.json`）：A=full+部署默认；B=no_memory（可选历史缺席，mandatory goal/plan 全臂共享——非记忆剥夺）；C=full+`EXPERIENCE_STRATEGY_MODE=live`；D=C+`ENABLE_MEMORY_UTILITY_GATE=True`。

| 臂 | dev 30 | holdout s1 120 | holdout s2 120 | utility（s1/s2） |
|---|---|---|---|---|
| A v3_full | 16/30 | 42/120 (35.0%) | 56/120 (46.7%) | -129.2 / -91.5 |
| B no_optional_history | 17/30 | 38/120 (31.7%) | 49/120 (40.8%) | -74.7 / -53.9 |
| C v4_all_legal | 16/30 | 42/120 (35.0%) | 56/120 (46.7%) | -129.2 / -91.5 |
| D v4_utility_filtered | 16/30 | 42/120 (35.0%) | 56/120 (46.7%) | -129.2 / -91.5 |

配对 profile 簇 bootstrap 95% CI（30 profile/seed）：

- **M11 形状（C−A、D−A）= 精确 0，CI [0,0]**——两 seed 一致。这是**结构性恒等**而非效果为零的空样本：A-08 决策回路不经过 I02 门集成面（context_pack），且 harness 的 patch 载荷（`{intervention, direction: prefer}`）不携带 do_not_apply/precondition 键、auto 激活的 patch 均带 observed benefit——I02 门在该回路无可触发条件；I05 live 门中 decision 门出无可触发条件，admission 收益门与 72h 有界窗真实触发过但差分被 confirm-backstop 吸收（结局级恒等实证：两 seed 120/120 episode 结局逐一相同，非记录级）。**不能据此宣称 V4 机制无效**；只能说本 harness 激励分布下无差分（limitations #2/#3）。
- **M12 形状（C−B、D−B）**：s1 +3.3pp CI[-4.2,+10.8]；s2 +5.8pp CI[-2.5,+15.0]——点估计为正但 **CI 均跨 0，未建立**（M12 目标 ≥0 的判定在 L1 不可达（live 层缺席），不得宣称）。
- **冻结 utility（A−B）**：s1 -1.82 CI[-2.73,-0.83]；s2 -1.25 CI[-2.16,-0.34]——**两 seed 稳定为负**：记忆臂跟错更多（wrong 196/67），B03 指认的坏经验污染模式在 L1 持续。
- **双 seed 敏感性**：A−B resolve-rate 符号在 dev（−3.3pp）与两个 holdout seed（+3.3/+5.8pp）间不稳定，效应量落在噪声域；utility 符号稳定为负。任何「记忆净收益已转正」的表述都不被本数据支持。

## 选择面 Surface-2（D 门唯一集成面；CTX 族 9 场景全绿）

真实 `ContextPackBuilder.build`（M-03 预筛→排序→I02 门）× 3 方式 × 9 场景（CTX-01..08 及 required-memory 正例）：

- 不合法引用=0（wrong-user 行在任何方式下不出现——M-03 上游砍除，门无复活路径）；
- **必要记忆不可全拒**：ctx08 全拒场景 bypass 如实登记（`verdict=required_memory_recall_miss_bypass`、`bypassed=true`、候选保留非静默清空、`precision=None`=N/A 不是 0%/100%）；正例场景 gate_on 有召回；
- selected ⊆ input（按内容比对，无复活）；mandatory goal 各方式保留（当前显式约束非可选历史，各臂共享）；
- ctx03 跨课程失败 `negative_transfer_cross_type` 硬拒实证（FIX52 集成面武装）；ctx05 过期约束 M-03 TTL 砍；ctx06 外部资料行不进偏好面；ctx07 缺失 source 装配不崩。

**面边界**：这些是**合规面**（合法性/召回纪律）全绿，不是**收益面**（解决率/utility）证据——两类证据在本报告中严格分开表述。

## L2 真模型层——BLOCKED_EXPLICIT（非无声 SKIP）

- 卡面 `heavy_token_required=false`；`budget.example.json` 冻结 `enabled=false, max_spend=null`（无授权不发收费批量请求）。四臂 live 层（M11 终判面）需要该授权，**缺失→明确 BLOCKED，不伪造、不以 Mock 冒充**。
- 模型账目：requested=无；actual llm_calls=0 / tokens=0 / cost=0。凭据存在性（B06 冻结 31 模型/30 key）≠预算授权；worktree 无 `.env`（gitignored），本卡按只读纪律未读取任何密钥。

## 验收逐条对照（卡面三条，全部可失败）

1. **合成结果不宣称真人留存；比较不丢失败** ✅：全报告限定 L1 合成用户模拟（NOT_MEASURED_HUMAN 显式标注）；未解决/缺失计入分母（`episode_rows.missing_or_unresolved`、denominator_notes）；分批按原顺序、无样本替换、无阈值调整。
2. **不用历史臂不能剥夺当前明确约束；selected 与 all 历史同可见范围** ✅：B 臂仅缺席可选历史，goal/plan mandatory 面四臂共享（PersonaWorld 同构播种，Surface-2 `goal_present` 三方式全 true 断言）；C（all）与 D（selected）同 M-03 预筛可见域，Surface-2 selected⊆input 断言 + D 门无放行权（选择集只能缩小）。
3. **同一 source 多摘要不加 n；利益门失败不靠全拒用通过** ✅：分析单元=episode/profile 簇，无摘要级 n 累积；证据 n 语义归 I05 `fold_evidence_refs` 单一权威（其 107 项服务面测试本次全绿复验，本卡不重写不削弱）；ctx08 实证全拒不过门（bypass 登记+保召回+precision N/A）。

## 工程门

- pytest 受影响面：**180 passed / 0 failed**（I02 门×2 套 + I05 策略×2 套 + 邻接 eval/prefilter/receipt 套）
- mypy：**59 ≤ 77 基线**（本卡新文件均在 `mypy app` 作用域外，清单零新增）
- ruff/black：新文件 **0 违规 / 已格式化**；既有文件零触碰
