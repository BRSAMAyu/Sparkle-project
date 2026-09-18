# Web 浏览器走查 · Round 2

- 日期：2026-09-19 凌晨
- 走查人：Web 全旅程二轮实测 subagent（ZCode）
- 环境：`flutter run -d web-server --web-port 8321`（Flutter 3.41.3 DDC debug 构建）+ headless Chromium 153（Playwright 1.63，venv `/tmp/webtest-venv`，已按纪律删除）；后端栈全健康，DeepSeek 真 LLM 已接入
- 仓库 HEAD：`b97a0674`（含 W-5 修复 commit `d4907bcc`，**但见下文「运行实例陈旧」定性**）
- 方式：Playwright（CDP 级真实输入事件）+ CDP `Accessibility.getFullAXTree` 语义树取证 + 截图 + 全程 console/network 监听

## 结论 TL;DR

**游客全旅程本轮 100% 打通**（登录页 → 访客登录 → 驾驶舱 → 五 Tab 全渲染 → 学习模式设置页 → 退出登录确认 → 回登录页），且 **W-6「点击穿透」定性反转：真实 CDP 点击全程有效**——一轮的「坐标点击不达」实为 **N-1 CORS 预检拦截（网关 CORS 白名单缺 `x-device-id`，P1 新阻断）** 造成的假象。W-5 语义树修复方向在 HEAD 源码中确认存在，但 **:8321 运行实例是 22:02 的陈旧快照（修复 commit 23:32 才落库，晚 90 分钟且未热重启），as-served 语义树默认关闭**；通过标准读屏激活路径（点击 `flt-semantics-placeholder`）可激活出**完整标记语义树**（36 节点，textbox/button 全带中文标签），自动化与读屏从此可用。真 LLM 聊天：消息可发出、AI 导师回复+意图收敛教练条真实渲染；发送后输入框不清空（新缺陷）、流式停止按钮未捕获到、中断保留测试未完成。会话**写入** localStorage ✓ 但**重载恢复**仍失败（W-2 残留）。

## 关键定性 1：运行实例陈旧（方法论警告）

- `flutter run`（pid 29235）**2026-09-18 22:02:52 启动**；W-5 修复 `d4907bcc` **23:32:28 落库**——运行实例早于修复 90 分钟，全程无人热重启。
- 实证：served `packages/sparkle/main.dart.lib.js`（57KB）含 `SemanticsBinding` 但 **0 处 `ensureSemantics`**（HEAD `lib/main.dart` 有）；`initFlutter` 计数正常（排除文件错位）。
- 推论：本轮所有「as-served」结论描述的是 **22:02 快照**的行为；`d4907bcc` 及之后的源码修复需重启 `flutter run` 后复验。任务前提「最新构建含 W-5 语义修复」在运行实例上不成立。

## 关键定性 2：三个测试架级辅助（非产品代码改动）

1. **dwds 引导 workaround**：headless 下 dwds 调试客户端连上 SSE 后永不调 `$dartRunMain()`，2012 个 DDC 模块载完后 app 挂起白屏。脚本在 `typeof window.$dartRunMain === 'function'` 且 networkidle 后手动调用一次（早调会失败——v3 教训：必须在模块流结束后）。
2. **CORS 预检补丁**：`context.route` 对 `localhost:8080` 的 OPTIONS 请求回 204 并镜像 `Access-Control-Request-Headers`。这是为了让真实 UI 旅程可以继续；**它恰恰实证了 N-1 是唯一阻断**。
3. **语义激活**：合成 click `flt-semantics-placeholder`（读屏用户的激活路径）。HEAD 修复（web 常开语义）落地后此步应可删除。

## 游客旅程矩阵（Round 2 最终态）

