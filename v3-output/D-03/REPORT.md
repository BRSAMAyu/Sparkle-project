# D-03 · Understanding 五维内部度量与校准 — Worker Report

**Status: READY_FOR_REVIEW**
**Base SHA:** 5abd1c4b5bd617608f4afe9a282ec2f1a93f119c（wt22 HEAD）
**Final SHA:** 同上（不 commit；交付 = 本报告 + changes.patch）
**Word count discipline:** 变更 = 4 个已跟踪文件修改（+167 行）+ 11 个新文件；词表 39（event_registry.py）**零触碰**（`git diff HEAD --name-only | grep event_registry` = 0）。

## 1. 解决的真实问题

替换「神秘 understanding_depth 百分比」。基线盘点发现现状有两套理解度量，各有飞轮反模式风险：

| 既有面 | 位置 | 问题 |
|---|---|---|
| 运行时 L0-L5 | `self_evolution_service.UnderstandingDepthService` | 纯 Redis 现算、原始计数里程碑，非决策相关度量（**未动，回归零回退**） |
| 每日 0-1 合成分 | `understanding_depth_metric_service` + `/insights/understanding-depth` | memory_injection=「注入越多越懂」贴近 §5「更多聊天量当理解增长」反模式；缺数据按 0 计（**未动，作为遗留趋势基线保留**） |

D-03 新增**可诊断五维内部度量真源**，每维可追溯到 D-01 事件域读投影/真实行为表。

## 2. 核心设计决策

**度量挂在确定性数据上，不挂在模型自评上**（卡面 work 2「禁止模型自评分当事实」）：

| 维度 | 公式（冻结） | 数据源（真实表） | 缺失语义 |
|---|---|---|---|
| coverage | mean(context_sufficiency_score) | `aurora_judgment_records`（Stage20 **确定性** judge——规则分桶非 LLM，已核实） | n<3 → unknown |
| correctness | 1−min(1,((neg+conflict)/usage)/0.5) | `memory_corrections`(否定动作) + `unresolved_conflicts` ÷ `context_pack_runs`(注入≥1) | usage=0 → unknown |
| scope_precision | 1−min(1,(scope_neg/feedback)/0.25) | `memory_corrections`(scope 面：scope_pause/update + memory_reference_corrected/denied) | 反馈通道 0 行 → unknown |
| freshness | 1−min(1,mean_lag_days/30) | 状态变更型 corrections 与被改记录 created_at 之差 | 无样本 → unknown |
| utility | accepted/decisive | `memory_corrections`(memory_reference_{accepted,corrected,denied}) | decisive<3 → unknown |

关键取舍（防假指标红线）：
- **correctness 分母 = 记忆被使用的次数**（注入 ≥1 的 pack run），不是聊天量——纠正的证据面是「用错」，分母必须是使用面。
- **scope/utility 的 dark channel = unknown，不给满分**：dev 实测（2026-09-20 只读）memory_reference_* 与 scope_* 面 live 0 行，声称「范围用得准/个性化有用」是无证据断言。
- **utility v1 = Immediate loop 接受率**，边界写入代码与 API 响应：这是个性化注入的即时接受度，**不是**因果性 outcome 改善；outcome 联动（D-05 intervention→outcome 关联 + D-02 truth-class 对比）在真实数据跑通后 bump 版本接入——不把相关性冒充因果（§5）。
- **动作分区不发明新词**：对 `MemoryCorrection.action` 的封闭分区（correctness 负/scope 面/freshness 状态变更/utility 决定性），单测从写方常量（M-08 `_USER_GOVERNANCE_ACTIONS`、`MEMORY_REFERENCE_OUTCOMES`、M-01 EPOCH/NON_EPOCH 族）**导入**校验每个被引用动作真实存在——防引用幻觉。

**校准机制**（两层，全部确定性无 LLM）：
1. **行为锚点对齐**：每维度量与外部可观察行为量对齐——coverage 锚 = 1−重复提问率（`chat_messages` 独立行为流，归一化沿用既有 metric service 单一真源）；行为定义四维锚 = 公式在取数时点的重算值。
2. **离线校准 + 漂移检测**：
   - coverage 仿射重标定（有界 OLS：a∈[0.5,2.0]、b∈[±0.25]；MAE 不优于恒等则不应用——**校准永不把误差变大**）。行为定义四维**不做拟合**（对自身行为拟合是循环论证），其校准 = 一致性检测。
   - 漂移检测：最近 3 行在**检测时点**从原始表重算锚点 vs 落行值 → 捕获落行后篡改 / late-arriving 数据 / 公式代码漂移；门限 = max(0.15 绝对, 基线+0.10 相对)。任一维 drift → overall red。

## 3. 实现清单

| 文件 | 内容 |
|---|---|
| `backend/app/core/understanding_dimensions.py` | 契约真源：五维公式/缺失语义/动作分区/冻结常数/可解释 summarize（纯函数无 I/O） |
| `backend/app/services/understanding_dimensions_service.py` | 真实表取数（user 隔离、7 天滚动窗）+ 行为锚点冻结 + 每日幂等 upsert |
| `backend/app/services/understanding_calibration_service.py` | 仿射拟合 + 漂移检测 + 校准运行落表 |
| `backend/app/models/understanding_dimensions.py` + 迁移 `d03_20260920` | `understanding_dimension_daily` / `understanding_calibration_runs`（挂 x06_20260919，单头保持） |
| `backend/app/api/v1/insights.py` | `GET /insights/understanding-dimensions`：可解释 summary，无单一百分比；漂移红维 value 扣发 |
| `backend/app/core/celery_tasks.py` + `celery_app.py` | beat `understanding-dimensions-daily` 03:55（与旧任务 03:40 错峰） |

