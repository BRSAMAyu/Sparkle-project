# V4-G05 · diff_or_evidence_only

## 断点续跑上下文

前任 agent 因宿主机强制重启阵亡，遗留 dirty worktree（9 个源文件改动 + 1 个未提交测试文件），本次续跑 **未丢弃任何前任改动**，在其基础上：

1. 盘点前任 diff（全部为呈现层风格面：全强度色替 shade600/透明度压色、pill tint 0.08–0.12→0.05、趋势次系列虚线形状双编码、reduce-motion 等价 ×3、雷达对比系列实色化）——U13 契约层零 diff 红线全程未破。
2. 对家族 13 屏全量续扫（9 屏前任未触碰），以「最终计算颜色」逐对复算（F06 判例公式）定位真缺陷。

## 本次新增改动（呈现层风格面）

| 文件 | 修复 | 判值依据 |
|---|---|---|
| learning_insights_overview_screen.dart | 推荐 pill 文本 accent→textPrimary | accent 于 0.12 tint×highlight 叠底 classic 3.95–4.44:1；textSecondary 亦不足（3.88–4.48） |
| growth_chronicle_screen.dart | 入口圆底 tint 0.14→0.05；pattern_discovered 图标 cs.secondary→DS.secondaryDark（同源变暗档）；状态 pill 文本→textPrimary | cs.secondary 图标于 0.14/0.05 tint 2.73/2.99:1 (<3)；pill 文本 4.50/2.78:1 |
| capsule_jobs_screen.dart | 状态 pill 底 0.15→0.05；失败框底 0.1→0.05 | classic 4.02–4.16 / 4.45:1 (<4.5)；0.05 起 ≥4.85 |
| capsule_detail_screen.dart | 深度 pill 底 0.12→0.05 ×3；选中筛选 chip 底 0.12→0.05 | classic 4.49–4.50 / 4.22:1；0.05 起 4.85–8.31 |
| review_plan_hub_screen.dart | hero 渐变止点 0.16/0.1→0.08/0.05 | textSecondary 副标题于 brand@0.16 止点 classic 4.37:1；0.08 起 ≥4.6 |
| curiosity_capsule_screen.dart | Tab 选中指示：0.14 tint→「0.14 tint + 全强度 capsuleAccent 描边」 | tint 边界四风格 1.16–1.32:1 (<3)；全强度填充会压标签墨（textPrimary 1.55–4.34:1）；描边承载边界 ≥3:1、标签落近 s2 底 ≥4.5 |
| learning_report_screen.dart | 触发横幅卡标签 pill、行动卡徽章、对比卡标签文本 accent→textPrimary；stat 单位文本 color@0.72→textPrimary | accent 于嵌套 tint 3.92–4.48:1；0.72 透明度压文字为 SPEC §1.3.1 禁式 |
| g05_family_four_style_test.dart（测试） | A 组续扫 +41 对四风格逐对守卫；对照探针 +6（旧公式 classic 确实失败）；hero 渐变 widget 钉；scrollUntilMounted 宿主修复（milestone 对话框 kG05MilestonePrefs 源头消弹 + 撤除常驻 barrier 角点补偿）；C 组控制组改挂载帧观察 | 前任宿主 3 处缺陷修复详见 limitations.md |

前任改动（已保留并受既有钉保护）：engagement_heatmap、pattern_list_screen、directive_audit_screen、learning_forecast_screen、evidence_insight_card、return_case_file_card、risk_observation_card、learning_report_screen（部分）、mastery_radar_chart。

## 契约红线核验

- D05 insight.presentation.v1 契约层（schema/字段/文案语义）零 diff；仅动颜色/tint/描边/文本墨色。
- E 组语义钉四风格逐字一致：撤回排除行、证据不足行、样本定义行、可忽略行；禁百分比面无 %。
- 无数据态显式「还没有可分析的行为记录」；复盘 hub 空态标题/清单/夜间复盘在册。
- 行为语义零改动：无路由/状态/交互变更；仅 lib/ 呈现色值与测试。
