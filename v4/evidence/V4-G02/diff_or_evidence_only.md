# V4-G02 · 对话/卡住/Hybrid/运行台——四风格商业化完备（diff 叙证）

分支 `agent/v4/g02`（worktree wtG02）：交付头 `96f8d1bb`（= 主提交 `b3eeac17` 65 文件 + 走查回环修正 2 文件）。**纯呈现层**：chat_provider / 滚动物理 / F566 语义零 diff；l10n 零改动。

## 0. 断点续跑盘点（前任 34 dirty 全保留）

前任 agent 宿主机重启阵亡，遗留未提交改动 34 项（33 lib + 1 新测）。本会话逐文件 diff 盘点后全量继承：

- `design_system.dart`：`textTertiary` 停止 `textSecondary@0.6` 透明度派生（SPEC §1.3.1 第四文字级禁令）→ 转发 B2-3a 定标槽（值源唯一 tokens_v2/theme_manager.dart）；新增 `DS.toneOnTint` 收敛槽（浅档 tone 向 textPrimary 收敛 12% → classic tone@tint 面 4.30-4.48:1 提至 ≥4.9:1；深档 tone 亮色恒等返回）。
- 流式气泡（chat_screen `_StreamingBubble`）：**G02-D1** 码面去亮度分叉（旧深档 neutral700 亮灰绿叠浅墨四档塌至 1.13-1.94:1）→ 与落定同源 surfaceTertiary；**G02-D2** 描边统一主题槽。附 reduce-motion 静态分支（光标静态块）。
- 家族 30 文件字号令牌化（10/11/11.5/12.5/13 → `DS.fontSizeXs`，约 90 处）；透明度压文字 5 处改离散槽（textTertiary/textDisabled）；classic-only 字面量退役：前门卡 E8F5EF/B5DDC8 → semanticSuccess@10/32%、7C3AED/F2EAFE → taskReflection@8%、action_card 0EA5A4/4F46E5 → info/primaryBase、专家圆桌 F7F9FC/D8E1EF → surfacePanel/borderSubtle、openclaw Colors.white@0.5 → surfacePrimary@0.5。
- `toneOnTint` 落地：状态行 StatusPill/TimeContext/TaskHealth/CorrectionEffect/CorrectionChip/Band 族、Hybrid _StatusLabel、前门 _Badge、openclaw 三 primitives、 accessory pill 选中态。
- 新测 `v4_g02_family_contrast_guard_test.dart`（四档×家族关键配对 WCAG 复算 + 透明度压文字禁令源扫描）——遗留 2 info + classic 7 配对红，本会话闭合。

## 1. 本会话缺陷闭环（缺陷清单）

| id | 缺陷 | 修法 | 验证 |
|----|------|------|------|
| G02-D3（新修） | 卡住 QuietChip 描边 borderSubtle 对胶囊面 classic 1.22:1（<非文字关键部件阈 3.0）；递进 neutral300=1.29 / neutralOutline=2.26 / neutral500=2.85 均不足——胶囊面与卡面同源，描边是唯一辨识边界 | 升 neutral600（classic 5.18:1） | 守卫四档达阈 + golden 语义钉（border==DS.neutral600） |
| G02-D4（新修） | 家族 9 处无条件 `repeat()` 动画不尊重 reduce-motion：_ShimmerDot、action_card、plan_review_card、avatar_stack、avatar_switcher、collaboration_timeline、regeneration_prompt、review_appeal_card、aurora 打字点 | 全部静态终态降级（S01 判例：不装动画壳；恢复正常重挂）；起表收敛单调用点保 DL-SPEC persistentRepeatLoop 棘轮（56→53 只降） | 活钉（reduce-motion 下 pumpAndSettle，修前必超时）+ 控制组（正常模式脉动可观测） |
| G02-D5（回环自纠） | 初版 _ShimmerDot 静态分支渲染四点列（组件即单点槽，外层 _ShimmerRow 负责排布 → 16 点视觉 bug）；aurora 打字点双路径重复 padding | 单静态点 / 单渲染路径（停表+相位冻结 0.0 → 三点全 0.2） | SPACING-RHYTHM 棘轮回 PASS；54/54 受影响测全绿 |
| 测试配对同步 | 守卫按「原始 tone」计算而 widget 已走 toneOnTint（Band 胶囊/Hybrid 错误徽章/前门徽章 4.30-4.48:1 假红） | 守卫配对改为出厂口径 `DS.toneOnTint(tone)`（守卫钉的是 DS 层派生达阈，非恒真：弱化收敛槽即红） | 守卫 5/5 |
| 遗留清理 | 前任新测 2 处冗余 import info | 删除 | analyze 零 |

