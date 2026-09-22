# PHOTON-IDEM · 每日首胜发放 check-then-insert 竞态收口（唯一部分索引 + 写侧冲突仲裁）— 收工报告

- Worker：V3 舰队 D 纵队 Worker（PHOTON-IDEM 卡，北极星全旅程 · PHOTON-STREAM 诚实申报最后残留缺口）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt170`（基线 `4328e318`）
- 日期：2026-09-23
- 交付物：
  - `backend/alembic/versions/photidem_20260923_photon_daily_first_idem_unique.py`（新增，迁移）
  - `backend/app/services/photon_service.py`（修改，写侧冲突仲裁，+191/-15）
  - `backend/tests/unit/test_photon_idem_daily_first_concurrency.py`（新增，并发绿证 6 用例）
  - `backend/tests/unit/test_photonidem_daily_first_idem_unique_migration_sqlite.py`（新增，迁移重放 4 用例）
  - 本报告 + `changes.patch`（4 文件；`git apply --check` 对干净 HEAD 克隆通过）
- 未 commit / 未 push（纪律遵守）；**未动活库**（sparkle_db 只读 SELECT，迁移由合入方执行）

---

## ① 取值域盘点表 + 索引范围裁决

### 1.1 `photon_transaction_history.related_item_id` 取值域

**代码面（全部写入方）+ 演示库只读 SELECT 实测（2026-09-23，共 297 行）：**

| 键形态 | 写入方（唯一入口） | transaction_type | 演示库实测 | 域内唯一性语义 |
|---|---|---|---|---|
| `daily_first:<ISO日期>` | `achievement_engine.check_daily_first` → `grant_photons(record_history=True)`（L2759） | `grant_daily_first` | 2 行 / 2 用户，**域内重复 0** | **本卡管辖域**：同用户+同日键=同一经济事件 |
| `achievement_combo:<hex16>` | `achievement_engine._handle_achievement_combo`（L2686） | `grant_bonus` | 32 行 / 4 用户，域内重复 0 | uuid4 生成器构造唯一 |
| `guest_welcome` | `guest_seed_service`（L1530，直 ORM add） | `grant_achievement` | 170 行 / **170 用户** | **跨用户同键合法** |
| 裸 `achievement_id` | `celery_tasks.L1637` / `achievement_engine.L1717,1827`（重试补发） | `grant_achievement` | 81 行 / 31 用户 | 读侧 `_find_existing_transaction` 已去重；重复=历史真实补发 |
| 裸 `contract.id` | `achievement_engine._grant_rewards`（L2984） | `grant_contract` | （演示库未及） | 读侧门去重 |
| 裸 `item_id` | `shop_service.L408`（purchase） | `purchase` | 5 行 / 2 用户，**实测 1 组同 (user,item) 重复对** | **同用户同 item 合法重复购买** |
| NULL | transfer_in/out、redeem_pro、旧 grant_achievement | 各异 | 7 行，**实测 1 组 (user,NULL) 重复对** | 无键语义；NULL 天然不进 LIKE 谓词 |

**全列 (user_id, related_item_id) 唯一当场炸掉 2 组域外既有重复**（重复购买 + NULL 转账组）——照 ERR-IDEM-CONCUR 调研方法用只读 SQL 证实，全列唯一否决。

### 1.2 索引范围裁决

**选中**：`CREATE UNIQUE INDEX uq_photon_tx_daily_first_idem ON photon_transaction_history(user_id, related_item_id) WHERE related_item_id LIKE 'daily_first:%'`——键域与读侧去重门在 daily_first 域内严格同域。

**combo 域不并入（裁决：否决并入）**，三条理由：
1. **零防重放价值**：combo 键 `achievement_combo:<uuid4.hex[:16]>` 的唯一性由生成器构造保证（2^-64 碰撞），索引防不住生成器防不住的东西；
2. **语义错位**：combo 的业务定案（PHOTON-STREAM）是「每次达标即一次独立合法经济事件」，**不存在**「同键=重复发放」的幂等语义可供索引执行——给它上唯一约束是在执行一个该域不存在的错误不变量；
3. **风险为正**：若假想生成器 bug 产出重复键，索引会把「静默双发」变成「无冲突处理路径上的硬 500」（combo 写入侧不进本卡的仲裁分支，见 ③）——把低概率噪音升级为可用性事故。成本虽同，价值为零，故不并入。

transaction_type 列可用性：列上是 `String(50)`（非原生 PG enum，PHOTON-STREAM 已定案），写侧原子 INSERT 沿用 `record_transaction` 同款枚举映射（含 `admin_adjustment` 兜底）；演示库现存 7 种 type 值（见 1.1），`grant_daily_first` 恰为其中之一。

## ② 红证 → 绿证（探针在 /tmp，收工已清）

**Harness**（照 ERR-IDEM-CONCUR 同款）：sqlite 文件库多连接 + 真实 `PhotonService.grant_photons` 写入路径（不 stub 流水 INSERT）+ `asyncio.Barrier` 把「两个请求都过读侧门、彼此都还没写流水」的毫秒窗口放大成确定性交错点。

**红证**（/tmp 干净 HEAD 克隆 = 未修复代码，无索引）：

```text
R1 gate passed → barrier → INSERT → dedup=False (0→30)
R2 gate passed → barrier → INSERT → dedup=False (0→30)
daily_first 流水行数: 2（两行都是 0→30）
最终 photon_balance  : 30（丢失更新）
判定: RED — check-then-insert 竞态双发复现：
  审计流水 ×2 → 「可兑换基数」重放口径虚增为 60，
  而余额只有 30 —— 审计与余额自相矛盾，基数诚实性被击穿。
