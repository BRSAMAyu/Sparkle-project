# SQUAD-REJOIN · 小队退队/重加入债务收口（软删行占死全列唯一键）— 收工报告

- Worker：V3 舰队 D 纵队 Worker（社群线，SQUAD-REJOIN 卡）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt181`（基线 `003f71f1`，恰为 PHOTON-IDEM 合入提交）
- 日期：2026-09-23
- 交付物：
  - `backend/alembic/versions/sqrejoin_20260923_group_member_rejoin_unique.py`（新增，迁移，`down_revision="photidem_20260923"`）
  - `backend/app/models/community.py`（修改，GroupMember 全列唯一约束 → 活跃行部分唯一索引，+14/-1）
  - `backend/app/services/community_service.py`（修改，join_group 重加入复活语义 + kick 系统消息修复，+72/-24）
  - `backend/tests/unit/test_squad_rejoin_group_member_unique.py`（新增，行为测试 7 用例）
  - `backend/tests/unit/test_sqrejoin_group_member_unique_migration_sqlite.py`（新增，迁移重放 4 用例）
  - 本报告 + `changes.patch`（5 文件；`git apply --check --3way` 对干净 003f71f1 克隆通过，本机已验）
- 未 commit / 未 push（纪律遵守）；演示库 sparkle 只读 SELECT（迁移由合入方执行）

---

## ① 盘点结论 + 债务真实形状（与卡面推断不同，以代码证据为准）

**卡面推断「退队=硬删行 → flame_contribution/tasks_completed/checkin_streak 全丢，重入白板重来」不成立。**
真实形状：**leave 是软删，统计没丢——但软删行占死全列唯一键，用户退出即被永久锁死在群外。**

### 1.1 代码路径全景（join / leave / kick / dissolve）

| 路径 | 位置 | 行为 | 事务边界 |
|---|---|---|---|
| 加入 | `GroupService.join_group`（community_service.py:784 起） | FOR UPDATE 锁群 → 活跃成员门（`not_deleted_filter`）→ 活跃人数上限（3-8）→ SAVEPOINT 内 INSERT；IntegrityError → `ValueError("已是群组成员")` → join 信号 + 管理员推送（try/except 吞异常） | API 层 `db.commit()`；SAVEPOINT 只包 INSERT |
| 退出 | `GroupService.leave_group`（:871 起） | 活跃门 → OWNER 禁退（先转让）→ **`member.delete(db, soft=True)`** | API 层 commit |
| 移出 | `GroupService.kick_member`（:1100 起） | 权限校验 → **软删** → 系统消息 | API 层 commit |
| 解散 | `GroupService.dissolve_group` | 群 + 全体成员行 + 消息等批量软删 | API 层 commit |
| 小队门面 | `SquadService.join_squad/leave_squad`（community_squad_service.py:188/200） | 纯委托 GroupService，ValueError→SquadStateError→400；冲刺周期校验 | 同上 |
| API/网关 | `POST /groups/{id}/join|leave`、`/members/{uid}/kick`、`/squads/{id}/join|leave`（api/v1/community.py:2003/2029/2114） | 网关 `proxyWithHeaders` **纯代理零业务**（proxy_routes.go:591-608） | — |
| 事件面 | member_joined/left/kicked | **进程内 WebSocket manager.broadcast，不经 event_bus** → EVENT-ACK 系无 group 消费面，条件项豁免 | — |

### 1.2 债务机制

`GroupMember`（models/community.py:245）无软删列？——**有**：`BaseModel/SoftDeleteMixin` 全局带 `deleted_at`。
但 `__table_args__` 里 `UniqueConstraint('group_id','user_id', name='uq_group_member')` 是**全列唯一**，谓词不含软删状态：

```text
leave/kick（软删，行还在、键还被占）→ 重加入 join_group
  → 活跃门查不到活跃行（放行 ✓）
  → INSERT 新行 → 撞 uq_group_member → IntegrityError
  → except 分支误报 ValueError("已是群组成员") → HTTP 400
  ⇒ 退出/被踢一次 = 该用户对该群永久无法回归（小队同理）
