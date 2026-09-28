# Q 线（Quality 8 卡）深挖章节 —— V4 交接文档素材（wt779）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」Q 线章节的深挖草稿，兼为 **Q-08 Final Gate Audit 的执行准备清单**（§Q.4-2 逐 gate 证据图）。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt779（2026-09-28，基线 main@c0306be1——撰写中途主干自 b12125ed 推进，已追平后定稿；快照时点 JOURNEY day7 终门（08:00）结果未入 notes）。方法：卡面（v3/07_tasks/cards/Q-0*.md）+ wt759 报告逐卡定位 → 全部交付 SHA `merge-base --is-ancestor` 亲证祖先（Q-01 `44252b88`/Q-02 `c6f0b342`+复验链/Q-03 `837f90e2`/Q-04 `66ab4dbd`+`12ce081b`+`7244efb2`/Q-05 `4671173e`+`61af0f0a`+`5236e68d`/Q-06 `12e89303`+`3717355e`+`a1587328`+`0f017515` 全过）→ 代码/数据开文件亲证（scenarios_v3.jsonl 逐行计数/v3_scenario_eval 六文件/q04_redteam 套件/test_q05_redteam_final.py）→ **测试实跑（O+Q 全部交付套件 445 passed @c0306be1）**→ 产物抽读（WT394 raw+HUMAN_INBOX/WT400 summary/WT401 rubric/WT404 REPORT+dashboard/WT406 REPORT+facts/WT460 REPORT）→ 台账闭环逐条复核（FIX-49~58/67~81 状态逐行）。**未轻信任何台账/报告结论性文字。**

---

## Q.0 线级概览

Q 线是 V3 的「终验执行器」：统一 Runner（Q-01）→ 20 Golden Journeys（Q-02）→ 视觉 QA（Q-03）→ 个性化红队（Q-04）→ 安全红队（Q-05）→ 性能/成本/波动终验（Q-06）→ Chaos/Restore Storm（Q-07，未启动）→ Final Gate Audit（Q-08，未启动）。当前 **6/8 done**（tasks.json@c0306be1 亲证；主档 §3「Q 线 1/8」系 wt759 销账前的陈旧口径，该行自带 ⏳ 待复核标记，本档即复核结果：**Q-01~Q-06 六卡全部有主干交付 SHA+产物**）。

Q 线执行形态的三个特点（V4 设计者必须先读）：

1. **「诚实 FAIL」是合法交付形态，且已被行使两次**——Q-04 总判定 FAIL（precision 0.0 / invalid 硬门违反 ×10 / overpersonalization 41.67% / uplift 0.0pp 原样交付）；Q-02 首轮 13 PASS/6 FAIL/1 RESTRICTED **0 waive 全部转动态卡**。Q 线的价值标准是「找出边界」而非「证明好」——这是全库诚实性教义最重的两个样本。
2. **「修而不复跑」是 Q 线最大的结构残差**——Q-02 与 Q-04 的全部修复都闭账了（FIX-49/51/53/54/55/57、67~70 逐行核验 FIXED@），但**两张卡都没有一次修复后的全量重跑**：Q-02 的终态=首轮 13/20+局部复验（wt400 只复跑 6 条 GJ，其中 GJ08 该轮 5/6）；Q-04 的终态=修前 FAIL dashboard+契约锁翻转（两锁+双失明锁）。最终状态口径=「首轮诚实判定 + 逐缺陷修复 + 局部复验/锁级证据」。**Q-08 终门必须对此显式裁决**（补全量重跑/按锁级证据判/如实判 FAIL 或 NOT_REMEASURED 三选一，两卡驱动都在库可复跑）。
3. **证据形态好于 D/E 线**——Q-02/03/04/06 有完整卡级产物目录（raw JSONL/REPORT/rubric/dashboard/chao­s_results），台账证据指针零死链（本档对台账引用的四个 Q 线目录逐一 `ls` 亲证在库）；Q-01/Q-05 无卡级目录但产物=在库测试套件+commit 内签收（wt759 已裁决合规、按 wt774 先例作形态残差不占号）。

---

## Q.1 意图（卡面目标与验收）

八卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| Q-01 260 场景统一 Runner 与证据格式 | medium/MEDIUM/1 | scenario library 变成可运行 deterministic/model/simulator runner | 260 case 可枚举；unsupported 不算 PASS；结果 JSON schema 稳定 |
| Q-02 20 Golden Journeys 三端终验 | medium/HEAVY/1 | 核心产品真实跑通，不是模块测试拼接 | 所有 required journey PASS；失败生成动态卡不用 waive；核心 GJ 三端或明确平台适用 |
| Q-03 Autonomous Visual QA 最终波 | medium/HEAVY/1 | 以用户视角对 final RC 逐屏视觉审查 | 核心 journey A/B=0；其它 reachable A=0；before/after 可对比 |
| Q-04 Personalization 独立红队 | high/MEDIUM/2 | 独立攻击「越用越懂我」 | 达 V3-4 指标**或明确 FAIL**；invalid=0 硬门；失败案例原样保留 |
| Q-05 Security/Privacy 最终红队 | critical/MEDIUM/2 | 从隔离/工具/Memory/community/entitlement 攻击 | P0/P1=0；cross-user=0；unauthorized side effect=0 |
| Q-06 Performance/Cost/Provider 波动终验 | medium/HEAVY/1 | 验证 V3 不因智能化变慢变贵到不可用 | p50/p95 only if n≥100；false smooth=0；SLO 不达即 FAIL/动态修复不剪异常 |
| Q-07 Chaos/Recovery/Offline/Restore Storm 终验 | critical/HEAVY/2 | 新 Runtime/Context 下重跑故障恢复，防回归历史雪崩 | false success=0；duplicate=0；历史 restore storm SLO 不大幅退化 |
| Q-08 V3 Final Gate Audit / Commercial RC | critical/MEDIUM/2 | 逐项审 V3 DoD，输出唯一最终状态 | DoD 每条有 evidence link+PASS/FAIL/BLOCKED；不能用「107 任务完成」替代产品 gate；输出 FINAL_V3_GATE_REPORT.md |

