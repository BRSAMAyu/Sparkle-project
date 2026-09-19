# Dynamic Issues Ledger

> Leader/Simulator 在 V3 执行中追加。不要在此预填历史已完成 bug。

| ID | Severity | Journey | Reproduction | Evidence | Owner task | Status |
|---|---|---|---|---|---|---|
| V3-FIX-01 | P0 | 排行榜/社群/统计聚合 | FINDINGS.md F1 SQL 直接复现（top-50=100% guest, top_score 132.5; 复核加强: top-100 亦 100% guest, email 用户全员 best_rank≥169） | v3-output/B-02/REVIEW_RECEIPT.md 断言1 + FINDINGS.md F1 | T-truth-leaderboard（补 WHERE registration_source NOT IN ('guest','seed') 等效 cohort 过滤） | OPEN |
| V3-FIX-02 | P0 | 聊天路由 entitlement | guest_seed_service.py:1486 写 flame=15 × 网关 IsPro=FlameLevel>=3（user_context.go:129）⇒ 166/166 游客 is_pro=true 进 LLM tier 钳制 | REVIEW_RECEIPT 断言2 代码链路五环实证 | T-truth-ispro（D17: entitlement 独立字段） | OPEN |
| V3-FIX-03 | P1 | 统计模块接线前 | core/statistics 三仓库 fetchFromApi 生成 mock 且经 _putInWarmCache 落 Isar（24h TTL, isFullySynced=true）; 红测因沙箱基建未入库，修复卡须先补写红测 | REVIEW_RECEIPT 断言3 代码级实证 + dart run 探针 25 mock 标记 | T-truth-corestats（接真实 API 或删除; Isar 假缓存一次性失效） | OPEN |
