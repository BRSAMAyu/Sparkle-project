# Dynamic Issues Ledger

> Leader/Simulator 在 V3 执行中追加。不要在此预填历史已完成 bug。

| ID | Severity | Journey | Reproduction | Evidence | Owner task | Status |
|---|---|---|---|---|---|---|
| V3-FIX-01 | P0 | 排行榜/社群/统计聚合 | FINDINGS.md F1 SQL 直接复现（top-50=100% guest, top_score 132.5; 复核加强: top-100 亦 100% guest, email 用户全员 best_rank≥169） | v3-output/B-02/REVIEW_RECEIPT.md 断言1 + FINDINGS.md F1 | T-truth-leaderboard | FIXED@V3-FIX-01（top-50=100% email, top_score 10.0; 双路验证+主仓 pytest 3+6 绿; 同族面转 V3-FIX-07） |
| V3-FIX-02 | P0 | 聊天路由 entitlement | guest_seed_service.py:1486 写 flame=15 × 网关 IsPro=FlameLevel>=3（user_context.go:129）⇒ 166/166 游客 is_pro=true 进 LLM tier 钳制 | REVIEW_RECEIPT 断言2 代码链路五环实证 | T-truth-ispro（D17: entitlement 独立字段） | OPEN |
| V3-FIX-03 | P1 | 统计模块接线前 | core/statistics 三仓库 fetchFromApi 生成 mock 且经 _putInWarmCache 落 Isar（24h TTL, isFullySynced=true）; 红测因沙箱基建未入库，修复卡须先补写红测 | REVIEW_RECEIPT 断言3 代码级实证 + dart run 探针 25 mock 标记 | T-truth-corestats（接真实 API 或删除; Isar 假缓存一次性失效） | OPEN |
| V3-FIX-04 | P1 | LLM glm 车道 | glm-5.3-flash 语义: 标准端点 thinking disabled 返 400 code 1210（"该模型始终思考"）; coding 端点可真实关思考(1.01s 无 reasoning); 引擎 clear_thinking extra_body 被静默忽略; 思考占 completion 预算 84-88% 可致 max_tokens=1024 空回复 | v3-output wt2 B-05b SUPPLEMENT_KEY_ROTATED.md（B-05b 复测 16/16+9/9 lane 实测） | T-llm-glm-thinking-control | FIXED@V3-FIX-04（coding 端点 reasoning_tokens=0 实证; ceil(1.25x) 留量; 构造点唯一; 主仓 6/6 绿） |
| V3-FIX-05 | P1 | shop 空目录暴露 | /shop 注册+streak_details_screen.dart:415 唯一入口；shop_items/shop_purchases 0 行（B-01 HIDDEN 判定 + Reviewer 确认） | v3-output/B-01/REVIEW_RECEIPT.md + REPORT §4 | T-hide-shop-entry（移除该入口，随 gamification 降权） | OPEN |
| V3-FIX-06 | P1 | 记忆仲裁契约 | correction_feedback.py:427 持续写入未登记 lane aurora_calibration_receipt（登记表 conflict_resolver_service.py:72-79 仅 6 lane，d1d4 定义该 lane 为红线测试用例故意不登记）；dev DB 0 行未爆量 | v3-output/B-06/REVIEW_RECEIPT.md R1-E1 | T-register-aurora-lane（产品裁决: 登记 lane 或迁移写入点，二选一） | OPEN |
| V3-FIX-07 | P1 | 榜单/推荐同族污染面（V3-FIX-01 波及排查） | 连胜榜/光子榜 top-20 全席 guest（1020 vs 10）+ 好友推荐候选池 173 个 guest/seed searchable_by=everyone 按 flame15 压头 + streak join 笛卡尔积独立 bug；共 HIGH×3/MED×3/LOW×4 | wt7 v3-output/V3-FIX-01/REPORT.md §4 | T-truth-family（按 HIGH→MED 顺序逐个修，SQL 复算同 F1 口径） | OPEN |
| V3-FIX-08 | P1 | 社区 Feed cohort 污染（B-02X 新发现 INV-15） | community feed 查询无 registration_source 过滤: DB as_of 2026-09-19 公开帖 331/331 全为 guest/seed 作者, email 用户 0 帖——真实用户进社区看到的全是种子内容 | wt6 v3-output/B-02X/REPORT.md INV-15 + lineage_extension.csv | T-truth-community-feed（feed/帖子列表加 cohort 过滤或混排策略, 需产品裁决顺序: 修过滤 or 先标注） | OPEN |