```

**灵敏度验证**（防绿证空洞）：同一 harness 给 baseline 加上索引但**不带**写侧冲突处理 → 败者当场
`sqlite3.IntegrityError: UNIQUE constraint failed: photon_transaction_history.user_id, photon_transaction_history.related_item_id`
（即：只有索引没有 ON CONFLICT 时竞态败者直接 500 并毒化事务；交付测试对两种残缺形态都能抓）。

**绿证**（本卡修复后）：恰一方 `deduplicated=False`、败者 `deduplicated=True`、流水恰一行、余额恰 +30。

## ③ 写入侧改造：冲突即「已发放」，与读侧门命中同结局

`PhotonService.grant_photons`（`record_history=True` 时）新流程：

```text
1. _lock_user_balance_row（FOR UPDATE，原样保留）
2. _find_existing_transaction 读侧快路径（原样保留——串行重放不触达写侧）
3. 前缀守卫 _is_daily_first_idem_key（daily_first: 域才进仲裁分支）：
     流水先行原子落定：INSERT … ON CONFLICT DO NOTHING RETURNING id
     ├─ 有行（胜者）→ _update_balance 补余额（同事务一致）→ 正常结果
     └─ 无行（败者）→ 重查胜者行 → 返回与读侧门命中同构的
        {"deduplicated": True, old/new_balance=胜者快照} → 零发放、零余额变更
