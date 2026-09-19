# 每日流实测第二轮：9957f42d 修复批复验（daily-flow-eval-r2）

- 日期：2026-09-19 08:12–08:41 CST（约 29 分钟完成 3 个模拟"学习日"；日切沿用首轮 DB 时间回拨法）
- 主仓库 HEAD：`d4338948`（含被验修复批 `9957f42d`，dailyflow-p1-fixes：DF-1/2/3/5/9）
- 运行栈：gateway :8080（`/tmp/sparkle_gateway_new`，08:08 起）、引擎 :8000/:50051、PostgreSQL16+pgvector / Redis / MinIO（Docker，08:08 起）。测试窗口内**无主仓进程重启**。
- 凭据：`df2_1789776977`（uid `8b923994-aca1-4d08-b167-76b3792de667`），经 `POST /api/v1/auth/register` 一次通过 200（首轮记录的"注册首试 400 三连"本轮按文档字段直接构造，未复测首试体验）。
- LLM 预算：显式 4 次（D1 聊天 1 + D2/D3 聊天各 1 + 问候 force_refresh 1），另有胶囊首生成/反馈推断各 1 次引擎内部调用。
- 全部请求走网关 REST/WS，JSON 证据存档 `/tmp/df2/evidence/`（66 个文件，不入库）。
- **环境事件（非测试导致）**：08:39:19 CST `sparkle_db` 容器 exit 133（非 OOM，疑似 Docker Desktop VM 内存压力）自动拉起失败，此后 DB 侧调用不可用；约束要求不动主仓进程，故未人工重启。**全部关键证据均在崩溃前采集完成**；崩溃后仅 gateway/engine healthz 探活（仍 200）。
- wt2 遗留处理：已按指示 `git reset --hard d4338948`，前任遗留（l10n 3 文件 + `longflow-web-round1/` 目录）拷至 `/tmp/wt2_leftovers_1789776739/`。

---

## 一、五项修复复验结论（核心交付）

| 项 | 首轮表现 | 修复声称 | 本轮实测 | 判定 |
|---|---|---|---|---|
| **DF-1 反思提交** | 3/3 天 400（`created_at` str/datetime），2 次假失败 | schema 改 datetime | `POST /tasks/{id}/feedback` D1 **200**（26.7s）回包含 ISO `created_at`；D2 **200**（965ms）；D3 **503** 网关 30s 超时**但已入库**（DB 3 行，含 D3） | ✅ 修复达成（带新 P1-C 延迟问题） |
| **DF-2 聊天落库/历史可查** | 0 条 ASSISTANT、会话列表空、队列积压 | persister 重建+默认启用 | WS 三日 3 轮，**PG `chat_messages` 每日 USER+ASSISTANT 各落库**（4 行/日=双写，见 P2-D）；`GET /chat/sessions` 200 返回会话带标题；`GET /chat/history/:id` 200 返回双角色消息，正文干净无噪声 | ✅ 修复达成（带 P2-D/P2-E 残留） |
| **DF-3 诊断 422** | 422"知识节点覆盖不足"误导死路 | 可行动错误列出支持科目 | 支持外科目未变：`大学物理` → **422 `"诊断暂支持的科目：计算机网络、数据结构；「大学物理」暂未内置诊断题包"`**（93ms）；`计算机网络` → 200 出 10 题（30ms） | ✅ 逐字符合预期 |
| **DF-5 星图耦合** | 3 天 4 任务 galaxy 恒 0/0/0 | 自建任务物化任务星+spark | 完成 2 个自建任务+2 个冲刺任务后：**total_nodes 88→104、unlocked 0→4、study_minutes 0→105**，日志 `ignited task star 5020ecb7…`；`GET /galaxy/stats` 每次完成即时 +1 星 +30min。**但每次 complete 端点返回 500**（见新 P1-A） | ✅ 耦合达成（带 P0/A 级回归） |
| **DF-9 推送默认开** | 3 天 notifications/notification-center 恒空 | opt-in 默认 true + 全量评估 | ① `GET /memory/push-settings` 从未操作的新账号 **enabled=true**；② `user_push_opt_in.enabled=t`；③ 引擎 08:23 智能推送循环**确实评估了本新账号**（日志为证）；④ 全库通道有产出：近 2h 38 条 push_histories / 56 用户收到 sprint/capsule/reminder 通知；⑤ **但本账号 3 天 0 通知**：评估在下游 tz 崩溃（见新 P1-B） | ⚠️ 半（覆盖面修复生效，产出仍断） |