| # | 步骤 | 结果 | 到达方式 | 证据 |
|---|---|---|---|---|
| 1 | 加载登录页 | ✅ | 直载 | 中文 UI、Sparkle 星火字标、480px 表单（W-7 修复保持）；01-login.png |
| 2 | 访客登录（点击「以访客身份继续」） | ✅ | **坐标点击 (640,606)，一次即中** | `POST /auth/guest → 200`（01:14:24，v7 events）；URL 正确切到 `/#/home`（W-9 已不复现）；无双触发（guest×1、login×0，W-4 真路径回归 ✅） |
| 3 | 主界面（驾驶舱） | ✅ | 自动跳转 | 底部导航 **驾驶舱/星图/对话/社群/我的**（注：一轮报告的「首页/任务」实为驾驶舱/社群）；02-home.png |
| 4 | Tab·驾驶舱 | ✅ | hash 深链 | 仪表盘+Agent 输入条渲染 |
| 5 | Tab·社群 | ✅ | hash 深链 | 伙伴/动态/群组/星火社群 |
| 6 | Tab·对话 | ✅ | hash 深链 | AI学习助手+会话卡；⚠️「服务暂时不稳定」横幅 + `chat/history 500`（N-2） |
| 7 | Tab·星图 | ✅ | hash 深链 | 空态引导 + 种子数据（OS.pdf 5 颗知识星） |
| 8 | Tab·我的 | ✅ | hash 深链 | 访客头像/初始画像/自我认识/学习档案；⚠️「连接失败」横幅（间歇） |
| 9 | 设置页 | ✅ | 深链 `#/settings/learning-mode` | **学习模式设置**真实渲染：深度/好奇心双轴滑杆（70%/80%）+ 保存偏好；08-settings.png |
| 10 | 退出登录 | ✅ | 滚动露出 → 语义点击「退出登录 安全退出当前账号」→ 对话框「确定」 | 回 `/#/login?return_to=/profile`；localStorage `access_token` 已清（guest_id 保留，符合设计）；09-after-logout.png |
| 11 | 会话重载恢复（W-2 复验） | ❌ | reload | token 四键在 localStorage 全在（guest_id/access/refresh/legacy），但重载后回登录页——**写 ✓ 恢复 ✗**（as-served） |

注：Tab 底栏的语义标签点击（get_by_text）不稳定（0/5 导航成功），本轮 Tab 覆盖用 hash 深链完成；登出/确定等列表行语义点击则真实生效。底栏点击需 headed 环境复验后定性（可能仍属 N-1 时代误伤的残留怀疑，无新证据）。

## W-5 定性（语义树）—「修复方向正确，运行实例未含修复」

- **as-served（22:02 快照）**：加载完成即查 `flt-semantics` = **0 个**，a11y 树仅 4 节点（RootWebArea「Sparkle 星火」+「Enable accessibility」占位符）——与一轮观察一致（残缺+懒激活）。Tab 焦点遍历只懒生成 6 个匿名 native Submit，无标签。
- **激活后**：合成点击占位符 → **21~36 个 flt-semantics 节点**，CDP 树完整可寻址：`textbox:用户名`、`textbox:密码`、`button:登录`、`button:以访客身份继续`、`button:忘记密码？`、`button:退出登录 安全退出当前账号`、`button:确定` 等，全部带中文 accessible name。
- **对照 HEAD 源码**：`SemanticsBinding.instance.ensureSemantics()`（web 常开）已在 `d4907bcc`，但 served 代码无此调用 → **修复未在运行实例上生效，无法据此宣布 W-5 关闭**。重启 flutter run 后按「加载即 0 占位符、非零语义节点」一节标准复验即可。
- 附带发现：语义激活后大部分节点 `pointer-events:none`、仅可交互节点 `all`——语义点击需选对 pe:all 祖先节点（本轮自动化已按此实现）。

## W-6 定性（点击穿透）—「反转：真实 CDP 点击有效」

- 本轮**真实 CDP 指针事件全程可达且生效**：
  - 激活前坐标点击 (640,606) → `pointerdown/click` 命中 FLUTTER-VIEW（capture 期监听取证）→ guest 请求发出（200）→ UI 跳转 `#/home`；
  - 激活后语义节点点击（退出登录、确定、发送、输入框聚焦）全部真实生效；
  - 设置行、登出行经滚轮滚动后点击成功（滚轮滚动 Flutter scrollable 有效）。
