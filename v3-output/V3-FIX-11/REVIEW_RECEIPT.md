# REVIEW_RECEIPT · V3-FIX-11（P0）Telemetry 渗入业务真值三链根治

- Reviewer: 独立验收 Reviewer（接任中断前任）
- 日期: 2026-09-19 ｜ 基线: wt2 @ 7ef808ee（未 commit 工作树 + v3-output/V3-FIX-11/{REPORT.md, changes.patch}）
- 约束: 全程 LIGHT；pytest 单文件/小批串行；dev DB 仅 SELECT；无 commit/push；守卫探针文件随验随删（已确认零残留、守卫复绿 4/4）。

## 1. 三链代码复核（逐条属实）

**T1（state_estimator_service.py）**
- 防抖收口在 service 层（单一 choke point），同时覆盖两个触发方（`api/v1/events.py:70` 与 `cognitive_stream_worker.py:157`），端点侧无需改动即覆盖 worker 路径——REPORT §1 的选型论证成立。`force=True` 无现存调用方（纯预留）。
- cap 公式 `min(min(1.0, wrong×0.15+total×0.02), 0.3)`：公式两项**均为**遥测派生，合并封顶在数学上完备；cap 作用面严格限于 cognitive_load（strain_index/interruptibility 公式核查无误，interruptibility ≥0.7，focus 模式 ≥0.5）。
- 残留（低）：防抖为 check-then-act，`get_latest_snapshot` 与 commit 之间的 await 使并发 burst 可在窗口内多铸快照；但每个快照值仍被 cap 无条件约束，安全相关边界不受竞态影响，仅"至多 5 分钟一次"退化为软目标。单实例 asyncio 与未来多副本均如此。可接受，建议后续卡随服务端调度器（force 消费方）引入时一并处理。

**T3（telemetry_boundary.py + worker + aggregator）**
- 常量真源成立：`EMOTIONAL_BLOCK_SENTIMENTS={anxious,frustrated,overwhelmed}`（与修前 aggregator 内联集逐字一致）；`TELEMETRY_SENSITIVE = 历史三件套 ∪ 前者`（⊇ 成立，不变量测试钉死双向）。
- **通道闭合穷举验证**（超出自报的加严复核）：全库 `CognitiveFragment(sentiment=...)` 写方仅四处——worker（behavior，修后拦截 ⊇ block 集）、guest_seed（behavior/capsule/interceptor）、community 分享复制（原样拷贝 source_type，behavior 拷贝同样被读取侧过滤）、其余 consumer（galaxy/focus/achievement/execution/chat_signal_collector）经 grep 确认**不写 sentiment**。关键加验：`POST /fragments`（`schemas/cognitive.py`）**无 sentiment 字段**，客户端无法借 capsule 通道注入情绪标签——capsule 通道确为用户自述内容，非可注入面。
- **存量中和**：dev 库 behavior 源仍有 501 条历史明文 sentiment（拦截只防新增），读取侧 `source_type NOT IN ('behavior')` 正好中和存量——双侧修复缺一不可，实证成立。

**T2（adaptive_replanner.py）**
- `JOIN users + registration_source NOT IN ('guest','seed')` 落在 0.7 门同一查询；既有谓词（confidence/is_archived）保留并有回归测试钉住；INNER JOIN 语义下已删用户的 pattern 自然出门（安全方向）。`EXCLUDED_COHORT_REGISTRATION_SOURCES` 常量真源就位。
- REPORT §3 对 receipt 建议"fragments→patterns 源头门"的不可实施澄清属实：`BehaviorPatternService` 只读 Task/FocusSession/ErrorRecord（代码复核无误）。

**守卫（test_telemetry_boundary_contract.py）**
- Tier1 目录级零容忍 + Tier2 双条件（源文件 marker ∧ WAIVED_MODULES 登记）+ 死 waiver 检测 + reason 必须具名 bound（filter/cap/debounce/gate/NOT IN）。注释剥离但保留字符串字面量的实现正确（tokenize 逐 token 过滤）。

## 2. 测试实证

| 项 | 结果 |
|---|---|
| 新增 5 文件（守卫 4 + 链路 17） | **21/21 passed** |
| 协调者指定命令 `-k "telemetry or state_estimator or cognitive_stream"` | 36 passed, 1 skipped, 0 failed |
| 回归批 A（estimator/aggregator/replanner×3/evidence_resolve + 新 21） | 49 passed, 0 failed |
| 回归批 B（event_pipeline/sufficiency/decision_context/cognitive_service_regression 等 12 文件） | 56 passed, 2 skipped（与自报分批 18+2/25/9/4 合计一致） |
| `test_c03_adaptive_replanner_wiring` 基线失败声明 | **实证为真**：HEAD 版 `adaptive_replanner.py:139` 已调用 `.scalars().all()`，c03 mock 返回无 `scalars` 的 SimpleNamespace；两文件均不在 patch 内，失败与本卡无关 |

## 3. 守卫双向探针（三轮，现场已还原）

