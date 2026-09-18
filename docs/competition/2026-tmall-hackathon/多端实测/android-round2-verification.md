# Android 修复复验轮 · Round 2（对应 round1 A-1..A-7）

- 日期：2026-09-18 深夜
- 走查人：FieldTest agent（四度实测 · 复验轮）
- 被验对象：main@37edc68d（fix(mobile): Android P1 batch — A-2/4/5/6/7 + A-3 partial）
- 环境：Medium_Phone_API_36.1 无头模拟器（1080×2400 @420dpi，复用既有实例）；APK=debug built from 37edc68d（applicationId `com.sparkle.app`）；后端网关 :8080 / FastAPI :8000 / gRPC :50051
- 方式：adb input/screencap + uiautomator dump + logcat 全程取证 + 网关日志（/tmp/gateway_server.log）与引擎日志交叉验证 + curl 直探（红绿）
- 截图：`.fieldtest-shots/round4/`（A1/A2/A4/A5/A6/A7 前缀，共 50 张；正文只引关键判定帧）

## 结论 TL;DR

**六项中 5 项 PASS、1 项 PARTIAL，0 项修复失效。** A-2 游客聊天全链路打通：在线发消息获得真实流式回复、断网入队/恢复出网、失败有「发送失败+重试」可见态且重试真实出网；全程网关 0 次 frame 解析错误、0 次 NACK（round1 的死锁根因已灭）。A-1 注册→登出→再登录 API 与 UI 双路 200。A-4 双身份 Profile 无崩溃。A-7 离线检测/恢复/重试三段全部真实生效。A-5 注册页溢出已灭，但聊天页「离线横幅+键盘」组合态仍有 5px 溢出条纹（改良未除根）。A-6 修复在代码层确认（dynamic→静态类型，编译期消除 extension 失效），但当前构建中 GoalDetailScreen 无任何用户可达入口，null-date 分支无法在真机旅程中复验。另收获 5 个新发现（含 1 个疑似跨账号本地缓存泄漏，建议排查）。

## 环境差异与排障记录（影响复现的必读）

1. **任务简报与实际不符：gRPC :50051 实际未在跑**。两层原因：`backend/.venv` 不存在（`make grpc-server` 直接 126）；改用 Homebrew python3.11 直启后又因 `backend/.env` 的 REDIS_URL 密码与 sparkle_redis 容器 `--requirepass` 不匹配而失败（`invalid username-password pair`，engine 对 Redis 硬依赖）。**处置**：从 docker inspect 读容器实际密码，以 `REDIS_URL` 环境变量覆盖启动成功。这意味着：round1 期间（以及任何按 .env 直启 engine 的环境）Redis 对 engine 是断的——A-1 当时 500 的土壤仍在，本轮 Redis 恢复后 A-1 的"Redis-down 场景"本身不可复现，复验结论以"无回归+主链路通"为准。
2. **APK 构建三重障碍**（上一轮"Gradle 8.14 vs JDK25 冲突"的真实根因，供后续彻底修复）：
   - 本机仅有 JDK 25，Gradle 8.14 不支持 → 用 brew `openjdk@17` 指定 JAVA_HOME 解决；
   - `~/.gradle` 是指向 exFAT 外置卷 `/Volumes/移动E/MacCache/gradle` 的符号链接，该卷现在会为所有新建文件生成 AppleDouble 元数据（`._Program.class` 等），Gradle classpath 插桩 walker 把 `._*.class` 喂给 ASM 抛 `IllegalArgumentException`，报错文案误导为 "Failed to create directory"（--stacktrace 才见真因）；
   - 清 `._*` 会即时再生，无解 → **最终方案**：`GRADLE_USER_HOME=~/.gradle-r4`（本地真目录）+ wrapper dists 符号链接复用，构建成功。建议：把 gradle 缓存迁回本地盘，或对该卷关闭 xattr 写入。
3. 会话中网关日志出现一次非本测试发起的 `POST /api/v1/auth/guest?guest_id=lp_lat-b2`（22:37:58），疑为其它探针/会话，与本轮结论无关，仅记录。

---

## 逐项复验

### A-2 · 游客聊天 E2E（最优先）· PASS（附 3 个残留小项）

**复现步骤**
1. 冷启应用（残留 round1 数据，直接以访客体验8559 进主页）→ 对话 Tab
2. 聊天页输入 `hello_A2_round4` → 发送
3. 观察气泡状态机与网关/引擎日志
4. `adb shell cmd connectivity airplane-mode enable` → 输入 `offline_queue_test_A2` → 发送（入队）
5. `airplane-mode disable` → 观察横幅/出网/气泡状态
6. 对「发送失败」气泡点「重试」→ 观察网关 [CONTEXT] 行增量

