# B-02 调查证据 · 数据真实性 / Mock 污染 / 指标 Lineage

Base SHA: `f01f4ae81ebd645b8f313afd2e9a243cfe83a3f0`（未 commit，工作树仅新增 `mobile/test/core/statistics/` 与 `v3-output/B-02/`）
调查日期：2026-09-19 ｜ 方式：静态代码溯源 + 主仓 DB 只读查证（`docker exec sparkle_db psql`）+ 网关 :8080 / 引擎 :8000 存活探测。

> **复核修订（2026-09-19，独立 Reviewer verdict CHANGES 已处置，详见同目录 REVIEW_RECEIPT.md）**：
> ①（C1）红测文件 `mock_statistics_guard_test.dart` **未随本卡收编入库**（沙箱 flutter test 基建挂起 + CI 关停），污染机制以代码链路与 dart run 探针实证；
> ②（C4）F1 验收 SQL 已补 `deleted_at IS NULL`，对齐服务实际过滤 `not_deleted_filter()`；
> ③（C3）文中全部 DB 计数为 2026-09-19 时点快照（复核时 live 已漂移：users 219→248、node_status 8135→8478，结构性结论经复核重跑全部成立），后续复核以重跑 SQL 为准。

---

## 一、结论摘要

| 真实性评级 | 判定 |
|---|---|
| **actual（真实计算）** | 首页 dashboard/growth、周报统计族、understanding-depth（新）、streak/成就的计算逻辑、星图掌握度的服务端写入族、focus 本地统计 |
| **actual 但被 seed 污染（cohort pollution）** | 排行榜（top-50 100% 游客种子号）、flame 等级、星图掌握度库（98.9% 行属 guest）、成就库（guest 944 行 vs 真实用户 3 行）、社群内容 |
| **estimated（明示的模型估计）** | 考试冲刺 estimated_score_now / pass_probability、predictive dashboard（带 confidence + fallback_used） |
| **demo（门控内 mock）** | 移动端 DemoDataService 全量假人生（编译期 DEMO_MODE / 游客偏好开关，有 token 即强制关闭）、insights 各 repo 的 demo 分支、Mock 认知/社群仓库（USE_MOCK） |
| **mock 休眠但污染路径健在** | `core/statistics` focus/capsule/agent 三个仓库 `fetchFromApi` 生成假数据并可写进 Isar 生产缓存（红测未随卡入库，机制经两路复核代码级实证） |
| **server mock** | llm_service `demo_mode`：无 API key 即把罐头回复当正常 AI 输出返回 |

## 二、两条最高严重度发现（可复现）

### F1 · 全局排行榜被游客种子号整体占据（D20 违例，共享表面）

`backend/app/services/leaderboard_service.py`（57-60 行权重）：
`score = mastery≥50 节点数×1.0 + total_checkin_days×0.5 + 成就数×2.0 + longest_streak×1.5`。
全文件**无任何 `registration_source` 过滤**，而 `guest_seed_service.py` 为每个游客直写
`user_node_status`（8050 行）、`user_streak_stats`（longest=30/checkin=45）、`user_achievements`（944 行）。

主仓 DB 复算（2026-09-19，与服务同权重）：

```sql
WITH leaderboard AS (
  SELECT u.id, u.username, u.registration_source,
    count(DISTINCT uns.node_id) FILTER (WHERE uns.mastery_score >= 50) * 1.0 +
    COALESCE(s.total_checkin_days,0) * 0.5 + count(DISTINCT ua.achievement_id) * 2.0
    + COALESCE(s.longest_streak,0) * 1.5 AS score
  FROM users u
  LEFT JOIN user_node_status uns ON uns.user_id=u.id
  LEFT JOIN user_streak_stats s ON s.user_id=u.id
  LEFT JOIN user_achievements ua ON ua.user_id=u.id
  WHERE u.is_active AND u.deleted_at IS NULL  -- C4 修订: 对齐服务 not_deleted_filter() (models/base.py:79)
  GROUP BY u.id, s.total_checkin_days, s.longest_streak)
SELECT registration_source, count(*) users_in_top50, round(max(score)::numeric,1) top_score
FROM (SELECT *, row_number() OVER (ORDER BY score DESC) rn FROM leaderboard) t
WHERE rn <= 50 GROUP BY registration_source;
-- => guest | 50 | 132.5   （email 用户 0 人入榜）
```

队列事实（时点快照，已漂移见文首修订③）：`users` 219 = guest 160 / email 52 / seed 7。
**修复映射**：leaderboard 查询加 `registration_source NOT IN ('guest','seed')`（或等效 cohort 标记）；社群/统计聚合同理。

### F2 · `IsPro = FlameLevel >= 3` × 游客种子 flame=15 ⇒ 所有游客以 is_pro=true 送入 AI 路由（D17 已冻结拆除）

