# PHOTON-STREAM · 每日首胜 / combo 加成的审计流水补录（micro-debt 卡）

- worktree：`wt159`（基线 `7d8a828d`，已含 D-COMM-2）
- 交付物：`v3-output/PHOTON-STREAM/REPORT.md` + `changes.patch`（4 文件，319 行）
- 验证：`git apply --check` 对干净 HEAD 克隆通过；未 commit / 未 push

---

## ① 盘点（发放点行号 + 词表现状）

### 发放点（改动前行号）

| 发放点 | 位置 | 改动前状态 |
|---|---|---|
| 每日首胜 | `backend/app/services/achievement_engine.py` `check_daily_first`（原 L2736） | `grant_photons(amount=30, source="daily_first", type=GRANT_DAILY_FIRST)`，**未开 `record_history`** → 零流水；幂等只靠 Redis cache key `daily_first:{uid}:{date}`（24h TTL），缓存失守无 DB 层兜底 |
| combo 加成 | `backend/app/services/achievement_engine.py` `_handle_achievement_combo`（原 L2665） | `grant_photons(source=f"achievement_combo:{combo}", type=GRANT_BONUS)`，**未开 `record_history`**；combo 计数器 5 分钟 TTL 窗口内可合法重复达标（combo=3 多次触发各发一次） |

D-COMM-2 侧：`backend/app/services/photon_redeem_service.py` 收入词表 `REDEEMABLE_INCOME_TYPES` 原为四类型（`grant_achievement / grant_daily_first / grant_contract / grant_contract_bonus`），**不含 `grant_bonus`**；`grant_daily_first` 本就在表内（收不到流水是唯一缺口）。

### 关键既有事实（修法依据）

1. **去重键无日期维度**：`PhotonService.grant_photons` 的 `_find_existing_transaction` 按 `(user_id, transaction_type, amount, source, related_item_id)` 精确匹配——这正是 D-COMM-2 警告「补流水会吞次日首胜」的机理：首胜每日键完全相同，次日必命中去重路径，**且该路径跳过整个发放（余额都不加）**。
2. **DB 枚举缺 `GRANT_BONUS`**：`models/shop.PhotonTransactionType` 无该成员，combo 若直接开流水会落 `admin_adjustment` 兜底误标。列类型为 `String(50)`（非原生 PG enum），加成员**零迁移**。
3. **既有范式**：契约奖励（`_grant_rewards`）早已是 `record_history=True, manage_transaction=False` + `related_item_id` 唯一键，本卡完全沿用。
4. `grant_bonus` 全仓仅 combo 一处引用（gateway / migrations / seeds / tests 均无），词表扩容零外溢。

## ② 去重交互的键设计（本卡核心）

| 发放点 | 去重键设计 | 语义 |
|---|---|---|
| 每日首胜 | `related_item_id = f"daily_first:{today.isoformat()}"`，`source` 保持稳定字面 `"daily_first"` | **同日幂等**：Redis 缓存失守时 DB 层兜底防重发；**次日键自然变化**，绝不吞次日首胜。审计溯源按 `source` 查询不受日期后缀污染 |
| combo 加成 | `related_item_id = f"achievement_combo:{uuid4()}"` | **每事件唯一**：连击窗口内合法重复达标（combo=3 → 6 各发一次）永不互吞；幂等限流仍由既有 Redis combo 计数器承担，发放语义与改前逐次发放完全一致 |

两处均加 `manage_transaction=False`（同契约范式），生产路径（get_db 外部事务托管）行为逐字节不变。

## ③ 改动面（4 文件）与冲突声明

1. `backend/app/models/shop.py` — `PhotonTransactionType` 增 `GRANT_BONUS = "grant_bonus"`（String 列，零迁移）；
2. `backend/app/services/photon_redeem_service.py` — 词表收录 `"grant_bonus"`；docstring 诚实申报段收敛为已修复状态；
3. `backend/app/services/achievement_engine.py` — 两发放点补 `record_history=True` + 上述去重键 + `manage_transaction=False`；`uuid4` 导入；
4. `backend/tests/unit/test_photon_stream_audit_ledger.py` — 新增 6 用例（见下）。