- 一轮「flt-glass-pane 0×0 点击全不达」**未复现**：本轮 flutter-view shadowRoot 内查询 glass-pane 为 null（3.41 引擎 DOM 结构与一轮描述不一致），且点击行为学证据（请求发出+导航发生）与「穿透」矛盾。
- 一轮误判根因还原：点击其实到达了 Flutter 并触发了 guest 登录逻辑，但**请求被 N-1 CORS 预检拦截**（`net::ERR_FAILED`，无 response 事件）——当时以「网关零请求/无响应事件」判定点击不达，实为「点击有效、请求被杀」。**W-6 建议降级关闭，N-1 升为 P1。**

## 真 LLM 聊天结果（DeepSeek）

| 项 | 结果 |
|---|---|
| 进入对话页 | ✅（历史拉取 500 → 错误横幅，见 N-2；重试后可用） |
| 消息 1（简单：「你好，请用一句话介绍你自己」） | ✅ 坐标点击圆形发送键后送出；**AI 导师回复渲染**（问候 hero）+ **意图收敛教练条**（「这句话更像是一个需要立即承接的意图…」+5 个情境 chips：继续让 AI 帮我推进/交给 AI 系统/先专注 25 分钟/直接回答/3 步执行清单）；12-chat-reply1.png |
| 流式过程观测 | ⚠️ 3s 轮询粒度下未捕获「停止」按钮态（回复很快完成或流式窗口短）；逐 token 渲染无法在 headless 轮询下确证 |
| 消息 2（具体：高数泰勒公式 3 天复习计划） | ⚠️ 输入成功（46/400），教练 chips 实时变为复习向（开始复习/查看错题本/3 步执行清单）= 意图管线真实消费了内容；但**发送未生效**（输入框不清空导致消息拼接，见 N-6），未产生第二条回复 |
| 停止中断保留测试 | ❌ 未完成：始终未出现可点的「停止」态（依赖流式进行窗口，两次都错过/未进入） |
| LLM 请求预算 | 实际发出 ≤2 条（≤5 合规） |

## Console / Network 错误清单（全程抓取，去重后）

| # | 级别 | 缺陷 | 证据 |
|---|---|---|---|
| **N-1** | **P1** | **网关 CORS 预检拒绝 `x-device-id` 头**：`Access-Control-Allow-Headers: Authorization, Content-Type, X-Requested-With, X-Request-ID, X-Trace-ID, Accept, Accept-Language` 不含 `x-device-id`，而 web 客端 Dio 全量携带 → `/auth/guest`、`/user/settings`、`/client-telemetry/events/batch`（30s 周期）全部 `net::ERR_FAILED`。curl OPTIONS 复现实证（带 x-device-id 与不带的预检响应对比）。**这是本轮唯一的全局阻断，也是一轮 W-1/W-6 误判的共同根因。** 修复：网关 CORS 白名单加 `x-device-id`（或客户端停发/改 query） | events_v6/v7.jsonl console_err；curl 预检记录 |
| N-2 | P2 | `GET /api/v1/chat/history/{sessionId}?limit=20/80 → 500`（×2，guest 会话 a0efce56…）→ 对话页「服务暂时不稳定」横幅 | chat.log 01:28:28/29 |
| N-3 | P2 | 「升级账户」页红屏崩溃：`UnimplementedError: respon…`（Oops, something went wrong），复现 2/2（v7/v9）→ 我的 Tab 点升级账户即崩 | 08-settings.png（v7 版，已被 v11 覆盖，事件留档） |
| N-4 | P2 | **会话重载恢复失败**：UI 登录成功后 localStorage 四键齐全（flutter.access_token/refresh_token/accessToken/guest_id），reload 后仍回 `#/login?return_to=…`（CORS 已补丁前提下）。写入 ✓、恢复链路 ✗——HEAD 的 checkAuthStatus 竞态收口是否已修需重启后复验 | v8 events；v11 ls 证据 |
| N-5 | P3 | 资源 404：`assets/FontManifest.json`、`assets/shaders/ink_sparkle.frag`、`assets/assets/audio/ui/tap.ogg`、`error.ogg` → **MaterialIcons 全屏 tofu**（截图可见）+ 交互音缺失。疑似 web-server debug 伺服资产清单缺失 | events 各轮 resp_err |
| N-6 | P3 | 聊天输入框发送后不清空 → 第二条消息与前文拼接（「…介绍你自己我下周要考…」46/400），既干扰用户也破坏自动化 | 12/13-chat 截图 |
| N-7 | info | dwds `DevHandler: Bad state: Not connected to an application` pageerror 风暴（headless+手动 runMain 引导的副产物，server 侧日志噪音）；另 `flutter analyze` 进程（pid 44285，00:40）非本轮所启 | events_v6 |

