# REVIEW_RECEIPT · V3-FIX-08（P1）：社区 Feed cohort 污染修复

- 验收员: V3 Fleet R1（wt6 独占，独立重验，不信任 Worker 自报）
- 日期: 2026-09-19
- 审查对象: `wt6/v3-output/V3-FIX-08/{REPORT.md, changes.patch}`；基线 820c0203
- 方法: patch↔树逐字节比对、基线浅克隆 RED 复现、两轮变异实验、13 用例+回归套件实跑、live DB 自构只读 SQL 复算、`apply --3way --check` 合入预演（含主仓 HEAD 前移后复验）、开关位查询级翻转实验

---

## 0. 逐断言 Verdict

| # | Worker 声称 | Verdict | 独立证据 |
|---|---|---|---|
| 1 | 基线：公开未删帖 341 = guest 336 + seed 5、email 0（漂移+10）；评论/点赞 0 行 | **CONFIRMED** | 自构只读 SQL：posts 全库 341、软删 0、非 public 0；feed 口径 guest 336 + seed 5、email 0；post_comments 0 行、post_likes 0 行。账号普查 guest 171 / email 106 / seed 7（deleted_at IS NULL）逐项吻合 |
| 2 | Post 唯一读取实现在 community.py（Go 网关仅代理） | **CONFIRMED** | 全仓 grep `select(Post)`：仅 community.py 5 处（319/478/572/635/673）+ guest_seed_service.py:2588（播种侧，非用户可见读面）；`community_service.py` import 列表无 Post 模型、无 Post 查询（:3012 是 FIX-07 R4 的 User 搜索过滤，与本卡无交集）；网关 `proxy_routes_test.go` 社区路由全部为代理 |
| 3 | 主修面 S1（全局 feed）+ S3（评论列表）+ S5（like/comment 护栏）已修 | **CONFIRMED** | patch↔树 `diff` 逐字节一致（含两轮变异后还原复验）；6 处编辑与 §3 描述一致；S6 写路径（delete_post/delete_post_comment）确未动且属 owner 自查 |
| 4 | 三个关系 scope 显式不过滤（与 FIX-07 好友列表同边界）且红测钉住 | **CONFIRMED（真绊线，非现状描述）** | 变异实验 2：把 cohort 谓词外溢到 squad/goal_mates/following 三分支 → `test_relational_scopes_stay_unfiltered[*]` 3 用例全红；FIX-07 REPORT §0 R8/§4 确立「群成员属显式关系面非聚合污染」同一边界，两卡口径一致 |
| 5 | 共享常量 import（FIX-07 parity），零新词表 | **CONFIRMED** | `community.py:45` import 自 `app.core.telemetry_boundary`（常量 `("guest","seed")` :87）；S3 评论过滤 `not_in(EXCLUDED_COHORT_REGISTRATION_SOURCES)` 与 FIX-07 friend_match :752 / user_search :3012 逐字同款；feed 面经理由 `_excluded_feed_cohorts()`（默认槽空 = 与共享词表完全等价，实测 binds 一致） |
| 6 | 本人帖始终可见有测试钉住（变异加全量过滤→红） | **CONFIRMED** | 变异实验 1：`_cohort_visible_post_clause` 去掉 or-本人分支改全量过滤 → `test_global_feed_keeps_self_posts_visible` + `test_interaction_guard_keeps_self_posts_manageable` 恰好 2 用例红；与 FIX-07「游客可见自己分数、只是不上榜」同族语义 |
| 7 | RED：基线克隆 4F/1P；feed 文件因新常量无法收集 | **CONFIRMED** | /tmp 浅克隆 820c0203（app/gen 补拷）实跑：comments 1F+1P、guard 3F，合计 **4 failed, 1 passed**；feed 文件收集失败主因 `ImportError: cannot import name 'FEED_EXAMPLE_CONTENT_SOURCES'`（与自报一致；伴随的 OpenAIError 是 llm_service 单例在无凭据下的 loguru 日志噪音，裸 import EXIT=0，不影响结论） |
| 8 | GREEN 13 用例 + 回归 25P+1F（1F 为 HEAD 既有） | **CONFIRMED** | wt6 实跑 13/13 passed；回归 7 文件 25 passed + 1 failed（`route_shadowing::test_community_accountability_registered_with_response_model`），该失败在基线克隆上同样 1F/1P 复现 → HEAD 既有，与 FIX-07 REPORT §4 记录一致 |
| 9 | 404 护栏语义（cohort 帖对非本人 = 不存在） | **CONFIRMED** | like/comment 取帖语句加可见性谓词 → `scalar_one_or_none()` 落 404（「动态不存在」/「Post not found」），与软删帖行为一致，不泄露存在性（403 会）；作者本人 or 分支不受限；2 个用例断言 404 + 谓词 + 绑定值 |
| 10 | 产品裁决：无现成「官方示例内容」机制，留 `FEED_EXAMPLE_CONTENT_SOURCES=()` 开关位 | **CONFIRMED** | `seed_content.py` 为 LLM few-shot 库、`BroadcastMessage` 为公告通道、Post 模型无官方/置顶字段（独立查证一致）；开关默认 `()`，翻转语义**查询级实证**：monkeypatch 槽=('seed',) 后编译 feed 查询 NOT IN binds 含 guest 不含 seed——翻转在查询层真实生效（见发现 B1：生效但未钉） |
| 11 | 修后 live 三面 guest/seed 全零、feed 空集 | **CONFIRMED** | 自构 SQL（仅追加 NOT IN ('guest','seed')）：S1 feed 0 行、S3 评论 0 行、S5 可交互集 0 行；email 帖 0 → 空集结论成立（诚实结果，冷启动属产品项，与 FIX-01 HIDDEN 建议精神一致） |
| 12 | 相邻面建议开卡（群目录/推荐+种子群成员） | **CONFIRMED 且证据更强** | 独立取证：未删群 171 个全部 is_public，群主 guest 168 + seed 3、email 0；群成员 guest 672 + seed 12；群消息 guest 336 + seed 14。真实用户加入任一种子群后 S2 关系面/群目录/群消息均见 cohort 内容。建议开卡成立（详见 §2 发现 C1 举例小瑕疵） |

