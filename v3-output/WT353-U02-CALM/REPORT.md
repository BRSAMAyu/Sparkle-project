# WT353-U02-CALM · 交付报告

- **卡**：U-02 · Calm/Warm 设计语言与低刺激模式落地（Stream UX / Gate V3-4 / medium / HEAVY）
- **Worker**：wt353 · 2026-09-25
- **状态**：**READY_FOR_REVIEW**（测试执行与截图证据两项 DEFERRED，见 §5）
- **base SHA**：`f9f0ae7a`（main）
- **final SHA**：本分支 HEAD（交付 commit + 本报告 commit）
- **分支**：`wt353-u02-calm`（worktree wt353-u02-calm）

## 1. 交付内容（6 改 2 增，128+/8-，外科手术式）

| 文件 | 改动 |
| --- | --- |
| `mobile/lib/core/design/tokens_v2/state_tokens.dart`（新） | calm/celebrate/attention 三态令牌 × standard/low 两档装饰预算（glowOpacity/emphasisScale/motionScale/particleScale/allowBounce），全数值令牌、零新颜色魔法值 |
| `mobile/lib/core/design/theme/sparkle_theme_extension.dart` | `StimulationLevel` 枚举 + `resolveSparkleMotionTokens` 两档动效真源 + 扩展档位字段（默认 standard=默认关），copyWith 档位切换即重解析 motion |
| `mobile/lib/core/design/theme/sparkle_context_extension.dart` | `context.stimulationLevel / lowStimulation / stateTokens(mood)` 消费访问面 |
| `mobile/lib/core/design/adaptive/emotion_responsive_theme.dart` | `applyToTheme` 低刺激时把已注册 `SparkleThemeExtension` 换到 low 档（Theme 层真实接线） |
| `mobile/lib/core/design/widgets/sparkle_confetti.dart` | 庆祝刺激整体短路：补齐声效/触感/控制器抑制（此前仅视觉抑制）；首播移 post-frame 防漏发；播放中切换即时停 |
| `mobile/lib/core/navigation/sparkle_route_transition.dart` | `sparkleTransitionCalm` 谓词合并系统档 + in-app 半边（MediaQuery.disableAnimations，N33 同源），两个转场 builder 接入——Galaxy 独立视觉保持、转场一致衰减 |
| `mobile/lib/core/design/design_system.dart` | 一行导出 state_tokens |
| `mobile/test/core/design/calm_low_stimulation_test.dart`（新） | 9 用例钉住两档真实差异（见 §3） |

## 2. 卡面逐条对账

- **Work1 calm/celebrate/attention 状态 token**：§1 state_tokens.dart；装饰竞争减法经预算令牌表达（celebrate low 档粒子 0、发光 0.16→0.08），不重建既有颜色真源（SparkleColors 未动）。
- **Work2 接入真实 Theme/Animation/Gamification**：Theme=applyToTheme 换档；Animation=resolver 两档输出 + copyWith 重解析；Gamification=SparkleConfetti（挑战性庆祝元素）整体短路 + achievement 系既有 `hideChallengeBadges` 门不变。**不是空设置值**：测试断言 `context.motion.normal` 250ms→150ms、celebrate glow 0.16→0.08、confetti 粒子预算 20→0。
- **Work3 Galaxy 转场一致**：galaxy_routes 三处均用 `buildSparkleTransitionPage`，其 builder 现按 in-app 档进平静渲染；Galaxy dark cosmic 主题未动。
- **开关进 settings 默认关**：复用既有真源不另建——统一设置→情绪自适应（auto/alwaysLow/alwaysNormal，**默认 auto=普通档**）与无障碍 reduceMotion，经 app.dart 既有 MediaQuery 叠加律到达全部消费点。加第二开关=重建真源，Forbidden。

## 3. 验收对账

- **验收1 普通/低刺激核心截图过 contrast/hierarchy rubric**：**DEFERRED**——内存门禁模拟器（本卡 HEAVY 的截图腿不可跑，见 §5）；替代性证据：低刺激 Theme 变换全部经令牌（无新颜色），对比度由既有 surface ladder 机检（`check_surface_ladder_de.py`）覆盖，档位切换不触碰颜色真源。
- **验收2 低刺激实际减少动效/挑战元素**：**测试钉住**（§3 用例清单）；执行 DEFERRED。

## 4. 测试清单（`mobile/test/core/design/calm_low_stimulation_test.dart`）

1. resolver standard 档=既有默认（150/250/400/600ms、elasticOut/easeOutBack）
2. resolver low 档时长严格更短 + 弹性/过冲撤除 + 语义曲线不变
3. celebrate 两档：low 粒子 0/弹性 false/时长收缩/发光更低
4. attention low 档：发光保正（不减到看不见）、粒子 0
5. calm 本征低装饰两档一致
6. Theme 接线·普通档：`context.motion.normal`=250ms、lowStimulation=false
7. Theme 接线·低刺激档：同消费点 150ms、glow 0.08（核心可测断言）
8. `sparkleTransitionCalm` in-app disableAnimations=true→平静档；false→全动效档
9. SparkleConfetti 低刺激：ConfettiWidget 不挂载、粒子预算 0；普通档：挂载、预算 20

## 5. DEFERRED 与理由（协议明文路径）

- **定向 flutter test**：本会话实测 swap free 703M→338M，始终 <1.2G 启动门，按 §4 协议第 3 条不执行、代码+测试照常交付。测试编译正确性已由 `flutter analyze` 背书（E0，测试文件零 error/warning）。
- **模拟器截图**：同内存纪律禁模拟器；建议 reviewer 在内存窗口期补跑 `flutter test test/core/design/calm_low_stimulation_test.dart --concurrency=1` 与截图 rubric。

## 6. 门禁与卫生

- 守卫：`run_all_rule_guards.sh` **83/83 exit 0**
- flutter analyze：**E0 / W15 / I587**，与基线（wt350 后）持平零推高（中途 +1E/+2I 均当轮修清；pub get 触发的 l10n 生成噪声已回退）
- mypy：零 backend 改动，天然 1278 持平
- diff 卫生：dart format 对既有行的重排已全部回退重放，最终 diff 只含本卡语义改动
- 战区：core/design 面广而浅——6 消费点全部是"令牌扩展+消费点切换"形态，零 feature 布局/逻辑深改；与在航（mypy/守卫/WVPL/猎缺）零交叠

## 7. 风险与交接

- `SparkleThemeExtension.copyWith` 的 motion 重解析：显式传 motion 时以显式值为准，未发现既有调用传自定义 motion（全库仅 design_system 默认构造）。
- 冷启动 `cold_start_motion.dart` 仍直读 platformDispatcher（N20 保护域，本卡不动）；in-app 低刺激对冷启动窗不生效，如需覆盖走后续卡。
- Reviewer 独立验收建议：跑 §4 测试 + `git diff main...wt353-u02-calm -- mobile/lib` 复核"无 feature 深改"。
