# D-LANDING · 扫码落地页 + 海报内容 · 交付报告

> Worker：D 线施工 ｜ 2026-09-22 ｜ worktree wt124（基线 main@0e931218，任务卡所写 de2f24c2 的直接后继，树内无漂移冲突）
> 交付物：`deploy/landing/index.html`（落地页）、`deploy/landing/poster-copy.md`（海报文案稿）、`deploy/README.md`（目录登记+部署说明）
> 边界：零产品代码、零 commit/push；联系方式全部占位、真实信息禁止入库；纯静态零构建。

---

## 1. 页面结构清单（index.html）

单文件自包含：`<!doctype html>` + 内联 `<style>` + 语义化 body + 1 个内联 `<script>`。零外链、零构建、离线可开。

| 区块 | 内容 | 规范依据 |
|---|---|---|
| 文件头 CONFIG 注释块 | 全部可配置项说明（apkUrl/wechatQrPath/groupQrPath/logoPath/contact/channelCopy）+ 渠道码 `?src=` 用法 + 色值来源声明 | 任务卡「可配置」；GROWTH_ASSETS §1.2 |
| `header.brand` | 内联 SVG 星标（品牌时刻，唯一 accent 允许面）+ 文字标 | SPEC §1.4.1 |
| `section.hero` | eyebrow chip（AI 学习成长系统，info 槽冷色）+ H1 主叙事「错题本 2.0：从静态收录，到状态引擎」+ 副文案 | DECISIONS H3 附注：方向假设口径，无品类断言 |
| `section` 三特性卡 | **01 记得住（Aurora 断点续学）→ 02 会教（分步+诚实边界）→ 03 星图生长（掌握度点亮）**；每卡带 info 槽 tag | H3 裁决权重排序（资源让位「记得住」）；温度降及格线，**无温度卡** |
| `section#download` 行动区 | S2 浮起面板：主 CTA「下载 Android 安装包（APK）」+ 游客体验指引（免注册直接玩，可转正）+ 现场专码 note（`?src=` 触发，S3 容器）+ 双二维码占位（公众号/交流群） | 游客链路 `/guest`+`/upgrade-guest` 零新开发；漏斗环节④ |
| `footer` | 数据主权句（一键导出与删除）+ 团队/比赛/联系占位 + 法务文档链接占位 | GROWTH_ASSETS §2.1 合规页脚要求 |
| JS（1 个，约 60 行） | CONFIG 应用：APK href 注入、二维码 img 注入、logo 替换、联系方式注入、`?src=` 渠道文案替换；全部留空时页面保持占位态可用 | 零依赖降级安全 |

移动优先：单列布局，`@media (min-width: 45rem)` 升三列卡/双列码；`clamp(30px,7.5vw,46px)` 对齐 displayLarge 档。

## 2. 色值对照表（web 值 ← theme_manager.dart `SparkleColors.light()` normal palette）

| Web 令牌 | 值 | Dart token（theme_manager.dart） | 页面用途 | SPEC §1 依据 |
|---|---|---|---|---|
| `--surface-ambient` | `#FCF8F3` | `surfaceAmbient`（0xFFFCF8F3） | S0 页面画布 | §1.2 表面阶 |
| `--surface-primary` | `#F8F4EF` | `surfacePrimary`（0xFFF8F4EF） | S1 特性卡/QR 卡/chip 底 | §1.2 |
| `--surface-secondary` | `#F1EBE4` | `surfaceSecondary`（0xFFF1EBE4） | S2 行动区浮起面 | §1.2 |
| `--surface-tertiary` | `#E7DED4` | `surfaceTertiary`（0xFFE7DED4） | S3 现场专码容器/QR 内框 | §1.2 |
| `--text-primary` | `#171717` | `textPrimary` | 标题/正文主体 | §1.3 |
| `--text-secondary` | `#6C655D` | `textSecondary` | 副文案/卡片正文/S2 面小字 | §1.3 |
| `--text-tertiary` | `#736F62` | `textTertiary`（B2-3a 定标） | 页脚/占位小字（仅用于 S0/S1 面） | §1.3 |
| `--accent` | `#825D49` | `brandPrimary`（0xFF825D49） | **唯一交互色**：CTA 按钮/星标品牌时刻/焦点环 | §1.4.1 |
| `--info` | `#48678D` | `semanticInfo`（0xFF48678D） | AI 信息唯一冷色槽：chip/AI tag（「系统在说话」） | §1.5 冷色准入 |
| `--border` | `#DED5CB` | `neutral300`（light border 派生） | hairline 描边/虚线占位框 | §1.2.3 |
| `--accent-ink` | `#FCF8F3` | 复用 `surfaceAmbient` 值 | CTA 按钮上的文字 | 对比度复算 5.50:1 |

