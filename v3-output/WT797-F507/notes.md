# WT797 · V3-FIX-507 —— D-05 intervention lifecycle 写路径生产接线

台账：V3-FIX-507（P2）。问题：D-05 四个写方法（record_exposure / record_response /
record_outcome_association / associate_pending_outcomes）全仓生产面零调用；读侧三消费方
（D-07 洞察卡 / M-06 经验投影 / North Star intervention 面）全部已接线——数据飞轮中段
断链被测试全绿掩盖：friction-pattern 与 interventions-that-helped 两类洞察卡生产零数据、
M-06 经验投影恒空。

## 0. 约束回看

- 不造新事件、不造轮询：只在既有事件流的真实节点挂调用（D-02 ledger 增量扫描定时任务
  是台账明文规定的第三接线点，celery beat 是本仓既有定时批扫惯例，非新增轮询机制）。
- 不改 D-05 服务自身语义；失败语义=韧性壳（FIX-530 判例）：lifecycle 写失败只
  logger.warning，绝不拖垮宿主链路（交付/响应/管线）。
- 不碰运行栈/docker；不 push；不改台账。

## 1. 接线设计图

```
【写面 1】交付面（InterventionRecord 卡协议域）
  触发事件（既有）：
    a) InterventionEventConsumer._handle_record_created 交付成功 → mark_delivered
    b) intervention_feedback_binding_service._apply_feedback_transition 反馈路径
       CREATED→DELIVERED（消费者未经手的交付）
    ⇒ 两者共用 InterventionRecordService.mark_delivered（唯一收敛点）
  挂点：mark_delivered → record_exposure（幂等：双路径重复标记 dedupe 为
        duplicate_event，零第二行）
  挂点：mark_accepted → record_response(accepted)
        mark_dismissed → record_response(rejected)
        mark_acted → record_response(started)   [ACTED=用户开始按干预行动]
        （snoozed/seen 无封闭词表成员 → 不接线，不造语义）

【写面 2】Aurora decision 执行点（spine 管线域）
  触发事件（既有）：SpineOrchestrator._run_signal_pipeline 中
    policy_engine.evaluate 产出 (decision, directive) 且 directive 定稿下发
    （set_active_directive 前后——intervention 动作实际下发的既有节点）
  挂点：_record_intervention_lifecycle_exposure(user_id, signal, decision, directive)
        → record_exposure
  契约构造（A-01 形态，参照 L2 _build_decision_contract 先例）：
    intervention_type = SPINE_STRATEGY_TO_INTERVENTION[decision.primary_strategy]
      （A-02 投影映射；映射缺失或 inert（no_action/abstain）→ 不记录——
       「不行动」没有用户可见载体，record_exposure 亦会拒绝）
    cognition_tier = "l1_light"（spine 管线规则评估，无 LLM）
    governance_mode = "live"（directive 实际生效）
    execution_mode = catalog item nominal_execution_mode 镜像
    evidence_refs = (f"signal://{signal.state_key}",) → friction_tag 真实归因
    input_context_hash = sha256(directive.directive_id)（每次下发实例唯一 →
      decision_id 内容寻址且 per-dispatch 唯一；重放可去重）
    rationale_summary = decision.reasoning_summary or signal.evidence_summary
    linkage = {}（spine signal 域无 plans/tasks UUID 锚——诚实留空，不伪造关联键）
  user_id 不可解析为 UUID → 跳过（L2 引擎同款纪律）

【写面 3】D-02 ledger 增量扫描定时任务
  新增 celery 任务 associate_intervention_lifecycle_outcomes（app/core/celery_tasks.py，
  惯例同 scan_aurora_scheduled_wakes）：
    选近期（≤37d=30d 最大观察窗+7d 宽限）有 exposure 的 distinct user（cap 500/轮）
    → 逐用户 associate_pending_outcomes（幂等可重跑，重复扫描零成本）
  beat 注册：every 6h，low_priority 车道（celery_schedule.setup_periodic_tasks），
    与 intervention-outcomes-full（02:00）错峰（*/6h @ :50）。

读侧（零改动，接线后自然有数据）：
  D-07 friction-pattern 卡     ← 写面 2（friction_tag 真实归因的 exposure/response）
  D-07 interventions-that-helped ← 写面 1（plan_id linkage）+ 写面 3（关联扫描）
  M-06 经验投影                 ← 两写面 exposure+outcome 关联行
  North Star lifecycle 计数    ← 两写面全部事件
```