## 与 Round 1 缺陷清单对账

| 一轮编号 | 本轮定性 |
|---|---|
| W-1 登录后不跳转 | **修复确认**（真实点击路径）：guest 200 → `#/home`。注意 as-served 构建已含该修复 |
| W-2 token 未持久化 | **部分**：写入 localStorage ✓；重载恢复 ✗（N-4），as-served 未闭环 |
| W-3 空凭据 200/500 | 维持一轮结论（引擎 400/401 正确）；本轮未复验空凭据路径 |
| W-4 Enter 双触发 | 真路径回归 ✅：全程 guest×1、login×0。但**键盘提交路径疑似被误伤**：聚焦输入框后 Tab+Enter ×8 零请求（Enter 不再提交任何表单）——建议补一条键盘提交用例 |
| W-5 语义树残缺 | 修复在 HEAD、不在运行实例（见关键定性 1）；激活路径可用，激活后树完整 |
| W-6 点击穿透 | **反转关闭**：点击有效，根因是 N-1 CORS（见 W-6 定性） |
| W-7 UI/UX | 中文/字标/480px 保持 ✅；新增 N-5 图标 tofu |
| W-8 运维 | 网关日志本轮未见异常增长；无新运维事件 |
| W-9 hash 不重写 | **已不复现**：登录后 URL 正确变 `#/home` |
| W-10 恢复风暴 | 未复验（单客户端；N-4 恢复失败反而避免风暴） |

## 截图索引（`Sparkle-sysrev/screenshots/web-round2/`）

| 文件 | 内容 |
|---|---|
| 01-login.png | 登录页 as-served（中文、字标、480 表单、无语义激活） |
| 02-home.png | guest 登录成功 → 驾驶舱主界面（v7） |
| 03-branch-home.png / 04-branch-tasks.png / 05-branch-chat.png / 06-branch-galaxy.png / 07-branch-profile.png | 五分支渲染（驾驶舱/社群/对话+错误横幅/星图种子/我的+访客头像） |
| 08-settings.png | 学习模式设置页（深度 70% / 好奇 80% 滑杆 + 保存偏好） |
| 09-after-logout.png | 退出确认后回登录页 |
| 10-profile.png | 我的 Tab 全景（升级账户/学习档案/学习资料库可见） |
| 11-chat-empty.png | 对话页初始态（错误横幅 + Aurora 会话卡 + 需你确认） |
| 12-chat-reply1.png | 消息 1 送出后：AI 导师回复 + 意图收敛教练条 + 5 chips（输入框未清空可见） |
| 13-chat-stopped.png | 消息 2 输入态：复习向 chips（输入拼接 46/400 可见） |

## 复验清单（交给下一棒）

1. **重启 `flutter run`**（先 `pkill -f grpc_server` 类纪律不适用；flutter run 直接重启即可）→ 复验：加载即有语义树（W-5 关闭判定）、reload 会话恢复（W-2/N-4）、键盘 Enter 提交（W-4 误伤确认）。
2. **网关加 `x-device-id`** CORS 白名单（一行）→ 撤掉测试架预检补丁复跑全旅程（预期 0 辅助通过）。
3. 修 N-2 chat/history 500、N-3 升级账户 UnimplementedError、N-6 输入框清空。
4. headed Chrome + 真鼠标补一轮：底栏 Tab 点击、流式「停止」按钮中断保留（本轮 headless 轮询粒度不足）。