---

## Q.2 实际交付逐卡

### Q-01 · 260 场景统一 Runner 与证据格式 —— done（`44252b88`，09-21，R2 PASS）

**交付（本档逐项亲证）**：

- **场景库**：`v3/05_metrics_eval/scenarios_v3.jsonl` **实测 260 行**；run_mode 分布 integration 54 / model 122 / simulator 84（逐行 json 解析计数，与 commit 一致）；12 类目（memory 36/first_value 24/conflict 24/ui_state 24/proactive 24/journey 24/allocation 20/agent_runtime 20/rag 18/security 18/performance 16/community 12）；case_id 恰为 V3-001..V3-260 无缺无重（scenario_schema.py:9 冻结校验）。
- **三路由 harness**：`backend/tests/v3_scenario_eval/`（六文件 2060 行：grading 505/harnesses 778/runner 223/schema 173/gate test 380）；34 frozen checkers。
- **unsupported 永不计 PASS**：聚合唯一出口判定；72 项诚实降级（wall-clock/L3-real-stack/ui-render 类）逐项 provenance 记录。
- **schema 冻结**：`sparkle.v3.scenario-results.v1`（runner.py:38）+ `verdict_semantics=contract-simulation` 钉死（runner.py:42、harnesses.py docstring「确定性参考实现」）。
- **RealModelAdapter 结构性零绕过**：无网络 import、无条件 raise（"real model calls are forbidden this round"）、无 env 门——真模型调用的禁止是**结构不可能**而非约定；seed sha256 per-attempt 确定性。

**验证**：gate 27/27（本次实跑绿，含在 445 内）。

**残差与 V4 必读**：① **「260 场景」的 verdict 语义是 contract-simulation**——跑的是确定性参考实现的判定，不是真模型/真产品全链；「260 全绿」≠「产品全绿」，V4 引用时必须带此定语（schema 里钉死的正是这个诚实性）。② model 型 122 例在 mock-provider 上跑（reference-mock-v1），simulator 型 84 例是 stub——三路由的「证据强度梯度」由 provenance 逐 case 记录，终门引用时应按路由分层引用。③ 卡面「支持 repeat/seed/provider config」：repeat/seed 在 schema（repeat 字段实测在 jsonl）；provider config 面=RealModelAdapter 的预留接口（raise 形态），真 provider 接入未发生（与 E-04/M-09 的真模型 eval 分工）。

### Q-02 · 20 Golden Journeys 三端终验 —— done（`c6f0b342`，09-25；修复链+局部复验；**无修复后全量重跑**）

**首轮（wt394，常驻栈双端 200 真服务 API 级 headless）**：**13 PASS / 6 FAIL / 1 RESTRICTED，0 waive**。证据 `v3-output/WT394-Q02-GOLDEN/`（summary.json + raw/20 条 journey 逐步 JSONL + REPORT.md + HUMAN_INBOX.md，本档 ls 亲证在库——先前后缀写短了误判缺失，特此留痕）。6 条 FAIL 同根因 chat 工具分支流中断（FIX-53 P1：200 空体/ECONNRESET，「我卡住了」跨编码×跨入口×双客户端 10+ 复现）+GJ10 叠加文档删除无 HTTP 出口（FIX-54）+guest 种子静默失败（FIX-55）+网关熔断级联（FIX-56）；GJ19 remote 无云端如实 RESTRICTED。通过面覆盖 fresh→goal→action（GJ01）/示例升级（GJ02）/命令路径审计链（GJ03/06）/hybrid run 幂等（GJ07/13）/galaxy 证据回流（GJ05）/stale plan 重锚（GJ11）/通知面+mute 抑制（GJ12）/run 恢复 admin 门+resume（GJ14）/squad checkin→错题共享（GJ16）/低刺激持久化（GJ17）/跨账号零泄漏全 40x（GJ18）。

**修复链（台账逐行核验）**：FIX-49/50/51 FIXED@`28442a5a`（wt412）；FIX-53 FIXED@`10d3d7e8`（wt400 三根因：_normalize_conversation_id TypeError/OpenAI 流式 tool_call 契约按 index 关联/growth_strategy_tools await 优先级——兜底层 event_generator 全包裹+SSE error 事件下行）；FIX-54/55/57 FIXED@`95dff6bf`（wt709 引链纠指定位集成）；**FIX-52 OPEN**（行为事实证据无双刃消解，随 A-03 迭代）；**FIX-56 OPEN**（wt474 分诊：网关仓无显式熔断实现，502 级联真源待排查，行内「熔断阈值」归因待勘误）。