1. 假违规必抓：state_aggregator/ **新文件**内 `text("select ... from tracking_events")` → Tier1 抓到（目录级覆盖 + 动态 SQL 字符串可见性双证）；services/evidence/ 新文件 import CognitiveFragment 无 waiver → Tier2 抓到，报错含修复指引（可审计）。
2. 不误报 + 动态可见性：注释提及 tracking_events → 豁免通过；`getattr(models, "CognitiveFragment")` 字符串字面量 → **仍被抓**。
3. waiver 放行：临时 marker + WAIVED_MODULES 登记（reason 含 bound 关键词）→ 4/4 绿。探针文件与测试临时改动已全部还原，终态守卫 4/4 绿、git status 与开工一致。

**动态 import 盲区评估**：运行期拼接标识符（"Cognitive"+"Fragment"）、importlib/base64 级混淆属真实盲区——但已属蓄意绕过范畴，静态守卫 + 代码评审的组合在此档位合理；`getattr`/动态 SQL 字面量等常规动态形态均已覆盖。

## 4. dev DB 只读复算（sparkle 库，仅 SELECT，零写入）

- **T2 池**：0.7 门 + 未归档 = **173 → 5**（自报 172；+1 为其查询后半小时内新增的 guest 行——guest 168/email 5，breakdown 证实数字漂移非口径差异）。167/168 条 guest seed 模式全部出门。
- **T3 窗口推演**（以 max(created_at) 为 now 复刻 24h 窗）：窗内 167 behavior-positive + 41 behavior-null + 6 reflection_auto-null；修前 dominant=positive、block=false；修后 sentiment 行清零 → emotion_hint 完全回退 server 侧 chat 分类（与自报 166/166 一致，+1 同为漂移）。
- **T1**：`user_state_snapshots` 0 行（休眠确认），无需写库验证。

## 5. 防绕过与审计性

- waiver 显式登记可查（模块名 + reason + bound 关键词三重），死 waiver 会红，marker 与登记漂移会红——审计性成立。
- **覆盖缺口（主要发现，非阻断）**：扫描集之外仍有约 17 个模块读取三张遥测衍生表（`core/plan_context.py`、`event_retention_service`、`evidence_health_service`、`core/celery_tasks`、`orchestration/context_builder`、`semantic/state_primitives`、`api/v1/cognitive`、`dashboard_service`、`persona_service`、`omnibar_service`、`analytics_service`、`unified_analysis_service`、`tools/prism_tools`、`core/profile_context`、`services/profile_context_service`、`memory_jobs`、`progress_narrative_service`）。**逐一核查均为 per-user 作用域，无跨用户污染路径**；其中 plan_context 将本用户快照浮点/pattern 注入本人 plan 生成 prompt，属决策邻接面但值已被 cap+防抖有界。REPORT §7 R2/R3 只披露了其中 4 个（persona/context_builder/progress_narrative/evidence_health），**plan_context 等未枚举**——波及面清单不完整，建议后续卡扩 TRUTH_PATH_FILES 或以目录策略收编 + 补 waiver 登记。

## 6. 行为影响评估

- **cap 0.3**：REPORT 如实声明了语义（方向保留、只封顶、服务端真值可在上限之上叠加）；当前消费面（plan_context prompt 浮点、runtime_context 的 focus_mode 布尔门）无阈值分支被"打死"（load 恒 ≤0.3 意味着未来若出现 >0.3/0.5 的阈值消费方需先解除本 cap——建议在常量 docstring 已有说明基础上，后续消费方引入时复评）。真实高负载用户的负载可见性被系统性压平至 [0,0.3]，属知情产品取舍且已声明。
- **strain_index 残留**：grep 确认唯一消费方是 plan_context prompt 展示，无决策门；R1"随首个决策消费方出现时同法封顶"的定级恰当。

## 7. 交付物核验

- patch 一致性：`git apply --reverse --check changes.patch` **通过**（patch ≡ 工作树差异，6 改 + 6 新）。
- 密钥扫描：无。测试环境变量均为内联 `SECRET_KEY=test` 假值。
- 收工状态：探针零残留、无进程/模拟器、/tmp 探针备份已删、dev DB 零写入、未 commit/push。

## 8. 结论

三链修复机制正确、红绿证据与 DB 复算相符、守卫双向实证有效、波及面声明基本诚实（覆盖清单不完整为唯一实质缺口，已枚举于 §5）。两项后续建议：(a) 扩守卫扫描集收编 plan_context 等第二跳读取方；(b) V3-FIX-01 合入时将其榜门口径指向 `EXCLUDED_COHORT_REGISTRATION_SOURCES` 常量，防双清单字面量漂移。

**VERDICT: ACCEPT**
三链根治在代码、测试与 dev DB 三个层面均获独立复现，防抖/cap/拦截集/SQL 口径逐条与自报相符且部分加严验证（sentiment 写方穷举、/fragments 无 sentiment 字段、存量 501 行靠读取侧中和）通过。守卫双层静态扫描经三轮双向探针实证能抓新违规、放行合规 waiver、不误报注释，动态 SQL 与 getattr 字面量均可检出。c03 唯一失败实证为基线既有问题（HEAD 即复现，与本卡无关）。主要残留为守卫扫描集外约 17 个 per-user 读取方未入 waiver 登记册（REPORT §7 披露不完整）与防抖 check-then-act 非原子（有界危害），均不阻断 P0 目标，建议开后续卡收编。patch 与工作树逐字节一致、无密钥、现场已清理。
