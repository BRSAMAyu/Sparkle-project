# 用户每日流程三日连测（daily-flow-eval）

- 日期：2026-09-19 02:36–03:08 CST（连续 27 分钟内完成 3 个模拟"学习日"；日切采用 DB 时间回拨法，见下）
- 主仓库 HEAD：`32d2ebe3`（测试期间无变化）
- 运行栈：gateway :8080（02:10 起）、引擎 :8000/:50051（02:07/02:26 起）、PostgreSQL16+pgvector / Redis / MinIO（Docker）。**测试窗口内无进程重启**，与 wt5 记忆修复批无交叠干扰。
- 凭据：注册账号 `dailyflow3d`（uid `4fe87b78-4f0c-42ca-b1a9-4fcae8fabf97`）经 `POST /api/v1/auth/register`（需 `accepted_tos`+`accepted_privacy`，首两试因缺 `username`/协议勾选 400——注册表单文档度低，App 端已填好所以无感）。
- LLM 预算：显式 4 次（胶囊生成 1 + 每日聊天 3），远低于 ≤20 上限；另有引擎内部 reviewer/synthesis 未计。

## 日切方法

引擎"今日"判定：growth/驾驶舱用 `date.today()`（进程本地时区 CST），streak 用 `datetime.utcnow().date()`（UTC）+ 30 天窗口内 task.completed_at / focus_session.start_time 的活跃日回溯（`growth_dashboard_service._get_current_streak_days`）。据此每天结束后把本人账号全部活动行（tasks/chat_messages/goals/task_feedbacks/curiosity_capsules/users 的 created_at/updated_at 等）`-INTERVAL '24 hours'`，真实墙钟不变。**副作用**：daily-context-line 的缓存按真实日期为键，Day3 早命中 Day2 缓存——这是模拟法产物而非产品缺陷，已用 `?force_refresh=true` 复验真实重生成内容（见 D3）。

## 一、三日旅程矩阵（每步：结果｜延迟｜证据）

| 环节 | Day 1（真实 02:36–） | Day 2（回拨×1） | Day 3（回拨×2） |
|---|---|---|---|
| 注册/登录 | ✅ 200（注册 252ms/登录 214ms） | ✅ 200 227ms | ✅ 200 215ms |
| 驾驶舱 growth/dashboard | ✅ 38ms，个性化 headline + streak=0；完成 1 任务后**即时**变 streak=1/MIT 切换 | ✅ streak=2（D2 完成后） | ✅ streak=3、周 4；但 what_changed 叙事仍停留在 D1"第一任务" |
| Aurora 问候 daily-context-line | ✅ rule 级文案，36ms；晚间仍返回早间缓存（日内不更新） | ✅ **4s 重生成并带上下文**：计划名+streak=1+今日动作"Day 2" | ⚠️ 命中同日缓存（模拟法产物）；force_refresh 4s 正确出"Day 3"；**但线内 streak=1 与驾驶舱 streak=2 矛盾** |
| 推送/提醒 | ⛔ notifications 与 notification-center 均空 | ⛔ 仍空 | ⛔ 仍空（3 天无任何系统提醒生成，尽管有 streak+计划+错因反馈） |
| 打开任务 tasks/today | ✅ 21ms，2 条（自建）；`GET /tasks/:id` 13ms 有 guide+success_criteria | ✅ 36 条 | ✅ 33 条 |
| 建任务 | ✅ 176ms；⚠️ type 枚举对外暴露内部值（"review"被静默映射 TRAINING，"memorize" 400） | — | — |
| 完成任务 | ⛔→✅ PENDING 直接 complete 400"Invalid state transition"，须先 start（学生直觉操作被拒）；start→complete 200 但 **3.14s** | ✅ 3.15s | ✅ 3.12s |
| 聊天（WS 流式） | ⚠️ 首帧协议错（`type:"chat"`→message_nack 后网关 5min 无提示挂机）；正确协议后 9.2s 单帧 full_text（无 delta） | ⚠️ 30.5s 完成，仍无 delta；回复 plays along"接着昨天"但无真实记忆（工作记忆会话级） | ✅ 真流式 54 帧，TTFT 11.1s/总 41.8s；**正文头尾被污染**：前缀"⚠️ 计划执行中断: Required step failed in layer 1"+后缀"[内容审查: 未通过]" |
| 做题 exam-sprint | intake ✅ 779ms 产出 32 天计划+首日任务+通过率 45%（强钩子）；**diagnose 422**：需请求自带 ≥5 知识节点，仅计算机网络有内置默认→真实新用户冷启动死路；完成 Day1 任务后 exam dashboard **today_progress 0/1 不认账** | ✅ 完成 Day2 任务后 1/1（与 D1 行为矛盾，边界不一致）；estimated_score 仍 40 不动 | ✅ 1/1；score 仍 40、days_left 与驾驶舱差 1（31 vs 32） |
| 目标 | ✅ 建 295ms（"exam"被归一为"academic"，回包无 progress 字段）；✅ 改 39ms | — | ✅ 列表正常 |
| 星图 galaxy | ⚠️ graph 79ms/stats 22ms 全通，但 60 节点全部 unlocked=0/mastered=0 | ⛔ 完成 3 任务后仍 0/0/0 分钟 | ⛔ 4 任务后仍 0/0/0——星图对学习行为完全无感 |
| insights | ⚪ recent-directives 空 | ⚪ 空 | ✅ **4 条 directives**（Execution/ModelWrite/UX/Skill，含用户可读理由"你最近节奏不错，我会适当减少催促"）——由 D3 聊天触发，迟到但真实 |
| 胶囊 capsules/today | ✅ 首调同步 LLM 生成 >15s（网关侧复调 20ms 缓存） | — | ⛔ **D1 的章鱼胶囊原样返回**：无每日再生成，"每日新鲜感"一次性 |
| 反思/总结 | ⛔→⚠️ POST feedback **400**（TaskFeedbackResponse created_at 期望 str 收到 datetime）**但数据已入库**（summary=1）；GET summary ✅ 17ms | ⛔ 同款 400，仍入库（summary=2） | ⛔ 第三次 400 且**这次未入库**（fast-fail，summary 仍 2）——两种失败模式并存 |
| 登出 | ✅ 200，token 即时失效（复用得 invalid_or_expired）；⚠️ 无 Content-Type:application-json 空 body 时 400 | ✅ 200 | ✅ 200 24ms |