4. 域外键（前缀守卫之外）不进分支，行为逐字节不变
```

- **发放金额语义零变化**（卡规红线）：首胜仍 30 光子/日；改动只是把「check-then-insert」的 insert 半边升级为「唯一索引仲裁的原子 insert」，幂等从「缓存+读侧门」双保险升级为「缓存+读侧门+唯一索引」三保险。
- 原子 INSERT 用 raw `text()` + GUID-typed bindparams（galaxy_service 审计 INSERT 同款、PG/SQLite 双方言；无 target 形态可命中部分索引；表上另一唯一约束只有 uuid PK，冲突不可能，无误伤面）。
- `achievement_engine.check_daily_first` **零改动**（写入面完全收在 PhotonService 内，调用方无感）。
- 读侧快路径保留（钉死在交付测试 4：串行重放 spy 断言 `_insert_daily_first_transaction_arbitrated` 不被触达）。
- 既有「已存在」路径的返回形状提取为 `_deduplicated_grant_result` 复用，竞态败者与读侧门命中逐字段同构（钉死在交付测试 3）。

## ④ 迁移细节（合入方执行）

- 文件：`photidem_20260923_photon_daily_first_idem_unique.py`，`down_revision = "dc5share_20260922"`；`alembic heads` 单头 `photidem_20260923`（本机已验）。
- **合入方步骤**（活库我只读，未动）：
  1. 合入 patch；
  2. `cd backend && alembic upgrade head`；
  3. 验证：`SELECT indexname, indexdef FROM pg_indexes WHERE indexname='uq_photon_tx_daily_first_idem';` 应恰一行，谓词 `WHERE related_item_id LIKE 'daily_first:%'`。
- 迁移内容：
  1. 先收敛存量：删除管辖域内 (user_id, related_item_id) 重复组中非最早的行，**保留最早 = 首个真实发放事件**；后来者 = 并发竞态双发的虚增基数污染，删除即还原审计诚实性。收敛写法用 correlated EXISTS + `(created_at, CAST(id AS TEXT))` 字典序——**注意 ERR-IDEM-CONCUR 的 `MIN(id)` 写法此处不可复制**：本表 PK 是 uuid，PG 无 `min(uuid)` 聚合；CAST 写法双方言语义一致（同刻并列以 id 文本序 tie-break，确定性）；
  2. 再建唯一部分索引（`IF NOT EXISTS`，可重入）。downgrade 仅 `DROP INDEX IF EXISTS`。
- **存量申报（演示库只读实测）**：297 行中 daily_first 域 2 行、域内重复 **0** → 索引当下可无损创建；域外 2 组既有重复（重复购买 + NULL 转账）不归本索引管辖，一概不动。
- sqlite 兼容性：部分索引 + LIKE 谓词 + 无 target `ON CONFLICT DO NOTHING RETURNING` 均为 PG/SQLite 双支持（迁移 sqlite 重放 4/4 绿证）。

## ⑤ 回归矩阵（全绿；全部定向，无宽扫描）

| 套件 | 结果 |
|---|---|
| **新增** 并发绿证（2 并发恰一发 / **8 并发**恰一发 / 败者结局==读侧门命中 / 串行重放读侧快路径 / 次日键不被吞 / 域外键不受索引约束） | 6/6 passed |
| **新增** 迁移 sqlite 重放（照 ERR-IDEM-CONCUR test_cp 模式）：存量收敛保留最早、域外零影响、索引违约 + ON CONFLICT RETURNING 契约、round-trip 可重入 | 4/4 passed |
| PHOTON-STREAM 族 `test_photon_stream_audit_ledger.py`（6/7 例回归红线，含「连续两日不被吞」） | 7/7 passed |
| D-COMM-2 族 `test_dcomm2_photon_redeem_pro.py` | 11/11 passed |
| `test_photon_service.py` + `test_photon_service_simple.py` + `test_d02_photon_spine.py` | 22/22 passed |
| `tests/api/test_photons_api.py` + `tests/api/test_shop_api.py` | 9/9 passed |
| 成就家族（engine_phase3 / engine_regression / system_alignment / contract_weekend） | 58/58 passed |
| observability + transparency + timezone（补 `app/gen/` 后） | 5/5 passed |
| `test_community_shared_errors.py` + `test_rd01_redeem_loop.py` + `tests/integration/test_photon_concurrency.py` | 35/35 passed |
| `tests/integration/test_shop_end_to_end.py` + `test_shop_acceptance.py` | worktree 与干净 HEAD 克隆**签名完全一致**：`1 failed, 1 passed, 3 skipped, 13 errors`（夹具与 `:memory:` URL 既有不兼容，非本卡引入） |
| `alembic heads` | 单头 `photidem_20260923` ✓ |
| ruff（4 个改动/新增文件） | 0 违规 ✓ |

## ⑥ 冲突面声明

- **本卡改动面**：`photon_service.py`（服务层写入侧，+191/-15）、1 个新迁移、2 个新测试文件。`models/shop.py`、`achievement_engine.py`、`photon_redeem_service.py` **零改动**。
- **wt166（intake）**：intake/plans 域，与本卡零文件相交。
- **wt167（mobile）**：`mobile/` 域，零相交；首胜响应契约（`check_daily_first` 返回 dict）未变。
- **wt168（photon status 端点）**：预期改 `app/api/v1/photons.py`（API 层）；本卡改 `app/services/photon_service.py`（服务层）——**文件面预期零重叠**。语义面提示：photon status/流水读端点会看到 daily_first 流水行，行语义与 PHOTON-STREAM 后完全一致（本卡只防「同键第二行」出现），无契约破坏。
- 卡面假设修正申报：卡文写「你动 achievement_engine 写入侧」——实际写入面在 `PhotonService.grant_photons`（`check_daily_first` 是其调用方），故改动落在 `photon_service.py`，冲突面比卡面假设更小。

## ⑦ 诚实申报

1. **PG 真机上 FOR UPDATE 行锁 + READ COMMITTED 本已近似串行化首胜发放**（败者阻塞在 `_lock_user_balance_row`，获锁后新快照可见胜者行），因此 PG 上写侧冲突分支是「近乎不可达的兜底」；它真正兜住的窗口是：(a) SQLite（FOR UPDATE no-op，测试/灰度环境，红证即在此复现）、(b) 未来任何隔离级别/重构变更。唯一索引的价值不在「修好 PG 当下」，在「让恰一次成为 schema 层事实而非执行层巧合」。
2. 败者分支设有一个**理论上不可达**的防御兜底（索引冲突已证明胜者行已提交，READ COMMITTED 重查必可见；若仍不可见则返回零发放 dedup 终局、余额原样、warning 日志），不伪造胜者账目。
3. 发现**既有**怪癖未处置（超范围）：`extra_data=None` 经 JSON 列落库为字符串 `'null'` 而非 SQL NULL——**ORM 既有路径与本卡原子路径行为逐字节一致**（对比实验证实），非本卡引入；对 `'null'` 真值敏感的下游（`extra_data or metadata` 惯用法）行为不变，建议另立 micro-debt 卡。
4. 活库未动（只读 SELECT ×5 次取值域取证），迁移留合入方；真 PG 端到端并发演练未做（活库只读纪律），合入后建议 staging 以 8 并发同用户同日打一轮首胜。
5. 并发绿证用 sqlite 文件库多连接建模生产并发，`Barrier` 放大交错为确定性、断言交错无关；`asyncio.Barrier` 必须跨协程共享单实例 + 读侧门包装必须单次拦截（败者重查胜者行会二次过门）——这两个 harness 陷阱已在测试 docstring 里写明，防后人复用时误判「测试挂死」。
6. worktree 曾缺 gitignored `app/gen/`（transparency_meta 收集失败），已照 ERR-IDEM-CONCUR 先例从主仓拷贝（不入 patch）；拷贝后该文件与 worktree 基线均绿。

## ⑧ 收工核查

- [x] 未 commit / 未 push；交付物 = REPORT.md + changes.patch（`git apply --check` 对干净 HEAD 克隆通过）
- [x] 活库与主仓只读（SELECT 取值域 ×5，无任何写；连接凭据零出现在交付物）
- [x] /tmp 探针与基线克隆已清（`/tmp/photidem_probe*`、`/tmp/photidem-baseline`、`/tmp/photidem_*.log`、bindcheck 库）；pytest tmp 已清
- [x] 无残留进程（全部后台任务已停）；无模拟器 / 浏览器实例；无 HEAVY 任务（纯 sqlite 单进程测试，峰值 <1G）
- [x] `git status` 仅含本卡 4 文件 + v3-output（`app/gen/` 为 gitignored，不入 patch）
- [x] 交付物零凭据
