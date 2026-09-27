# WT664-D03 · Understanding 五维内部度量与校准 — 集成 HEAD 复核 + 死活裁决

- 会话：wt664（卡池 D-03）｜基线：main@9cb02bd9｜分支：agent/node-b/wt664/d03（零产品代码变更）
- 性质：D-03 已由 ad5efa35 落地合并（R2 PASS，2026-09-20）；本会话执行卡面执行协议「合并后在 integration HEAD 重跑相关检查」+ 双死岛关系裁决，增量不重做。

## 1. 双证判定：卡面已完成部分

1. **git 证**：ad5efa35「feat(D-03): understanding five-dimension internal metrics + calibration (reviewed)」在 main 历史（`git merge-base --is-ancestor` 实证），提交体含契约真源/服务/校准/API/迁移/62 定向+6 变异测试；其后 main 又落 1149 提交，其中 3 波触达 D-03 文件（68bd0c29 models Mapped 迁移、ba909e74 mypy 批 6、667001e6 D-07 insights.py 重构）均未破坏契约。
2. **状态证**：v3/.sparkle_v3_fleet_state.json `done[]` 含 D-03，合并注记「D-03 合入（R2 PASS 0P1/0P2；judge 真源性复核=规则分桶确认；d03 重挂 x03b；五维挂确定性数据+校准恒等回退）」；v3-output/D-03/REPORT.md 在库。
3. 备注：v3/07_tasks/tasks.json 的 D 流 8 卡 status 均为 TODO（含已合并的 D-01/02/04/05/07/08）——tasks.json status 字段未被集成侧维护，运行状态权威以 fleet state 为准；本会话不越权改 tasks.json（集成侧卫生项，见 §7）。

## 2. 死活裁决：understanding_benchmark 与 D-03 的关系

- `app/services/understanding_benchmark_evaluator.py`：wt652 改判 **DEAD 双死岛**（其唯一消费方 rule-bj 族已 DEAD；fixture 驱动、零运行时触发、零测试；lifecycle §2.1 :49 已注记）。
- 亲证零依赖：D-03 活体实现（understanding_dimensions_service / understanding_calibration_service / core/understanding_dimensions / insights API）grep 零 `benchmark` 引用，import 闭包只触 D-01/M-01/M-08 真实表模型。
- B-06 实体映射旁证（v3-output/WT657-B06/ENTITY_MAP.md）：UserInsightState/understanding_*/aurora_stage31 各面消费者不相交，无同概念双写。
- **裁决**：D-03 卡面 path seeds（state_aggregator/evidence/aurora）为导航种子，实际实现锚定真实表，未依赖死模块；死岛维持 wt652 判定与 lifecycle 注记，本卡不接线不重建（不得重建已存在的权威真源/接线即第二套记账，同 330 裁决逻辑）。

## 3. 卡面逐条验收对照（今日 HEAD 实测）

| 卡面条目 | 状态 | 证据（本 worktree 实测） |
|---|---|---|
| work1 五维计算+缺失语义 | 已完成 | 契约真源 core/understanding_dimensions.py（冻结常数+golden sha256）；62 定向全绿 |
| work2 从真实取证、禁模型自评 | 已完成 | coverage←aurora_judgment_records（Stage20 确定性 judge）、correctness←memory_corrections+unresolved_conflicts÷context_pack_runs、utility←memory_reference 接受率（显式声明非因果）；dev DB 只读复核 64 活跃用户真实取数 |
| work3 UI 只消费可解释 summary | 已完成（API 层强制） | /insights/understanding-dimensions 只出 {status,band,value?,samples}；unknown 维 value=null+原因、漂移红维 value 扣发、overall 只报 ok/unknown 计数；API 测试 4/4 钉死（unknown 扣值/漂移扣发/诚实空/遗留端点未动） |
| 验收1 每维公式/数据源/边界；缺数据=unknown | 满足 | contract 31 测试 + 服务 11 测试；本会话只读复核三暗通道（scope/freshness/utility）如实 unknown 带 unknown_reason，samples<3 如实 unknown，零默认 0/1 |
| 验收2 纠正与错误使用合理降维 | 满足 | 服务测试钉「纠正降 correctness、scope 误用降 scope_precision」（11 用例含窗口边界/用户隔离/幂等） |
| Forbidden 四条 | 未触 | 零 mock/seed；零真源重建；零守卫弱化；UI 纪律由 API 层承载 |
| required_evidence | 齐备 | base/final SHA+定向测试+dev DB 集成证据+review receipt（R2 PASS）均在首轮 |