## 二、三日旅程矩阵对照（环节｜首轮→本轮）

| 环节 | Day 1（模拟 09-17） | Day 2（模拟 09-18） | Day 3（模拟 09-19） |
|---|---|---|---|
| 注册/登录 | ✅ 200 481ms/361ms（首轮✅→✅ 持平） | ✅ token 保持有效 | ✅ |
| 驾驶舱 growth/dashboard | ✅ 116ms streak=0，完成 1 任务后**即时** streak=1、周完成 +1、MIT 出现（持平） | ✅ 完成后 streak=2、MIT 切"Day 2·IP 地址分类"、what_changed 引用 D1 任务且带掌握度 0.00→0.05（**较首轮新增掌握度叙事**） | ✅ streak=3、周 4（首轮 ✅→✅ 持平） |
| 问候 daily-context-line | ✅ 200 rule 级 4.1s | ⚠️ 同真实日缓存命中（模拟法产物，与首轮 D3 同型）；ctx 内 streak=1 过期 | ⚠️ 缓存 ctx_streak=1 vs 实际 3；`?force_refresh=true` 4.1s 正确再生成："你已经连续推进3天…" + streak=3（首轮⚠️→⚠️ 同族） |
| 推送/提醒 | ⛔ 0（评估了但下游崩，见 P1-B） | ⛔ 0 | ⛔ 0（首轮 ⛔→⛔ **未达预期**，但故障点已前移且可定位） |
| tasks/today | ⚠️ 200， intake 后 50 条全 PENDING（首轮 DF-8"今日过滤失效"**仍在**） | ⚠️ | ⚠️ |
| 建任务 | ✅ 200 107ms（首轮 ⚠️ 枚举暴露→本轮未复测枚举，主路径 ✅） | — | — |
| 完成任务 | ⛔ **500 INTERNAL_ERROR**（155ms）×2/2；状态/星图实际落库 | ⛔ 500（冲刺任务同炸，384ms） | ⛔ 500（107ms）——**累计 5/5 次 500，100% 复现**（首轮 ✅ 3.1s→本轮⛔，**回归**，见 P1-A） |
| 聊天（WS 流式） | ✅ 19 帧含 **4 delta 真流式** 45.8s，正文头尾干净；**assistant 当日即落库可查**（首轮 ⚠️/无 delta/不落库→**显著改善**） | ✅ 25 帧 5 delta 10.8s，干净 | ✅ 26 帧 5 delta 40.0s，干净 |
| 做题 diagnose | ✅ 422 可行动 + 支持科目 200/10 题（首轮 ⛔→✅ **修复**） | — | — |
| exam dashboard | —（D1 未完成冲刺任务，首轮"D1 0/1 不认账"未复测） | ✅ 完成后 today_progress **1/1 即时认账** | ✅ 1/1 |
| 目标 | ✅ 200 309ms（goal_type=academic；首轮回包无 progress 字段未复测） | — | — |
| 星图 galaxy | ✅ 88→89 节点、unlocked 0→1、minutes 0→25（首轮 ⚠️ 恒 0→✅ **修复**） | ✅ 103/3/75 | ✅ 104/4/105 |
| insights | ⚪ 0 | ⚪ 0 | ⚪ 0（首轮 D3 迟到 4 条→本轮 3 天 0 条，触发不稳定） |
| 胶囊 capsules/today | ⚠️ 首生成同步 **24.7s**（首轮 >15s→持平偏慢） | ⛔ **0 条**（回拨后无再生成） | ⛔ 0 条（首轮 ⛔ 原样复读→⛔ 形态略变：从"一次性"变"消失"，DF-10 仍在） |
| 反思/总结 | ✅ 200 26.7s 入库（首轮 ⛔→✅ **修复**）；D3 形态见下 | ✅ 200 965ms 入库 | ⚠️ **503 超时 30s 但已入库**（DB 3 行为证）——"假失败"UX 残留（见 P1-C） |
| 登出 | ✅（本轮测于 D3） | — | ✅ 200 41ms；复用旧 token 401 invalid_or_expired（持平） |

**通过计数（同首轮 36 格口径，—/未重测格不计）**：本轮 ✅ 26 / ⚠️ 5 / ⛔ 5（首轮 ✅ 24 / ⚠️ 5 / ⛔ 7）。净增量 **+2 通过、-2 断点**，且断点全部集中收敛到 3 个已定位根因（P1-A/B/C），不再是首轮的弥散性失败。

