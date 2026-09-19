# REVIEW_RECEIPT_2 · B-02 第二独立 Reviewer 复核（协议要求 high-risk 双 Reviewer）

- Reviewer: 第二独立复核 agent（wt4 @ 51f5acd7），不信任 R1 结论与 Worker 自报，全部关键点自行重算/重读码
- 复核日期: 2026-09-19
- 被审对象: R1（REVIEW_RECEIPT.md，verdict CHANGES C1-C4）+ Leader 处置 commit 51f5acd7
- 复核方式: 主仓/主产出只读 + `docker exec sparkle_db psql` 只读 SELECT + mobile/backend/gateway/proto 代码实证；csv 模块程序化解析；未运行模拟器/构建/写路径（LIGHT 约束遵守）；live DB 已漂移（users 248），全部 SQL 以当前值重跑
- 定位声明: R1 已实锤四断言（top-50/100 全 guest、166/166 游客 is_pro、mock→Isar 链路、四类 namespace 可区分），本文不重复其 SQL；职责为 ①验证 C1-C4 修复本身 ②换角度抽查 ③找 R1/Worker 双方遗漏

---

## 一、修复验证（C1-C4 处置，5 项全过）

### ① data_truth_inventory.csv 结构（PASS）
csv 模块解析：header 9 列，**14 数据行全部 9 列、零错位**。
- INV-08 location（已加引号）= `backend/app/services/llm_service.py:291,339-340,386-387,542-549`，四个行号引用经读码逐一证实为真（291 settings 初始化 demo_mode；339-340 动态路由路径无 key 激活+warning；386-387 legacy 路径激活+warning；542-549 `_check_demo_match` 罐头回复匹配器）；evidence 引用的 `:340 logger.warning` 精确命中；truth_class=`demo` 归位正确。
- INV-09 remediation 含完整 `WHERE registration_source NOT IN ('guest','seed')`；location 含 `deleted_at IS NULL 对齐 not_deleted_filter`。

### ② JSON 与 CSV 同口径（PASS）
JSON 14 items × 9 字段与 CSV **逐字段全等**（0 mismatch，含 C2 修复前的乱序赋值已全部消除）；`truth_class_counts` 与 CSV 重算结果逐键相等且总和=14（demo 2 / mock(休眠) 3 / mock 1 / seed_namespace 2 / pollution 2 / actual 3 / actual(本地) 1），`revised` 修订注记在位。

### ③ 四处红测表述（PASS，口径一致且如实）
| 处 | 表述 |
|---|---|
| FINDINGS §三:71 | "红测…**未随本卡收编入库**（C1 修订…机制结论不依赖红测…）" |
| COMPLETION_RECEIPT Files:12 + checks#3:35 | 删除线 + "复核修订 C1：红测文件**未随收编入库**" / "~~运行…~~（文件未入库）改为对照代码路径" |
| lineage.csv row11 pollution_notes | "红测未随卡入库(仅工作树/探针记录; 复核方已代码级实证污染链路)" |
| inventory INV-02 evidence | "红测未随卡入库(仅工作树/探针记录; 污染链路由代码实证…)" |

如实性核验：`git ls-files` 全树无 `mock_statistics_guard*` —— 文件确不在库，四处表述与实况一致。
**P3 残余（不阻断）**：C1 列明的四处之外仍有两处旧表述——FINDINGS:21 摘要表"（红测已钉）"、COMPLETION_RECEIPT:7"1 个红测钉住…路径"。同文档 §三 已如实澄清，建议下轮顺手改为"探针+代码级实证钉住"。

### ④ F1 SQL 补条件（PASS）
FINDINGS.md:45 `WHERE u.is_active AND u.deleted_at IS NULL  -- C4 修订: 对齐服务 not_deleted_filter() (models/base.py:79)`，与 leaderboard_service 实际过滤语义一致；live DB 重跑结果与快照逐位一致（见 §四）。

### ⑤ commit 范围（PASS）
`git show 51f5acd7 --stat`：9 文件全部位于 `v3-output/`（B-02 六文件 + B-06/ENTITY_MAP.md 摘要行修正）与 `v3/`（fleet state、DYNAMIC_ISSUES 三条 V3-FIX），**零业务代码改动**（mobile/backend/gateway/proto 无一触碰）。V3-FIX-01/02/03 内容与四断言/修复映射逐条对得上。

