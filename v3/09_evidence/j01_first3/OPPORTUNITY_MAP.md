# J-01 Opportunity Map — First 3 Minutes 当前体验（机会图）

> 实测卡产出（J-01, stream JOURNEY, gate V3-1）。所有行内事实均来自本 worktree
> 的 macOS 桌面集成测试真实运行（真后端 :8080/:8000，真实墙钟计时，截图为证），
> 非静态推断。生成时间：2026-09-26。

## 一、机会图（阻碍 / 影响面 / 砍 or 改 / 证据）

| # | 阻碍（现状） | 影响面（谁被挡） | 砍 or 改 | 证据 |
|---|---|---|---|---|
| O1 | **新访客首屏被种入未声明演示目标**：guest 注册即被 `guest_seed_service.py` 种入「数据结构期中冲刺」目标与「二叉树遍历」卡点，首屏主 CTA 是「解开卡点」，无任何「示例体验」标识 | 全部新访客（第一屏即虚假状态）；违背 FIRST_3_MINUTES.md「我目前确认的目标」诚实原则与 Example Mode 标识要求；同时违反卡片红线「不得用 mock/seed 冒充真实行为」（产品行为层面） | **砍**：guest 首屏不再自动种完整假目标；要保 demo 就按 FIRST_3_MINUTES Example Mode 加持续「示例体验」标识 + 一键「用我的目标开始」 | `screenshots/own_goal/PX1/03-dashboard-guest-first-screen.png`；run2/3/6 PX1-PX5 `seeded_goal_visible=true, declared_example_marker=false`；`backend/app/services/guest_seed_service.py:1854-1859`；触发点 `backend/app/api/v1/auth.py:978-1002` |
| O2 | **Guest 的 own-goal 入口被种子数据堵死**：`先定下你的第一个目标` CTA 只在 cockpit noGoal 态出现；guest 有种入目标 → 永远见不到 → 目标创建向导对 guest 全程不可达 | 摩擦最低的 guest 路线用户完全无法表达 own goal；「告诉 Sparkle 你想完成什么」的核心动作缺失 | **改**：guest 种子若保留，也必须并行暴露「这不是我的目标 → 设定我自己的目标」入口；或 guest 默认 noGoal 态 | run2/3/6 `set_first_goal_cta_visible=false`（6 passes 一致）；`today_cockpit_card.dart:263` 是全库唯一 `/goals/new` 入口 |
| O3 | **UI 注册在 macOS 桌面提交无效且无反馈**：表单可填、协议可勾，点「注册」后无跳转、无校验错误、无 snackbar、`authProvider.error=null`（7 次运行 × 3 种点击策略一致） | 走注册路线的新用户在第一分钟内无法完成注册（若真机上同样存在，则是 P0 注册阻断；自动化与真机差异待人工复核） | **改**：修复提交链路并补失败反馈；在 iOS/Android/真机复测（见 DEFERRED） | run3-7 日志 `J01_FINDING ... register did not reach dashboard`；`TEXTDUMP [after-register-submit]` 13 个文本无错误项；`register_error_markers=[]`、`auth_provider_error=null`；截图 `07b-register-result.png` |
| O4 | **注册 API 拒绝保留域邮箱且报错只有英文原始校验**：`@test.local` 被拒，detail 为 pydantic 原文（"The part after the @-sign is a special-use..."） | 用企业/内网域名邮箱注册的用户直接失败；错误文案不产品化 | **改**：邮箱域策略要么放行要么产品化文案；建议前端预校验 | curl 复现记录（见报告 §方法）；`api_register_status=200`（example.com 可过） |
| O5 | **Example Mode 没有用户入口**：`体验示例/示例体验/tryExample` 全库 0 命中；`demo_guest_mode_enabled` 只被写 false；唯一 demo 体验需编译期 `--dart-define=DEMO_MODE=true`（开发者知识依赖） | 新用户无法「先体验一个示例」就被迫选择 guest（假目标）或注册（O3 阻断） | **砍 or 改**：按 FIRST_3_MINUTES Screen 1 增加 `体验一个示例` 次级 CTA，接 seed example 并带标识 | `grep -rn "体验示例\|tryExample" mobile/lib` = 0 命中；`auth_provider.dart:19,233...`（全为 setBool false）；本卡 example 跑测被迫用 build flag |
| O6 | **splash/登录页文案绑定「期末备考」单一 persona**：splash 副标题「期末一周，星火陪你备考…」、登录页「期末备考提分，AI 陪你把该拿的分拿回来」 | 比赛/科研/作品集/Creator 4 类 Builder（JTBD 5 persona 中 4 个）在第一眼即被文案排除 | **改**：副标题回归「把卡住变成下一步」类的目标中性文案（FIRST_3_MINUTES Screen 1 原案） | `screenshots/own_goal/PX*/02-login.png`；`app_localizations_zh.dart: splashSubtitle / authLoginSubtitle` |
| O7 | **本地状态清理后仍可能自动登录**：secure storage deleteAll + prefs.clear 后冷启动直接进 Dashboard（keychain token 残留路径） | 卸载重装类"全新开始"体验不成立；测量与用户真实换账号场景受影响 | **改**：提供「不是你？切换账号」快捷路径；核查 keychain 生命周期与卸载语义 | run5/6 PX1 `auto_login_after_wipe=true` + `01b-after-logout.png` |
| O8 | **首屏出现无来由的等级/状态数字**：新访客首屏显示 Lv.15、火苗 Lv.15、心境晴朗 | 第一分钟可信度：用户什么都没做却有等级，损害「真实进展」核心价值 | **砍**：新用户等级/状态在无数据时显示空态而非默认数值 | `screenshots/own_goal/PX2/03-dashboard-guest-first-screen.png`（访客体验91f0，Lv.15） |
| O9 | **注册成功路径不落 Dashboard（当前仅 API 证据）**：API 注册 200 返回 token；UI 提交链路在桌面端未走到 provider（O3），成功后路由行为未能实测 | 注册后用户能否直接进入价值面未知 | 与 O3 一并修复后复测 | `api_register_status=200`；`provider_login_to_dashboard=true`（provider 登录后可正常到 Dashboard） |
| O10 | **AI 意图分析对全部目标静默失效（网关 404）**：`POST /goals/analyze-intent` 网关返回 404 route not found（Python 引擎 :8000 上路由存在，返回 401 未认证=已挂载）；客户端 catch 后静默回退 legacy 5 选 1 类型表单。实测 5/5 persona（含考试类 PX4）全部 127-141ms 内回退，无一进入 AI 理解卡 | 所有新用户的「告诉我你想达成什么」旗舰入口死亡：第一分钟的核心 AI 价值（FIRST_3_MINUTES Screen 2「系统能从文本提取」）不可达且用户无感知 | **改（P0）**：网关补 `/goals/analyze-intent` 代理路由；客户端对 disabled 回退至少给一次性提示 | curl：gateway 404 `{"error":"route not found"}` vs engine 401 `Not authenticated`；pass0-4 `intent_outcome=legacy_type_chooser` ×5；`goal_intent_service.dart:20-37`（catch-all 静默回退） |
| O11 | **向导终点创建失败**：走到 confirm 步点「创建」→ 弹「创建失败，请检查目标内容」；同 payload 直接 API `POST /goals/`（307→200）创建成功并返回 first_task_id | 用户走完 5 步表单在最一步失败且无下一步指引；「有价值的第一步」承诺在最后 1 秒破灭 | **改（P0）**：排查客户端创建链路（307 跟随/响应解析）并复测 | pass1-4 `create_failed_marker=true` ×4 + 截图 `13b-create-failed.png`；curl 同 payload 200 创建成功（`"first_task_id":"5f6abae1…"`） |