## 2. 幂等键与失败语义（逐挂点）

| 挂点 | 幂等键 | 失败语义 |
|---|---|---|
| mark_delivered → exposure | (decision_id, "exposed", "")；decision_id=A-01 内容寻址（input_context_hash=sha256(record.id)，同 record 恒同 id） | refused（inert/shadow/损坏载荷）→ info 留痕；DB 异常 → warning 壳，宿主转场不受影响 |
| mark_accepted/dismissed/acted → response | (decision_id, accepted/rejected/started, "") | 无 exposure → refused(no_exposure)（D-05 漏斗完整性既有语义，可观测降级） |
| spine 指令下发 → exposure | (decision_id, "exposed", "")；per-dispatch 唯一 | 韧性壳：任何异常 warning + 返回 None，管线永不中断 |
| 关联扫描任务 | (decision_id, "outcome_observed", outcome_id) | 单用户失败 warning 继续；任务级 retry（既有 celery 惯例） |

decision_id 合法性：全部经 AuroraDecisionContract.decision_id_or_compute() 产出
（aurora_<32hex>），不手搓前缀。 InterventionTriggerType → A-01 目录投影（冻结映射，
L2_INTERVENTION_TO_CATALOG 同款纪律，语义判据逐条对齐 SPINE_STRATEGY_TO_INTERVENTION
既有判例）：
- PLAN_RISK → rescope（adjust_plan→rescope 判例）
- CONCEPT_GAP → practice（repair_knowledge_bottleneck→practice 判例）
- STALL_PATTERN → split（insert_easy_win→split 判例）
- OVERLOAD → pause（reduce_next_48h_load→pause 判例）
- MISALIGNMENT → explain（insert_reassurance→explain 判例）

交付面 exposure linkage：plan_card_id → Card.metadata_.legacy_plan_id → linkage.plan_id
（与 D-02 task 完成 OutcomeEntry.correlation.plan_id 同 plans.id 域——这是 interventions-
that-helped 关联真实成立的唯一合法桥）。task_occurrence_id 与 Task.id 不同域，不伪造。

## 3. 红先行设计（三读侧消费方各一测）

1. D-07 面：真实交付流（create_record→mark_delivered→mark_accepted）+ spine 写面入口 +
   真实 Task 完成 + associate → build_cards 断言 friction_pattern 与
   interventions_that_helped 卡出现。修前：lifecycle 零写入 → 卡恒空 → 红。
2. M-06 面：同数据流 → project(use_cache=False) 断言投影 records 非空。修前恒空 → 红。
3. North Star 面：同数据流 → _intervention_lifecycle 断言 lifecycle_events_by_type
   含 exposed。修前恒空 → 红。

（红=证明「生产写路径驱动下读侧仍恒空」即零调用事实；绿=接线后同一测试翻转。）

## 4. 红绿实录

环境：worktree wt797-f507（branch agent/node-b/wt797/f507，base main@02a05425）；
backend gen 按先例主仓 cp -RL 不入库；SECRET_KEY=test env；主仓 venv。

**红（修前，main 基线代码）**：
```
tests/services/test_f507_readface_dataflow.py  —— 5 failed in 2.75s
  test_delivery_face_writes_exposure_and_response_rows     FAILED
    （真实 create→consumer 投递→mark_accepted 后 lifecycle 0 行：生产零调用实证）
  test_spine_pipeline_writes_friction_attributed_exposure  FAILED
    （ModuleNotFoundError: app.services.intervention_lifecycle_wiring
     —— spine 写路径不存在本体）
  test_readface_d07_cards_fed_by_production_writes         FAILED
  test_readface_m06_projection_fed_by_production_writes    FAILED
    （ExperienceProjection records=() watermark='empty'）
  test_readface_north_star_counts_fed_by_production_writes FAILED
```

