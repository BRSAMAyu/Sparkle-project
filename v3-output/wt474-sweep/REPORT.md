# wt474 · OPEN 池批扫陈+分诊报告

- 日期：2026-09-25｜工号 wt474｜基线：main `7cfd984c`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt474-sweep`，分支 `wt474-sweep`）
- 对象：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 全部 38 条「行内无 FIXED@」行 = 31 条 OPEN + 7 条非 OPEN 终态/中间态（CLOSED@×3、DIAGNOSED@×1、已修@wt422×2、裸 FIXED×1，状态均已如实记录，本轮不触碰）。
- 纪律：不动产品码；台账只做行内注记/补记；证据标准 = commit SHA + 代码在场两点齐备；存疑宁漏勿错。

## 一、三分类计数

| 分类 | 数量 | 行 |
|---|---|---|
| N1 已修未记（补记FIXED@） | **4** | FIX-09、FIX-10、FIX-23、FIX-25 |
| N2 真开放-可派发 | **12** | FIX-05、14、21、22、31、37、40、46、52、56、144、156 |
| N3 真开放-待拍板/备忘/存疑 | **15** | 待拍板×7（06、20、26、48、97、160、174）+ 备忘型×8（15、27、30、32、38、39、42、44） |
| 非 OPEN 终态行（不处理） | 7 | FIX-16/45/47（CLOSED@）、17（DIAGNOSED@wt6，诊断已归档修复卡待开）、108/109（已修@wt422）、118（FIXED） |

## 二、已修未记补记清单（ID→SHA，均已核代码在场）

| ID | 补记 SHA | 一句话证据 |
|---|---|---|
| V3-FIX-09 | `b2e8fa13` | C-01 硬化 F1/F3/F4/F6/F7 单审 ACCEPT 合入在 main；decision_context.py:85/184/201-202/235/369 五处锚点 + context_pack.py:2276-2304 degraded_reasons + business_metrics.py:550 |
| V3-FIX-10 | `fa4e5837` | M-04 ACCEPT 合入落地各 F 项：F2 生命周期过滤+重放幂等（conflict_resolver_service.py:575-615）、F4 第 5 破坏性入口（:779、memory_invalidation_pipeline.py:81）、F6 explicit 声明（:34）、F7 跳过计数指标（business_metrics.py:373） |
| V3-FIX-23 | `a2327787` | E-07 键型对齐健康上报（llm_service.py:79-99 docstring 明标 FIX-23，report 走 model_key+resolve_model_key 反查）；顺带的 slim 关键词归拢未做，重构微项留记不阻关闭 |
| V3-FIX-25 | `5776b430` | 与 V3-FIX-118 同一缺陷点（3315=3335 行漂移），wt426 改名修正在场（execution_service.py:83/113/3335 锚点）；与 wt472-execclass 分支独立结论同 SHA 一致 |

另：FIX-26/27 的收口已在 wt472-execclass 分支（6b3f9597/9aec29c4）**未合入 main**——本行不代为补记（26 的缺陷代码在 main 在场），分详见下。

## 三、可派发队列（按价值排序，P1 优先）

| # | ID | Sev | 卡面（一句话） |
|---|---|---|---|
| 1 | V3-FIX-37 | P2 | **stats 时区/窗口债**：mobile stats UI 已真实接线（sprint_view/focus_stats_tool），naive-UTC 边界（api/v1/statistics.py:48/251）把 UTC+8 晨间会话整段排除→streak/heatmap 误报成真——聚合窗口与存储时区同源化（前置条件已生效，优先级上调） |
| 2 | V3-FIX-21 | P2 | **kill-switch 劫持**：kill_switch.py:83-86 + stage18 legacy_bool_attr + settings.py:946 默认 True 三环在场——显式 off 被 legacy bool 静默抬回 live；默认改 False 或显式优先级+红绿测 |
| 3 | V3-FIX-40 | P2 | **账本同事务缺口**：notification_service.py:279/387、plan_state_service.py:202 等、persona_service.py:197 内部 commit 仍在场——账本与工具写入不同事务、失败即 key 中毒；收编事务边界（X-09 批未覆盖） |
| 4 | V3-FIX-14 | P2 | **telemetry 硬化**：plan_context.py:302 读 strain_index 无 waiver 标记（登记册机制在库）；防抖 check-then-act 原子化；TELEMETRY_DERIVED_LOAD_CAP=0.3 覆盖面核查 |
| 5 | V3-FIX-156 | P2 | **pre-LLM-pool 瓶颈画像**：60 并发撞共享 PG 连接顶（77/100），FIX-78/79 快速失败被池前瓶颈遮蔽——定位连接占用时序+轮次级排队门，定义 admission 用户语义 |
| 6 | V3-FIX-05 | P1 | **shop 空目录入口移除**：streak_details_screen.dart:427 context.push('/shop') 仍在场——移除入口小卡（随 gamification 降权） |
| 7 | V3-FIX-46 | P3 | **outbox→Redis stream 桥**：triggers.py:29-33 明示 run.awaiting_user「Python stream 无发布点…等桥落地即生效」——桥卡可开（②gen 环境债属环境备忘） |
| 8 | V3-FIX-31 | P3 | **D-05 残余微项一批清**：P2-1 已由 e56be400 消费面修复在场勿重做；剩 P3×6（watermark 全集指纹/计数窗末上界/decision_id 捕获/global fallback；ilfe_ 项真本体=唯一约束已在场） |
| 9 | V3-FIX-22 | P3 | **测试隔离**：test_stage38_d3_persistence.py:38-44 sys.modules.setdefault 注入无恢复——fixture 摘除所装 fake 模块 |
| 10 | V3-FIX-52 | P3 | **摩擦事实消解**：friction_diagnosis.py:1290 recent_failure_count≥阈值直给 skill/difficulty 证据——降权或类型关联（随 A-03 迭代） |
| 11 | V3-FIX-144 | P3 | **词牌短语出载荷**：_strip_input_snapshot（friction_chat_wiring.py:165-175）只剔 input_snapshot——utterance_matches/negated 短语仍进 metadata，142 同构投影（计数/指纹替代） |
| 12 | V3-FIX-56 | P3 | **网关 502 级联排查**：网关仓无显式熔断实现（仅 chaos.go:55 模拟）——先定位级联真源（transport/上游重启窗）再谈配置，行内「熔断阈值」归因待排查后勘误 |

排序说明：P1 的 FIX-05 是删一行入口的微卡，价值密度低于 P2 的四个真实语义缺陷，故队列以 P2 语义缺陷为前五；派发时按容量取用。

## 四、待拍板清单（谁拍什么）

| ID | 谁 | 拍什么 |
|---|---|---|
| V3-FIX-06 | 产品 | aurora_calibration_receipt 登记进 KNOWN_SOURCE_LANES（含仲裁位次）或迁移写入点——契约已留 RESERVED_UNREGISTERED_LANES 槽位（memory_epistemic_contract.py:152-163），写入点 correction_feedback.py:427 在场 |
| V3-FIX-20 | 产品 | 群目录/搜索/推荐 cohort 过滤或官方群标识机制（search_groups community_service.py:461 无过滤在场；feed 面已修属显式保留边界） |
| V3-FIX-48 | 产品 | dismiss 冷却/指数退避或扫描频率策略 + 过期窗口（非完成）是否衰减/停投建议 |
| V3-FIX-97 | 产品 | 无行动出口的第二纠正入口形态（自由纠正 vs B3 候选集低承诺出面），须与 FIX-49 降噪目标联合权衡 |
| V3-FIX-160 | 产品 | 截断轮历史可见性：方案 A/B/C + 两个拍板问题（FIX160_DECISION_MEMO.md，推荐 A=三轨统一不落库） |
| V3-FIX-174 | 产品 | 与 FIX-160 合并裁决落地（同卡组，检测 error 帧→跳过持久化+缓存） |
| V3-FIX-26 | ——（存疑归此，宁漏勿错） | **勿派发**：缺陷在 main 在场（community_signal_bridge.py:447-448 双 .all()→opted_out 恒空），但修复+回归锁已在 wt472-execclass 9aec29c4 在库未合入、其台账已收口本行——等合入后按其 SHA 补记 |

备忘型×8（行内自登记「不阻塞/随 XX 迭代」，本轮未深查）：FIX-15（随 M-05/M-09 评测迭代）、27（P4；wt472 分支已定位收口嫌疑证伪）、30、32、38、39、42、44（「见底」裸词 memory_storage_gate.py:563、「确诊」:571 抽查仍在，低优）。

## 五、方法与边界

- 每条 OPEN 行均按行内 file:line 锚点在基线 7cfd984c 读码核实；补记类另跑 git log -S/--grep 锁定修复 commit 并以 merge-base --is-ancestor 确认在 main。
- 抽查级核实（未跑全量测试）：可派发行的「缺陷仍在」以锚点读码为准；标注中的修法建议是方向非验收。
- wt472-execclass 分支（在途未合入）覆盖 FIX-25/26/27 收口：25 与本轮独立同判（5776b430），26/27 按上表处理避免重复派发；新缺陷登记本轮为零（未发现全新缺陷，未占用 176+ 号段）。
- 未动产品码；台账改动全部为行内注记/补记；本报告+台账更新一个 docs commit。
