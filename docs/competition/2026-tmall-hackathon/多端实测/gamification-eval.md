# 游戏化模块服务端实测报告（achievement / shop / photon / leaderboard）

> 实测日期：2026-09-19 ｜ 主仓 HEAD：`b62b530b` ｜ 测试人：游戏化模块实测代理
> 方法：纯服务端 API 实测（串行 curl，游客 token），客户端仅读代码定位调用面；未改任何产品代码。
> 测试环境：网关 :8080 / 引擎 :8000（运行于 sysrev worktree `b97a0674`，经 diff 验证本报告涉及的 5 个游戏化文件与主仓 HEAD **逐字节一致**）/ PG `sparkle_db` / Redis。
> 测试账号：`POST /api/v1/auth/guest?guest_id=gameprobe01`（JWT `is_guest:true`，初始光子 1000）。

---

## 1. 结论速览

| 维度 | 结论 |
| --- | --- |
| **API 通过率（网关语义正确）** | **21 / 26 ≈ 81%**（`events/process` 为有意不代理的内部端点，已剔除）；引擎直连榜型 5/6 |
| **P1 问题数** | **4**（成就详情 500、排行榜网关重定向死循环、引擎 global/summary 500、游客可转账） |
| **演示阻断（P0 级）** | **商店表在真实环境为空**（`shop_items` 0 行，需手动跑 `scripts/init_shop.py`） |
| **数值真实性** | **全部真实计算，无 mock**（行锁、幂等键、账本链、SQL 排行榜均为实打实实现，并实测通过对账） |
| **综合演示价值** | 光子+商店：**可秀且能秀工程深度**（修 2 个阻断后）；成就：列表/地图可秀、详情页会炸、无法现场解锁；排行榜：数据真实但 App 内不可达、网关链路坏 |

---

## 2. 客户端 API 面（mobile 侧消费方式）

定义集中在 `mobile/lib/core/network/api_endpoints.dart`：

- **成就**（:523-551）：`/achievements`、`/stats`、`/map`、`/streak`、`/streak/history`、`/{id}`、`/{id}/share`、`/{id}/pin`、`/share-templates`、`/contracts`、`/skins(/{id}/equip)`、`/titles(/{id}/equip)`、`/close-to-unlock`；`/events/process` 标注 internal
- **排行榜**（:574-581）：`/leaderboards`、`/summary`、`/my-rank`、`/types`、`/top-three/{type}`、`/refresh-cache`
- **商店**（:614-617）：`GET /shop/items`、`POST /shop/purchase`（客户端强制带 `Idempotency-Key` 头）、`GET /shop/purchases`
- **光子**（:619-622）：`GET /photons/balance`、`GET /photons/transactions`、`POST /photons/transfer`
- **背包**（:625-627）：`GET /inventory`、`GET /inventory/owned`、`POST /inventory/equip`（shop_repository.dart:127 调用**裸 `/inventory`**）

网关侧全部为代理（`proxy_routes.go` :301-322 成就白名单式注册、:914-919 榜、:1023-1035 shop/photons、:1043-1048 inventory 均挂 authMiddleware）。

---

## 3. API × 结果矩阵

### 3.1 光子系统

| # | 端点 | 结果 | 断言 |
| --- | --- | --- | --- |
| 1 | `GET /photons/balance` | 200 | 游客种子 1000 光子 ✅ |
| 2 | `GET /photons/transactions` | 200 | 含 `guest_seed:welcome_bonus` +1000 流水，`meta.total_count` 正确 |
| 3 | `POST /photons/transfer` | **200（应为 403）** | **P1**：游客转账成功（100→90，收款方 1010）。守卫只比对遗留常量 `GUEST_USER_ID="guest_sparkle_demo_visitor"`，不看 JWT `is_guest` 声明；与 `guest_seed_service.py:1492` 注释"访客…不能转账"矛盾 |

**账本链对账（购买后全量拉取）**：`0→1000(+1000 seed) → 900(-100) → 800(-100) → 300(-500) → 100(-200)`，逐笔 `balance_before == 上一笔 balance_after`，**链完全一致**；4 笔购买每笔都有对应交易记录（shop_service.py:408 的"修复bug：购买未记录交易"确实已修）。

### 3.2 商店系统（seed 后）