## 二、换角度抽查（3 条 R1 未深查 lineage 项，全部自走）

### 抽查 A · home_exam_sprint（estimated_score_now / pass_probability）—— rating "estimated" 成立
- 后端：`exam_sprint_diagnostic_service.py:892` `estimated_score_now = round((earned_points/max(total_points,0.001))*100.0, 1)` —— 由用户真实诊断答题计分推导，非编造；`pass_probability` 为其公式衍生（`:1135-1145` forecast = score + improvement_window − risk_penalty）；`exam_sprint_dashboard_service.py:83-106` 从 goal_model/explicit prefs/diagnostic 摘要取数。
- mobile：`dashboard_repository.dart:73-85` demo 分支硬编码 `days_left: 5 / estimated_score_now: 71.0` —— **确被 `DemoDataService.isDemoMode` 门控**（lineage 注述逐字属实）；正常路径走真实 API。
- 结论：非 mock、非真实统计，属"明示的模型估计"，评级与"demo 硬编码 days_left=5/score 71 (gated)"注述均准确。

### 抽查 B · weekly_stats 族（INV-12）—— rating "actual" 成立
`analytics/weekly_stats_service.py` 全文件为纯 SQL 聚合（`func.sum/func.count` over StudyRecord/FocusSession/Task，user_id 强隔离，`get_weekly_summary`/daily trend），无任何 mock/random 分支。（同族 ProgressNarrativeService 未走读，记入 §五遗漏。）

### 抽查 C · demo_mode span（INV-08 C2 修复后新增引用 542-549）—— 成立
`:542-549` 确为 `_check_demo_match`（演示关键词→预设响应匹配器，`if not self.demo_mode: return None`）。`llm.demo_mode` span 属性在 643/938/1094/1105 四处设置，"仅 OTel span 可查"的门控描述属实。
观察（非缺陷）：`:497` 还有第 5 处 demo_mode 再推导点（`not provider.has_api_key`，可在 key 修复后解除 demo），INV-08 列表非穷举但无虚假引用。

### 附带 · home_weather（遗漏扫描中顺带）
`dashboard_service.py:313-348` `_calculate_weather` 为真实行为数据上的规则推导（2 日无完成→cloudy、焦虑占比>50%→rainy 等），lineage "actual 规则计算于真实行为数据" 成立。

## 三、断言 2 独立走读（IsPro 劫持链，五环自证 + 一项加强）

| 环 | 证据（本 Reviewer 读码） |
|---|---|
| 网关派生① | `user_context.go:129` `IsPro: user.FlameLevel >= 3`（逐字） |
| 网关派生② | `chat_orchestrator_chatflow.go:283-284` `if !profile.IsPro { profile.IsPro = fallbackUser.FlameLevel >= 3 }` |
| 契约 | `proto/agent_service.proto:140` `bool is_pro = 4;` |
| 引擎接收 | `agent_grpc_service.py:303` `set_request_user_tier(self._resolve_request_user_tier(request))`；`:268-289` `is_pro=true → tier="pro"`，否则 "free" |
| 引擎钳制 | `llm_router.py:235-237/255-257` 仅 `tier=="free"` 才钳制；`:867-877` free_tier_downgrade 将 TOP/MAX/PRO/PLUS/STANDARD/FAST 压到 ceiling |

**加强证据**：全 gateway Go 代码 grep 无 `user_tier` —— `_resolve_request_user_tier` 的 `extra_context.user_tier` 覆盖通道在生产网关侧无任何写入点（docstring 自述为未来扩展），故 **is_pro 是唯一过界 entitlement 信号**。
**结论**：R1 "entitlement 被劫持" 无夸大，且可更锐化——live DB 下 166/166 游客（flame=15）以 pro 免钳制进入模型路由（成本失控面），而 75/75 真实 email 用户（flame=1）反被压为 free 层（体验降局面）。方向对真实用户恰好相反于直觉，强化 T-truth-ispro（V3-FIX-02）的 P0 定级。

## 四、live DB 重跑（users 248 漂移后，只读 SELECT）

