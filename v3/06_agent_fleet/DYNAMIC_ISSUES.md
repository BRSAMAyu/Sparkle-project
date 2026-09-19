# Dynamic Issues Ledger

> Leader/Simulator 在 V3 执行中追加。不要在此预填历史已完成 bug。

| ID | Severity | Journey | Reproduction | Evidence | Owner task | Status |
|---|---|---|---|---|---|---|
| V3-FIX-01 | P0 | 排行榜/社群/统计聚合 | FINDINGS.md F1 SQL 直接复现（top-50=100% guest, top_score 132.5; 复核加强: top-100 亦 100% guest, email 用户全员 best_rank≥169） | v3-output/B-02/REVIEW_RECEIPT.md 断言1 + FINDINGS.md F1 | T-truth-leaderboard（补 WHERE registration_source NOT IN ('guest','seed') 等效 cohort 过滤） | OPEN |
| V3-FIX-02 | P0 | 聊天路由 entitlement | guest_seed_service.py:1486 写 flame=15 × 网关 IsPro=FlameLevel>=3（user_context.go:129）⇒ 166/166 游客 is_pro=true 进 LLM tier 钳制 | REVIEW_RECEIPT 断言2 代码链路五环实证 | T-truth-ispro（D17: entitlement 独立字段） | OPEN |
| V3-FIX-03 | P1 | 统计模块接线前 | core/statistics 三仓库 fetchFromApi 生成 mock 且经 _putInWarmCache 落 Isar（24h TTL, isFullySynced=true）; 红测因沙箱基建未入库，修复卡须先补写红测 | REVIEW_RECEIPT 断言3 代码级实证 + dart run 探针 25 mock 标记 | T-truth-corestats（接真实 API 或删除; Isar 假缓存一次性失效） | OPEN |
| V3-FIX-04 | P1 | LLM glm 车道 | glm-5.3-flash 语义: 标准端点 thinking disabled 返 400 code 1210（"该模型始终思考"）; coding 端点可真实关思考(1.01s 无 reasoning); 引擎 clear_thinking extra_body 被静默忽略; 思考占 completion 预算 84-88% 可致 max_tokens=1024 空回复 | v3-output wt2 B-05b SUPPLEMENT_KEY_ROTATED.md（B-05b 复测 16/16+9/9 lane 实测） | T-llm-glm-thinking-control（coding 端点 lane 发 thinking disabled; 全 lane max_tokens 留量≥15%） | OPEN |
| V3-FIX-05 | P1 | shop 空目录暴露 | /shop 注册+streak_details_screen.dart:415 唯一入口；shop_items/shop_purchases 0 行（B-01 HIDDEN 判定 + Reviewer 确认） | v3-output/B-01/REVIEW_RECEIPT.md + REPORT §4 | T-hide-shop-entry（移除该入口，随 gamification 降权） | OPEN |