UI 消费纪律（work 3）：API 只给 {status, band, value?, samples}；unknown 维 value=null+原因；漂移维 value=null+「pending recalibration」；overall 只报 ok/unknown 计数与证据面结论。移动端接线为后续卡（本次 backend 面）。

## 4. 证据

### 4.1 测试（217 全绿，最终合并跑）
- D-03 新增 62：契约 31（golden sha256 冻结 + 公式 + 单调性 + unknown 语义 + 词表交叉校验）/ 聚合服务 11（真实表端到端、纠正降 correctness、scope 误用降 scope_precision、窗口边界、用户隔离、幂等）/ 校准 12（误差量化前后、安全回退、**篡改注入红、late 数据注入红**、稳定不红）/ API 4 / 迁移 sqlite 重放 4。
- 回归 155：D-01 词表契约 + 幂等隔离（除 1 个 pre-existing 失败，见 §6）、M-01 认识论 3 套件、D-02 outcome ledger 契约+服务、旧 understanding_depth 3 套件、`test_migrations_single_head`。

### 4.2 变异必红（5 组，cp /tmp 备份逐字节还原，还原后 sha 比对一致）
1. `CORRECTNESS_TOLERANCE` 0.5→0.6 → 3 红（冻结常数+golden）
2. unknown 偷偷给 1.0 → 7 红（假指标红线）
3. 漂移门限调 999（检测器失能）→ 3 红（两个注入漂移测试+系统性 gap 测试）
4. golden JSON 篡改 0.6→0.7 未重冻 → sha 测试红；还原后绿
5. coverage mean→min → 2 红（golden）

### 4.3 校准误差量化（端到端实测）
构造 judge 恒 1.0、行为锚 5/7（重复提问率 2/7）的 4 日序列：拟合 b=−2/7（clamp −0.25）后 **MAE 2/7 → 1/28**（mae_before/mae_after 落 `understanding_calibration_runs` 可审计）；拟合对数不足时 map=identity 且同一 gap 读作 drift red——系统性失准在未校准时即被检测，校准后回到 aligned。

### 4.4 真实数据集成证据（dev DB 只读，零写入）
近 7 天 judgment Top3 用户用真实聚合过五维公式：coverage ok（0.667 / 0.833 / 0.833）；correctness 仅在记忆被使用过的用户上 ok（1.0），未使用者 unknown；scope/freshness/utility 在 dev 全体 honest unknown（对应反馈面 live 0 行）。**度量确实挂在真实事件/行为数据上，且缺数据如实呈现**。源可用性盘点（只读）：aurora_judgment_records 229 行/75 用户、context_pack_runs 243、memory_corrections 3（reject×2/epoch_bump×1）、unresolved_conflicts 0、memory.invalidated 0、tasks COMPLETED 380。

## 5. 与 D-01/M-01/D-02 的衔接（不重建真源）
- D-01：词表 39 零触碰；度量只读 D-01 域内的表；correlation/telemetry 边界未涉及（本卡无事件写入）。
- M-01：认识论分类不重建；correctness/freshness 消费 M-01 兄弟面（memory_corrections 动作流）的读侧；动作分区校验**导入** M-01 动作族常量。
- D-02：utility 的 outcome 联动升级路径已在契约注释与 API 边界声明中指向 D-02 truth-class 面（`query(truth_class=actual)`）+ D-05 关联，本卡不抢跑。

## 6. 已知限制与诚实声明
- **pre-existing 失败（非本卡回归）**：`test_event_idempotency_isolation.py::test_galaxy_service_mastery_outbox_row_carries_envelope` 在**干净 HEAD 克隆**（/tmp 克隆复现）同样失败——`app.gen`（proto 生成产物）不在 worktree，需 `make proto-gen`；本卡未动 galaxy_service。
- 迁移 `d03_20260920` 挂在 `x06_20260919`：在途卡（如 X-09）若同窗加迁移，合入时 down_revision 需 Leader 顺链（D-02 merge 同款已知操作）。
- utility/scope 维度在 dev 当前数据上恒 unknown——这是诚实态而非缺陷；两维转绿依赖 memory_reference 反馈面与 M-08 scope 治理在真实用户处产生数据。
- 漂移基线对行为定义四维是绝对门（其冻结锚点与落行值同源，基线误差恒 0，已在代码注释说明）；相对门只对 coverage 有增量语义。
- coverage 锚（1−重复提问率）是行为对齐的 v1 选择，不是「理解」的完备外部真值；锚点语义演进需 bump 契约版本。

## 7. 建议后续
- 移动端消费 `/insights/understanding-dimensions`（band 档位 UI）。
- D-05 intervention→outcome 数据量足够后做 utility v2（outcome-linked），届时 bump `understanding.dimensions.v2`。
- 校准运行可加人群面聚合（fleet 级漂移监控）——需产品决策是否建。