**局部复验（WT400-FIX53-REVERIFY，worktree 真栈 :8001/:8081 真实 LLM）**：6 条 GJ 复跑——GJ04 8/8、GJ09 5/5 回暖；**GJ08 FAIL 5/6**（episodic_count=0——commit message 叙「GJ08 6/6 回暖」与 summary.json 5/6 存在轮间波动，raw 在档）；GJ10 14/14 步过但 delete 拍语义不可测（FIX-54 当时尚未修）；GJ15/20 残留续写空文本（新开 FIX-57，后修但真栈复验 DEFERRED——台账原注「需常驻引擎+真 LLM key 窗口」）。

**残差（V4/终门必读）**：① **修复后从未有一次全 20 GJ 重跑**——「所有 required journey PASS」的验收以「首轮+逐 FIX 闭账+局部复验」链式成立，Q-08 必须显式裁决此口径；② GJ19 remote RESTRICTED 等 O-01；③ 视觉/真机/远程三段转 HUMAN_INBOX（WT394-Q02-GOLDEN/HUMAN_INBOX.md 清单 17 项+真机段 B 项在库，未采集——FIX-511 同族）；④ 驱动 `scripts/devtools/q02_run_golden_journeys.py` 在库可复跑（--help 程序化汇总）。

### Q-03 · Autonomous Visual QA 最终波 —— done（`837f90e2`，09-26）

**交付（WT401-Q03-VISUAL/ 全套产物在库，rubric_scores.md 本档抽读）**：真实 GoRouter 泵 standard 档 390x844@2x **逐屏真渲染截图 107 张**（核心 13 屏 19 态+long-tail 85 屏+参数屏缺数据态）；逐屏程序化探针（溢出异常/截断候选/越界 widget/WCAG 对比度采样）修复后 **107/107 零异常**；红测先行修 4 真缺陷（G1 A：发布动态心情条 390w 溢出 66px 第 5 chip 不可达→横向滚动；G2 B：连胜 ticker mixin 双 controller；G3 B：海报生成窗口期 context 失活调 Theme.of 整屏红→主题快照；G4 B：星图模式面板 top:112 被 top:48 统计列压住→挂入同列流式）。

**12 维 rubric 终态**：核心 13 屏逐屏 12 维打分表在库——**核心旅程 A/B 合计=0**（遗留 C：C02 density 首屏三层叠/C03 时间戳对比度 3.08/C05「普通」1.74/C06 品牌字 4.28/C11「75 分钟」2.50——全部次级信息 C 级带坐标证据）；long-tail 85 屏 12 维汇总（Clarity 1.93~Consistency 2.0）**A=0、遗留 C 7 项**；before/after 6 组成对+并排合成图。q03 套件 26/26+守卫 4/4 红→绿+analyze 601=601 零漂移。

**附带登记**：V3-FIX-57（P2 连胜概览文案窗矛盾）/58（P3 星图 rail/CTA 重叠，先于本卡存在）/59/60。

**残差**：① 单档单尺寸（standard 档 390x844@2x）——低刺激档属 wt399 不触碰、三端真机尺寸未渲染（转 HUMAN_INBOX）；② 「独立 visual Reviewer」的独立性=程序化 12 维 rubric+独立会话产物（非独立人类/独立模型审查者）；③ 截图基线与 U-09 的 visual_baseline.py matrix 命令的回归链是**就绪清单**非已建基线（U 线章已述，本卡同口径）。

### Q-04 · Personalization / Overpersonalization 独立红队 —— done（本体 `66ab4dbd` + 修复 `7244efb2`/`12ce081b`；总判定 **FAIL 如实**；**修复后无全量重跑**）

**首轮六路攻击（10/10 persona × 六路双跑，dashboard 逐字节一致）**——WT404-Q04-REDTEAM/（raw/redteam.jsonl 100 记录+blind 四件套+dashboard.json+DASHBOARD.md+REPORT.md）：

| V3-4 指标 | 目标 | 实测 | 判定 |
|---|---|---|---|
| precision | ≥95% | **0.0**（observable uses 10 全为被否认记忆复活；纠正后偏好 0 次到达输出面——selfcheck 词面门） | NOT MET |
| invalid memory use | =0 硬门 | **10**（patch 归因跨 scope，V3-FIX-67） | **VIOLATED** |
| overpersonalization | ≤5% | **41.67%**（50/120） | NOT MET |
| paired uplift | +15pp | **0.0pp**（双臂决策全同） | NOT MET |

PASS 面（隐私与隔离的四路）：敏感信息零泄漏（含切题轮）/删除撤回注入三面零复活/跨用户 pack+squad+spine 零串号/无关历史零上 prompt 面。findings 4 类 50 条照登（FIX-67/68/69/70）。

**paired blind review 方法（卡面「Reviewer 不看实现」的机械化）**：20 对同 context 双臂候选；臂→候选映射 seeded RNG（`pair_id::v1`）单独落 blind_key.json；pairs 文件零臂标识（契约测断言）；冻结程序化 rubric 只读 pairs 打分→评审后解盲 join；**模型 judge 0 次**（全部确定性词面/链头/差分判据）。结果：rubric 偏好 personalized 8/20、control 12/20；双臂决策质量全同——**个性化臂在决策面零增益的根因=纠正后偏好/自评主张几乎全被 selfcheck 词面门切掉，从未进入决策上下文（precision=0 的同源根因）**。

