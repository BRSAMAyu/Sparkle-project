# WT777-P499 — FIX-499 total_days 类型收口 + wt768 批十三处静态观察可信度探针

- **Agent**：wt777（node-b）｜**分支**：`agent/node-b/wt777/p499`｜**base**：main@5a30f98f｜**worktree**：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt777-499probe`
- **日期**：2026-09-28｜**纪律**：先证后修；号段 508 起（grep 复核 505-509 全仓 0 命中，在册最高 504）
- **提交**：代码+测试 `749341e1`；台账+本 notes 为后续独立提交（FIXED@ 指针指 749341e1）

## FIX-499（P4）——修 ✅ FIXED@749341e1

**病灶**：`plan_review_service.py` `total_days = params.get("total_days", params.get("duration_days"))` 裸取（497 修后 :926），字符串型真值过 `:956 if total_days and total_days <= 7:` falsy 守卫后 `str <= int` TypeError；:972 `daily_hours * total_days` 在 497 修后 daily_hours=float 下遇字符串 total_days 为 `float * str`（数值语义仍错）。与 497（daily_hours）同族。

**修法**（与台账修法方向逐字一致）：改 `self._positive_float(params.get("total_days", params.get("duration_days")))`，对齐同函数 `_collect_feasibility_comments` :721 同键族既有收口先例；注记 6 行（与 497 同款），修后取值行 :932。

**红→绿**（新增 `tests/unit/test_plan_review_feasibility_total_days_type_coercion.py` 7 测，工具名 `generate_study_material` 避开 SAFE_TOOL_CATEGORIES 短路与 plan/sprint/schedule/task token 过滤，确保病灶就是 :926，同 497/492 判例）：

| # | 用例 | 修前 | 修后 |
|---|------|------|------|
| 1 | total_days="5"+3h，expert | TypeError @:956 | False（5≤7 且 3h<4h 拒） |
| 2 | total_days="7" 边界 | TypeError | False（同 int 7） |
| 3 | total_days="10" | TypeError（`"10" <= 7` 同炸） | True（>7 跳过不误罚） |
| 4 | "4"×"7" 双字符串 | TypeError | False（28<50 乘法数值语义，非字符串重复） |
| 5 | total_days="abc" | TypeError | True（垃圾值→None 缺参语义） |
| 6 | duration_days="5" 回退键 | TypeError | False（回退键同收口） |
| 7 | _quick_rule_check 端到端 "8"×"7" | TypeError | `high_confidence_simple_plan` |

修前 7/7 failed 全部 `TypeError: '<=' not supported between instances of 'str' and 'int'` @:956（与 wt767 台账运行级探针签名一致）。修后 7/7 绿；497 既有 5 钉测零回退；plan_review 直触族 64 passed + openclaw/perceptible 15 passed 零回退。

## 观察① last_activity_date 漂移——确证，登记 V3-FIX-524（OPEN，不动）⚠️→📋

`UserStreakStats` 三列（achievement.py:219/:223-224）`Mapped[date|None]` 套 `DateTime`。wt768 静态观察**属实**，且实探发现比注解漂移更深一层：

- **列侧为真（四重证据）**：基线迁移 cc9383c4c29f:2056 `sa.DateTime()`；schema.sql:6938 `timestamp without time zone`；time_utils.py:122 注释「UTC 存储列」；读侧 `_coerce_activity_date`（achievement_engine:231）对读回值 `isinstance(datetime)→.date()` 即运行时补偿。
- **漂移是活的**：`date == datetime` 恒 False（探针亲证）→ :2053 归一比较每次读都判不等、每次重写；mypy 基线 streak_signal_processor.py:46 `recency_weight(observed_at: datetime|None)` arg-type 一条即此投影；`date <= datetime` 混型排序直接 TypeError。
- **双写者语义分裂（新发现）**：achievement_engine 9 处写用户本地日 `date`（列=日界语义，V3-FIX-293）；guest_seed_service :855/:1838/:2692 写 `now-timedelta(hours=2)` 非零点 `datetime`（列=时刻语义）。

**处置**：两条修法都非纯声明面——列改 Date 属迁移面（按任务口径只登记）；注解改 datetime 则 9 处 date 写面连带翻+归一舞/delta 计算运行时邻接面。登记 **V3-FIX-524 OPEN**，未动任何行。

## 观察② leaderboard selectinload——探针证真且升级，修 ✅ FIXED@749341e1（V3-FIX-525）

- **探针实录（SA 2.0.48）**：`selectinload(GroupMember)`（映射类，非关系属性；User 全文件零 GroupMember 引用）在**选项构造时**即抛 `ArgumentError: expected ORM mapped attribute for loader strategy argument`——wt768 猜想「无效 loader」实为**群组榜（带 group_id）必炸 500**（路由 leaderboards.py `except Exception → 500` 兜底），非静默。
- **双重死码**：即便合法也无消费——flame_contribution 来自 :493 独立 members 查询，loader 产物零读者。无合法形态可修（无关系路径可指）→ 整块摘除 `.options(...)` + import。
- **红→绿**：`tests/unit/test_leaderboard_group_loader_invalid.py` 2 钉——①真实 async sqlite 端到端（三成员贡献 30/20/10：出榜序、my_rank、my_score、total_participants 数值断言；修前 ArgumentError）②AST 源码扫描永久禁 selectinload 回流。percentile guard 5 测零回退。
- **意外收获**：mypy 基线中 `Argument 1 to "selectinload" has incompatible type "type[GroupMember]"` arg-type 一条即此病灶投影，摘除随之烧减。

## 观察③ call-arg 五条——逐条核真全为活路径，修 ✅ FIXED@749341e1（V3-FIX-526）

批十后基线 76 中 5 条 call-arg 逐条对照被调方真实签名+调用链可达性，**无一死面**，全部为「TypeError 被 except 吞掉→功能静默全死」族：

| # | 现场 | 真实签名 | 症状（修前） | 修法 |
|---|------|---------|-------------|------|
| 1 | photons.py:224 `record_transaction(metadata=)` | extra_data（photon_service.py:715） | grant/deduct 生效后 500，余额变历史记不上 | 改 extra_data= |
| 2 | summarization_worker.py:324 `rpush(ex=86400)` | rpush 无 ex（属 set 族） | :172 活路径，TypeError 被 `except (TypeError, RedisError)` 吞，日志队列恒空 | rpush+独立 expire 86400（滚动 TTL 同原意图） |
| 3/4 | correction_feedback.py:526 `correction_text=/user_context_payload=` | keyword-only user_id/signal_id/reason/source（self_model.py:230） | 被 except 吞，self_model 修正计数恒不更新（aurora.py:587/:657+orchestrator.py:962 活路径可达） | reason=json.dumps(correction_context)（含完整 to_dict **零信息损失**，callee 关键词扫描+evidence_detail 落存）+source 直传；signal_id 缺省维持无去重 |
| 5 | file_processing_orchestrator.py:118 `get_spine_orchestrator(redis=)` | redis_client（spine_orchestrator.py:5140） | TypeError 被同函数 except 吞，Spine 文件信号恒不发（V-14 同函数漏网；celery_tasks.py:2921 正确形态对照） | 改 redis_client= |

红→绿：新增 `tests/unit/test_v3_fix510_callarg_realpath.py` 2 运行时钉（修前形状即 TypeError 被吞、断言必红；①③④回归由 mypy call-arg 静态覆盖）。②⑤两模块修前零既有测试（病灶长期潜伏成因面，已在台账注记）。

## 验证汇总

- **mypy**：主仓同 commit 同口径对照 **76=76**（1387 files，冷缓存独立目录）→ 修后 **70**；去行号 diff 移除恰 6 条（call-arg 5 + 509 的 leaderboard selectinload arg-type），**新增 0**。
- **pytest 触达面**：plan_review 直触族 64 + openclaw/perceptible 15 + 499 新 7 + leaderboard 2+5 + 510 新 2 + photon/self_model/calibration/journey/signal_spine/context_pruner 1010+（978 passed 8 skipped + 32 passed）全绿零回退。
- **ruff**：触达 9 文件 All checks passed（含新测试文件；修掉一处自引入 F401）。
- **台账 verify**：`ledger_union_merge.py --verify` 通过（347 行全 8 管、ID 无重号、状态枚举合法）。
- SECRET_KEY 一次性 env 沿 wt766/wt767 先例；app/gen symlink（指主仓）不入库、提交显式路径；未 push；未碰 docker/运行栈/.env。

## 遗留与移交

- V3-FIX-524（streak 三列语义统一）OPEN：修法 (a) 列迁移 Date+种子路径改写为域正解方向，需迁移面授权；烧减基线 streak_signal_processor:46 那条须连写面一起处置。
- ①③④⑤ kwargs 回归的静态防线=mypy call-arg；②⑤新增运行时钉补零覆盖面。
- 号段消费实录：508=观察①登记（OPEN）、509=观察②（FIXED@749341e1）、510=观察③（FIXED@749341e1）；证伪号段零消耗（本批三观察无一证伪，探针证据均为证真方向）。
