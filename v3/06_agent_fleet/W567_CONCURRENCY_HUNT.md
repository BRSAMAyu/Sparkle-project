# W567 并发与数据正确性猎缺（第一轮·并发/数据正确性轴）

- **Agent**: wt567（双轮审查机制·第一轮）｜**基线**: wt567-concurrency@f85255fe｜**日期**: 2026-09-25
- **范围**: 今日 40+ 卡大改面的针对性猎缺——FIX-257 转正 SAVEPOINT 清洗、wt536 ×61 ensure_awaitable 收窄、FIX-258 origin 标记写侧、FIX-250/243/251 时区写侧、wt552 task_card_protocol 真修后遗。
- **方法**: 纯只读分析（读码 + grep 调用面 + `git log -S` 断代），零产品码改动。所有判定附 file:line 证据与可证伪判据。
- **产出**: 本报告 + 台账登记 V3-FIX-286/287（DYNAMIC_ISSUES.md）。

## 总判定

| 轴 | 判定 | 风险 | 登记/观察 |
|---|---|---|---|
| 1 SAVEPOINT 语义 | **PASS**（原子性正确） | 低 | 登记 V3-FIX-286（相邻面 FIX-55 盲区）；观察 O1 |
| 2 ensure_awaitable 收窄 | **PASS** | 低 | 护栏观察 O2/O3 |
| 3 origin 标记竞态 | **PASS**（有已记录边缘 + 一条窄缝） | 低 | 登记 V3-FIX-287（判据窄缝）；观察 O5 |
| 4 时区写侧幂等 | **PASS** | 低 | 无 |
| 5 task_card_protocol 后遗 | **PASS**（无第三同型） | 低 | 观察 O6/O7 |

**总体判断：今日大改面未发现并发/原子性级别的回归。** 两条登记项均为低危（一条 09-26 诞生的观测盲区、一条 config-gated 的判据裂缝），五轴核心语义（SAVEPOINT 原子性、awaitable 收窄、origin 单点判据、本地日单快照、协议构造契约）全部站得住。

---

## 轴 1：FIX-257 SAVEPOINT 语义 — PASS

**问题**：转正外层事务若后续步骤失败回滚，SAVEPOINT 内已释放的删除会怎样？清洗内有无独立 commit 破坏原子性？幂等二调外层语境同理？

**证据链**：

1. 清洗实现 `cleanup_guest_seed_statistics_for_upgrade`（`backend/app/services/guest_seed_service.py:3871-3900`）：`async with session.begin_nested()` 包裹 `_cleanup_guest_seed_statistics`；内层实现（:3903-4053）**只有 SELECT 与 `session.delete()`，无任何 `commit()`/独立事务**——grep 可证伪：函数体内零 commit 调用点。
2. 外层事务语境：auth 端点 `db: AsyncSession = Depends(get_db)`，`get_db` 成功路径统一 `await session.commit()`、异常路径统一 `rollback()`（`backend/app/db/session.py:116-135`）。SAVEPOINT `RELEASE` 不产生持久化——删除仅在端点成功、get_db 收尾 commit 时落库；**清洗之后任何一步失败（如 `_issue_auth_tokens` 内 `upsert_session` 抛出，auth.py:1118-1127 前后）触发 get_db rollback，已删除行原样恢复，转正整体原子回退**。这正是卡面设问的正确答案：release 后随外层回滚=正确，且实现确实没有内层 commit。
3. 失败降级路径：清洗任一步异常 → 回滚到 SAVEPOINT → warning + 全 0 返回（:3886-3896），session 回到可用态，转正不受影响——与「裁决 B」（同文件 :1591-1593 注释）一致。`upgrade_guest`（auth.py:1092-1099）与 `upgrade_guest_social`（auth.py:1194-1198）两处调用均在 `db.flush()` 成功之后、同一外层事务内，语境正确。
4. 幂等二调（guest_login 重登补种，auth.py:1008-1029）：`seed_guest_user_data` 同型 SAVEPOINT（guest_seed_service.py:1660-1674，V3-FIX-13@1cb10a7d 09-19），种子失败回滚到 SAVEPOINT 后 `await db.commit()` 照常提交用户侧已有数据，外层语境同样自洽。