| # | 场景 | 结果 | 断言 |
| --- | --- | --- | --- |
| 4 | `GET /shop/items`（seed 前） | 200 但 `data:[]` | **P0 演示阻断**：`shop_items` 表 0 行；`seed_shop_items()`（15 件：4 皮肤/4 称号/3 消耗品/4 加成）**全仓唯一调用方是手动脚本 `backend/scripts/init_shop.py`**，engine 启动、guest seed、迁移均不触发 |
| 5 | `GET /shop/items`（seed 后） | 200 | 15 件，稀有度/价格/限量/`is_owned` 字段齐全 |
| 6 | 购买消耗品（100） | 200 | 1000→900 ✅，`balance_before/after` 与余额端点一致 |
| 7 | 重复购买同款消耗品 | 200 | 900→800，数量累加（`/inventory/owned` 可见 2 条）✅ |
| 8 | 购买皮肤（500） | 200 | 800→300 ✅，购买即自动装备（`EquipmentService.equip_shop_skin`），`is_owned` 翻转 |
| 9 | 重复购买已拥有皮肤 | 400 | `User already owns item`，余额不动 ✅（非消耗品唯一性守卫生效） |
| 10 | 余额不足（300 买 3000） | 400 | `Insufficient photon balance: 300 < 3000`，余额复核不变 ✅（**无负余额**） |
| 11 | 幂等重放（同 key 同物品） | 200 | `replayed:true`、同一 `purchase_id`、**不重复扣款** ✅ |
| 12 | 同 key 换物品 | 409 | Idempotency conflict ✅ |
| 13 | 缺 `Idempotency-Key` 头 | 400 | ✅（服务端也强制，双重保险） |
| 14 | **并发双购竞态**（余额 300，并发 2×200 称号，不同 key） | 1×200 + 1×400 | 行锁（`with_for_update`）生效：**恰好一单成功，余额精确 100，无丢币无双花** ✅ |
| 15 | `GET /shop/purchases` | 200 | 4 条记录，`before/after` 与流水互洽 |
| 16 | `GET /inventory/owned` | 200 | 所有权与购买记录一致 |
| 17 | `GET /inventory`（裸路径） | **301→307 死循环** | **P2**：与排行榜同款重定向乒乓（见 §3.4）；客户端 `getInventory()`（shop_repository.dart:127）正打此路径，背包页会挂 |

### 3.3 成就系统

种子形态（游客）：**43 个成就**（legendary 5 / epic 10 / rare 14 / common 14），**3 个已解锁**（`night_owl` 隐藏 epic、`streak_7`、`sprint_first`），进行中：`study_100hours` 62/100、`nodes_100` 45/100、`streak_30` 7/30；连胜态 7/30、冻结券 2/3、累计打卡 45 天——**演示数据充足且形态讲究**（隐藏成就带 hint、多线路地图）。

| # | 端点 | 结果 | 备注 |
| --- | --- | --- | --- |
| 18 | `GET /achievements` | 200 | 43 项，`achievement`+`user_progress`+`is_unlocked`+`progress_percentage` 结构完整 |
| 19 | `GET /achievements/stats` | 200 | `unlocked 3/47=6.4%`、`total_photons` **等于真实当前余额** ✅；但 `total=47` 与列表 43 不一致（P3，疑含隐藏/未上线定义） |
| 20 | `GET /achievements/map` | 200 | 23KB，三线路（含 `conquest_lane`）+坐标+隐藏节点，可秀 |
| 21 | `GET /achievements/streak` | 200 | 与种子一致（7/30，45 天） |
| 22 | `GET /achievements/streak/history` | 200 | 逐日 `missed/kept`+冻结券使用明细 |
| 23 | `GET /achievements/close-to-unlock` | 200 | 5KB 推荐列表 |
| 24 | `GET /achievements/contracts` | 200 | `has_active_contract:false`（契约功能在但游客无契约） |
| 25 | `GET /achievements/skins` | 200 | 8 皮肤（default + 7 成就解锁） |
| 26 | `POST /skins/default/equip` | **404** | **P2**：`Skin default not unlocked`——全仓只有 2 处创建 `UserGalaxySkin` 行（guest seed 只给 `skin_nebula`、成就解锁），**无人能拿到 default 行**；即玩家换肤后永远回不去默认主题 |
| 27 | `POST /skins/skin_nebula/equip` | 200 | 已解锁皮肤正常装备 ✅ |
| 28 | `POST /titles/title_sprinter/equip` | 200 | 装备态回读一致 ✅ |
| 29 | `GET /achievements/{id}`（3 个不同 id 均试） | **500（100% 复现）** | **P1**：`'AchievementEngine' object has no attribute 'get_achievement'`——公开别名方法（achievement_engine.py:2993 "Public alias for _get_achievement"）**加错了类：定义在 `ContractService`（:2824 起）而非 `AchievementEngine`（:124 起）**；API 层（api/v1/achievements.py:79）调用必炸。成就详情页全挂 |
| 30 | `POST /achievements/events/process` | 网关 404 | **设计如此**：引擎直连要求内部 token（`Invalid internal token`），网关有意不代理；客户端常量标注 internal。副作用：**现场无法公开触发成就解锁**，解锁只能由学习事件驱动 |
| 31 | `GET /achievements/share-templates` | 200 | 4 模板 |

