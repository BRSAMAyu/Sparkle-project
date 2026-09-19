# 多端实测报告索引

| 报告 | 平台 | 状态 |
|---|---|---|
| [web-round1.md](web-round1.md) | Web（Chrome 1280×720，debug 构建） | ✅ 已完成：后端链路全通实证；发现 W-1..W-8（游客会话断链/空凭据 200/语义残缺等），修复顺序已列 |
| macos-round1.md | macOS | 🔄 进行中（wt4 agent） |
| [android-round1.md](android-round1.md) | Android 模拟器（无头，1080×2400） | ✅ 已完成（三度合轮）：游客模式入口/种子/各 Tab 实证；A-1 注册用户登录 500 已修复（红绿）；A-2..A-11 待修（游客聊天卡队列/建模聊三连坏/Profile type-cast/溢出条纹等）；ANR 定性=资源饥饿非应用缺陷 |
| [android-round2-verification.md](android-round2-verification.md) | Android 模拟器（无头，1080×2400） | ✅ 已完成（修复复验轮，验 main@37edc68d）：A-2/1/4/7 PASS、A-5 PARTIAL（离线组合态 5px 条纹）、A-6 PARTIAL（代码级确认但 UI 无入口）；0 项修复失效；新发现 N-1/N-3..N-7（含疑似跨账号本地缓存泄漏 N-4、community-accountability 对新客 500 N-5）；含 Gradle/JDK/exFAT 构建排障记录 |
| [ai-functions-real-eval.md](ai-functions-real-eval.md) | 引擎 LLM 路径（WS/API/直调，DeepSeek 真接入） | ✅ 已完成（@aabc7f1e）：7 路径 12 测点，8 通/2 半通/2 断；P1=plan 创建 500（advisory lock SQL）阻断 LLM 计划链；P2=reason 档 0 次触达 v4-pro（首答强制 fast）、推送文案 JSON 解析失败静默塌陷；A-3 定性=已修复、残留 TTFB 长尾 |
| [exam-system-eval.md](exam-system-eval.md) | 测试系统（exam-sprint/诊断/错题本，游客+注册双身份 API 实测） | ✅ 已完成（@164a1cd6）：exam-sprint 全端点 12/12 形态正确、判分受控验证 100%；闭环半成立（判分→画像→dashboard 通，galaxy 掌握度/成长值/spine 三段断）；P1×5=错题本网关 gRPC 桥 401（App 全功能不可用）/游客种子场景 422+dashboard 不激活/掌握度写库静默丢弃/grading_payload 答案下发+文本作答判 0/移动端无诊断入口；题目质量 3 题人工 9/9/9（模板题非 LLM，0 解析） |
| [deep-analysis-qwen-eval.md](deep-analysis-qwen-eval.md) | 引擎 deep_analysis 新栈复验（qwen3.8-flash 全 tier，WS 真调 7 条） | ✅ 已完成（@91f8f1cd）：F-1 深度档真实路由 MAX ✅、d859c194 execution_review 无崩溃且 create_plan 真建 plan ✅、max 档 TTFT 15-28s（中位 22s，无 M-2 式尾暴）；P1=reviewer 仍路由退役 deepseek-v4-pro（4/4 失败，每轮 +12s）；P2=免费层钳制对强制 max 主生成不生效（组合缺口）+ 游客种子 flame=15 实为 is_pro |
| [daily-flow-eval.md](daily-flow-eval.md) | 用户每日流程三日连测（注册账号 API/WS 全旅程，DB 回拨日切） | ✅ 已完成（@32d2ebe3）：3 日 36 步 24 通/5 半/7 断；跨日影响成立 5 项（streak/驾驶舱/问候带上文 ✅，星图成长/错因个性化/推送 ⛔）；P1×5=反思提交 3 日 3 败（含 2 次"已入库假失败"）/聊天回复 0 落库+会话表空/回复被"计划中断+内容审查"噪声污染/诊断做题冷启动 422/星图 3 天 0 变化；LLM 显式 4 次 |
| [daily-flow-eval-r2.md](daily-flow-eval-r2.md) | 每日流二轮：9957f42d 修复批复验（同法三日连测对照首轮） | ✅ 已完成（@d4338948）：修复 3 全绿（反思 200 入库/诊断 422 可行动/聊天真流式+落库可查）+1 达标带回归（星图 0→4 星 105min，但 complete 端点 5/5 必 500=P1-A outbox SQL）+1 半通（推送默认开/全量评估生效，偏好行用户 tz 崩溃仍 0 通知=P1-B）；36 格 24→26 通、跨日 5/10→8/10；新 P1×3/P2×7 只记录不修 |

截图存档：`/Users/brsama/code/GitHub/Sparkle-sysrev/screenshots/{web,macos,android}/`（不入库）

另：主仓根 `.fieldtest-shots/`（round1–round4 真机原始截图，约 32M）为 FieldTest 实测本地证据存档，被 android-round1/round2 及 B-05 回执按相对路径引用，已加入 .gitignore 永不入库。