**登记 V3-FIX-286（P3）——相邻面真缺陷**：FIX-55 的 seed_status 观测面（09-26@95dff6bf）挂在 `seed_guest_user_data` 这个**自 09-19 起就不抛异常**的调用外（guest_seed_service.py:1667-1674 吞一切 `Exception`），种子内部失败恒报 `seeded/reseeded` + success 计数；auth.py:988/1003/1018 三个 except 分支只剩 commit/refresh 失败可触发，auth.py:990 的「Rollback everything (including failed seed data)」重试注释自 09-19 起即为死注释。FIX-55 卡面目标「失败不再只留日志静默（客户端/运维可见）」被 FIX-13 的吞异常直接击穿。可证伪判据与修法候选见台账行。

**观察 O1（低）**：`upgrade_guest` 的验证邮件派发（auth.py:1101-1116，celery `dispatch_task_async` + redis verify token）发生在外层 commit **之前**；若其后 `_issue_auth_tokens`/audit 抛出导致整体回滚，邮件与 token 已发出——收件人拿到一个指向仍为 guest 账号的验证链接。概率极低（派发后失败面窄）且方向无害（验证不产生权限），记录不动。

## 轴 2：ensure_awaitable 收窄面 — PASS

**问题**：「运行期恒走 awaitable 分支」在 redis.asyncio pipeline()/transaction() 返回对象上是否成立？sync Redis 实例混入（test fixture）会否炸？

**证据链**：

1. `ensure_awaitable` 本体（`backend/app/core/redis_utils.py:12-25`）是**双分支保守收窄**：`isinstance(result, Awaitable)` 为真直通，否则 `_wrap()` 包成协程——即使 sync 客户端返回裸值也语义不变。收窄面本身不可能引入行为差异。
2. 全部 83 个调用点（25 文件，`grep -rn ensure_awaitable backend/app`）均为**客户端直连命令**（`ping/lrange/llen/eval/sadd/hgetall/hincrby/lpush/ltrim/lpop/rpush/scard/srandmember/smembers/setex/get`），**零调用点作用于 `pipeline()`/`transaction()` 返回对象**——pipeline 调用面（llm_quota.py:229/260、cost_controller.py:260、version_conflict_service.py:417、signals 族等 20+ 处）全部自行 `await pipe.execute()` 或 `async with pipeline()`，未经过 ensure_awaitable。
3. 测试注入面：`grep -rn "fakeredis" backend/tests` 12 个文件**全部使用 `fakeredis.aioredis.FakeRedis`（async 版）**（含 `import fakeredis$` 的 3 个文件实际也是 `fakeredis.aioredis.FakeRedis(...)`），无 sync FakeRedis 注入 ensure_awaitable 消费服务的路径。即使未来注入 sync 客户端，`_wrap` 分支兜底，不会炸。
4. `redis.asyncio` 客户端普通命令运行期恒返回 coroutine，「恒走 awaitable 分支」论断在其覆盖面内成立。

**护栏观察 O2**：`redis.asyncio.Pipeline` 的**缓冲态命令**（`pipe.set(...)` in transaction）返回 Pipeline 自身，而 Pipeline 实现 `__await__`（`isinstance(result, Awaitable)` 为**真**）——若未来有人把缓冲态命令结果塞进 ensure_awaitable，`await` 会提前执行整批事务。今日零此类调用点；此为不可见于类型检查的护栏线，建议保持「pipeline 结果不走 ensure_awaitable」惯例。
**观察 O3（cosmetic）**：`semantic_cache_service.py` 直 await（:188/:197/:249/:278）与 ensure_awaitable（:279/:302/:308/:310 等）混用——async 客户端下行为相同，风格统一即可。