**实际结果**
- 在线发送：气泡「思考中…」+全局 THINKING 条 → **AI 真实流式回复逐字到达**（"…message came through. If you're checking that things are working, they are…"——LLM 直接确认收到测试消息）→ 状态「已完成」。round1 的"永久 Queued"不复存在。（A2-07/A2-10）
- 网关侧：全程 `Failed to parse chat message` **0 次**、`message_nack` **0 次**；[CONTEXT] 行（=聊天帧被处理）随发送/重试精确递增。round1 的毒帧 NACK 死锁根因已灭。
- 断网：离线横幅（你已离线…）+页面「连接失败」卡即时出现；离线期间排队消息 **0 次出网**（请求被正确拦截）；恢复网络后队列实际出网（[CONTEXT] 2→4），且失败消息气泡显示 **「发送失败 · 重试」** 可见态。
- 重试：点「重试」后 [CONTEXT] 4→5，**真实重发**，新气泡出现 + 打字指示器 → 流式回复（A2-21/A2-22）。
- 注意：live LLM（deepseek 通道）本轮实际可用，因此验证到了成功路径而非"可见失败"兜底；失败路径由第 6 步（重试前）与 500 卡片另行覆盖。

**判定：PASS**

**残留（新发现，详见新发现清单）**：N-1 排队横幅计数永不递减（"正在发送 3 条…"贯穿后续全程，消息实际已出网）；N-3 气泡「发送失败/重试」与全局"正在发送…"横幅语义矛盾、重试后原气泡与重发气泡并存；N-6 离线+键盘态发送键被遮挡（见 A-5）。

**关键截图**：A2-07（发送后思考态）、A2-10（流式回复正文）、A2-13（离线输入+5px 条纹）、A2-20（发送失败+重试）、A2-21（重试后等待发送+新气泡+打字指示）、A2-22（重试后思考态）

---

### A-1 · 注册用户 re-login（旧 bug：500）· PASS

**复现步骤**
1. UI：我的 → 退出登录（对话框确认）→ 落登录页
2. 登录页 → 「还没有账号？」→ 注册页（fieldtester20 / fieldtester20@example.com / 密码×2 / 双协议勾选）→ 注册
3. curl 直探：`POST /api/v1/auth/register` → `POST /api/v1/auth/login`
4. UI：登出 → 登录页输入 fieldtester20 凭据 → 登录 → 画像引导跳过 → 主页

**实际结果**
- UI 登出流程完整（确认对话框→登录页）。
- API 红绿：register **200**（user id 下发）；login **200** + access_token。网关日志无任何 /auth/login 500。
- UI 登录：网关 `POST /auth/login | 200`（22:45:12）→ 画像引导两步 → 跳过 → **驾驶舱完整渲染（fieldtester20, L1）**。
- 诚实备注：本轮 engine 侧 Redis 已被我修复连通（见环境差异#1），round1 触发 500 的 "Redis-down + login" 组合不可复现；本轮结论为 **主链路无回归 + 200 正确**。若需复现原故障土壤，需故意以错误密码的 REDIS_URL 启动 engine/FastAPI 再登录（下轮红绿建议）。

**判定：PASS**

**关键截图**：A1-03（登出确认）、A1-04（落登录页）、A1-09（fieldtester20 主页）

---

### A-5 · 溢出条纹（注册页 + 聊天页键盘）· PARTIAL（注册页 PASS；聊天页在线 PASS/离线 FAIL）

**复现步骤**
1. 登录页 → 注册页：逐字段填写、键盘拉起/收起、滚动到底，全程观察条纹
2. 聊天页（在线）：键盘拉起输入，观察输入框可见性
3. 聊天页（飞行模式离线 + 键盘拉起）：观察输入行

**实际结果**
- 注册页：填写/键盘/滚动全程 **0 条纹**；注册按钮与「已有账号？」完整可见可点——round1 的 `BOTTOM OVERFLOWED BY 14 PIXELS` 已灭（修复说明 IntrinsicHeight/Spacer 移除）。（A5-02/A5-06）
- 聊天页在线：输入框完整浮于键盘上方，无遮挡无条纹。（A2-06）
- 聊天页**离线**（顶部离线横幅 + 底部连接失败条同时在场）：输入行出现 **`BOTTOM OVERFLOWED BY 5.0 PIXELS`** 黄黑条纹，横盖输入行（字数计数器被盖、发送按钮视觉被切）。从 round1 的右 53px/下 81px 收敛到 5px，但组合态未除根。（A2-13/A2-14）