**绿（接线后，同一数据流）**：
```
test_f507_readface_dataflow.py   5 passed
test_f507_lifecycle_wiring.py    9 passed
  （映射全员覆盖/decision_id 稳定且内容寻址/重复投递幂等恰 1 行/韧性壳
   lifecycle 宕机不影响交付转场/无 exposure 响应 refused 不炸/spine 契约
   inert+未映射短路/管线调用点 AsyncMock 断言 awaited_once/beat+路由注册）
```

**触达面回归（全绿）**：
| 套件 | 结果 |
|---|---|
| f507 两文件 + D-05 service 36 + D-05 contract + feedback_binding + M-06 projector + north_star service | 147 passed |
| phase2 pipeline（consumer 端到端）+ consumer 异常传播 + spine_orchestrator + x08 ledger | 75 passed |
| test_signal_spine.py（spine 管线全量） | 960 passed |
| context_persistence + card_protocol phase3/4 + phase_e + strategy_learner + verification_loop + profile_transparency + north_star api + o07 | 57 passed |
| golden north_star + intervention_catalog 契约 + aurora_decision 契约 | 62 passed |
| insights API | 4 passed |
| 核心触达重跑（格式化后） | 125 passed |

**门禁**：
- ruff：8 个触达文件 All checks passed。
- mypy 冷缓存：worktree `Found 55 errors in 51 files (checked 1388)` ==
  主仓 base `Found 55 errors in 51 files (checked 1387)` —— 55 基线零新增；
  触达 6 文件 0 error。
- black：3 个新文件格式化后 clean；5 个既有触达文件 base 既有漂移
  （主仓同 5 文件 would-reformat 对照实证，未碰），
  新增行 `-/+` flag grep = 0（判例 V3-FIX-05/14 同款）。

## 5. 数据流前后对照

修前（断链）：
```
真实交付/响应/下发事件 ──✗──> intervention_lifecycle_events（0 生产写入）
D-07 friction_pattern 卡          = 整面静默缺席（无数据不出卡守卫）
D-07 interventions_that_helped 卡 = 整面静默缺席
M-06 经验投影                     = records=() watermark='empty'
North Star lifecycle_events_by_type = 全 0
（D-08 飞轮闭环证明的 lifecycle 写入系评测 harness 直接驱动，非生产流量）
```

修后（飞轮中段接通）：
```
交付面  InterventionRecord 交付/接受/拒绝/行动（消费管线 + 反馈绑定双路径）
        → exposure + accepted/rejected/started（plan_id 关联桥 → D-02 task 完成
          correlation.plan_id 同域）
spine 面 管线 directive 定稿下发 → friction 归因 exposure（signal://state_key
          → SPINE_STATE_KEY_TO_FRICTION 族）
定时面  6h 关联扫描 → associate_pending_outcomes（白名单 outcome 关联，幂等）
        ⇒ D-07 两类卡 / M-06 投影 / North Star intervention 面全部吃到真实数据
```

边界如实声明：交付面无 spine 信号锚 → friction=unattributed（不算分析失败，
D-05 词表既有档）；spine 面无 plans/tasks UUID 锚 → linkage 留空不伪造；
friction-pattern 卡的数据源是 spine 面（真实归因），interventions-that-helped
的数据源是交付面 plan 关联 + 关联扫描——两类卡各由其合法写面供数。
edits 类响应（InterventionAcceptanceStatus 无 edited 档）生产无真实节点，
不造语义，如实缺位。

## 6. 交接注记

- 改动文件：新增 `app/services/intervention_lifecycle_wiring.py`、两测试文件、
  notes.md；修改 `intervention_record_service.py`（4 转场挂点）、
  `spine_orchestrator.py`（下发点 hook + 方法）、`celery_tasks.py`（新任务）、
  `celery_app.py`（路由）、`celery_schedule.py`（beat）。
- D-05 服务自身零改动（lifecycle_service.py 未触碰）。
- 韧性壳判例：FIX-530（宿主链路永不因 lifecycle 失败中断；refused 是
  D-05 既有可观测降级语义，原样透传）。