层级纪律执行：卡与底区分靠色阶（S0→S1→S2→S3），无 box-shadow；唯一 accent 不兼做正文强调；冷色仅经 info 槽出现（判定口诀通过：两处冷色都在替系统说话）。零常驻动画（仅 `:active` 即时位移反馈 + reduced-motion 抑制规则兜底）。

## 3. 文案稿摘要（poster-copy.md）

- **主标语 3 选**：①「错题本 2.0：从静态收录，到状态引擎」（**推荐**，与参赛叙事逐字对齐）②「它记得你每一次卡住，也看见你每一次长进」（情感面，标注与温度纪律的张力慎用）③「学过的不会白学，星火把它点亮成星图」（星图视觉联动）。
- **副标**：「AI 学习成长系统：分步教、记得住、知识星图随学习生长。」
- **三特性**（顺序即权重，勿倒）：记得住 / 会教 / 星图生长，各一句短文案；明确注明不加温度类第四条。
- **二维码引导语**：主钩子「**扫码即玩，免注册**」+ 操作链小字「扫码 → 下载 APK → 打开点『游客体验』」+ 现场专码版文案；附合规注（免注册指游客链路，不夸大为免下载）。
- **版式建议**：A2 竖版三段式 ASCII 示意（顶标语/中星图视觉+三特性/底码+钩子），含色值、码尺寸（≥12cm）、字号下限、截图纪律（只用星图画面——AUDIT S1-S3 未修复罪状截图禁上海报）。
- **占位清单**：团队/比赛/二维码成品/主视觉四项 checkbox，禁止入库真实信息。

## 4. 验证结果

| # | 项目 | 方法 | 结果 |
|---|---|---|---|
| 1 | HTML 结构闭合 | python `html.parser` 配平（剥注释/script 后）：未闭合 0、错配 0、重复 id 0；语义标签 `html[lang]`/`viewport`/`main`/`header`/`footer`/`section`/`h1` 齐备 | **PASS** |
| 2 | 外链依赖 | 正则扫 `src=`/`href=`/`<link`/`@import`/`url(`（剥注释）：外部引用 **0**；内联 `<style>`×1 + `<script>`×1 | **PASS**（离线可开） |
| 3 | 对比度复算（WCAG 相对亮度公式） | textPrimary/S0 16.95:1；textSecondary/S0 5.43:1；textTertiary/S1 4.59:1；textSecondary/S2(btn-note) 4.85:1；accent 文字对 5.50:1；info/S1 5.33:1 —— 全 ≥4.5:1 | **PASS**（tertiary 只用在 S0/S1 面，S2 面已改 secondary） |
| 4 | 色值对照 | 页面全部 hex ∈ SparkleColors.light() 10 值集合（见 §2 表），无令牌外色值 | **PASS** |
| 5 | 零常驻动画 | 无 `@keyframes`/`animation` 声明；唯一命中为 `prefers-reduced-motion` 抑制规则 | **PASS** |
| 6 | 叙事合规 | 全文无「品类空位/无人/唯一」断言；主叙事为「错题本 2.0」方向表述 | **PASS**（DECISIONS H3 附注） |
| 7 | patch 完整性 | `git apply --reverse --check` 通过（见收工核查） | **PASS** |

未做：Lighthouse 实测（需要浏览器实例，按内存纪律从省）；基本面已人工对齐（viewport/meta description/语义标签/无阻塞资源——样式脚本全内联即无 render-blocking 外链）。

## 5. 收工核查

- [x] 产物仅在 wt124 内：`deploy/landing/index.html`、`deploy/landing/poster-copy.md`、`deploy/README.md`、`v3-output/D-LANDING/{REPORT.md,changes.patch}`
- [x] 零产品代码改动（`backend/`、`mobile/`、`proto/`、`gateway` 未触碰）
- [x] 无真实联系方式/URL 入库（CONFIG 与页脚全占位，示例域名仅以 `<你的域名>` 形式出现在注释）
- [x] 纯静态零构建：无 package.json/构建脚本/外部字体
- [x] `/tmp/dlanding_validate.py` 验证脚本已删（见下）
- [x] 未 commit/push；patch 以 `git add -N` + `git diff` 生成后还原 index，工作树回到 untracked 原状
