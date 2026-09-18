# Android 无头模拟器走查 · Round 1（三度实测合轮）

- 日期：2026-09-18 晚
- 走查人：FieldTest agent（续行轮三，吸收前两轮 21+16 张截图结论）
- 环境：Medium_Phone_API_36.1 无头模拟器（1080×2400 @420dpi，2GB RAM，API 36）；APK=main@5c6210fe（mobile 最后提交 8cdc12f7 含 AA 对比度批量修复，构建于 15:39，无重复构建）；后端网关 :8080 / FastAPI :8000 / gRPC :50051 / PG 在跑（**Redis 不可用**，全程遥测返回 `redis_unavailable`）
- 方式：adb input/screencap + uiautomator dump + logcat 全程取证 + 网关/引擎日志交叉验证 + curl 直接探针（红绿验证）
- 截图：`.fieldtest-shots/round3/`（01–48）与 `Sparkle-sysrev/screenshots/android/round3/`

## 结论 TL;DR

**游客模式主线已通（登录→首页→种子数据→各 Tab），但"游客发第一条消息"被离线队列恢复缺陷卡死（消息永久停在 Sending）；注册主线能走通但注册用户一旦退出登录就再也登不回来（本轮已修复，红绿验证通过）。** 另收获建模聊天静默挂起、Profile 整页 type-cast 崩溃、注册页 14px 溢出等 6 个 P1。本轮 0 次 ANR，历史 2 次 ANR 均为设备资源饥饿所致，非应用主线程死锁。

## ANR 专节

### 历史 ANR 取证（前两轮遗留线索，本轮定性）

设备 dropbox 存有两条本轮之前的 ANR（均 foreground）：

| 时间 | Subject | 关键指标 |
|---|---|---|
| 13:38 | Input dispatching timed out (**Application does not have a focused window**) | TOTAL 71% CPU，**iowait 37%** |
| 15:01 | Input dispatching timed out (**Waited 8943ms for KeyEvent**) | **kswapd0 43%、major faults 7552、VmSwap 163MB、CPU some avg10=89%、irq 18%** |

两条 trace 的主线程 waiting channel 均为 `do_epoll_wait`（空闲态），且 `libdebuggerd_client` 连 app 栈都抓不下来（系统级过载）——**主线程没有死锁，是整机资源饥饿导致输入派发超时**。与本机环境吻合：模拟器仅 2GB RAM（MemFree 一度 94MB）+ 宿主机磁盘 95% 满（本仓 ENOSPC 惯性病史，见 commit 294206a0 磁盘守卫）。

### 本轮复现尝试（注册页）

注册页全流程压测：连续快速输入、输入中途切字段、IME 反复拉起/收起、键盘中断滚动、失误路径（密码不一致、光标中途插入编辑）——**全程 0 ANR、0 input dispatch 超时**（`dumpsys input` 队列始终 empty）。

### 定性结论与环境差异

- **不复现成立**：历史 ANR 是"低资源环境噪声"，不是注册页的应用层缺陷。
- **风险面仍在**：模拟器 2GB 内存 + 宿主机磁盘 95% 满的组合下，任何大内存时刻（星图渲染、长对话流）都可能再触发同类 ANR；评审/演示前建议 4GB+ AVD 并清出磁盘。
- 防御建议（非本轮改动）：对 `CheckinEvent`/流式渲染等高频路径观察 jank 遥测（app 已有 `performance_warning` 事件在发，但因 redis_unavailable 被网关丢弃——见 A-10）。

## 游客模式体验专节

| 步骤 | 结果 | 证据 |
|---|---|---|
| 登录页 → Continue as Guest | ✅ 一键进入，无表单无验证码 | 19/20 |
| 身份发放 | ✅ `访客体验8559`（L15），token 端到端 | 20 |
| 首页种子数据 | ✅ 高质量：目标「数据结构期中冲刺」（还剩7天/连着7天/今天先啃二叉树遍历）、今日任务卡、Aurora 理解快照 75%、过载风险 medium 等 | 20/29 |
| 会话持久化 | ✅ force-stop 重启后游客身份与页面恢复 | 29 |
| 各 Tab 渲染 | ✅ Cockpit/Galaxy(暗色星图+OS.pdf 5 颗待审知识星)/Community/Settings 均可进 | 40-48 |
| **游客发消息** | ❌ **永久 Queued**（见 A-2，游客主聊天目前不可用） | 25-32 |
| 飞行模式 | ✅ 横幅 + 失败卡；❌ 恢复半残（见 A-7） | 45-48 |