## 4. 本会话验证件套（integration HEAD@9cb02bd9）

1. D-03 定向 5 套件 **62/62 绿**：contract 31 + dimensions_service 11 + calibration 12 + insights API 4 + d03 迁移 sqlite 4（worktree 补 gen 环境后；venv 软链主仓，隔离 worktree 无 .env 落 sqlite，TEST-DBGUARD 门卫合规）。
2. 邻域回归 **18/18 绿**：旧 understanding-depth API + metric service + 迁移 sqlite 三套件（遗留趋势基线零回退）。
3. 迁移单头 **2/2 绿**：d03_20260920 挂 x03b_20260920，单头保持。
4. **dev DB 只读复核（零写入，复刻首轮 §4.4 形态）**：/tmp 一次性脚本（不入库），collect_window_inputs+纯函数过公式，未 commit：近 7 天 64 活跃用户；样本 3 用户=coverage ok 0.9502（97 样本，top_missing 可诊断）/coverage ok 0.75/correctness ok 1.0（77 次使用机会 0 负纠正）/第三用户五维全 unknown（judgment 1<3）；coverage 行为锚=1−重复提问率（chat_messages 独立流）在 HEAD 正常产出；`understanding_dimension_daily` 行数复核前后均 0=真只读。
5. 零产品代码变更→ruff/mypy/守卫/契约零新增定义域为空集（触达文件集=∅）；worktree 内 D-03 文件两态 diff 为零。

## 5. 邻接面裁决（不扩卡，留痕）

- **遗留 /insights/understanding-depth**（每日 0-1 合成分，v0.1）：首轮裁决「未动，遗留趋势基线」+R2 PASS 维持；wt651 审计列真轨（真实离线聚合）。mobile 零消费（mobile/lib 全 grep 零命中）。**留痕警告**：其 docstring「前端按日期补零即可」与 D-03「缺数据=unknown」红线相抵——未来任何 UI 接该趋势前必须先改补零语义（无活动日≠0 分）；本会话不改（契约面零新增纪律+零消费方，改动无消费收益）。
- **/experience/understanding-snapshot**（mobile understanding_snapshot_card/panel/screen 实际消费面）：A-spec Aurora 控制面 claim 级置信，UI 为高/中/低置信档位+单 claim 百分比 pill+证据链，非 D-03 所指「神秘全局理解百分比」；D-03 五维 API 目前 mobile 零接线（首轮明确「移动端接线为后续卡」），work3 负向纪律（UI 不显示未校准百分比）当前全产品成立。

## 6. FIX 登记

无新登记（grep 台账至 V3-FIX-356；D-03 度量面未发现新的不诚实面——全部 metric 源于真实表、缺失如实 unknown、校准有界且 MAE 不优则恒等）。

## 7. 运行级待验清单（集成侧/运维窗口）

1. **dev/staging celery beat 落行验证**：`understanding_dimension_daily`/`understanding_calibration_runs` 在 dev 当前 0 行（beat 任务 wiring 完整：celery_app.py:1260 03:55 + celery_tasks.py:3870 含逐用户校准漂移，测试绿；dev 环境 beat 进程未长跑属环境事实）。真环境 beat 跑一晚后核「行数>0 且 drift/校准块落行」。
2. **tasks.json D 流 status 卫生**：D-01..D-08 全 TODO 与 fleet state done[] 不一致，建议集成侧统一（本会话不越权）。
3. **utility v2（outcome 联动）**：依赖 D-05 intervention→outcome 与 D-02 truth-class 真实数据量，届时 bump understanding.dimensions.v2——归后续消费卡，wt662（intervention×outcome）并行落地后为自然时点。
4. **移动端五维 band UI**（首轮 §7 建议的后续卡）：消费 /insights/understanding-dimensions 档位视图；当前无未校准百分比露出，接线非阻塞。

## 8. 结论

D-03 卡面在 ad5efa35 已完整交付并通过 R2 审查；本会话按执行协议在 integration HEAD（+1149 提交，含 3 波触达）完成可证伪复核：62+18+2 测试全绿、真实 dev DB 只读聚合成立、缺失语义与 UI 纪律钉死、双死岛零依赖裁决留痕。**建议集成侧将 D-03 记 ACCEPT（复核凭据=本文件），零产品代码增量。**