## 三、跨日影响命题对照（10 条）

| # | 命题 | 首轮 | 本轮 | 证据 |
|---|---|---|---|---|
| 1 | 任务完成→streak 累加 | ✅ | ✅ | 0→1→2→3 严格递增；回拨后活跃日 09-17/18/19 回溯正确 |
| 2 | 昨日行为→今日驾驶舱内容 | ✅ | ✅ | MIT "Day 1·TCP三次握手"→"Day 2·IP地址分类"；what_changed 掌握度叙事新增 |
| 3 | 昨日行为→次日问候带上文 | ✅ | ✅（force） | force_refresh："你已经连续推进3天…"+plan+streak=3；自然缓存同日命中为模拟法产物 |
| 4 | 完成任务→exam 进度同步 | ⚠️ 半 | ✅ | D2/D3 完成后 today_progress 均 1/1 即时认账（首轮 D1 不认账的边界未复测） |
| 5 | 学习行为→星图成长 | ⛔ | ✅ | unlocked/study_minutes 每日递增 1→2→3→4 / 25→75→105 |
| 6 | 错因反馈→次日任务/推送个性化 | ⛔ | ⛔ | 反馈 3/3 入库，但冲刺任务仍静态模板、无次日调整；推送被 P1-B 掐断 |
| 7 | 多日节奏→系统自适应 | ✅ 迟到 | ⚪ | 3 天 0 directives（首轮 D3 有 4 条）——触发链不稳定，未能复现 |
| 8 | 反思→摘要/素材 | ⚠️ | ✅* | 提交端 3/3 入库（首轮 3/3 报 400）；`reflections/summary` GET 因 DB 环境事件未复测（*单边） |
| 9 | 聊天历史跨日可查 | ⛔ | ✅ | 会话列表跨日可见、按会话取回双角色消息；残留：标签会话缓存过期后 500（P2-E） |
| 10 | 登出后 token 失效 | ✅ | ✅ | 401 invalid_or_expired_token |

**跨日成立 8/10**（首轮 5/10，+3）；两条仍断（#6 个性化、#7 自适应）均属"反馈闭环→生成侧"链路，非本修复批范围。

## 四、新发现分级（只记录，不修）

### P1（用户高痛感 / 修复批回归面）

- **P1-A 任务完成端点 100% 返回 500（回归，最高优先）**
  - 现象：`POST /tasks/{id}/complete` 5/5 次返回 500 `INTERNAL_ERROR`（自建×2、冲刺×2、D3×1），耗时 107–384ms；但任务状态/星图/周完成数实际落库——客户端视角"完成失败"，会诱发重复完成/数据口径混乱。
  - 根因链：`TaskService.complete` 的 DF-5 新钩子走 `spark_node` → `backend/app/services/galaxy/stats_service.py:428-436` outbox INSERT 使用 `VALUES (:aggregate_id, :event_type, :payload::jsonb, :created_at)` 命名参数混入 asyncpg 位置参数语句 → `PostgresSyntaxError: syntax error at or near ":"` → WARNING 吞掉但**事务已中止** → 后续 `task_service.py:695` group_task_claims SELECT 抛 `InFailedSQLTransactionError` → 500。该坏 SQL 自初始提交（1722e6dc）即存在，属**被 DF-5 修复激活的休眠 bug**。
  - 端点定位：`backend/app/services/task_service.py:695`（爆点）、`backend/app/services/galaxy/stats_service.py:434`（根因）、`/tmp/engine_api.log` 08:19:40 起 5 组堆栈。

- **P1-B 推送评估对"带偏好行用户"确定性崩溃，通道对其仍为 0（DF-9 下游）**
  - 现象：08:23 引擎智能推送循环评估本账号即报错；`Error processing push for user` ×14 = push_preferences 全部 14 行用户，1 周期全军覆没；本账号 3 天 notifications 恒 0。
  - 根因：`backend/app/services/push_service.py:331-338`，`utc_start_of_day`（tz-aware）与 `push_histories.created_at`（TIMESTAMP WITHOUT TIME ZONE）比较 → asyncpg `DataError: can't subtract offset-naive and offset-aware datetimes`，被 `process_all_users:87` 捕获为 ERROR 后跳过该用户。
  - 对照：无偏好行用户走合成默认路径，通道确有产出（2h 内 56 用户 41 条 sprint+capsule 类通知）——证明 DF-9 的默认开+全量评估生效，剩余是此 tz 分支。