**评价**：游客模式的"第一眼体验"是全产品最强的——零门槛进来就有真实感的种子人生（目标、连续天数、AI 对你的理解快照），这对大学生试用决策极其关键。但它当前是"只能看不能聊"的展厅：主聊天被 A-2 卡死，游客在第一次真正想对话时就会流失。修掉 A-2（一行级）后游客闭环才算成立。

## 旅程覆盖

| 旅程 | 状态 | 备注 |
|---|---|---|
| 登录页渲染/滚动 | ✅ | 底部 "Don't have an account?" 首屏被手势条遮挡，需滚动（P3） |
| 注册 E2E（抽查） | ✅ 走通 | 表单→不一致校验→提交（21s 慢）→自动登录→Persona Guide 2 步→Skip→建模聊天（坏，A-3）→Cockpit |
| 游客 E2E | ⚠️ 半通 | 入口/首页/种子/Tab 全通；聊天被 A-2 卡死 |
| 聊天 3 条（长文本/流式 fallback/气泡对比度） | ⚠️ 受阻 | 主聊 A-2、建模聊 A-3；对比度只在主聊验证（成功），流式 fallback 未获得有效样本 |
| 任务创建/完成 | ⚠️ 受阻 | 创建首次失败（A-8），完成流未及验证 |
| Galaxy/insights | ✅/部分 | Galaxy 好；insights 未独立走查 |
| 设置 | ✅ | Schedule Preferences 渲染正常 |
| 飞行模式错误态→恢复 | ⚠️ | 检测✅ 恢复❌（A-7） |
| 中断恢复（杀进程重启） | ✅ | 会话恢复，但队列排空暴露 A-2 第二段 |
| ANR | ✅ 0 次 | 见专节 |

## 缺陷清单

### A-1 · P0 · 已修复（红绿通过）· 所有注册用户无法再次登录（500）

- **用户场景**：大学生注册成功→退出/换机/token 过期→重新登录。
- **观察**：`POST /auth/login` 对**任何注册用户**返回 500 `INTERNAL_ERROR`（guest 登录正常、注册当时正常）。错误密码正确 401，说明崩在密码校验之后。
- **复现**：注册任意账号（如 fieldtester3/fieldtester9）→ 用正确密码登录 → 500。
- **根因链**（traceback + 代码交叉）：登录成功路径调用 `security_monitor.record_login_attempt` → `_record_security_event` 内 `self.redis.setex` 在 **Redis 不可用**环境抛异常 → 外层 `except` 执行 `db.rollback()` → 请求级 session 事务终结使 `user` ORM 实例属性过期 → 返回路径 `_issue_auth_tokens` 读 `user.id`（auth.py:139）触发同步刷新 → `MissingGreenlet`（连接池 pre-ping IO 落在无 greenlet 上下文）。注册路径不做监控写入所以不炸；这解释了"仅 Redis-down 环境 + 仅 login"的组合。
- **修复**（3 处一行级）：
  - `backend/app/core/security_monitor.py`：两处 `await db.commit()` → `await db.flush()`（行 133/422，事务交由 get_db 成功尾统一提交）
  - `backend/app/api/v1/auth.py` login() return 前补 `await db.refresh(user)`（防御 best-effort 监控失败后的属性过期）
- **验证**：fieldtester3/9 登录 500→**200**（token+user 正常）；guest 登录回归 200；curl 直探与 UI 同路径。
- **警示**：这是"监控旁路故障拖垮主链路"的典型——best-effort 旁路的异常不该以 rollback 共享session 的方式外溢。