行为面登记（不顺手修）：collaboration_timeline `_buildTimelineNode` 引用外层 `isLast` getter（恒 false，连接线不渲染）——既有行为语义问题，超本卡风格面，留行为卡裁决。

## 2. 四风格验收面（卡面验收 1-3 对应）

- **验收 1（零风格专属缺陷）**：对比度守卫四档 × 家族真实配对（对话气泡/流式·落定码块/跳最新胶囊/Aurora 状态行五胶囊族/Hybrid 横幅与错误徽章/卡住正文与 QuietChip/前门确认区与预测徽章/运行台 tone 胶囊族 4 tone×2 文本槽 + 描边）全部 ≥4.5:1（描边 ≥3.0）；透明度压文字禁令源扫描三呈现根目录零命中。
- **验收 2（每风格 golden+语义钉，CI 可失败）**：`v4_g02_family_golden_semantic_test.dart` 27 测——组件面（真实 TaskStuckCard + OpenClaw primitives）×4 档 golden + 语义钉（三段层级在场、QuietChip 描边槽、toneOnTint 槽四档各有断言、白面字面量零命中）；真实 ChatScreen 四态（content/empty/streaming/model-failure）×4 档 golden + 结构钉；200% 文本钉；reduce-motion 活钉+控制组。25 张确定性 golden（macOS 签发；Linux 像素断言跳过、语义钉全平台，wt296 判例）。
- **验收 3（既有功能全绿+analyze 零+棘轮只降不升）**：回归 7 批全绿（329/348+3skip/286/527+4skip/54/21/5），analyze 零，UI-TOKENS（213/275、557/727）、DL-SPEC（persistentRepeatLoop 56→53）、SPACING-RHYTHM（1590/1623）三棘轮基线只降。

## 3. 特有风险逐项结论

- **流式增量在 quiet/dusk 对比衰减**：量化根因 = 深档码面 neutral700（quiet 1.13 / dusk 1.55 / paperDay 1.13 / classic-dark 1.94:1）；G02-D1 修正后流式与落定同源 surfaceTertiary，四档 8.33-14.04:1（最低值为阈 1.85 倍），流式/落定差 ≤1.07:1。数值表见 test_results.json `streaming_contrast_probe`。
- **状态行辨识度**：五胶囊族全走 toneOnTint 收敛槽（classic 4.30-4.35:1 → ≥4.9:1，色相保持可辨）；字号 11 → DS.fontSizeXs 统一。
- **卡住 sheet 三段层级**：真实 TaskStuckCard 语义钉（陈述文案 → 任务胶囊 Wrap → 动作按钮三段在场）；J-05 旗舰 sheet（stuck_journey_sheet：单问 → 提案卡 → 照做/纠正）为 FIX-569/U02 已验收承载面，本卡核其呈现零令牌外颜色，不重做行为验收。
- **胶囊与 OVERLAY-SMALL 让位几何**：跳最新胶囊 `bottom: dockFloatsOverMessages ? DS.spacing64 : DS.spacing12`——DS 间距常量四档恒等（几何随 profile 天然一致），由既有 f566 测试钉行为、本卡对比度守卫钉其面（surfaceOverlay 合成胶囊面 textSecondary ≥4.5）。

## 4. 15 态覆盖口径

本卡可 widget 级复现态：默认（content face）、空（empty face）、加载（streaming/typing 呈现 + reduce-motion 活钉）、模型失败（failure face，横幅+重试语义钉）、200% 字体（content_classic_200 golden+钉）、减少动态（9 处降级+活钉）、部分内容（streaming face「不伪装完成态」钉）。离线（连接态横幅）由 f566/既有 chat 测覆盖；恢复/取消/未知写入/过期版本/权限失效/键盘遮挡/深链返回为 screen 级行为态，属行为卡与 Q05 三端截图矩阵口径（见 limitations）。