- `backend/gateway/internal/service/user_context.go:129` `IsPro: user.FlameLevel >= 3`
- `backend/gateway/internal/handler/chat_orchestrator_chatflow.go:284` `profile.IsPro = fallbackUser.FlameLevel >= 3`
- `guest_seed_service.seed_guest_user_data` 写 `user.flame_level = 15` → DB 实测 160 个 guest 全部 flame_level=15。
- 商业/路由 entitlement 被游戏化字段劫持，且被种子数据灌满。

## 三、mock → Isar 生产缓存路径（红测）

`core/statistics/presentation/providers/{focus,capsule,agent}_statistics_provider.dart` 的
`fetchFromApi` 返回 `_generateMock*` 常量；父类
`core/statistics/data/repositories/hybrid_statistics_repository.dart`
`getStatistics()` cold 路径把返回值 `_putInWarmCache()` 写入 Isar（TTL 24h），
且 `isFullySynced = !entity.isFromCache` = **true** —— 假数据被标记为"已与服务器完全同步"。
当前三个仓库无 UI 消费者（休眠脚手架），但路径是活的，接线即污染。
红测：`mobile/test/core/statistics/mock_statistics_guard_test.dart` —— **未随本卡收编入库**（C1 修订：沙箱 flutter test 在 loading 阶段挂起属环境限制、CI 已关停，文件仅存于工作沙箱；机制结论不依赖红测，由下行探针 + Reviewer 代码级复核实证）。
RED 判定已用等价逻辑的独立 `dart run` 探针确定性验证：三个 `fetchFromApi` 实现体共 25 个生成 mock 标记（focus 8 / capsule 10 / agent 7；复核按 `_generateMock*` token 口径计 19（6/8/5），口径差异不影响 RED 结论）。
注 1：未采用真实 Isar 集成断言，因仓内 IsarCore 测试环境有预存 segfault（`test/unit/sync_engine_test.dart` @Skip）。
注 2：本沙箱 `flutter test` 对所有测试（含既有 hash_utils_test.dart）在 loading 阶段挂起 12 分钟超时，属环境限制；红测文件在正常环境应得 1 个 failure（= RED）。

## 四、游客种子命名空间（可查询区分 —— 验收项 2）

| 标记 | 位置 | 查询方式 |
|---|---|---|
| `users.registration_source` ∈ {'guest','seed','email'} | auth.py 注册路径 / `_ensure_demo_user` | `SELECT registration_source, count(*) FROM users GROUP BY 1;` |
| `knowledge_nodes.is_seed = true` | guest_seed_service.py:1688 | 种子知识节点 |
| `sector_classification_model='guest_seed'` | guest_seed_service.py:1677,1696 | 星域分类来源 |
| Photon 流水 `source='guest_seed:welcome_bonus'` | photon_transaction_history | 体验积分可追溯 |

游客种子是**显式体验模式**（D05 边界内），但必须在排行榜/社群/真实 cohort 指标中按上述标记排除——目前仅"可查询区分"，未"实际区分"。

## 五、新上线路径验证：GET /insights/understanding-depth

链路：gateway `proxyWithHeaders`（proxy_routes.go:461，未登录 401 实测）→
`app/api/v1/insights.py::get_understanding_depth` → `UnderstandingDepthMetricService.get_trend`
→ 表 `understanding_depth_daily`（Celery `compute_understanding_depth_daily` 每日聚合，
输入 `context_pack_runs.memory_counts` / `chat_messages(role=user)` / `memory_corrections`）。
公式 v0.1：`0.40*memory_injection + 0.25*personalization + 0.20*non_correction + 0.15*non_repeat`，无活动日不落行。
DB 实测：149 用户、2026-09-18 首跑、score 0.275–0.933（avg 0.384）——**真实计算，非 mock**。
遗留：聚合未排除 guest/seed cohort，"越用越懂"统计当前混入大量种子账号会话。
Mobile 消费端尚未发现（后端先上线），UI 接入时遵守 D06（不得渲染成神秘单百分比）。

## 六、API 实测记录

- `GET :8080/healthz` → 200；`GET :8000/health` → 200（两服务在跑）
- `GET :8080/api/v1/insights/understanding-depth | /dashboard/status | /leaderboards`（未带 token）→ 均 401（鉴权隔离正常，未伪造 token 写库）

## 七、后续任务映射建议

1. **T-truth-leaderboard**（P0）：leaderboard/社群/统计聚合排除 guest/seed cohort（F1 SQL 即验收）。
2. **T-truth-ispro**（P0，D17）：拆除 `IsPro=FlameLevel>=3`，entitlement 独立字段。
3. **T-truth-corestats**（P1）：`core/statistics` 三仓库接真实 API 或删除；红测转绿；已入 Isar 的假缓存需一次性清理（迁移或版本号失效）。
4. **T-truth-guest-ux**（P1，D05）：游客体验界面显式标注"体验示例"；photon 体验积分 UI 标注。
5. **T-truth-llm-demo**（P2）：生产配置强制 LLM key；demo 回复需明示。
6. **T-truth-ud-cohort**（P2）：understanding_depth 聚合按 cohort 过滤或报表区分。