## 轴 3：FIX-258 origin 标记竞态 — PASS（已记录边缘 + 一条窄缝）

**问题**：流式长回复跨模式切换时分片落库的 origin 判据会否中途漂移？9 个 `_persist_assistant_message` 调用面是否同一 run 内一次性取判据？

**证据链**：

1. **无分片漂移**：`_persist_assistant_message`（`backend/app/orchestration/persistence_layer.py:55-134`）收的是 **turn 收尾的全量 `full_response`**，origin 判据在函数内**单点读取一次**（:99-101）。9 个调用面（execution_engine.py:277/531/580/1534/1750、orchestrator.py:832/1401/2409、response_builder.py:1402）全部汇入这同一处读取——不存在逐 chunk 各自取判据的形状。
2. **翻转时机封闭**：`demo_mode` 全部赋值点仅 4 处（llm_service.py:364 init、:412/:459 init 无 key、:580 `switch_specific_model` 重估）——运行期唯一翻转入口是管理面 `switch_specific_model`，与 persistence_layer.py:96-98 注释「mid-turn 翻转误标是已记录的可接受边缘」吻合。同判据第二消费点 memory_inferred_write_lane.py:283-287 注释同口径（观察 O5：lane 是后台队列，读判据时刻晚于落库时刻一个队列延迟，翻转窗内整轮误跳——同一已记录边缘族）。
3. **充分性前提验证**：`_check_demo_match`（llm_service.py:628-660）在 `demo_mode=True` 时对**任何非空 user 内容**必然返回脚本响应（精确命中→模糊命中→通用兜底三段，:655-660 兜底「已收到你的请求。当前处于演示模式…」）——「demo_mode 置位 ⇒ provider 调用前脚本短路」对正常聊天轮成立。
4. **窄缝（登记 V3-FIX-287，P4）**：`messages` 中**无 user 角色行**时 `_check_demo_match` 返回 None（:644-645 user_content 为空短路），chat/reason 两路径落穿 budget 与 `if not self.provider` 检查走**真实 provider 调用**（:726-740/:1068-1075；stream 路径有 `demo_mode and not provider` 兜底不落穿）。此时若部署为 `DEMO_MODE=true` 且 key 有效（唯一能让 demo_mode=True 且 provider 存活的形态；无 key 初始化 provider=None → 501 不会静默），真实模型产出被 persistence_layer.py:99-101 / chat.py:1270 标 `origin=DEMO`，再被记忆推断读侧整轮丢弃——**过标方向=内容损失，非污染**。config-gated，仓内无该部署面证据，故 P4 记录判据边界。可证伪判据见台账行。

## 轴 4：时区写侧幂等（跨日界）— PASS

**问题**：用户本地 23:59 snooze+1 → 00:01 再 snooze+1 落库值链；replan today 三同源跨本地日界窗口。

**证据链**：

1. **snooze 值链正确**：`snooze_task`（`backend/app/api/v1/tasks.py:1011-1044`）每次调用**即时**取 `today = local_date(utcnow(), tz_name)`（:1024-1027，tz 沿 PushPreference 标量直查缺省 Asia/Shanghai），`target = request.target_date or today + days`（:1028-1030），`days` schema 锁 `ge=1 le=30`（schemas/task.py:371）。23:59 调用 → D+1；00:01 再调用 → 当日新鲜 today=D+1 → D+2。**无跨调用缓存的 today、无共享日网格状态**——每次调用内部自洽，跨日界两连按得 +2 天恰是「两天各按了一次」的诚实语义。并发双 snooze 同值覆盖，幂等无害。
2. **replan 三同源单快照**：`replan_plan`（plans.py:1333-1419）`today = await _user_local_today(db, user_id)`（:1356，def :151-156）读一次，三个消费点全用同一变量——`explicit_target<=today` 422 闸（:1387）、`previous_target>=today` 幂等 no-op 闸（:1395）、`_derive_replan_target` 派生（:1403）。**请求跨本地日界时三处仍互一致**（同一快照），不存在「422 用新日、派生用旧日」的混合窗口；代价只是终点锚定请求起始日，与「重复点击不无限续期」幂等设计一致。
3. 残余宿主机 `datetime.now()` 面（llm_quota.py:138/223/254/471）是**配额 Redis key 的基础设施日**，非用户日网格（due_date/phase 游标/checkpoint），不在 FIX-250 意义域内；写侧全面切本地日的 six sites（tasks.py:256/1027、plans.py:1356/1595、phase_sketch_service.py:113、discovery_manager.py:107）实测口径一致。