```

打卡/贡献的行存在语义：`CheckinService.checkin`、群任务完成（:2370 `if member: member.tasks_completed += 1`）、成员列表/火苗榜/冲刺聚合**全部走 `not_deleted_filter()` 活跃行口径**——复活原行对读面零侵入。群级累计（`total_flame_power/total_tasks_completed`）在 Group 行上，与成员行无关。

### 1.3 演示库只读 SELECT 实测（2026-09-23，sparkle_db@sparkle，只读）

| 指标 | 实测 |
|---|---|
| `group_members` 总行数 / 去重对 | 693 / 693（**重复对 0**，全列唯一约束下的必然） |
| 软删行（`deleted_at IS NOT NULL`） | **0** —— leave 路径从未成功走通重试面（失败即 400，用户无法重试，侧面印证债务为真） |
| 现有索引 | `uq_group_member` 唯一 + 普通索引若干；无部分索引 |

⇒ 索引当下可**无损创建**；迁移预检按 fail-loudly 设计（见 ④）。

## ② 设计裁决与理由

### 2.1 软删形制：**不新增 `left_at`，复用既有 `deleted_at` + 部分唯一索引**

卡面建议「`left_at` 可空列 + 部分唯一索引 `WHERE left_at IS NULL`」。照「以代码证据为准」：代码库已有全仓统一的软删列 `deleted_at`（SoftDeleteMixin），leave/kick/dissolve 已写它，全部读面已按它过滤——再造一个 `left_at` 会产生**双份软删真相**（两列可能不一致，每个读者都得双查）。故落地为：

```sql
CREATE UNIQUE INDEX uq_group_member_active
    ON group_members (group_id, user_id)
    WHERE deleted_at IS NULL        -- 与 not_deleted_filter() 读口径严格同域