三日显式 LLM 消耗：4 次。三日通过/半通/断计数（按环节×3 天合计 36 步）：✅ 24 通 / ⚠️ 5 半 / ⛔ 7 断（断点多为复现性缺陷而非当日偶发）。

## 二、跨日影响验证表

| 跨日命题 | 成立? | 证据 |
|---|---|---|
| 1. 任务完成 → 次日 streak 累加 | ✅ | streak 0→1→2→3 三日严格递增；UTC 活跃日回溯逻辑按 DB 时间正确工作 |
| 2. 昨日行为 → 今日驾驶舱"今日"内容变化 | ✅ | MIT 从自建任务→"Day 2"→"Day 3"跟随冲刺计划推进；growth_signal 在多日积累后出现（delta_points 3.0） |
| 3. 昨日行为 → 次日问候语带上文 | ✅ | D2 问候"今天最值得先做的是「Day2·建立框架」"并携带计划名/科目/streak；⚠️ 线内 streak 数与驾驶舱相差 1 |
| 4. 完成任务 → exam 冲刺进度同步 | ⚠️ 半 | D1 完成 0/1 不认账、D2/D3 完成 1/1 认账——同链路两行为，日界/归属不一致 |
| 5. 学习行为 → 星图成长 | ⛔ | 3 天 4 任务后 unlocked/mastered/study_minutes 恒 0；星图与学习完全脱钩 |
| 6. 错因反馈 → 次日任务/推送个性化 | ⛔ | D1 反馈"明天想做综合题"、D2 反馈"想练同类题"均石沉大海：无推送、无次日任务调整（任务全来自静态 sprint 模板） |
| 7. 多日节奏 → 系统自适应 | ✅ 迟到 | D3 出现 4 条 directives（momentum_high→sustain_momentum，用户可读理由），D1/D2 颗粒无收 |
| 8. 反思 → 反思摘要/周报素材 | ⚠️ | GET summary 正常聚合（total/mood/时间线），但提交端 3/3 天报 400，客户端视角"每日反思失败" |
| 9. 聊天历史跨日可查 | ⛔ | 3 天 4 条 USER 消息入库、**0 条 ASSISTANT**；chat_sessions 0 行（会话列表空）；Redis 缓存有 assistant（AI 上下文可用）但 PG 持久层断——换设备/重装后历史残缺 |
| 10. 登出后 token 失效、次日可重登 | ✅ | 复用旧 token 得 401 invalid_or_expired；三次登录均成 |

**成立 5 项（含 2 项半）**：硬性成长数字（streak/周完成/驾驶舱内容）跨日全部成立，这是回访钩子的主承重墙；但"星图成长""推送带上下文""错因驱动个性化"三个产品叙事级承诺均断。

## 三、每日循环"钩子"强度评价（产品视角）

- **强**：`exam-sprint/intake` 是全链路最佳钩子——一次输入即产出 32 天计划、首日任务、45% 通过率和"今天先把三道代表题做了"的明确动作，配合次日问候点名"Day 2"任务，构成"明天有具体的事等我"的回访理由。
- **中**：驾驶舱 streak/周完成数的即时一致性反馈扎实（完成 3.1s 后 40ms 内驾驶舱可感知），what_changed 叙事卡有养成感，但 D3 仍复述 D1 事件，新鲜感衰减快。
- **弱**：推送通道 3 天静默（无早报/无计划提醒/无错题回顾 nudge），被动等待用户打开——召回钩子缺失；胶囊"每日"变一次性；星图 0 变化使"看着星图长大"的核心隐喻在真实前 3 天不可体验；insights 的惊喜第 3 天才到且无主动曝光渠道。