成就解锁的光子奖励链路为真实实现：`_unlock_achievement → _grant_rewards`（achievement_engine.py:1465），带 Celery 补偿重试（:1612-1651）。

### 3.4 排行榜（对照 KNOWN_CODE_DEBT_LEDGER #3）

| # | 端点 | 结果 | 备注 |
| --- | --- | --- | --- |
| 32 | `GET /leaderboards/types` | 200 | 6 类型 |
| 33 | `GET /leaderboards?type=…`（裸集合） | **301↔307 无限重定向** | **P1**：网关 gin 对 `/*path` 空段 301 → `/leaderboards/`；引擎 FastAPI `redirect_slashes` 再 307 回裸路径，且 **Location 为绝对内网地址 `http://127.0.0.1:8000/...`（内网拓扑泄露）**。`curl -L` 跟到底得 401（换 host 丢 Authorization）。Dio 默认 3 次重定向后必抛异常 |
| 34 | 引擎直连 `?type=friends/weekly/streak/photon/photon_weekly` | 5×200 | 真实数据：60 参与者、光子榜榜首 5000+、`my_rank` 各榜各异 ✅ |
| 35 | 引擎直连 `?type=global` | **500（100% 复现）** | **P1**：`sqlalchemy.exc.InvalidRequestError: Don't know how to join to UserNodeStatus`——`_get_global_leaderboard`（leaderboard_service.py:205-317）ORM join 歧义（诊断脚本抓到全栈）；同 SQL 手译 PG 手跑正常，纯 ORM 层 bug |
| 36 | `GET /leaderboards/summary` | **500** | P1 的连带（summary 内含 global 榜，:175-178） |
| 37 | `GET /leaderboards/my-rank?type=streak` | 200 | rank 52/60、percentile、nearby_users ✅ |
| 38 | `GET /leaderboards/top-three/streak` | 200 | 前三+徽章 ✅ |

**债务台账对照**：#3 指出移动端排行榜 1143 行完整实现但**未挂路由**（App 内永远到不了该页）——这恰好掩盖了本节 3 个服务端 bug。#1（移动端统计 mock）不属游戏化三模块，三者服务端**无任何 mock**。

### 3.5 数值真实性定性（任务 6）

| 模块 | 定性 | 证据 |
| --- | --- | --- |
| 光子余额 | **真实** | `_update_balance` 带 `FOR UPDATE` 行锁+负余额守卫（photon_service.py:106-153）；另有原子条件 UPDATE（`WHERE balance >= amount`，:155-194）；缓存事务后失效 |
| 交易流水 | **真实** | 实测全链对账一致（§3.1） |
| 商店购买 | **真实** | 单事务：行锁查物→库存→所有权→扣款→流水→发码→购买记录→自动装备（shop_service.py:298-504）；幂等键表 `idempotency_keys` 带 24h TTL+请求指纹冲突检测 |
| 成就进度 | **真实** | 引擎 3000+ 行，事件驱动评估（`process_event`）、前置条件链、解锁副作用（光子奖励+皮肤/称号/视觉元素发放）；种子进度与 streak 端点互洽 |
| 排行榜 | **真实** | 全部 live SQL 排序（streak 榜 join `user_streak_stats`、光子榜直接排 `users.photon_balance`、global 为加权复合分公式 `节点×1.0+打卡×0.5+成就×2.0+连胜×1.5`）；`my_stats` 实算（46 节点/3 成就/7 连胜） |

**结论：游戏化数值不是 mock，是真金白银的工程实现**——文档"材料未覆盖实测"填补后，实测反而证明其服务端质量高于移动端统计模块（台账 #1 的 mock 在统计，不在这里）。

---

## 4. 问题清单（按严重度）