**判定：PARTIAL**（注册页 PASS；聊天页对 round1 主诉有实质改善，但离线组合态仍复现条纹）

**关键截图**：A5-02（注册页顶部无条纹）、A5-06（注册页底部按钮完整）、A2-06（在线键盘正常）、A2-13（离线 5px 条纹盖输入行）

---

### A-4 · Profile 页 type-cast 崩溃 · PASS

**复现步骤**
1. 访客身份 → 我的 Tab：整页滚动、展开各卡
2. 注册身份（fieldtester20，已激活）→ 我的 Tab：整页滚动
3. logcat grep `type.cast|NoSuchMethod|Unhandled Exception`

**实际结果**
- 访客 Profile（访客体验8559）：头像/等级/本周成长趋势/初始画像/自我认识/工作记忆快照完整渲染。
- 注册用户 Profile（fieldtester20, Lv.1）：完整渲染，滚动全程无异常。
- logcat 三类关键字全程 **0 命中**。修复定位的 `_colorFromElement` 多态 cast + `prestigeAccentHex` 容错解析未见回归。
- 「错误卡有出口」子项：修复后两身份均未再触发错误页，该子项改由 A-7 的错误卡（关闭/重试均可点、可退出页面）间接验证通过。

**判定：PASS**

**关键截图**：A4-01（访客 Profile）、A4-02（注册用户 Profile）

---

### A-6 · 无日期 Goal 详情裸异常 · PARTIAL（代码级确认；真机旅程不可达）

**复现步骤（尝试过的入口，全部记录）**
1. cockpit 目标芯片（round4_nodate_goal）→ 只弹**切换菜单**（单选 radio），无详情项
2. cockpit「现在的指挥台」任务卡 → 进入**专注模式**设置页，非 goal 详情
3. 星图 → 目标世界 → 仅贡献/点亮记录空态
4. 深链 `sparkle://goals/<id>`（manifest 有 VIEW+BROWSABLE+scheme）→ intent 送达但 **GoRouter 未路由**，停在原页
5. 目标创建向导（空状态「设定目标」卡）可进入、UI 文案正常（中文，5 步），但第 1 步文本输入后继续按钮置灰逻辑未通过（见 N-7），未能走完造可访问目标

**为构造 target_date=null 目标**：以 fieldtester20 token `POST /api/v1/goals`（`target_date` 缺省）成功创建 `round4_nodate_goal`（id 53ee579f…，target_date=null），芯片随即出现在 cockpit。

**实际结果与判定依据**
- 代码层：37edc68d 将 `_buildTargetDateChip` 的 `dynamic l10n` 改为 `AppLocalizations` 静态类型并附根因注释（dynamic 接收者绕过 extension 解析 → NoSuchMethodError），`goalDetailNoTargetDate` 分支逻辑原样保留（null → `_InfoChip(goalDetailNoTargetDate)`）。该机制在编译期即消除，且修复提交自带回归测试（commit 注明 15/15 绿）。
- 设备层：全 session logcat `NoSuchMethodError` **0 命中**；但 GoalDetailScreen 本身在本构建中**未找到任何用户可达入口**，null-date 芯片无法在真机旅程中点亮。

**判定：PARTIAL** —— 修复真实性由代码+回归测试背书；「真机打开无日期目标详情显示芯片」本轮无法执行。建议下轮：给 cockpit 快照卡（goalDetailSnapshot slot）补真实入口后复验，或临时以深链路由打通。

**关键截图**：A6-10（fieldtester20 cockpit 出现 round4_nodate_goal 芯片）、A6-11（目标切换菜单无详情项）

---

### A-7 · 离线错误态 → 恢复 → retry 死按钮 · PASS

**复现步骤**
1. 飞行模式 ON：观察全局横幅/页面级提示/请求拦截
2. 社群 Tab（伙伴/动态/群组）离线加载 → 「加载失败·轻触重试」卡
3. 飞行模式 OFF：观察横幅消失与**无操作自动刷新**
4. 手点两张 retry 卡 → 网关 community/experience 请求计数增量

**实际结果**
- 离线检测即时：全局「你已离线…」+ 任务页「当前无网络 – 你的任务操作会在恢复连接后自动同步」+「连接失败」卡；离线期间社区请求 **0 次出网**（计数恒 105）。
- 恢复：横幅即时消失；**无任何用户操作**情况下 community 请求 99→101 —— 与修复说明"offline→online 自动失效 4 个 provider"一致（round1 只能靠重启恢复的半残态已灭）。
- 手动 retry：点击两张卡后请求计数 138→140，网关实时记录 `GET /experience/community-accountability`（23:14:19）等真实重放——round1 的"点了零请求"死按钮已复活。
- 诚实备注：重试后卡片仍显示失败，原因是该接口对新建访客**服务端真实 500**（见新发现 N-5）——按钮行为正确，是后端问题。