**冲突面声明**：本卡未读取 wt144 / wt158 / wt160 的任务卡与工作树（隔离纪律）。按文件相交面评估：`achievement_engine.py` 是热点文件（成就域各卡常改），合并窗口建议主会话对它做 `git diff` 交叉核对；`photon_redeem_service.py` 若有 D-COMM 系后续卡（如 wt160）同时在改词表，需后合者 rebase 本 patch 的词表段（一行元组新增，冲突易解）。`models/shop.py` 仅一行枚举新增。测试文件为全新文件，零冲突。

## ④ 新测试与回归

### 新增 `test_photon_stream_audit_ledger.py`（6 用例，全绿）

1. `test_daily_first_writes_audit_row_and_counts_into_base` — 首胜发放即入流水（旧码零流水 → 红），类型为专有枚举非兜底误标，键=当日日期，基数 +30；
2. `test_consecutive_days_first_win_both_ledgered_and_counted` — **红线钉死**：连续两日各恰一条流水、两天都计基数（60）、余额 60（次日光子未被去重路径吞）；
3. `test_same_day_repeat_stays_idempotent` — 缓存守门（同日二次 None）+ 缓存失守时 DB 去重兜底（`deduplicated=True`），全天仍只一条流水；
4. `test_combo_bonus_writes_audit_row_with_dedicated_enum` — combo 入流水、`grant_bonus` 专有枚举（非 admin_adjustment）、键前缀 `achievement_combo:`；
5. `test_combo_bonus_repeated_triggers_never_swallow_each_other` — combo=3 → 6 连续达标两次各入流水（30/60），键互不碰撞，基数 90；
6. `test_redeemable_base_includes_daily_first_and_combo` — 端到端：补录直接转化为可兑换基数，60 光子成功兑得 Pro。

### 回归（对比法零新增；全部定向，无宽扫描）

| 测试族 | 结果 |
|---|---|
| D-COMM-2 族 `test_dcomm2_photon_redeem_pro.py` | 11 passed |
| `test_photon_service.py` + `test_photon_service_simple.py` | 18 passed |
| 成就家族（phase3 / regression / alignment） | 35 passed |
| `tests/api/test_photons_api.py` + `test_photon_concurrency.py` | 7 passed |
| `test_ai_opaque_markers.py`（改 shop.py 后必查守卫） | 1 passed（基线同） |
| 新测试文件 | 6 passed |
| `test_shop_end_to_end.py` + `test_shop_acceptance.py` | worktree 与干净 HEAD 克隆**签名完全一致**：`1 failed, 1 passed, 3 skipped, 13 errors`（`no such table: users`，夹具与 `:memory:` URL 的既有不兼容，非本卡引入） |

ruff 全部改动文件 0 违规。

## 诚实申报

1. **发放金额语义零改动**（卡规）：首胜仍 30 光子/日、combo 仍 combo×10，仅补记录；同日幂等从「仅缓存」升级为「缓存+DB 双保险」——理论上比改前**更强**地防重发，不存在反向放水面。
2. **时区口径沿用现状**：`check_daily_first` 的 `date.today()` 为本地时区日界（Redis cache key 原本同口径），本卡未改为 UTC——流水日期键与发放日界天然一致，不构成新偏差，但如产品要求 UTC 日界需另立卡。
3. **Redis 失守窗口的极端重复**：同日缓存失守 + DB 去重兜底后，若两次发放发生在去重查询的并发缝隙（同键同时通过 `_find_existing_transaction`），理论上仍可双发——这是既有 `_find_existing_transaction` 的固有竞态（check-then-insert 无唯一索引），本卡不扩大它，也顺手不在 micro-debt 卡里加表约束（零迁移纪律下加唯一索引需 Alembic，超出本卡范围）。
4. **基数口径变化**：词表 +`grant_bonus` 后历史用户若已有 `grant_bonus` 流水（当前不可能，因为此前从未落流水）会抬升基数——实际无历史行，纯增量前向生效。
5. 环境借用申报：测试使用主仓 `backend/.venv` 解释器（只读执行，未写主仓任何文件）。

## ⑤ 收工核查

- [x] 未 commit / 未 push；交付物 = REPORT.md + changes.patch
- [x] `git apply --check` 对 HEAD 克隆通过
- [x] 主仓零写入（`.venv` 仅执行）；worktree 内只动了上述 4 文件 + v3-output
- [x] 无新进程残留、无模拟器、无浏览器实例
- [x] pytest tmp 已清（见下）、`/tmp/photon-stream-baseline` 已清（见下）
- [x] 磁盘余量健康（开工 7.3G）