| 级别 | 问题 | 复现 | 根因位置 |
| --- | --- | --- | --- |
| **P0（演示）** | 商店表空，购买链路在真实环境整体不可走 | `GET /shop/items` → `data:[]`；DB `SELECT count(*) FROM shop_items` → 0 | `seed_shop_items` 仅 `backend/scripts/init_shop.py` 可触发，无启动钩子。**本次实测已执行该脚本播种 15 件**（测试者动作，非代码改动） |
| **P1-1** | `GET /achievements/{id}` 全量 500 | 任意 id（`study_100hours`/`streak_7`/`night_owl`）均 500，`detail='AchievementEngine' object has no attribute 'get_achievement'` | 别名方法加进 `ContractService`（achievement_engine.py:2993），`AchievementEngine` 无此方法；api/v1/achievements.py:79 |
| **P1-2** | 排行榜裸集合经网关 301↔307 死循环+内网地址泄露 | `curl -D- http://…/api/v1/leaderboards?type=photon`：301→`/leaderboards/`；再请求 307→`Location: http://127.0.0.1:8000/api/v1/leaderboards?…`；`-L` 终态 401 | gin `RedirectTrailingSlash`（proxy_routes.go:914-919 `/*path` 空段）× FastAPI `redirect_slashes`；`registerREST` 转发未去尾斜杠。`/inventory` 裸路径同病（P2，客户端 `getInventory()` 会踩） |
| **P1-3** | 引擎 global 榜 500，连带 `/leaderboards/summary` 500 | 引擎直连 `?type=global` 500；诊断脚本复得 `InvalidRequestError: Don't know how to join to UserNodeStatus` | leaderboard_service.py:221-244 select 多实体后 outerjoin 推断失败（需 `select_from`） |
| **P1-4（越权）** | 游客可转账光子 | `POST /photons/transfer`（is_guest JWT）→ 200，100→90 | api/v1/photons.py:122-127 只比对遗留常量 `guest_sparkle_demo_visitor`，未读 JWT `is_guest` 声明 |
| P2 | 默认皮肤无人可装备（回不去默认主题） | `POST /achievements/skins/default/equip` → 404 | 无任何代码路径给 `user_galaxy_skins` 写 `default` 行 |
| P2 | `/inventory` 裸路径重定向死循环（同 P1-2 机制） | `curl -D- /api/v1/inventory`：301↔307 | 同 P1-2；客户端 shop_repository.dart:127 |
| P3 | `achievements/stats` 总数 47 ≠ 列表 43 | 两端点对比 | 统计口径含未上线/隐藏定义，未过滤 |
| P3 | 购买响应体冗余 | 同一 payload 重复出现在 `data` 与 `item` 字段 | api/v1/shop.py:133-141 |

**未测**：`POST /achievements/{id}/share`（分享卡生成）、`/{id}/pin`、契约 CRUD、`/leaderboards/refresh-cache`；跳过原因：非核心链路/时间盒。半端实测（websockets 消费时机）按预案跳过——API 面已足够定性。

---

## 5. 演示价值评估（这三模块 demo 能不能秀）

| 模块 | 能否秀 | 条件与话术建议 |
| --- | --- | --- |
| **光子+商店** | **能，且是全场少有的"工程深度"素材** | 前置：先跑 `python scripts/init_shop.py init`（一条命令）。可现场连秀：真实扣款→余额/流水双端点对账→同 key 重放不重复扣款（幂等）→并发双购只成一单（行锁防双花）→余额不足拒付。这是一套完整的分布式一致性叙事，比"能买"高一个档次。**别点背包页**（`/inventory` 死循环），只走商店主页+余额卡 |
| **成就** | **半能** | 能秀：43 成就地图（三线路+隐藏成就）、连胜详情、稀有度面板、close-to-unlock 推荐流，种子形态讲究。不能秀：成就详情页（P1-1 必炸，演示动线要绕开详情点击）；现场"解锁新成就"做不了（events/process 是内部端点，解锁只能由真实学习事件驱动——除非现场跑一次学习会话触发事件总线） |
| **排行榜** | **仅能 curl 秀，App 内不可达** | 数据真实（60 参与者、光子榜/连胜榜/好友榜/周榜全通、my-rank+top-three 可用），但移动端整链未挂路由（台账 #3）+ 网关列表死循环 + summary 500。演示建议：要么按台账决策整链下线别提，要么修 P1-2/P1-3 后以"好友榜"单榜切入（friends 榜数据最漂亮：7 人小圈子、游客排第 1） |

**修复优先级建议（演示视角）**：`init_shop` 挂启动钩子（或 README 写明）> P1-1 一行搬家 > P1-2 registerREST 去尾斜杠（连带修好 /inventory）> P1-4 补 `is_guest` 校验 > P1-3 `select_from` 一行 > P2 default 皮肤。

---

## 6. 实测动作留痕

- 测试账号：`gameprobe01`（user_id `2a993502-4481-4188-944b-1620b714cb53`），测试后余额 90（含一笔 10 光子 P1-4 转账探针）、4 条购买记录、已装备 `skin_nebula`/`title_sprinter`。
- 测试者改动：仅执行仓库自带 `backend/scripts/init_shop.py init`（数据播种，无代码变更）；诊断脚本 `/tmp/lb_diag.py`（会话产物，未入库）。
- 引擎运行副本说明：服务进程跑在 `Sparkle-sysrev/wt6`（HEAD `b97a0674`），与本报告评估的 `b62b530b` 在 shop_service/photon_service/guest_seed_service/shop_seeds/api shop 五文件逐字节一致（`diff` git show 验证），实测结论对主仓 HEAD 有效。