| 项 | 当前实测 | 与快照比 |
|---|---|---|
| users 分布 | guest 166 / email 75 / seed 7 | 漂移（219→248），方向一致 |
| flame≥3（is_pro 派生） | guest 166/166（全部=15）、email 0/75（全部=1）、seed 7/7 | 断言 2 成立 |
| F1 top-50 复算（含 deleted_at IS NULL） | `guest \| 50 \| 132.5 \| best_rank 1` | **与快照逐位一致** |
| understanding_depth_daily | guest 138 / email 7 / seed 1（**94.5% guest**，score 0.275–0.933） | 较 R1 时 92.6% 再升，污染加重 |
| user_node_status | 8478 行中 guest 8364（98.7%） | 与 R1 漂移后一致 |
| user_achievements | 1011 行中 guest 980 | 结构不变 |
| photon `guest_seed:welcome_bonus` | 165 行；guest 余额 100–1020 vs email 0–10 | 一致 |
| knowledge_nodes.is_seed / streak 注入 | true 72/157；guest longest 30·checkin 45（seed 25/52） | 一致 |

C3 的"快照会漂移、复核以重跑为准"注记经本轮重跑检验有效：全部结构性结论在漂移后仍成立。

## 五、遗漏清单（不计入本次 verdict，建议后续卡）

**新缺陷（本轮发现，计入 verdict，见 §六）**：
- **C5（必须）lineage.csv 5/20 行字段错位**：csv 模块解析，`insights_weekly_narrative`、`insights_growth_dashboard`、`understanding_snapshot` 三行缺 `mobile_data_layer` 值致其后整体左移 1 列（truth_rating 槽位被 pollution_notes 内容占据）；`cognitive_patterns` 缺 2 列；`photon_balance` 缺 4 列。与 C2 同类缺陷，但位于 B-02 主交付物 lineage.csv——R1 对该文件只做了语义级抽查与 row11 措辞复核，未做列数校验，故漏网。语义内容基本齐全，作为结构化基线则 5 行损坏（按 truth_rating/computation_logic 列做程序化消费即错）。**git 考古：96004ea5 原始提交即如此，非本轮修复引入**。修复 = 补齐缺失列值（三行补 repo 层取数描述，photon/cognitive 补 gateway/backend 空位），并全表重跑 13 列校验。
- **C6（应当）数量口径失实**：COMPLETION_RECEIPT:9 与 96004ea5 commit message 均称 "22 个用户可见数字"，lineage.csv 实际 **20 行**（含 3 个休眠脚手架行，真正用户可见仅 17）。改为如实数字或补齐缺失的两行。

**后续卡建议（R1/Worker/本 Reviewer 均未端到端走读的用户可见数字，per R1 建议 streak/understanding-depth/galaxy_mastery 已验）**：
1. insights_weekly_narrative（ProgressNarrativeService "LLM 于真实周数据"声明 + Redis 7d 缓存）
2. insights_growth_dashboard（GrowthDashboardService.build_snapshot 聚合）
3. understanding_snapshot（claims confidence/user_can_correct 链）
4. home_predictive（PredictionService confidence/fallback_used 是否如实透出）
5. home_growth_status（narrative rule|ai 双路 source 标注）
6. community_feed 查询路径（种子内容与真实帖混合的排序/曝光，DB namespace 侧已验）
7. cognitive_patterns（CognitiveWorker 分析产物）
8. focus_stats 本地 Isar+服务端对账 merge（`focus_statistics_repository.dart:345-417` 机制声明未独立复核）
9. photon_balance mobile 展示链（DB 侧已验，UI "不可转账"标注缺失属 D05 跟进项）

## 六、第二 Verdict: **CHANGES**

- R1 的 C1-C4 处置**全部验证通过**（修复忠实、如实、范围克制，无新引入问题）；四条断言经本路换角度重走无一推翻，断言 2 经五环独立走读后结论反而加强。
- 但本路在 R1 未覆盖的角度（lineage.csv 结构化解析）发现 **C5：主交付物 5/20 行字段错位**——与 R1 为 C2 定的"必须"级同类缺陷，按同一标准应修复后收编；随附 C6 数量口径失实（应当）。
- 两项均为文档数据修复，不动业务代码，预计一个 LIGHT 小卡即可关闭；B-02 的事实结论（FINDINGS/REVIEW_RECEIPT 承载）不受影响。
- P3 残余（不阻断）：FINDINGS:21 摘要表与 RECEIPT:7 的"红测已钉/红测钉住"旧措辞建议顺带改口径。

收工清理：本轮 /tmp 仅 `r2_verify_b02.py`（收工即删）；未起模拟器/构建/写路径；唯一持久产出为本 RECEIPT（wt4 内）。
