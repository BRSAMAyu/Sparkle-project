# 多端实测报告索引

| 报告 | 平台 | 状态 |
|---|---|---|
| [web-round1.md](web-round1.md) | Web（Chrome 1280×720，debug 构建） | ✅ 已完成：后端链路全通实证；发现 W-1..W-8（游客会话断链/空凭据 200/语义残缺等），修复顺序已列 |
| macos-round1.md | macOS | 🔄 进行中（wt4 agent） |
| [android-round1.md](android-round1.md) | Android 模拟器（无头，1080×2400） | ✅ 已完成（三度合轮）：游客模式入口/种子/各 Tab 实证；A-1 注册用户登录 500 已修复（红绿）；A-2..A-11 待修（游客聊天卡队列/建模聊三连坏/Profile type-cast/溢出条纹等）；ANR 定性=资源饥饿非应用缺陷 |
| [android-round2-verification.md](android-round2-verification.md) | Android 模拟器（无头，1080×2400） | ✅ 已完成（修复复验轮，验 main@37edc68d）：A-2/1/4/7 PASS、A-5 PARTIAL（离线组合态 5px 条纹）、A-6 PARTIAL（代码级确认但 UI 无入口）；0 项修复失效；新发现 N-1/N-3..N-7（含疑似跨账号本地缓存泄漏 N-4、community-accountability 对新客 500 N-5）；含 Gradle/JDK/exFAT 构建排障记录 |

截图存档：`/Users/brsama/code/GitHub/Sparkle-sysrev/screenshots/{web,macos,android}/`（不入库）
