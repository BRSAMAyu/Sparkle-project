# Rule AT Exceptions

- Legacy baseline exceptions retained until dedicated cleanup:
- `backend/app/services/agent_grpc_service.py`
- `backend/app/services/analytics/behavior_pattern_service.py`
- `backend/app/services/capability_selection_evaluator.py`
- `backend/app/services/experience_phase_evaluator.py`
- `backend/app/services/five_layer_learning_evaluator.py`
- `backend/app/services/error_book_grpc_service.py`
- `backend/app/services/galaxy_grpc_service.py`
- `backend/app/services/llm/parser.py`
- `backend/app/services/planning_benchmark_evaluator.py`
- `backend/app/services/profile_eval_runner.py`
- `backend/app/services/skill_share/service.py`
- `backend/app/services/skill_store/service.py`
- `backend/app/services/state_driven_push_service.py`
- `backend/app/services/traits_guardrails.py`
- `backend/app/services/traits_nlp_observer_service.py`
- `backend/app/services/understanding_benchmark_evaluator.py`
- `backend/app/services/card_protocol/consistency_validator.py`
- `backend/app/services/jpush_sender_service.py`
- `backend/app/services/analytics/dual_core_decision_bench.py` — offline decision audit bench（模块自述 intentionally read-only），直接受测（tests/unit/test_dual_core_decision_bench.py），无运行时导入方属设计内；同 planning_benchmark_evaluator / profile_eval_runner 先例（wt340 登记）

- Dead modules (no runtime importers, candidates for removal):
- `backend/app/services/budget_optimization_service.py`
- `backend/app/services/feedback_adjustment_service.py`
- `backend/app/services/galaxy/event_listener.py`

- Merged/deprecated modules (logic moved to another file, kept for reference):
- `backend/app/services/compliance/deletion_protocol.py` — merged into age_gate.py during Rule K refactoring

- Guard false positives (have importers via absolute/relative imports, guard AST resolution misses them):
- `backend/app/services/feedback_service.py`
- `backend/app/services/personalization/runtime_context_service.py`
- `backend/app/services/session_service.py`
- `backend/app/services/stt_grpc_service.py` — imported by `backend/grpc_server.py` (outside scanner scope)
- `backend/app/services/inference_grpc_service.py` — imported by `backend/grpc_server.py` (outside scanner scope)
- `backend/app/services/routing_parameter_proposal_service.py` — dead module, only referenced in tests
- `backend/app/services/community_context_boundary.py` — S-02 群上下文隐私边界守卫库（orphan-by-design）：生产消费方是后续群 AI prompt/tool 面（当前全仓无 group prompt 组装点，本卡交付该面唯一合法入口 + 纯函数滤芯 + 契约测试钉死）；接入时移除本条

- `backend/app/services/graph_knowledge_service.py` — AGE 双写/探针基础设施（orphan-by-design）：唯一生产消费者 graph_monitor router 已随 V3-FIX-341 假开关撤面删除（wt646）；预留消费方=后续 GraphRAG 可视化/运维面（ENABLE_GRAPHRAG_FASTPATH 翻开后的节点同步与探针面）。重建消费面时移除本条；裁决不建则整体退役


- `backend/app/services/analytics/ope_gatekeeper.py` — 正/负信号分类门（orphan-by-design）：零运行时消费者、测试独占（test_ope_gatekeeper.py）——wt777 批十一触碰进 diff 范围后 AT 守卫暴露的预存孤儿（V3-FIX-537 登记 2026-09-28）；预留消费方=O-PE 分析/成本门面（O-07 族扩展）。接线时移除本条；裁决不建则整体退役

- `backend/app/services/retraction_recompute_service.py` — V4-D03 撤回派生影响与投影重算服务面（orphan-by-design）：结果撤回的生产触发方按卡序接线（结果撤回 UI/FSM 入口、重算 job 调度归消费卡）；本卡交付登记/栅栏重算/读门唯一 IO 入口 + 契约测试钉死（tests/services/test_retraction_recompute_service.py），同 community_context_boundary 先例。接线时移除本条
