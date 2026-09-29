# V4-G03 diff_or_evidence_only — 记忆/Aurora/我的理解家族四风格商业化完备

分支 `agent/v4/g03`（worktree wtG03，自 main `9369f0e5` 开出）。**断点续跑卡**：前任 agent 因宿主机强制重启阵亡，dirty=19 未提交改动经 `git status` 盘点后全部继承续跑，零丢弃。本页按「缺陷清单（含前任已修标注）→ 辨识度专项 → 令牌化清零 → l10n 增量 → 测试与棘轮」组织。

## 1. 缺陷清单（对比度四风格复算，205 组合量化）

复算工具：`contrast_recompute_g03.py`（WCAG 2.1 相对亮度，五档口径 = classic-light/classic-dark/paperDay/dusk/quiet；文本门 4.5:1、图形门 3:1、字号门 12sp）。**[前任已修]** = 阵亡前已落盘、本次盘点确认并保留；**[续跑修复]** = 本次走查新发现并修复。

### 1a. 前任已修（dirty=19 盘点确认，全档复算达标）

| # | 面 | 缺陷 | 修法 | 修后 |
|---|---|---|---|---|
| P1 | semantic_pill（memory 面徽章基座） | tone 色 12sp 对 0.10 tint 合成底 classic 两档 4.26–4.45:1 | alpha 0.10→0.05 | 全档×card/panel/secondary ≥4.51 **[前任已修]** |
| P2 | aurora_calibration_strip | 4 处硬编码中文 + confidence 徽章 0.12 tint（classic-dark 4.11:1） | l10n 化 + tint 0.06 | ≥4.50 **[前任已修]** |
| P3 | aurora_core_session_sheet typing dots | OS 减动效下仍播循环闪烁 | build 内 stop 静态三点 | 等价 **[前任已修，本次重构为 didChangeDependencies 首帧前门控——前任方案首帧仍闪，见 R6]** |
| P4 | capsule_detail 反馈 chips | 选中态 0.12 tint 对 12sp brandPrimary 4.06–4.22:1 | tint 0.05 + 实色描边承担辨识度 | ≥4.52 **[前任已修]** |
| P5 | capsule_jobs 状态/生成/错误/chips 族 | 状态色 12sp 3.61–4.16:1；dark 侧 neutral700 浅灰底多处 <2.5:1；错误正文 error 色 3.6:1 | 标签 textPrimary + dark 侧 surfaceTertiary + tint 0.06 | 文本 ≥4.5/图形 ≥3.4 **[前任已修]** |
| P6 | pattern_list 类型标签/类型色 | prismPurple（退役别名槽 brandSecondary）图标 classic-light 玻璃面 2.72:1；彩色 12sp 标签 4.32:1 | taskReflection 语义槽（B2-3a）+ 标签 textSecondary | 图标 ≥4.3/文字 ≥4.8 **[前任已修]** |
| P7 | interactive_decay_timeline / prism_behavior_card 字号 | 10/11sp 低于字阶下限；prism 紫 0.8 透明衰减 <3:1 | DS.fontSizeXs 收敛 + 全色图标 | 达标 **[前任已修]** |
| P8 | realtime_nudge_bubble | dark 侧 neutral800 泡对 info 图标 ~2.2:1、对 neutral200 文字反向倒挂 | dark 侧 surfaceTertiary + textPrimary | ≥4.3 **[前任已修]** |
| P9 | memory_settings 状态 chips/choice/filter | 令牌外 `Color(0xFF71917D)`；primaryBase 0.14/0.12 tint 3.97–4.22:1 | semanticSuccess/info 语义令牌 + tint 0.05 + 实色描边 | ≥4.52 **[前任已修]** |
| P10 | context_receipt/understanding/why_this | textTertiary 辅助文字低对比 | textSecondary 升档 | ≥4.85 **[前任已修]** |
| P11 | evidence_drawer | I18nService 双语三元 ×9 处 + _SummaryChip 彩色标签 classic-dark ~4.3:1 | l10n arb 化 + 标签 textPrimary + tint 0.06 | 达标 **[前任已修]** |

### 1b. 续跑修复（前任遗漏，本次量化确认后就地修）