### A-2 · P1 · 游客主聊天：消息永久 Queued；恢复路径发出的帧被网关永久 NACK

- **用户场景**：游客在主聊天发第一条消息。
- **观察**：发送后气泡转灰 "Sending 11:49"，全局横幅 "Sending 1 queued messages..."，**4 分钟+不排空**，而 /ws/chat 心跳正常（RTT 1-26ms）。杀进程重启后队列恢复（Isar 离线队列生效）并真正出网，但网关立即 NACK。
- **网关日志铁证**（19:53:57）：`chat_orchestrator.go:521 Failed to parse chat message: json: cannot unmarshal string into Go struct field chatInput.extra_context of type map[string]interface {}`，并回 `message_nack(permanent)`；客户端不处理 NACK → UI 永远 Sending。
- **根因**：`websocket_chat_service_v2.dart:1987` 离线队列恢复时 `extraContext: payload['extra_context']?.toString()` 把 Map 转成 Dart Map 字面量字符串（非 JSON），此后该消息每次重发都是非法帧。
- **附带**：WS healthy 时 `_flushPendingMessages` 也未触发（首次 4 分钟未排空），ready 门控与排空的联动需复查。
- **修复建议**：1987 行保型还原（Map 或 jsonDecode），并处理 `message_nack`（permanent 时标记失败并给用户重试入口）。
- **证据**：截图 25-32、网关日志、`/tmp/sparkle_r3_logcat.txt`。

### A-3 · P1 · 注册用户建模聊天（onboarding 第二阶段）三连坏

1. 进屏自动发 `_onboarding_start_` 拉开场白 → 失败，横幅 "Modeling chat temporarily unavailable: Oops, something went wrong"（错误被映射成最笼统文案）。
2. 用户气泡棕底棕字**完全不可读**（对比度批量修复漏掉此屏；`modeling_chat_screen.dart` 文本用 `DS.brandPrimaryConst`）。主聊同主题气泡白字可读，形成对照。
3. 打字发送后 WS 心跳正常但**无回复、无错误、无超时**——静默挂起；客户端无流起始超时兜底。
- **证据**：截图 14-16；`modeling_chat_screen.dart:345/408`。

### A-4 · P1 · 注册用户 Profile tab 整页 type-cast 崩溃 + 错误页无出口

- 错误屏全文：`type '_Map<String, dynamic>' is not a subtype of type 'List<dynamic>?' in type cast`。
- 数据层根因：`/profile/context` 的 `user_insight_state.signal_evidence[].value`（及 projection 副本）是**多态字段**——游客= list、活跃注册用户= dict；移动端模型单向 cast List。
- 伴生 UX：错误页无重试按钮、无返回引导，**登出入口恰在此 tab** → 用户被关死在错误页（本测只能 `pm clear` 脱困）。
- 证据：截图 18；`/tmp/gctx.json` vs `/tmp/f3ctx2.json` shape diff（唯一 list→dict 分叉即 signal_evidence value）。

### A-5 · P1(debug)/P2(release) · 溢出条纹直接盖住核心操作

- 注册页：`BOTTOM OVERFLOWED BY 14 PIXELS`，黄黑条纹盖住 **Register 按钮**与 "Already have an account?" 链接（1080×2400@420dpi 即现；debug 可见条纹，release 静默裁切 14px，底链接失能）。命中测试未被遮挡，按钮仍可点（评审易误判为正常）。
- 聊天 tab（键盘拉起时）：`RIGHT OVERFLOWED BY 53 PIXELS` + `BOTTOM OVERFLOWED BY 81 PIXELS`，输入框被条纹覆盖——打字时用户看不见自己输入的内容。
- 证据：截图 08/10/22-24。

### A-6 · P1 · Goal detail 页渲染裸 Dart 异常文本

- `NoSuchMethodError: Class 'AppLocalizationsEn' has no instance getter 'goalDetailNoTargetDate'` 直接印在页面卡片里。
- 根因：`goal_detail_page.dart:269` 在全局 l10n 上调用 getter，但该 getter 只定义在 `goal/presentation/widgets/goal_detail_l10n.dart:11` 的局部包装类（arb 未含此键）。
- 证据：截图 39。