## 二、必须砍掉的信息（第一屏瘦身清单）

1. 种入的假目标卡（O1）——新用户首屏唯一主位应留给用户自己的目标或 noGoal 态。
2. 无依据的等级数字与状态徽章（O8）。
3. Guest 首屏「解开卡点」主 CTA（属于演示数据剧情，不是用户自己的卡点）。
4. splash/登录页的备考专用文案（O6，换目标中性文案）。
5. Aurora「轻量感知中」横幅在第一屏占位（对零数据新用户无信息量，截图可见）——降级为可折叠或延后出现。

## 三、example vs own-goal 分叉（实测结构）

- **分叉点 1（登录页）**：FIRST_3_MINUTES 目标设计有 Primary「开始我的目标」/ Secondary「体验一个示例」双入口；现状只有「登录/注册 + 以访客身份继续」，无示例入口（O5）。
- **分叉点 2（guest 登录后）**：现状 guest 即被种入演示目标（未声明的 example），own-goal 路线被堵（O1/O2）；目标设计应是 example 与 own-goal 显式二选一。
- **分叉点 3（注册/登录后）**：注册用户（API 建 + provider 登录，无种子）首屏出现 noGoal 态 CTA「先定下你的第一个目标」→ 目标向导（run7 `goal_cta_found=true`）。两条路线的第一屏内容完全不同且用户不可见地被 guest 种子决定。

## 四、Wizard（own-goal 向导）实测数据

见 `REPORT.md` §计时表（UI 注册/登录不可自动化后的 instrumented 登录已在数据中标注 `provider_login_to_dashboard=true`；向导内 intent 分析、步骤、创建计时来自真实后端交互）。

## 五、DEFERRED（如实）

- 真机（iOS/Android）复测：本环境无移动设备，全部结论来自 macOS 桌面集成测试真实渲染路径；触摸/键盘差异未覆盖。
- O3 的真机归因：自动化 tap 无效是否同样发生在人手操作，需一次人工验证。
- 录像：环境无录屏，以截图序列替代（每 pass 9-15 张）。
- persona.py「10 persona」差异说明：实际文件为 3 arc（stalled/deadline/completion）种子总体生成器，非 10 个命名 persona；本卡以 USER_SEGMENTS_AND_JTBD 的 5 Builder persona 为权威抽 5 个，arc 映射记录于报告。