## 轴 5：task_card_protocol 真修后遗 — PASS

**问题**：wt552 修的 WhyThisTask 字段/for_practice 参数——还有无第三处同型（协议缓存 miss→TypeError 族）？

**证据链**：

1. wt552 修点确认：`backend/app/api/v1/tasks.py:672-683`，注释自证原 `primary_signal/user_visible_reason` 非 WhyThisTask 字段（types.py:1247-1252 契约只有 signal_ids/policy_decision_id/bottleneck_node_id/reasoning_summary），现改 `reasoning_summary`。
2. **无第三同型**：全库 grep `WhyThisTask(` 在 app 代码仅此一处外部构造（协议模块内部 `why or WhyThisTask()` 为缺省兜底）；`TaskCardProtocol(` 直接构造零外部调用；`TaskCardBuilder.for_*` 全部经 tasks.py:664-670 的 builder_map 调用，kwargs（goal_id/bound_nodes/why/steps/stuck_protocol）为 for_study/for_practice 共有签名，无参数面 TypeError。`from_dict`（types.py:1388-1403）全 `.get` 防御，反序列化面无同型风险；`from_goal_type` 生产零调用（仅 tests/unit/test_signal_spine.py:14200 引用）。
3. **观察 O6**：缓存键 `spine:task_card_protocol:{task.id}` 在 tasks.py:648 只有**读**无任何**写**（repo 全量 grep + `git log -S` 断代仅 initial commit 1722e6dc）——cache-hit 分支永久死路。良性（fail-open 到 wt552 修好的重建路径，反而保证了走修后代码），但 docstring「cached Spine task-card-protocol payload」误导后来者；建议要么补 writer 要么删分支。
4. **观察 O7**：`from_goal_type` 的 `stuck_hint` 配置被 `hasattr(card, k)` 过滤器静默丢弃（task_card_protocol.py:224-226，TaskCardProtocol 无此字段）——死配置键，与 TypeError 族相反的「静默 no-op」失败模式；生产零调用故仅记录。

## 登记清单

| 编号 | 严重度 | 一句话 | 状态 |
|---|---|---|---|
| V3-FIX-286 | P3 | FIX-55 seed_status/GUEST_SEED_TOTAL 对种子内部失败恒报成功（FIX-13 吞异常击穿 FIX-55 观测目标，09-26 诞生） | OPEN |
| V3-FIX-287 | P4 | FIX-258 origin 判据在「无 user 角色消息 × DEMO_MODE=true+有 key」形状下过标真实产出为 DEMO 并整轮退出记忆推断 | OPEN |

编号注记：基线 f85255fe grep 验证 256-284 全占、285/286 空闲；工作期间主仓集成段前进至 3b9e45fc 顺延占用 285（wt564），故自 286 起登记；wt566/557 在航若先占 286/287，撞号由集成侧重编号先到先得。

## 第二轮建议焦点

本轴未覆盖的今日改面：FIX-240 semantic_cache 序列化保形在**并发写读**下的类型保形（`candidate_keys` 联合分支已在 wt536 连带修过注解，但 setex/get 往返中 pydantic/json 双形的并发一致性未审）；FIX-258 读侧过滤（memory 推断读侧）与写侧 origin 的**回填一致性**（历史行无 origin 列时的缺省语义）。
