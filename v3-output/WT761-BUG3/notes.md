# WT761-BUG3 — wt754 mypy 批九停手登记三真 bug 修复（V3-FIX-491 / 492 / 493）

- Agent: wt761 ｜ 分支 `agent/node-b/wt761/bug3`（base main@4ad52ea6）｜ 2026-09-27
- 台账: v3/06_agent_fleet/DYNAMIC_ISSUES.md 行 378/379/380（491/492 wt754 登记，493 wt757 登记）
- 主线仓库只读；worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt761-bug3`

## FIX-491（P2）auto_degrade 审计事件 publish 形参错位恒失败

**病灶**：`app/api/internal/auto_degrade.py::_write_audit` 以
`await event_bus.publish(SLOAutoResponseAuditEvent(...))` 单实参调用
`EventBus.publish(event_type: str, payload: dict, stream=...)`（event_bus.py:1071）。
TypeError 在**调用点实参绑定阶段**抛出（缺第二位置实参 payload）——publish 函数体
（内含重试/DLQ 的自吞错面）根本未进入，异常被 `_write_audit` 自身
`except Exception: logger.exception(...)` 吞掉，仅落日志、零指标、零测试覆盖。
净效果：SLO 自动降级/升级动作的审计事件从未进入 Redis Stream（全库 grep
`slo_auto_response_audit` 仅此一处发布点、零消费者，事件类型自类定义起从未入流）。

**修法**：按 publish 真实签名双参调用——先构造事件对象，再
`await event_bus.publish("slo_auto_response_audit", event.to_dict())`。
event_type 词表取事件类 `to_dict()` 既有自述 `"event_type": "slo_auto_response_audit"`
（`_publish_once` 对 payload 已含 event_type 键时不覆盖，线协议一致）；payload
平铺事件字段（沿用 `srl_events.py:35`、`task_reflection_service.py:533` 的
`publish(事件名, event.to_dict())` 仓库惯例）。

**吞异常面处置（让未来签名错配可见）**：`except Exception` 保持宽面——审计属
best-effort，发布失败不得破坏 kill-switch 响应主链；但新增 Prometheus 计数器
`sparkle_slo_auto_response_audit_publish_failures_total{alert_type}`（复用本文件
`get_or_create_metric` 惯例）在 except 内递增——修前恒现故障只能翻日志发现，
修后进 SLO 指标面可告警。

**红→绿**（tests/api/test_slo_auto_degrade_api.py::TestAuditEventPublishing）：
- `test_publish_called_with_event_type_str_and_dict_payload`：断言 publish 以
  `("slo_auto_response_audit", dict)` 双参调用且 payload 字段齐整。修前红（首参
  是事件对象非 str）；修后绿。
- `test_audit_event_reaches_redis_stream`：真实 publish→`_publish_once` 路径，
  mock redis 断言 `xadd("sparkle_events", body)` 且
  `body["event_type"]=="slo_auto_response_audit"`。修前红（TypeError 被吞、xadd
  零调用——红实录 traceback 即 `EventBus.publish() missing 1 required positional
  argument: 'payload'`）；修后绿。

## FIX-492（P3）plan_review daily_hours None 未守卫 TypeError 500 崩

**病灶**：`app/orchestration/plan_review_service.py:939`（修前行号）
`if _is_liberal_arts(user_background) and daily_hours < 3:`——daily_hours 来自
:919 `params.get("daily_hours")`（ToolCallSpec.params 键缺失即 None）。None 落
:934 `if daily_hours and daily_hours < 2:` falsy 跳过后，:939 裸比较
`None < 3` 直接 TypeError，沿 `_quick_rule_check` 快速审查通道上抛 500。
同函数 :934 与 :948 均带 `daily_hours and` 短路守卫，:939 为漏网不一致点。
触发三重合取：difficulty∈{expert,master,精通} + user_background 判定文科
（`_is_liberal_arts` 词表）+ tool_calls 参数缺 daily_hours 键。

**修法**：:939 与 :934/:948 对齐补 `daily_hours and` 短路（None/0 跳过该检查，
与 :934 缺参语义一致），一行守卫 + 行内注释。

**红→绿**（tests/unit/test_plan_review_feasibility_daily_hours.py，4 用例）：
- `test_expert_liberal_arts_missing_daily_hours_does_not_crash`：直测
  `_validate_feasibility`，修前红（`TypeError: '<' not supported between
  instances of 'NoneType' and 'int'` @:939）→修后绿（返回 True 放行）。
- `test_quick_rule_check_missing_daily_hours_auto_approves`：快通道端到端
  （confidence 0.97 + 非只读词表工具 `generate_study_material`，避开
  all_tools_are_read_only 短路打到 feasibility 门），修前红（TypeError 穿透
  `_quick_rule_check`）→修后绿（`high_confidence_simple_plan`）。
- `test_expert_liberal_arts_low_daily_hours_still_rejected` / 
  `..._sufficient_daily_hours_passes`：守卫边界保持（daily_hours=1 文科专家仍
  拒、=3 放行），修前后均绿——证明守卫未吞掉真实检查。

## FIX-493（P4）event_registry docstring 幂等闸契约声明陈旧

**病灶**：`backend/app/core/event_registry.py` `derive_event_id` docstring
（任务文本误记 orchestration/ 路径，实际 core/；台账行正确）「CURRENT CONSUMER
STATUS」段三处失实（基线 main@4ad52ea6）：①称 gateway processed_events route
「NOT usable as-is——IsProcessed 跑 uuid.Parse 拒 evt_ 前缀」，而 V3-FIX-469 已修
（`outbox/repository.go normalizeEventKey`：非空 ≤varchar(100) 键逐字接受、仅
UUID 形 canonicalize 为小写连字体、空/超宽拒）；②「zero consumers」已过时——
`cqrs/worker/base.go` BaseWorker 以 IsProcessed/MarkProcessed 为权威持久幂等闸
（469 修后生效），另有 487 的 `processed_events_cleaner.go` 保留清理；③同段
「publisher.go 经 Go `EventMetadata{...}` 解码 metadata、event_id 等字段该跳丢弃」
双重失实——`EventMetadata` 结构体全 gateway grep 零命中，publisher.go 现状为
`GetUnpublished`/`MarkPublished` 轮询、不经 processed_events、无 metadata 解码跳。

**修法**：docstring 该段整体改写为 469/487 修后事实（纯文档，零运行时行为；
event_registry 契约测试不触 docstring，触达面 pytest 全绿佐证）。

## 验证

- **pytest 触达面**：18 文件 **227 passed / 1 skipped / 0 failed**
  （auto_degrade API 全文件、新 492 四用例、plan_review breaker、planning HITL
  链、langgraph timeout、event_registry 契约、adaptive_replanner、perceptible、
  memory_provenance、openclaw followup、degraded_plan_review_honesty、
  round1_p2_fixes、orchestrator_process_stream、hitl_gate_wiring、
  plan_feedback_decision_vocab、plan_review_service、stage35 journey smoke、
  phase5 north star acceptance；skip 为既有条件跳过）。app 内新用例
  29 passed（27 auto_degrade + 4 feasibility，其中修前红 4）。
  - 环境注：worktree 缺 gitignored `backend/app/gen/`（SQLC/protoc 产物）致
    部分收集 ERROR，按 wt369/J-05 先例从主仓 symlink 补齐后全绿，产物不入库。
  - 测试环境变量 SECRET_KEY 以进程 env 注入（Settings 强制项），未改任何 .env。
- **mypy 同环境 BEFORE/AFTER**：`cd backend && mypy app --ignore-missing-imports
  --no-error-summary`（与 scripts/ci/mypy_ratchet.sh 同口径，venv mypy）：
  - BEFORE（main@4ad52ea6，主仓跑，独立 cache-dir）：**94** 条——与任务口径
    基线 94 精确吻合（即 wt754 批九烧减后基数；仓内 `quality/mypy_baseline.txt`
    的 380 为更早环境口径，本卡以同环境对比为准）。
  - AFTER（本分支）：**91** 条 = 94 − 3（auto_degrade:152 call-arg、
    auto_degrade:153 arg-type、plan_review_service:939 operator 三条消失）。
  - diff 逐条核对：除三条目标错误消失外仅既有错误行号平移
    （rate_limiting.py:264→199 为批九改名余波、plan_review_service:1801→1804
    为本卡注释插入），**零新增**。
- **ruff**：5 触达文件（3 app + 2 test）`ruff check` 全过。
- **black**：新测试文件两枚收口（--line-length 120）；auto_degrade /
  plan_review_service 的 black diff 与 main 既有漂移逐 hunk 恒等（本卡零新增
  格式漂移，不重排既有漂移纪律）。

## 新发现登记

- **V3-FIX-497（P4，OPEN）**：`plan_review_service.py:919`
  `daily_hours = params.get("daily_hours")` 无类型收口——LLM 生成 params 若携
  字符串型数值（`"daily_hours": "2"`），:934/:942/:951 的 `daily_hours and
  daily_hours < N` 真值短路后 `str < int` 同型 TypeError、:960
  `daily_hours * total_days` 同炸（str*int 为重复非数值语义亦错）。同类
  `_resolve_daily_capacity_minutes`（:833-840）对同键已走
  `cls._positive_float(...)` 收口（TypeError/ValueError→None），:919 为平行
  裸取值不一致点。修法方向：:919 改 `self._positive_float(params.get("daily_hours"))`
  （缺键/垃圾值→None，与 492 守卫语义衔接）。代码审读级，未运行级实证 LLM
  实际产出字符串型 daily_hours 的频率；停手登记不顺手修（循 wt754 判例）。
  497 号 grep 复核空闲：台账 `V3-FIX-49[5-9]` 0 命中（495 在 wt760 分支、
  496 任务口径 wt760 预占）。**498 未占用**——本批无第二个实证新发现，不凑数。

## 边界

- 不 push；不碰 docker/运行栈/.env；主线仓库只读（mypy BEFORE 在主仓只跑
  只读命令，独立 cache-dir 零写入仓库面）。
- 残余留记：`slo_auto_response_audit` 事件现发布入流但全库仍零消费者——事件
  落 Redis Stream `sparkle_events` 后无人读，审计查询面（如按 alert_type 检索
  自动降级历史）为后续卡空间；本卡修复的是「审计留痕从未落盘」的写侧断链。