**修复与锁**：FIX-67 FIXED@`7244efb2`（applied_patch_ids 对齐 situation_patches 同一 scope_matches 谓词）；FIX-68/69/70 FIXED@`12ce081b`（种子库筛查+围栏+来源标注三层；prompt_note loser 改 id 归因零原文；deny 确定性标记+72h 冷却窗）——**q04 两锁翻转为修复后形态（L1 loser 零过境/L2 deny 后零同位复活）+双失明锁（合成过境/复活记录仍须被 _invalid_events 计出）**；FIX-70②隐式漂移吸收如实 DEFERRED（行为反证阈值属产品决策）。测试：backend/tests/q04_personal_redteam/ 套件（engine/metrics/protocol/worlds+test_q04_redteam_final.py），本次实跑绿（445 内）。

**残差（终门 V3-4 的直接输入）**：① **修复后无六路全量重跑**——dashboard 的 FAIL 数字是修前快照；invalid=0 硬门的「现值」只有锁级证据（两条翻转锁+失明锁），没有 dashboard 级复测；② precision 0.0 的同源根因（纠正后偏好不到输出面）与 FIX-36（渲染器不渲染偏好值）同族——M-09 侧的「真模型复验」欠账已在册（V3-FIX-503 OPEN）；③ uplift 0.0pp 的深层问题（模拟人口上个性化无增益）与 A 线章 A-08 终态（no_memory 臂双指标反超 full）**互相印证**——两个独立 eval 指向同一结论：**当前实现下记忆/个性化面对模拟人口的净贡献未被证明为正**，这是 V4 个性化设计的最重要负面输入。

### Q-05 · Security/Privacy/Permission 最终红队 —— done（`4671173e` + 合并态补修 `61af0f0a` + 审查轮4 `5236e68d`，09-25/26）

**交付（commit message 逐项+测试在库亲证）**：五路攻击面 **43 scenario** headless 真实链验证——跨账号/local cache/prompt injection/tool escalation/revoked memory/seed namespace；**当场修 4 缺陷**：P0 seed 跨账号私库泄漏 / P1 轨迹 revoked 复活 / P1 错误本记忆复活 / P1 日志敏感正文（合并态验证抓到工具历史失败日志带 [parameters] 正文——worker 单跑未触发路径，教训「合并态验证必须跑跨卡重叠文件组合」入 fleet notes）；`test_q05_redteam_final.py`（1145 行）+stubs 在库，本次实跑绿（445 内含 security 套件）。独立审查：wt410 审查轮 4（5236e68d）+wt424 审查轮的注入围栏变体逃逸族由 wt432 修复（cd36f682，FIX-112/113）——**Q-05 的审查不止一轮**。

**残差**：① 无卡级 v3-output 目录（签收在 commit message；台账零死指针本档复核——按 wt774 先例形态残差不占号）；② 卡面「动态扫描+手工 scenario」中手工 scenario 面与「logs/trace 无敏感正文」的运行级证据未在产物层定位（判定域=43 scenario 套件覆盖面）；③ 与 O-03 分工：O-03=机制红线对抗复测+修复（词表 fail-closed），Q-05=最终面确认（跨账号/工具/Memory/community/entitlement 五路）——终门引用时按此分工。

### Q-06 · Performance / Cost / Provider 波动终验 —— done（本体 `12e89303` + 修复族 `3717355e`/`a1587328`/`0f017515` + 真栈复验 wt460；**「400 样本 0.06s」的出处卡**）

**路线一：分层 bench（400 真样本，L0-L3 各 n=100，50 distinct × 2 reps；真实 dashscope/deepseek/zhipu/xiaomi 上游，guest JWT→gRPC StreamChat；WT406-Q06-PERF/raw-bench.jsonl+facts-bench.json）**：

