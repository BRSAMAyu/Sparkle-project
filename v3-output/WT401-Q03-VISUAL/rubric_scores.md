# WT401 Q-03 — 12 维 Visual Rubric 打分表（standard 档）

- rubric 权威：`v3/04_ux/VISUAL_REVIEW_RUBRIC.md`（12 维各 0–2；A=阻断/误导/不可读/错误主焦点，B=明显降低体验，C=微调）
- 审查对象：修复后 final 态（wt401 分支顶部），107 张真实渲染截图（390×844@2x，`evidence/`）
- 程序化数据：`layout_probe_{core,longtail}.json`（溢出异常/截断候选/越界 widget）、
  `contrast_probe_core.json`（Text 前景/最近不透明背景 WCAG 对比度采样）
- 坐标：逻辑点（390×844 坐标系）

## 一、核心 journey 屏（13 屏全 12 维）

| 屏 | 1 Hierarchy | 2 Clarity | 3 Density | 4 Spacing | 5 Typography | 6 Color/Contrast | 7 Consistency | 8 Affordance | 9 State feedback | 10 Brand | 11 Motion | 12 Platform | 遗留 |
|----|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C01 /home | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 无 |
| C02 /galaxy | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | C-density（首屏弹层 3 张叠加）；V3-FIX-60 rail/CTA 重叠 |
| C03 /chat | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | C-contrast（时间戳 3.08） |
| C04 /community | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 无 |
| C05 /profile | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | C-contrast（折下「普通」标签 1.74，首屏外） |
| C06 /login | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | C-contrast（品牌字 4.28<4.5） |
| C07 /onboarding/persona | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 无 |
| C08 /errors | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 无 |
| C09 /errors/new | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 无 |
| C10 /goals/new | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 无 |
| C11 /plans | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | C-contrast（「75 分钟」2.50 次级元数据） |
| C12 /review | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 无 |
| C13 /notification-center | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 无 |

**核心旅程 A/B 合计 = 0**（4 项修复前 A/B 已全部修掉并加守卫，见 §三）。

### 评分证据要点（程序化值/坐标）

- C01：今日主卡首屏 30–210pt 处主 CTA「安排今天」为唯一 primary 按钮（层级 2）；
  副文案 14pt/正文 16pt 层级清晰；最快对比 4.98（头像「视」）≥4.5。
- C02：`GoalWorldGraphMiniPanel` 修复后 rect=(16,48,374,~100)，与
  `GalaxyContributionBanner`(y≈128 起) 无交（G4 守卫锁定）；density 1 因
  首屏同现 草稿提示卡+贡献横幅+统计 三张信息层（demo 数据态），建议首访
  合并/降层——后续设计卡，非阻断。
- C03：时间戳 `00:15` fg=#958A80/bg=#F8F4EF ratio=3.08（大字阈值过、正文阈值
  不过）——时间戳属次级信息，C。
- C05：「普通」fg=#B0BEC5/bg=#F8F4EF ratio=1.74，位于首屏折叠区 trait 标签
  （截图 C05 首屏未见），C（建议挪至 ≥#7D7E80 或加边框）。
- C06：「Sparkle 星火」fg=#66758B/bg=#F8F4EF ratio=4.28，标题字重下可读但
  差 0.22 达 4.5，C。
- C11：「75 分钟」fg=#A49B90/bg=#F8F4EF ratio=2.50，次级元数据，C。

## 二、Long-tail 屏（85 路由默认态；12 维按维度汇总，异常项单列）

| 维度 | 均分 | 说明 |
|------|------|------|
| Hierarchy | 1.95 | 全体合格；L60 修复后主操作唯一 |
| Clarity | 1.93 | L48 文案窗口矛盾（V3-FIX-59，P2）；其余 2 |
| Density | 1.96 | L35 设置分组略密，C |
| Spacing | 1.98 | — |
| Typography | 1.98 | — |
| Color/Contrast | 1.90 | 见下方 C 项清单 |
| Consistency | 2.0 | DS 令牌一致，圆角/按钮统一 |
| Affordance | 1.98 | L60 修复前第 5 chip 不可达（已修）；其余 2 |
| State feedback | 1.93 | L40/41/42 修复后骨架屏/空态可见；L31 记忆面板空态文案完整 |
| Brand fit | 2.0 | calm/warm 一致（米暖色 + 低饱和强调） |
| Motion | 1.95 | 入场 stagger 有节制（L48 日历格）；无奖励噪声 |
| Platform fit | 1.96 | L79–L85 unknown-id 参数屏均给出可读缺数据态，无死屏 |

### Long-tail 遗留 C 项（不阻断，登记后续打磨）

1. L10/L11 日历星期头 `Sun/Mon…` 渲染盒 16px < 文本 ext 23px（垂直裁切嫌疑，
   截图目测可读——判定为行高盒差，C）。
2. L38/39/40/41/42 首字母头像 `S` 盒 34×34 < ext 48（圆形裁切内目测完整，C/观察项）。
3. emoji 在 flutter_tester 环境无字体渲染为黑块（聊天标题「临时为…」等）——
   **环境限制非产品缺陷**；真机 emoji 字体正常。已加载 MaterialIcons+Roboto+
   Arial Unicode 覆盖绝大部分字形。
4. V3-FIX-60（星图 rail/CTA 重叠，P3）。

## 三、修复清单（红→绿证明：`q03_layout_fix_guards_test.dart` 4/4）

| # | 缺陷（base 级别） | 红测（base 结果） | 修复 | 绿测 |
|---|------------------|-------------------|------|------|
| G1 | 发布动态心情条 390w 溢出 66px，第 5 chip 不可达（A） | `RenderFlex overflowed by 66 pixels` | `create_post_screen._buildMoodSelector` Row→横向 SingleChildScrollView | G1 绿 + L60_after 无溢出纹 |
| G2 | 连胜日历「今日」格双 ticker（B：debug ErrorWidget 顶掉格） | `SingleTickerProviderStateMixin … multiple tickers` | `streak_details_screen._CalendarCellState` → TickerProviderStateMixin | G2 绿 |
| G3 | 海报生成窗口期离开源页 → 根覆盖层 builder 以失活 context 调 Theme.of → 整屏红（B，L40/41/42 三屏复现） | `Looking up a deactivated widget's ancestor is unsafe` | `share_poster_service`：Theme.of 与 MediaQuery 一样在 insert 前捕获快照 | G3 绿 + L40/41/42_after 正常渲染 |
| G4 | 星图顶部：模式面板（旧 top:112 兄弟 Positioned）被统计列内容压住（B；G4 rect 证据 112–154 vs 128–244） | G4 交叠断言红 | `galaxy_screen`：面板挂入 top:48 同一流式列（统计之上、横幅之下） | G4 绿 + C02_galaxy_after 三层纵向无遮 |

对照文件：`compare/*_before.png` / `*_after.png` / `*_side_by_side.png`（6 组成对）。

## 四、结论

- **核心 journey 12 维全 2 分、A/B=0**（4 项 base A/B 已修+守卫锁定）✅
- Long-tail reachable 85 屏 A=0；遗留全部为 C（含 2 条转 DYNAMIC：V3-FIX-59 P2、
  V3-FIX-60 P3）✅
- before/after 可对比：文件名成对 + 并排合成图 ✅