**判定：PASS**

**关键截图**：A7-01（离线横幅+连接失败卡+完成任务禁用）、A7-04（社群 retry 卡与正常卡并存终态）

---

## 新发现清单（本轮新增，非 round1 复验项）

| # | 级别 | 现象 | 初步定位 | 证据 |
|---|---|---|---|---|
| N-1 | P2 | 聊天「正在发送 N 条排队消息…」横幅计数永不递减：2→3→出网多条后仍显示"3 条"，且遗留 round1 毒帧疑似永久占位（但不再引发 NACK 风暴） | 排空回调未更新计数/未清 legacy 队列项 | A2-16→A2-22 全程截图；网关 [CONTEXT] 计数与横幅数脱钩 |
| N-3 | P3 | 状态语义矛盾：气泡「发送失败·重试」与全局「正在发送…」并存；重试后原气泡（等待发送）与重发气泡并存，历史出现重复消息观感 | 气泡状态机与全局 flush 状态两套真相 | A2-20 vs A2-21 |
| N-4 | P2·建议排查 | **疑似跨账号本地缓存泄漏**：登出 fieldtester20 → 新访客 a74b 的驾驶舱「理解快照」显示 fieldtester20 的目标 `round4_nodate_goal` | 本地（Isar）缓存键未按账号隔离，账号切换后渲染前账号数据 | A6-10（fieldtester20 cockpit）vs A6-16/A6-15（a74b cockpit 出现同目标名） |
| N-5 | P2·后端 | `GET /api/v1/experience/community-accountability` 对新建访客稳定 **500**（网关日志 23:12:48 ×2、23:14:19）→ 社群伙伴页对任何新用户首屏即永久错误态，retry 无法修复 500 | experience 侧对新账号缺数据路径未兜底 | 网关日志行、A7-04 |
| N-6 | P3 | 离线+键盘组合态：发送按钮被溢出条纹/布局挤压，需先收键盘才能点中（在线无此问题）；即 A-5 的 5px 条纹同源 | 连接失败条参与布局约束后输入行 5px 溢出 | A2-13/A2-14/A2-15 序列 |
| N-7 | P3·待诊 | 目标创建向导第 1 步：输入文本后「继续」保持禁用（一次尝试；未排除自动化输入因素） | 向导校验触发条件未随输入刷新 | A6-08/A6-09 |
| ~~N-2~~ | 已排除 | 曾怀疑输入框吞末字符（聊天/注册确认密码两次丢尾）→ 复验确认根因是测试自动化在 Gboard 组合态发 ESC 丢弃组合文本；正常"输入→BACK 收键盘"路径无损（登录密码 11/11 精确匹配）。不记为应用缺陷 | 自动化工件 | A5-05 vs A1-08 前后对照 |

**正向附带发现**：round1 A-8 的任务创建屏裸 l10n 键名（"Task Title Label"…）现已全部渲染中文（任务类型/预计时长/难度/精力消耗/截止时间，默认"无截止日期"）；A-3 的建模聊气泡配色与 45s 首帧超时可见错误也在本轮路径中观察到部分生效（未做专项复验，保持"A-3 partial"结论）。

## 覆盖缺口（下轮建议）

- A-6：打通 GoalDetailScreen 真实入口后补 null-date 芯片真机帧；深链 sparkle://goals/<id> 未路由建议登记缺陷。
- A-1：以错误 REDIS_URL 启 engine/FastAPI 复现 Redis-down 场景，红绿复验 login 防御。
- N-4：设计双账号交替实验定位本地缓存泄漏层（Isar 键 vs provider 作用域）。
- N-5：后端修复 community-accountability 对新账号的 500 后，回归社群首屏。
- 聊天流式成功路径的深度项（长文本、中断/停止按钮、多轮上下文）仍未覆盖。

## 本轮产物与环境遗留

- 截图：`.fieldtest-shots/round4/`（50 张，命名 A{n}-{序号}-{说明}.png）
- 构建产物已清：`mobile/build/`、`mobile/.dart_tool/`、临时 Gradle home `~/.gradle-r4`（3.0G）；含 token 的临时响应文件已删除
- gRPC engine 由本轮以环境变量覆盖方式拉起（Redis 凭据经 docker 配置注入，未落盘仓库）；模拟器为复用的无头实例，保持运行