### A-7 · P1 · 飞行模式恢复半残：Community "Tap to retry" 是死按钮

- 离线时：全局横幅 + 每卡 "Failed to load · Tap to retry"（好）。
- 联网恢复后：横幅即时消失（检测✅），但点 retry **零网络请求**（logcat 仅遥测）；切走再切回也不重验证 → 恢复只能靠重启 app。
- 证据：截图 45-48。

### A-8 · P2 · Create Task 整屏渲染 l10n 原始键名 + 首次提交失败

- 屏上全是 "Task Title Label / Task Type Label / Task Generate Guide Subtitle…"（arb 缺失整屏文案）。
- 首次提交：两次 `POST /tasks`（38s/43s）**无响应记录** + 笼统 "Oops"；同 payload curl 200（1.6s）→ 疑似瞬时挂起，且无超时文案差异化。
- 证据：截图 33/37、logcat 19:58。

### A-9 · P2 · 视觉杂项

- 聊天 tab 文案重复："Deep calibration available · Deep calibration available (1 remaining…)"。
- Galaxy 右侧缩放控制栏与 "Review now" 按钮重叠。
- 离线横幅用等宽+下划线样式（终端风），与产品气质不符。
- 重启后偶见全屏黄绿描边（来源未定性，debug 疑似 focus/语义高亮）。

### A-10 · P2 · 平台/环境

- 注册接口 ~21s（LLM 生成 personas？），期间按钮无进度反馈、可双击。
- 网关遥测端点全程 `reason: redis_unavailable`——**客户端性能/网络观测数据在本环境被静默丢弃**，这让 A-1 这类问题的发现完全依赖人工。
- BGM 资源缺失：`BGM asset failed for profile (audio/bgm/calm_track_loop.m4a)`（有 fallback，仅日志）。

### A-11 · P3 · 登录页首屏 "Don't have an account?" 被手势条遮挡，需滚动才能发现注册入口（首用转化风险）。

## 大学生视角困惑点

1. 进来看到 "AI currently remembers 0 memories / 5 correctable claims / Can go deeper 3/4"——**每个词都认识，连起来不知道在说什么**；建议首屏给一句话引导。
2. 注册页密码强度条（Strong）是好设计，但 "100" 数字裸奔在旁边，没人懂 100 是什么。
3. 任务创建屏一堆 "Label" 英文键名（A-8），第一反应是"这 App 没做完"。
4. 发消息后 "Queued/Sending" 长时间不动（A-2），大学生只会理解为"网不好/号废了"，直接流失。
5. 首页种子数据反而最抓人（"还剩7天，今天先啃二叉树遍历"很有代入感）——建议把这条体验前移到注册前。

## 本轮代码改动

| 文件 | 改动 | 验证 |
|---|---|---|
| `backend/app/core/security_monitor.py` | 133/422 行 commit→flush（+注释） | 红绿：login 500→200 ×2，guest 回归 200 |
| `backend/app/api/v1/auth.py` | login() return 前 `await db.refresh(user)` | 同上 |

未改动但已定位到行的待修项：A-2（v2ws:1987 + NACK 处理）、A-3（modeling_chat_screen 气泡配色 + 流超时）、A-4（signal_evidence 多态 + 错误页出口）、A-5（注册页/聊天页 Column 溢出）、A-6（goal_detail_page.dart:269）、A-8（任务屏 arb 文案）。均为一行级，但需重构建 APK/重启前端验证（本机 Gradle 8.14 vs JDK25 冲突未解，APK 复用策略见环境节）。

## 覆盖缺口（下轮建议）

- 聊天流式成功路径（修 A-2 后）：长文本、流式中断/停止按钮、fallback 提示、多轮上下文。
- 任务完成闭环 + Start Focus + View Calendar。
- Insights 页、Community Feed/Groups、Memory drawer、深链/通知。
- 4GB AVD + 磁盘清理后的 ANR 复测基线。