## 1. 验收要求逐项结论

1. **改动面**：`git status` = 1M + 3A + 1??，与自报一致；`git diff HEAD` 与 changes.patch 逐字节一致（变异实验后还原复验二次通过）；无夹带（diff 仅 community.py +60/-3 与 3 个测试文件，untracked 仅交付目录）。
2. **FIX-07 parity**：词表共享 import 非字面量 ✓；S3 谓词与 FIX-07 逐字同款 ✓；本人帖可见双钉 + 变异红 ✓。
3. **关系 scope 边界**：变异实验证明是「不得把关系面也过滤」的真绊线（过度过滤即红），非现状描述 ✓；与 FIX-07 好友列表/群成员显式关系边界一致 ✓。
4. **404 语义**：合理（不可见=不存在，同软删帖；不泄露存在性）；测试覆盖 404 状态码 + 谓词 + 绑定值 ✓。
5. **测试实跑**：13/13 + 25P/1F 全部复跑吻合；RED 4F/1P 基线复现 ✓。
6. **live 复算**：自构 SQL（非照抄 Worker 口径）三面归零、空集确认 ✓。
7. **开关位**：默认 () + 只放行指名 cohort 的 helper 行为有单测；**查询级翻转生效经我方实验证实**，但生效接线本身未被已提交测试钉住（见 B1，非阻塞）。
8. **合入预演**：`git apply --3way --check` 对 820c0203 ✓；主仓 HEAD 审查期间前移至 2375694c（C-03 merge），fetch 后复验同样 ✓（community.py 走 3-way clean，新测试文件 fallback 直加）。在途重叠：C-03 改动文件与 FIX-08 零交集；wt5（test_task_quick_actions）/wt8（llm 面）/wt9（conflict_resolver+memory 面）均不触及 community.py 与本卡测试文件 → 预测合入冲突面：无。
9. **群目录相邻面**：建议成立，数据比 REPORT 更强（见 #12）。

## 2. 发现与分级

**A 级（必修，阻塞合入）**：无。