| # | 面 | 缺陷（实测） | 修法 | 修后 |
|---|---|---|---|---|
| R1 | pattern_list 归档徽章 | success 10sp 对 0.157 tint classic 两档 **4.01–4.45:1** 且低于字阶下限 | tint 0.06 + textPrimary + 12sp + success 实色描边承担归档辨识 | ≥8.45 **[续跑修复]** |
| R2 | pattern_list 脚注日期 | `brandPrimary.withAlpha(100)` 衰减文字五档 **1.71–2.38:1**（全档崩，最重之一） | textSecondary + 12sp | ≥4.85 **[续跑修复]** |
| R3 | pattern_list meta 徽章（观察档/频次） | info/success 11sp 对 0.11 tint 4.27–4.35:1 + 字号不达标 | tint 0.06 + textPrimary 标签 + 12sp；色相由图标承载（图标 ≥4.55） | ≥8.45 **[续跑修复]** |
| R4 | pattern_list 描述正文 | `brandPrimary.withAlpha(200)` 正文 classic 两档/paperDay **3.25–3.90:1** | textSecondary（正文不借品牌色相） | ≥4.85 **[续跑修复]** |
| R5 | pattern_list 方案正文 | successLight 13sp 对 0.078 tint 浅色三档 **2.12–2.88:1**（关键正文近不可读） | textPrimary；语义色保留灯泡图标（≥4.46）与 tint 容器 | ≥8.07 **[续跑修复]** |
| R6 | aurora typing dots 时序 | 前任方案 build 内 stop：首帧前 repeat 已启动（首帧闪 + 空转一帧） | **didChangeDependencies 首帧前门控**：reduce-motion 档动画从不启动；OS 开关实时跟随；非 reduce 档行为不变（测试钉双向） | 等价强化 **[续跑修复]** |
| R7 | aurora turns 剩余轮次芯片 | `borderSubtle` 中灰底（border@0.72/0.6 合成）对 textSecondary **2.03–4.3:1 五档全崩**——中灰底对浅墨/深墨双向失配，本卡最重缺陷 | surfaceTertiary 底 + textPrimary + 12sp | ≥8.33 **[续跑修复]** |
| R8 | capsule_detail 字数计数器 | 11sp 低于字阶下限 | DS.fontSizeXs | 达标 **[续跑修复]** |
| R9 | memory_evidence_badge（F05 记忆面组件） | I18nService 双语三元 ×3（'OK'/'已隐藏'/'Redacted'/'缺失'/'Missing'）绕过 arb 管道 | l10n 化（arb 双语纯增量 + gen×3 手改同步），与 P11 同批收口 | L10N-PARITY PASS **[续跑修复]** |
| R10 | capsule_jobs fontSize 棘轮越线 | 前任给 capsule chips 显式加数字 `fontSize: 12` 致 UI-TOKENS 文件计数 10>基线 9（守卫实测红） | 该文件 10 处数字 12 全量令牌化 `DS.fontSizeXs`（==12.0 语义不变） | 棘轮 fontSize 616→**615 只降** **[续跑修复]** |

## 2. 辨识度专项结论（卡面特有风险：四操作/三分区在 quiet/dusk 的辨识度 + 清空进度反馈可见性）

- **三分区（事实/已确认偏好/待确认观察）**：memory 面以 SemanticPill tone 族承载（success/warning/info/danger/neutral）。复算确认 **quiet（全浅、低刺激）与 dusk（深绿）下五 tone 全部 ≥4.5:1**（0.05 tint 收口后）；跨档语义钉（`g03_family_four_profile_test`）逐档断言五 tone 徽章在位 + tint 定值——quiet/dusk 无失辨识。登记项：pill **brand tone 在 classic-dark panel 面 4.40:1**（家族面未用 brand tone，属 DS 层潜在面，归 DS 收敛卡，见 limitations）。
- **「来自/仅用于/更改/忘记」四操作**：来自=SemanticPill info/neutral 来源徽章、仅用于=scope 徽章（P9/P10 修后达标）、更改/忘记=context_receipt 面操作行（预算说明只作如实说明不禁用——U03 交付的行为合同，本卡只复算其文字对比度：budget note textTertiary→textSecondary 升档后 ≥4.85，quiet/dusk 同达）。
- **清空进度反馈**：mobile 侧现无「记忆清空+可查询进度」用户流（L10 规格句的后半段属行为面交付）——**登记 stop-condition 登记：行为语义缺陷超风格面→不顺手修**，见 limitations L-1。
- **纠正≠本轮生效**：why_this_receipt/context_receipt 面以文案承载（F03 冻结文案族），本卡复算其文字对比度达标（P10/R 组）；「纠正成功只代表该状态保存」语义由 U 线既有测试钉（memory_correction_test 等全绿），本卡零触碰。
- **无人格雷达**：Prism 卡为三分区列表（认知/情绪/执行），无雷达图；四档钉 `find.byType(PrismBehaviorCard)` + 三分区标题在位，星图/雷达组件在该面零引用（结构性事实，E2E 面归 Q05）。

## 3. 令牌化清零

- 家族 diff 内清零：`Color(0xFF71917D)`→DS.info、`primaryBase` 状态语义→semanticSuccess（P9）；capsule_jobs 数字 fontSize 全量令牌化（R10）；`withAlpha(28/40/100/200)` 衰减取色全数改语义令牌（R1–R5）。
- UI-TOKENS 守卫 PASS：color 224/275、fontSize **615**/727（基线 616，只降）。
- repeat 棘轮：48 文件/家族内 1 文件（≤48 上限达标零漂移）。

## 4. l10n 双语纯增量

arb×2 + gen×3 手改同步（wt729 判例）：auroraCalibration 系 ×4、evidenceDrawer 系 ×7（前任），memoryEvidenceStatus 系 ×3（续跑 R9）。L10N-PARITY：10280 template keys == abstract members，zh/en subclasses complete。**arb 勘误面零**（纯增量）。

## 5. 测试与分母

新套 12 用例（每验收面一正一反或逐档钉）：四风格语义钉 ×4（逐档：五 tone/三态徽章/三分区/tint 定值/textPrimary 标题钉）+ 跨档反例 ×1（四档同 run 全锚全勤 + 挂载档核对）+ 证据采集门控 ×1 + reduce-motion 双向钉 ×2（静/动）+ turns 芯片四档令牌钉 ×4。

回归分域：core/design **271**、家族 features **156**、widget 家族 **28**、i18n golden+chat 邻接 **19+1skip**（env 门，FIX-368 判例）、token 收口复跑 **13**、全量套件见 test_results.json（错峰 --concurrency=1）。analyze 零 issue。

## 6. RF-06 与行为面

diff 不含 RF-06 三文件、不含 routes、不含主题通道结构（DS 令牌纯消费）。行为语义零 diff：所有修改为颜色/字号/令牌/l10n/动效等价；typing dots 双向钉证明等价≠摘功能。