| 层 | n(ok) | TTFT p50/p95 | total p95 | 首事件 p95 |
|---|---|---|---|---|
| L0 | 100 | 0.91s/1.88s | 22.97s | 0.04s |
| L1 | 100 | 1.58s/2.25s | 35.01s | 0.05s |
| L2 | 98 | 1.80s/9.36s | **48.25s** | 0.04s |
| L3 | 95 | 7.20s/**141.40s** | **215.03s** | **0.06s** |

**SLO 判定 4 PASS/2 FAIL/1 NOT_REPORTABLE**（对照 E-08 修前 2/6）：L1 双达标改善；**L3 ACK 0.06s 由 E-08 的 7.03s FAIL 转准=最大改善项**（wt380~wt400 修复链直接证据）；**仍 FAIL：L0 no-model 1879ms（TRIVIAL 不跳过生成链，E08-ISS-L0-TTFT 悬置）与 L2 total 48.25s（15s 预算 3 倍+）**。tier 账本复活实证：fast263/plus67/max25/standard2 四车道（对照 E-08 塌缩 85/85 全 fast）；wt392 提权封堵实测（free+伪造 user_tier=pro 仍 fast）。成本全量 $0.7288（$0.0018/query；L3 单条是 L0 的 61 倍，73% 成本集中于 deep_analysis pro 车道）。计量盲区 39/400 model='default'→FIX-80。

**路线二：供应商波动注入（七场景+干净对照，7→11 个 provider base_url 指向本地 mock，产品代码零改动）**：单点 429/慢 TTFT<60s/单车道断流=弹性合格（换道/限速学习/stage 反馈）；**全断供/全慢/过载三面不合格实锤**（S2 全断 6/12 烧满 180s 静默+6/12 未标注模板文本顶替；S5 过载 22/30 烧满 150s）→ **FIX-77~81 全修**（77 FIXED@a1587328/78/79 FIXED@3717355e/80/81 FIXED@a1587328）+**wt460 真引擎复验**（S2：11/12 error 帧 code=8 UNAVAILABLE retryable、首探针 ≤13.7s≪180s、每模型连败封顶 5 而非 86；S5：cap=20 下 30/0 全部 ≤15.1s；S5 改善归因如实并报 wt400/410/416 同窗变更）。

**路线三：增长标度**：episodic 10→1000 行 Context token **完全水平**（护栏三层生效）；preference 版本链 25→500 行 build 亚线性（b=0.142）——无 O(n²) 灾难，PASS。

**方法论诚实样本（V4 教材级）**：① **首轮数据作废声明**（注入面不全：4 个 provider 未重定向，「成功」样本混入真实 xiaomi 答案；S3a 受内存健康残留失真——首轮 raw 不入交付，全部重跑）；② n=60 深载探针触发共享 PG 连接顶（too many clients）**立即停止该量级探测**并登记（FIX-156）——「不剪异常」与「不制造事故」的边界示范。

**残差**：L0/L2 两项 FAIL 未修（E-08 族承接，E 线章已给复测路径）；FIX-57 的 GJ08/GJ15 真栈复验 DEFERRED 在册；bench 的「帧间最大静默 p95=10.1s 恒定值」系统性节奏未归因（疑似 stage/心跳帧间隔）。

### Q-07 · Chaos / Recovery / Offline / Restore Storm 终验 —— TODO 未启动（前置接近就绪）

依赖 X-09✓（`0c0e08ef` dual-reviewed：18 failure_kind×账本证据→四归因分类器 162 组合×100 次零偏差、UNKNOWN_OUTCOME 禁自动重试=duplicate side effect=0 机制根源、SIGKILL 真实杀进程 e2e、recover_inflight_runs）/ **O-05 交付待审** / U-06✓。

**Q-07 执行计划草案（基于本档盘点，供派卡参考）**：

1. **现成资产三层复用**（全部在库亲证）：① chaos rig=wt406/wt460 的 `q06_provider_chaos.py`+mock 上游 :9099+「场景间引擎重启」隔离纪律（wt460 已把注入面补齐到 11 个 base_url）；② 恢复面=O-05 的 `restore_consistency_check.py` INV-1..7 + `scripts/backup_prod_data.sh`/`restore_prod_data.sh`（已修版）+WT773 一次性容器栈形制（零触碰常驻栈）；③ 失败语义面=X-09 failure_semantics+X-05 sweep+461 PEL 重放/469 幂等闸/487 清理接线的耐久测试族。
2. **卡面 Work 六项对应执行面**：worker kill（SIGKILL celery worker mid-task→PEL 重放断言，461 族先例）；Redis issue（瞬时断连/重启→**注意 wt780 后新登记 FIX-530 P1：billing 队列消费者 BLPOP 遇 Connection reset 引擎进程死亡——此缺陷与 Q-07 Work 1 直接相关，建议先修再验**）；Celery issue（queue backpressure 已有单测，需真栈面）；network toggle/app restart（GJ13/GJ14 已 PASS 面+U-06 状态机）；**20 concurrent restore**（restore_prod_data.sh 到一次性栈+并发 run query+INV-1..7 断言+M-07 墓碑/epoch 门防已删 memory 复活——O-05 判例的并发扩展）；EndpointShield/dispatch async 仍有效（X-05/09 已交付面回归）。
3. **验收判据**：false success=0（chaos S4b「模板顶替」形态的回归探针——FIX-78 修复后未标注降级文本已消除，需在 restore/离线面重验同语义）；duplicate=0（X-09 幂等键纪律+FIX-335/336 闸）；历史 restore storm SLO 不大幅退化（历史锚=X-09 SIGKILL e2e+461/469/487 修复链的基线数字）。
4. **顺序建议**：O-05 审查回账→Q-07 本地容器栈先行→remote 段（若 O-01 解锁）或如实 RESTRICTED。估量 HEAVY：六项 Work 全走真栈约一个整窗。

### Q-08 · V3 Final Gate Audit / Commercial RC —— TODO 未启动（全链唯一压轴，唯一缺的前置=Q-07）

依赖 Q-02✓ Q-03✓ Q-04✓ Q-05✓ Q-06✓ D-08✓ P-05✓ G-05✓ + Q-07（未启动）。

#### Q-08 验收标准逐条盘点（卡面 Work/Acceptance × DoD V3-0..V3-10 证据图）

**卡面 Work 三条的准备度**：
- Work 1「读取所有 gate 原始证据，不只任务 status」——**就绪**：本档 §Q.4-2 证据图即索引草案；每 gate 的原始产物（jsonl/json/REPORT）都在库可程序化复核。
- Work 2「未执行标 NOT_RUN；未达标 FAIL；外部依赖 BLOCKED」——**纪律在库已被示范**（Q-04 FAIL/Q-02 RESTRICTED/wt346→wt759 的 BLOCKED→交付演化链），执行无障碍。
- Work 3「生成 RC manifest/SHA/config/model/flags/deploy/runbook」——**大半就绪**：O-06 `GET /api/internal/ops/release-manifest` 已给 model/config（release 五旗冻结键集+64 能力快照）/migration（alembic 双侧对账）；**缺口①git SHA**（O-06 设计决定「运行时进程不可靠自证构建 SHA」——Q-08 需 build-time 注入（属 O-01 部署面）或 out-of-band 记录集成 SHA 并显式注记）；**缺口②deploy**（O-01 未启动→deploy 段=BLOCKED/本地 compose 形态注记）；**缺口③runbook**（RUNBOOK_DEMO.md 在库；docs/05_部署与运维/RUNBOOK_LLM_HEALTH_RESET.md 先例存在）。

**卡面 Acceptance 三条**：
- 「DoD 每条有 evidence link 和 PASS/FAIL/BLOCKED」——§Q.4-2 即底稿。
- 「不能用『107 任务完成』替代产品 gate」——结构上已满足（DoD 是产品级条款；且 101/107 现状+7 张非 done 卡的存在使这个替代诱惑天然不存在）。
- 「输出 FINAL_V3_GATE_REPORT.md」——纯执行项。

**DoD 十一个 gate 的证据图（PASS 候选 / 需补 / 需裁决三分）**：

| Gate | 已天然满足的证据面 | 需补/需裁决（终门前必须处理） |
|---|---|---|
| V3-0 Truth | 42 feature portfolio 双产物在库（B-01 MODULE_MATRIX.csv 五态+RECEIPT 42/42 EXACT MATCH）；B-01 759 模块四态审计；FIX-258 origin 标记（demo 产出不喂记忆推断）；FIX-333 能力宣称真实化（五族状态机） | **portfolio 词表分裂（本档登记 V3-FIX-513）**：DoD 枚举 CORE/CONTEXTUAL/LABS/HIDDEN/RETIRE，而 MODULE_PORTFOLIO.md 用 CORE 15/CONTEXTUAL 15/LABS 5/SECONDARY 3/CORE_OPTIONAL 1/HIDDEN 1/INTERNAL 2（**RETIRE=0**）；B-01 矩阵基线 a2d8a10c 距今 9+ 天未随 HEAD 复核（GOV-015/WS6 删 3958 行、FIX-490 learning-mode 摘除等 reachability 变化未入册）——终门需裁决唯一真源+复核或显式钉时点 |
| V3-1 First Value | J-01 真驱动 5 persona（A/J 章口径）；Q-03 核心 A/B=0；JOURNEY day1-6 门 PASS | J-02 simulator 补证卡排队门后（wt772 审查 PARTIAL 不销账）；「≤3 分钟」的数字锚=J-01 面非统计口径 |
| V3-2 Stuck→Action | A-08 修后终值（对照侵入 0/friction 门生效）；FIX-49/50/51 修；Q-01 journey/conflict 族覆盖 | **「20 个代表性 friction scenario ≥18」无直接单数证据**——最近似锚=A-08 四臂（journey 面 accuracy 0.45/0.55/0.45/0.30）与 Q-01 的 contract-simulation 判定；终门需裁决 evidence link 的映射口径 |
| V3-3 Human-AI Collab | X-10 77 场景（allocation 100%/high-risk auto=0/false success=0，real_llm_calls=0 显式）；X-05/09 run 状态机可恢复（GJ14 PASS 面） | 基本齐；rubric 符合率「≥90%」的统计锚在 X 线章（77/77+85 场景盲评），终门直接引用 |
| V3-4 Personalization | 隐私与隔离四路 PASS（Q-04）；M-07/M-10 删除级联（红→绿）；FIX-67~70 修复+锁 | **Q-04 修后无全量重跑**（dashboard=修前 FAIL）；precision 0.0 根因与 FIX-503（M-09 复验欠账）联动——终门三选一：补跑（q04 驱动在库）/按锁级判/如实 FAIL；**uplift 0.0pp+A-08 no_memory 反超=两个独立 eval 同向，终门应作为已知边界如实报告而非改口径（DoD 原文「达不到必须报告真实结果而非改口径」）** |
| V3-5 Data Flywheel | D-07 goal-progress 洞察卡真数据；D-08 双臂配对闭环 10/10+--verify-repro；五维 understanding_depth（D-02 面） | **FIX-507 OPEN（P2）：intervention lifecycle 写路径零生产调用方**——friction/helped 两类洞察卡生产零数据、M-06 经验投影恒空，「数据飞轮」中段断链；终门此 gate 大概率 FAIL/PARTIAL（门后派修已在协调队列） |
| V3-6 Trustworthy Runtime | X-09 162 组合零偏差+SIGKILL e2e；461/469/487 耐久链；FIX-78/79 修+wt460 复验（false success 面）；O-02 trace 脊柱+FIX-491 审计链修复；Q-06 chaos | **O-02 运行级 trace 重建证据缺一口**（O 线章 §O.4-3，trace_timeline.py 跑真 GJ 即补）；FIX-530 P1（Redis 瞬断杀引擎进程）建议终门前修；「100 run ≥99 terminal」的批量 run 统计锚需从 X-05/09 测试面提取或补跑 |
| V3-7 Experience | Q-03 核心 A/B=0+long-tail A=0；Q-02 13/20+修复；U-09 视觉基线设施；U 线 L2 双审 APPROVE | Q-02 修后无全 20 GJ 重跑（同 V3-4 处理）；**三端实机段整体未采集**（FIX-511：U-09 45 张矩阵/G-05 真机批/U-08 走查/Q-02 HUMAN_INBOX 清单——中央箱零覆盖）；「Android/Web/macOS 核心 GJ 均通过」条款按现状只能判 BLOCKED（真机）/PASS（API 级+模拟器）双口径 |
| V3-8 Performance & Cost | Q-06 4 项 PASS（L1 双达标/L3 ACK 0.06s/L2 阶段反馈改善）；tier 账本四车道复活；增长标度 PASS；cost/WVPL 度量链在库 | **L0 1879ms/L2 48.25s 两项 FAIL 未修**（E-08 族复测路径=E 线章 §E.2-E-08④）；E-08 卡本身三笔未闭（receipt/wt755 集成/残差移交笔）；「每 tier 有账本」已满足、SLO 不达标款按 DoD 原文「必须重新定真实 SLO」→终门需产出 SLO 修订决议而非沉默 FAIL |
| V3-9 Commercial | O-04 解耦双侧判官；O-06 操作面+ENGINE_ONLY；O-07 预算/背压/超预算 UX；数据导出/删除端点在库（data_export.py/memory export/ai-usage export）；O-05 备份链修复+INV 校验器 | **O-01 整款 BLOCKED**（HTTPS 远程部署/远端 endpoint 配置/密钥服务端验证全未执行）；O-05 待审查回账+FIX-505 compose 裁决 OPEN；「RC 一键 smoke+rollback runbook」未在远端行使过（ops_rollback_smoke 真栈面只在本机 sparkle_redis 发生过一次） |
| V3-10 North Star WVPL | 定义→实现全链在库：north_star_wvpl.py 词表+D-06 fact+O-07 cost_per_wvpl（loops=0 不伪造）；「不得把 chat/send/task-click 当闭环」的判据在 north_star 词表 | 生产分母=JOURNEY ns001 单用户七日（day1-6 PASS，**day7 终门在快照时点未决**）；「active users 分母」在无公网部署下只有演示语义——终门按「本地演示形态」如实标注 |

**终门执行建议（成本从低到高）**：① 先跑零成本项=O-06 release-manifest 抓取+各 gate 产物程序化索引（本档证据图即起点）；② 低成本补证=trace_timeline.py 真 GJ 重建+Q-02/Q-04 全量重跑各一次（驱动在库、真栈形制 wt400/wt460 先例，各约半窗）；③ 裁决项=portfolio 词表/V3-2 映射口径/SLO 修订/三端条款双口径——需要协调方拍板，建议随 FINAL_V3_GATE_REPORT 的 NOT_RUN/FAIL/BLOCKED 标注一并产出。

---

## Q.3 设计决定与取舍（从提交/审查考古）

1. **诚实 FAIL 是合法交付且优于假 PASS**（Q-04 总判定 FAIL 照登/Q-02 0 waive/Q-01 unsupported 不算 PASS/Q-06 首轮数据作废声明）：终验线的价值函数是「找到真边界」，四次行使无一次例外。
2. **contract-simulation 语义用 schema 钉死**（Q-01）：换来可复现/零 LLM 成本/确定性判定，代价是「260 全绿≠产品绿」——用 provenance 逐 case 记录路由与语义，把解释责任交给引用者。V4 若建新 eval 体系，这是现成的诚实性模板。
3. **程序化判据替代模型 judge**（Q-04 blind rubric 0 次 judge/Q-03 四类探针/Q-06 全 raw 复算）：可审计可复跑，代价是判定域受限（词面/结构判据抓不到语义级个性化伤害——Q-04 的 DEFERRED 项如实承认这一点）。
4. **独立性靠机制不靠人头**（blind_key 分离落盘/冻结 rubric 只读 pairs/解盲在评审后）：「Reviewer 不看实现」从纪律变成数据流结构。
5. **修而不默认复跑——修复以契约锁钉住，全量重跑留给终门**（Q-02/Q-04 共同形态）：省了两轮全量重跑的成本，代价是终态口径碎片化（首轮+局部复验+锁三级证据并存）。本档判断：**对终门而言这个债必须一次性还掉或显式裁决**，因为 FINAL gate 的语义就是「唯一最终状态」。
6. **注入面完整性先于结论**（Q-06 首轮作废声明+wt460 补齐 11 个 base_url）：chaos 结论的可信度=注入面覆盖率；「部分注入的成功样本」是最危险的 false smooth 形态。

---

## Q.4 残差与 V4 注意点（汇总）

1. **「修而不复跑」清单（终门必清）**：Q-02 全 20 GJ、Q-04 六路红队、FIX-57 的 GJ08/GJ15 真栈复验（在册 DEFERRED）——三个驱动（q02_run_golden_journeys.py/q04 驱动/q06 五件）全在库，补跑是执行问题不是工程问题。
2. **两个独立 eval 同向的负面结论必须带进 V4**：Q-04 uplift 0.0pp + A-08 no_memory 臂反超——当前记忆/个性化面在模拟人口上净贡献未被证明为正；V4 的记忆/个性化设计应以「让个性化被证明有用」为第一命题，而不是扩面。
3. **V3-5 数据飞轮中段断链（FIX-507）**：Q-06 的 Quality 维度、D-07 两类洞察卡、M-06 经验投影全部因此缺真实数据流；终门 V3-5 判 FAIL/PARTIAL 时的根因指针已在册，门后派修已在协调队列——V4 排期应把它当「飞轮上线」的第一块板。
4. **三端实机证据是 V3 体验面唯一整段缺位**（FIX-511 中央箱零覆盖）：V4 初期安排一次集中采集批次（成本在设备/浏览器权限不在代码）——U 线章 §U.4-4 已给清单索引。
5. **Q-07 前置只有一个**（O-05 审查回账），执行资产全部现成（§Q.2-Q-07 计划草案）；**FIX-530 P1（Redis 瞬断杀引擎进程）是 Q-07 Work 1 的直接前置缺陷**，建议先修后验。
6. **Q-08 的四个裁决项**（portfolio 词表/V3-2 映射/SLO 修订/三端双口径）建议在终门前由协调方预先拍板，避免审计会话变成裁决会话。
7. **Q 线台账闭环质量自查结论**：Q 线相关 FIX（49-58/67-81/112-113/156）状态逐行核验——除 FIX-52/56（Q-02 遗留，分诊在案）与 FIX-53 状态格问题（本档 512 收口）外全部 FIXED@主干可达；Q 线是台账与代码一致性最好的线之一。

---

## Q.5 本次审查登记

- **V3-FIX-512**（P2，本次新登记并**当场收口**，Q 线章主登记）：台账 V3-FIX-53 行状态格为混合体「`OPEN 补记FIXED@10d3d7e8（集成时已修，行状态漏更新——2026-09-26 卫生补记…）`」——修复本体 10d3d7e8 已在主干（本档 `merge-base --is-ancestor` 亲证祖先），补记也在行内，但状态格仍以 OPEN 开头：机器口径（`grep "| OPEN"`）计其为 OPEN，导致「唯一 OPEN P1=FIX-53」的台账态与「修复在主干」事实矛盾（wt780 度量章「唯一 OPEN P1=FIX-53」即受此影响——该表述对代码状态误报、对台账状态属实）。与 V3-FIX-504/508/510 同族（台账低估漂移）的**状态格未翻转型变体**。修法：状态格改写 FIXED@10d3d7e8（保留补记原文），本档已按「集成即纠指」当场执行（同 commit）；ledger 工具可加「行内 FIXED@ 与行首状态枚举一致性」自检（与 504/508 的 FIXED@ 可达性抽检建议合并实施）。
- **V3-FIX-513**（P3，本次新登记，OPEN，Q 线章主登记——Q-08 准备项）：**42 feature portfolio 状态双真源词表分裂**——`v3/V3_DEFINITION_OF_DONE.md` Gate V3-0 要求「42 个 feature 有唯一 portfolio 状态：CORE/CONTEXTUAL/LABS/HIDDEN/RETIRE」；而 `v3/00_context/MODULE_PORTFOLIO.md`（初始 pack 导入 0c7fa4c5，自述「desired role」）用扩展词表 CORE 15/CONTEXTUAL 15/LABS 5/SECONDARY 3/CORE_OPTIONAL 1/HIDDEN 1/INTERNAL 2 且 **RETIRE=0**（本档逐行解析亲证）；B-01 交付的 `v3-output/B-01/MODULE_MATRIX.csv`+portfolio.json 才是 DoD 五态口径（RECEIPT 独立复核 CORE 15/CONTEXTUAL 18/LABS 5/HIDDEN 4/RETIRE 0，42/42 EXACT MATCH）。后果：①「唯一 portfolio 状态」在文档层不可直接满足——两真源同 feature 值不同（如 achievement：CSV=CONTEXTUAL vs PORTFOLIO=SECONDARY）；②B-01 矩阵基线 a2d8a10c 距今 9+ 天，GOV-015/WS6 删除（~3,958 行）、FIX-490 LearningModeScreen 摘除等 reachability 变化未入册——终门按旧矩阵判 V3-0 会过判。修法方向：终门（Q-08）执行前裁决唯一真源（建议 B-01 矩阵为准、MODULE_PORTFOLIO.md 降级为 desired-role 参考并加注）+按 HEAD 重跑 B-01 式审计或显式钉「矩阵时点=XXX，其后变化见 FIX-490/GOV-015 等」注记；词表映射表（SECONDARY/CORE_OPTIONAL/INTERNAL→五态）随裁决产出。
- 复核过但**不构成新发现**的四项：①Q-01/Q-05 无卡级 v3-output 目录且台账零死指针（本档对台账引用的 Q 线目录逐一 ls 亲证）——按 wt774 先例形态残差不占号；②Q-02 summary.json GJ08 5/6 与 commit message「6/6 回暖」的轮间波动——raw 在档、两数字各属其轮，如实并存非失实；③Q-04 FIX-70② 隐式漂移 DEFERRED——台账注记在案属产品决策留白；④主档 §3「Q 线 1/8」「O 线 4/7」陈旧口径——该行自带 ⏳ 待复核标记，本档即复核（正确值 Q 6/8、O 5/7 done+O-05 交付待审），随章并入修正不占号。
- 号占用核验：512/513 占用前 grep 复核——HEAD 台账 `grep -c "V3-FIX-512\|V3-FIX-513"` 零命中；在册号段 500-511/524-526/528-530（530=P1 OPEN，wt780 后新增），512-523 与 527 空闲；本档取 **512/513**（514 归兄弟章 O-line.md §O.5，同批登记三号两章共用）。