**B 级（建议，不阻塞）**
- **B1 开关位查询级接线未钉**：`test_example_content_switch_admits_only_named_source` 只断言 `_excluded_feed_cohorts()` 返回值；若未来有人把 `_cohort_visible_post_clause` 改回直接用 `EXCLUDED_COHORT_REGISTRATION_SOURCES`，13 测全绿而翻转在查询层失效。我方实验证实当前接线正确（default binds ⊇ {guest,seed}；flipped binds = {guest}），但建议后续补一条「翻转后编译 feed 查询、NOT IN 绑定值不含被放行 cohort」的用例把接线钉住。
- **B2 槽位不对称的既设计性**：S3 评论过滤有意用全量词表（不经裁决槽，REPORT §3.4 已给理由：槽语义是「示例帖回投」非「示例评论」）——意味着未来翻转槽位后 seed 帖回投而其评论不可见。属合理设计选择，建议在翻转真正启用时随产品裁决一并复审，现在无需动。

**C 级（记录）**
- **C1 相邻面举例小瑕疵**：REPORT §0 相邻面举例「算法冲刺小队」实为 guest 群主（5+ 实例）；seed 群主实例为「期末自习室/英语口语晨读营/产品设计共学社」3 个。结论（seed 拥有公开群 + 12 席群成员 + 14 条群消息）不受影响。
- C2 基线克隆收集期的 OpenAIError 噪音（llm_service 单例无凭据时 loguru 打印）与 FIX-07 时代环境一致，非本卡引入；测试全程零真实 LLM 调用。

## 3. 实跑命令清单（R1 独立执行）

```bash
# 树状态与 patch 一致性
cd wt6 && git status --short && git log --oneline -3
git diff HEAD > /tmp/r1_wt6_actual.diff && diff /tmp/r1_wt6_actual.diff v3-output/V3-FIX-08/changes.patch
# 环境（wt6 内临时 venv，收工已删）
uv venv .venv --python 3.11 && uv pip install -r <reqs 去 python-lzo>（aliyun 镜像 403 → pypi.org）
# GREEN
pytest tests/api/test_{community_feed_cohort_filter,post_comments_cohort_filter,post_interaction_cohort_guard}.py -v   # 13 passed
# RED（/tmp 浅克隆基线 820c0203 + 补拷 app/gen + 拷入 3 测试文件）
git clone --depth 1 wt6 /tmp/r1-fix08-baseline
pytest <同上 3 文件>   # 4 failed, 1 passed；feed 文件 ImportError: FEED_EXAMPLE_CONTENT_SOURCES
# 变异实验（cp /tmp 备份法，单文件粒度，逐一还原）
M1 全量过滤去 or-本人分支 → 2 红（self-posts 两钉）
M2 cohort 谓词外溢三关系分支 → 3 红（scope 边界钉）
还原后 git diff HEAD 与 patch 再比对 → 一致
# 回归
pytest <7 个回归文件>   # 25 passed, 1 failed（route_shadowing，基线克隆复现同败 → HEAD 既有）
# live 只读复算（docker exec sparkle_db psql，BEGIN TRANSACTION READ ONLY ... ROLLBACK）
账号普查 / posts 普查 / feed 面 pre-post / comments 面 / 可交互集 / post_likes / 群主·群成员·群消息 cohort 分布 / seed 群名
# 合入预演
git apply --3way --check changes.patch   # 对 820c0203 ✓；fetch 主仓新 HEAD 2375694c 后复验 ✓
# 开关位查询级翻转实验（临时 python -c，不入库）
default binds ⊇ {guest,seed}；槽=('seed',) 后 binds={guest}（seed 放行）→ 查询层生效
```

## 4. 总 Verdict

**ACCEPT**（附带 B1/B2 建议，不阻塞合入；B1 建议随相邻面卡或后续小卡补钉）。

改动面干净、口径与 FIX-07 家族严格对齐、边界钉经变异实验证明为真绊线、全部声称独立复算吻合、合入无冲突预测。污染面主修三面 + 防御护栏成立；关系面不过滤是明示且钉住的边界；空 feed 为 D20 口径下的诚实结果，冷启动属产品项已正确上抛。

---

- R1 验收员（wt6 独占）
- 2026-09-19