```

先例：PHOTON-IDEM（部分唯一索引 + 单头挂接 + sqlite 重放）、INTAKE-IDX（模型侧 `postgresql_where`+`sqlite_where` 双 where 声明 + 迁移收敛）。模型与迁移谓词一字不差，conftest 的 create_all 测试基座自带该索引。

### 2.2 重加入语义：**复活原行**（清 `deleted_at`），不新建行

| 维度 | 复活原行（选定） | 新建行（含继承变体） |
|---|---|---|
| 统计诚实 | 本人累计连续保存在同一行；「重入不得重置打卡连胜」直接满足 | 碎片化到多行；零值新行=重置连胜，违反卡面红线 |
| 刷分面 | 无新增：连胜延续仍由 `last_checkin_date` **日历语义**诚实衰减（断签 3 天后打卡如实归 1，绿证钉死）；重加入不触发任何经济事件（join 无 XP/光子/光子发放，代码核实）；榜/队内比较唯一口径是 sprint_task_ledger（BP-4，用户级账本，不读 GroupMember 统计）——**反刷分红线面零接触** | 「退出→重入清零→重头累积」徒增表膨胀与聚合歧义（漏过滤即双计） |
| 数据归属 | 行键=user_id，继承的是**本人**数据；不涉他人（卡面「不凭空继承他人数据」天然满足） | 同左 |
| 数据形状 | 全列唯一约束下每 (group,user) 恰一行 ⇒ 迁移后不变式最强：**至多一行活跃行，且实际恒一行** | 多历史行，聚合需处处小心过滤 |
| 迁移成本 | 演示库零重复、零软删行 → 无损 | 同左 |

复活时三笔显式赋值（写进 join_group 注释）：`role=MEMBER`（被踢/退出的管理员不得带权回归，群主可再晋升；OWNER 行不可能被软删——群主禁退且不可被 kick，唯一软删路径是解散，此时群已死）、`joined_at=now`（当前成员周期起点，join 信号时间戳诚实）、`last_active_at=now`。`is_muted/warn_count` 保留行史（被禁言者重入不洗白，防滥用）。

**残余申报（接受）**：leave↔join 循环会重复触发 join 信号与管理员推送—— nuisance 而非计分面（信号只进上下文/关系模型，无任何榜分）；修复前该循环根本不存在（重入即 400），修复后为正常产品语义。

### 2.3 写侧（join_group）改造：域内分支 + 冲突仲裁同结局

- 门改为 `_find_any_membership`（查**任意状态**行）：活跃 → `ValueError("已是群组成员")`（既有语义逐字节不变）；软删 → 复活分支（SAVEPOINT 内 flush，IntegrityError → 同款 ValueError——并发复活竞态败者与「已是成员」同结局）；
- 无行 → 原 INSERT 路径不动（IntegrityError 语义由全列唯一改为部分唯一索引仲裁，行为等价且更准）；
- 活跃人数上限检查对复活路径同样生效（先查满员再复活；演示：满员群的前成员重入被拒「群组已满」）；
- `_record_community_signal` + 管理员推送为 join/revive 共享尾部（复入同样通知管理员）。

### 2.4 相邻缺陷顺带修复（kick 路径盘点发现，属本卡盘点域）

`kick_member` 系统消息 `target.nickname or target.username`——**GroupMember 两列皆无**（同文件 846/1671/1865 行的同类访问对象都是 User），生产 kick 必 AttributeError→500（且软删发生在消息之前，API 只捕 ValueError→实际 500 回滚，kick 完全不可用）。修复为照 promote/demote 惯例 `target.user_id`（不触发 user 关系异步懒加载）。红证在 baseline 上即因此先于重入断言失败暴露。

## ③ 红证 → 绿证

- **红证（baseline 003f71f1，未修复代码）**：5 红——
  1. `test_leave_then_rejoin_succeeds_and_inherits_own_stats`：leave 后重入抛 `ValueError("已是群组成员")`（债务本尊）；
  2. `test_kick_then_rejoin_resets_role_to_member`：先撞 kick 的 `AttributeError: nickname`；
  3. `test_rejoined_member_streak_follows_calendar`：重入即 400；
  4/5. 两个并发用例：`_find_any_membership` 不存在（AttributeError）。
- **绿证（修复后，7/7 稳定，重跑 3 轮全绿）**：
  1. 退队→重入成功：复活**同一行**（id 相等）、继承 flame_contribution=42/streak=5/tasks_completed=3、角色复位 MEMBER、成员列表含两人；
  2. 被踢管理员重入 → MEMBER；
  3. 活跃成员双 join 仍拒（既有语义零变化）；满员群前成员重入仍拒（容量语义）；
  4. 复活不清零连胜，但断签后打卡如实归 1（日历诚实，`new_streak==1`）；
  5. **并发首 join**（sqlite 文件库多连接 + Barrier 门后放大毫秒窗口，PHOTON-IDEM harness 同款）：恰 1 个 GroupMember、败者 `ValueError("已是群组成员")`、joiner 名下恰一行活跃行；
  6. **并发重入**：双方复活同一行（id 集合大小=1）、恰一行、deleted_at IS NULL、统计继承（flame=7）。
- **迁移重放 4/4**：upgrade 删全列约束+建部分索引；同键第二活跃行违约、活跃+软删历史行共存合法；downgrade round-trip 可重入（存量行存活）；schema 漂移（同键多行）时预检 RuntimeError fail-loudly。
- **并发台工程注记**：`mock.patch.object` 恢复 staticmethod 时会把普通函数写回类属性，破坏描述子语义并使 patch 泄漏到后续测试（traceback 实锤双层 gated 嵌套 + 旧 loop 报「bound to a different event loop」）。并发台改用 `__dict__` 描述子保真的上下文管理器（单 patch 包 gather，finally 精确还原）。此坑已写进测试 docstring，供后续 harness 复用者避坑。

## ④ 迁移细节（合入方执行）

- 文件：`sqrejoin_20260923_group_member_rejoin_unique.py`；`down_revision="photidem_20260923"`；本机 `alembic heads` = **单头 `sqrejoin_20260923`**。
- 内容：① 预检 `(group_id,user_id)` 重复组（演示库实测 0；若非 0 = schema 漂移，RuntimeError 拒绝执行——成员行承载用户可见统计，不静默手术）；② `batch_alter_table` 删全列唯一约束 `uq_group_member`（PG 渲染 ALTER TABLE DROP CONSTRAINT，SQLite 走表重建，双方言）；③ `op.create_index(checkfirst 默认)` 建部分唯一索引（`postgresql_where`/`sqlite_where` 同谓词，可重入）。downgrade：删索引 + batch 重建全列唯一约束（**数据前提**：无同键多行，即库中尚无重加入发生；违反时以 IntegrityError 失败属预期防护，见迁移 docstring）。
- **合入方步骤**：
  1. 合入 patch（`git apply --3way`，已对干净 003f71f1 验证）；
  2. `cd backend && SECRET_KEY=… DATABASE_URL=… alembic upgrade head`；
  3. 验证：`SELECT indexdef FROM pg_indexes WHERE indexname='uq_group_member_active';` 应恰一行，谓词 `WHERE (deleted_at IS NULL)`；`uq_group_member` 应消失；
  4. `make sync-db` 刷新网关 `schema.sql` 快照（网关代码零改动，纯代理面）。

## ⑤ 冲突面声明（逐个声明）

| 并行卡 | 面 | 与本卡重叠 |
|---|---|---|
| wt176/177/178 | mobile | **零重叠**：本卡只动 `backend/app/models/community.py`、`backend/app/services/community_service.py`、迁移与 backend 测试；wt167 合入的 squad mobile 面未触碰，其消费的 API 契约（join/leave/squads 路由与返回形状）零变化 |
| wt179 | main / security_monitor / predictive | **零重叠**：文件集不相交；无共享模块引入 |
| wt180 | event_bus / 网关 | **零重叠**：本卡零 Go 改动；成员事件走进程内 WebSocket manager 不经 event_bus（EVENT-ACK 条件项据此豁免，未跑其用例） |
| wt170 PHOTON-IDEM（已合入基线） | alembic 链 | 挂其 head 之下，迁移重放邻居面 4/4 复验通过 |

## ⑥ 回归（对比法，定向不宽扫描）

community/squad 域定向集，修复前后各跑一轮，**零新增失败**：
`test_community_squad_mvp(14)/community_service_group_tasks/community_privacy_fv05/community_shared_errors(15)/community_signal_kill_switch/community_template_injection/context_manager_community_context/privacy_community_production(4)/community_study_room` 合计 **73 passed**；`test_community_e2e + test_community_security(12) + services/test_community_advanced_access + services/test_capsule_share_service + integration/test_community_integration` 合计 **44 passed, 2 skipped**（skip 为既有条件跳过）。本卡新面 7+4 用例全绿；PHOTON-IDEM 迁移重放邻居面 4/4。

## ⑦ 诚实申报

- 卡面「无软删列」与「退队=硬删丢统计」两个前提均与代码不符，已按证据修正（详见 ①②）；若主会话对「复活原行 vs 新建行」另有产品裁决，改动面收敛在 join_group 单分支 + 测试用例 1/6 的断言，迁移不受影响。
- `guest_seed_service._ensure_group_member`（演示数据播种）查询不带软删过滤、找到行直接改值不复活：属 bootstrap 面，与用户路径无交叠，本卡未动（若播种库存在软删行+重播种，该行保持不可见，无害），申报备查。
- leave↔join 循环的重复 join 信号/管理员推送为接受的 nuisance 残余（非计分面），见 ②.2。
- 并发台发现并绕开 `mock.patch.object` 对 staticmethod 的恢复缺陷（测试基建坑，已文档化进测试 docstring）。
- 收工已清 `/tmp/sqrejoin_probe`（探针）、`/tmp/sqrejoin-verify`（patch 验证克隆）；worktree 内无 build/.dart_tool/进程残留。