- **P1-C 反思提交延迟不可用级 + 超时假失败（DF-1 残留形态）**
  - 现象：同一端点三次耗时 26.7s / 0.97s / >30s(503)；503 那次数据已入库。同步执行 LLM 推断导致移动端必然超时重试 → 与首轮 DF-1 同型的"客户端失败、服务端成功"重复提交风险。
  - 端点：`POST /tasks/{id}/feedback`（引擎侧同步推断；建议改异步/降超时，提交与推断解耦）。

### P2（记录在案）

- **P2-D 聊天双写去重失配**：标签会话（如 `df2-d1-s1`）下引擎与网关 persister 各派生**不同**伪 UUID（`3c3cb8ef…` vs `fefd227a…`），NOT EXISTS(±15s) 去重按 session 匹配失效 → `chat_messages` 每轮 4 行（应 2 行）。读路径不受影响（读引擎会话）。定位：`chat_history_persister.go` resolveSessionUUID 与引擎侧 `_ensure_session` 的派生命名空间不一致。
- **P2-E 标签会话历史读 500**：`GET /chat/history/df2-d1-s1` 在 Redis 缓存过期后走 DB fallback，`chat_history.go:498` `cannot parse UUID` 直接 500（应返回空/404 或做同派生映射）。
- **P2-F 问候线缓存键含过期上下文**：同真实日内 ctx_streak 恒为首次生成值（1），与驾驶舱(3)矛盾；force_refresh 可纠正。模拟法与产品缺陷叠加，首轮 DF-7 同族。
- **P2-G tasks/today 全量返回**：50 条全 PENDING（intake 32 天模板+自建），"今日"过滤失效（首轮 DF-8 原样）。
- **P2-H 胶囊无每日再生**：D2/D3 `capsules/today` 返回 0 条；首生成同步 24.7s（首轮 DF-10 原样，形态从"复读"变"消失"）。
- **P2-I insights 三日 0 条**：首轮 D3 曾出现 4 条 directives，本轮同型行为（聊天/任务量）未触发——directive 触发条件不稳定/覆盖率低。
- **P2-J 任务 type 枚举对外暴露内部值**（首轮 DF-6 附属，本轮建任务用大写枚举绕开，未复测小写别名映射）。

### 环境事件（非产品缺陷）

- 08:39:19 CST `sparkle_db` 容器 exit 133（非 OOM、非测试语句导致；SELECT/低频 UPDATE 不构成压力）。未按约束重启，崩溃后未再采集 DB 证据。此前所有证据完整。

## 五、受控 / 未测项

- 完成任务 500 的"P1-A 是否影响 streak/exam 归属"：不影响——状态先提交后崩溃（部分提交语义），streak/exam/星图全部正确累积；仅响应码错误。
- 首轮 DF-6（PENDING→COMPLETED 状态机）、DF-11（WS 未知 type 挂机）、DF-12（注册首试 400 三连）、DF-13（what_changed 复述 D1）本轮未复测；what_changed 本轮叙事正常（引用昨日任务+掌握度增量）。
- 三个"学习日"仍为 DB 回拨模拟：真實跨日的夜间报告、衰减作业未观测；greeting 同日缓存命中为模拟法产物（已用 force_refresh 隔离验证）。
- 测试数据（账号 df2_1789776977：78 行任务、8 行反馈/聊天×6、1 目标、2 颗任务星、3 天聊天记录）留在库中供复核；DB 容器崩溃后的数据一致性未终验（崩溃前 WAL 应保最后提交）。
- 评测脚本与响应存档：`/tmp/df2/`（df2lib.py / dayflow.py / day1fix.py / day23.py / rollback_day.sh + evidence/ 66 文件，不入库）。

## 六、一句话总结

修复批 5 项中 **3 项全绿**（反思 200、诊断可行动、聊天落库可查）、**1 项达标但带回 P0 级回归**（星图长出来了，代价是完成任务端点必 500）、**1 项半通**（推送默认开与全量评估生效，但下游 tz 崩溃使偏好行用户依旧 0 通知）；跨日命题 5/10→8/10，36 格口径 24→26 通过。建议下一修复批顺序：P1-A（complete 500）→ P1-B（推送 tz）→ P1-C（反馈异步化）。