## 四、P1 清单（按用户痛感排序）

1. **DF-1 反思提交三日 3 败（其中 2 次"假失败"）**：`POST /tasks/{id}/feedback` 返回 400 `TaskFeedbackResponse.created_at` 期望 str 收到 datetime（`backend/app/schemas/task_feedback.py`）；D1/D2 已入库但客户端视为失败（重复提交风险），D3 fast-fail 且未入库。晚间反思入口实质不可用。复现：任一 COMPLETED 任务 + 合法 feedback JSON。
2. **DF-2 聊天回复不落库、会话列表空**：3 天 4 轮 WS standard 聊天，PG `chat_messages` 0 条 ASSISTANT、`chat_sessions` 0 行；Redis 缓存有 assistant（`chat:history:df-dX-s1`）。持久队列 `queue:persist:history` 积压 131 条未消费；persister 写入的 `timestamp` 用秒而 SQL 按 `to_timestamp($/1000.0)` 解释（`chat_history_persister.go:224-227` vs `chat_orchestrator_feedback.go:84`）——换设备后历史/回放/多端一致全断。与记忆批 MR-1 同族（主路径不持久化）。
3. **DF-3 回复正文被系统噪声污染**：D3 回复头"⚠️ 计划执行中断: Required step failed in layer 1"尾"[内容审查: 未通过] 发现 1 个严重问题需要处理"直接拼进正文下发客户端（MR-5 家族；card_lifecycle_enum 迁移漂移未修）。用户视角=产品每句话都在报错。
4. **DF-4 诊断做题冷启动死路**：`exam-sprint/diagnose/generate` 422"知识节点覆盖不足，至少需要 5 个不同知识领域"（`exam_sprint_diagnostic_service.py:556`），仅计算机网络科目有内置默认节点；新学生在其余科目永远无法诊断。
5. **DF-5 星图与学习行为零耦合**：3 天 4 任务，galaxy stats 恒 0（与 exam-system-eval"掌握度写库静默丢弃"互证）。核心成长可视化在真实前 3 天为空转。

## 五、P2 清单

- **DF-6** 任务状态机拒绝 PENDING→COMPLETED，必须 start→complete（API 层无 merge 语义）；且每次 complete 固定 ~3.1s（副作用同步执行），快速连点场景会认为失败。
- **DF-7** exam 冲刺"今日进度"D1 不认账、D2/D3 认账（日界/归属 off-by-one 家族）；`days_left` exam 端 31 vs 驾驶舱/问候线 32；问候线 streak=1 vs 驾驶舱 streak=2。三套日切口径并存（`date.today()`/`utcnow().date()`/UTC 目标日差值）。
- **DF-8** `tasks/today` 返回 32 天冲刺任务全量（36 条），"今日"过滤失效；已完成的自建任务反而从列表消失。
- **DF-9** 推送/提醒通道 3 天零产出（notifications、notification-center 恒空），无任何主动召回钩子。
- **DF-10** capsules/today 无每日再生（D1 后一直返回同一条）；首次生成同步 >15s。
- **DF-11** WS 协议脆弱面：未知 type 只回一个 message_nack 后连接挂至 5min idle 超时；短问句走单帧 full_text 无 delta（D3 长问句才有真流式），TTFT 波动 9–30s。
- **DF-12** 注册接口首试必 400 三连（username 必填但报错置底/协议字段不直观）；logout 对非 JSON 空 body 400。
- **DF-13** what_changed 叙事 D3 仍复述 D1"第一任务"；insights 第 3 天才出现且依赖聊天触发。

## 六、受控/未测项

- 三个"学习日"以 DB 回拨模拟，非真实跨 72 小时；daily-context-line 的同日缓存命中为模拟法产物（已用 force_refresh 隔离验证）；真实跨日的定时任务（夜间报告、衰减作业）未观测。
- 未动 focus session（streak 的另一活跃源）、社区/ Accountability 打卡、付费/光子；LLM 预算克制未触发 plan 配额上限路径。
- 内存中批（wt5）声称的记忆链修复可能改变 DF-2/MR-1 行为——本次实测时间窗内引擎进程未重启，结论对 `32d2ebe3` 运行栈有效。
- 测试数据（账号 dailyflow3d 及其 38 行任务/4 轮聊天/1 目标/1 胶囊/2 反馈）留在库中供复核，未清理；未触碰他人数据。
- 评测脚本与响应存档：`/tmp/dailyflow/`（不入库）。
