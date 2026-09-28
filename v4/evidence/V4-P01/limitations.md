# V4-P01 · limitations（如实）

1. **subject-less spine 提示不受跨渠道 subject 抑制**：`scan_recall_notifications` 以空 context 派发（真实 task/plan id 在 detector 内部发现，多数分支因缺参早退）——此类提示无 subject 键，跨渠道拒绝匹配与一次 effect 去重均不生效，其节奏仍由 spine 既有 per-trigger Redis 冷却 + 30 分钟扫描去重约束；共享日预算与 quiet hours 对它们**已生效**（本卡收口）。带 subject 的 context（API 直调/后续卡传参）全量受保护。
2. **过期计划抑制为单侧**：`subject_expired` 只作用于 spine 渠道（卡面「不再被**另一渠道**补发」的保守读法）；nudge 渠道的过期计划呈现保留 J-07 rescope 流（已校准的重校准建议，A-07 staleness guard）。若审查裁决为双侧阻断，需先裁决与 J-07 的语义冲突（会杀死「先把这几天接回来」的合法回访面）。
3. **FIX-48 未在本卡闭合**：「今天不再看」类型级 24h 冷却在每日扫描节奏下次日复活（30 dismiss 中 26 次次日仍投放）的台账项仍 OPEN——其修法涉及 ignored_until 锚点语义裁决（时刻 vs 日界），本卡 subject 级抑制把同一拒绝**跨渠道**挡住（同 subject 不再被另一渠道补发），但同渠道同类型次日重发仍按 P-03 既有语义走。
4. **一次 effect 去重窗固定 24h**（`PROACTIVE_PROMPT_EFFECT_WINDOW_HOURS`，仅带 subject 提示）：不区分渠道既有冷却差异（spine task_missed 8h < 24h 窗——带 subject 时被去重窗统一到 24h；无 subject 时不受影响）。时长语义未经产品裁决，按「今天不看」同窗保守取值。
5. **情绪中性钉的口径**：钉的是「预算/抑制/接线面零写入情绪推断输入（CognitiveFragment.sentiment / emotion_hint 读面）」；全仓其他回归路径（如未来把 comeback 消息写入 cognitive fragments 的功能）不在本卡守卫范围。消息文案面的「零心理推断」由 P-03 既有词表纪律承载（`build_suggestion_elements`），本卡未改动。
6. **budget_state_unavailable 的 reason 复用**：P-03 抑制读失败与 P-06 设置读失败都 fail-closed 抑制，对外 reason 分别映射为 `notification_settings_unavailable`（nudge 渠道既有形状）/闸门 metrics `budget_state_unavailable`；spine 渠道被 fail-closed 拦下时 skipped reason 即 `budget_state_unavailable`。两条 fail-closed 路径未区分「哪一层读失败」的细分审计（metrics 有 reason 无层）。
7. **信封审计面的边界**：被抑制决定无账本行（生成源头抑制），审计靠 Prometheus 计数（有界 label，无用户维度）+ 任务 skipped 返回值；无独立持久化抑制台账表（「抑制态提升为一等实体」是 S16 交接建议，涉及迁移，归单一 owner 卡）。
8. **环境口径**：wtP01 无独立 .venv，Python/pytest/mypy/ruff/black 用主检出共享 venv；`backend/app/gen` 为复制实体目录（gitignored 未提交）；CI（Linux）口径未复跑。black/mypy 棘轮基线：`suppression.py` 与 `celery_tasks.py` 存在 base 既有格式漂移（main 主检出同命令同报），本卡文件全清、零新增。
9. **value 面未验证**：真人打扰/precision 指标未验证（无真实用户试验）；P-05 纵向评估覆盖 nudge 族（S16 交接注记：管线 live 化前应补同构评估）——本卡闸门对 P-01 事件管线投递面未接线（该管线默认 shadow，其 live 化是悬置决策，不属本卡）。
