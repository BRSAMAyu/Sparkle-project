# Sparkle 反馈-学习-适应管线深度审计报告

> 审计范围: response_feedback_service / prompt_bandit / jitai_trigger_service / progress_narrative_service / struggle_signal_aggregator
> 审计日期: 2026-05-15
> 审计角色: 架构审计 (L3 Cross-Boundary)

---

## 1. 架构分析: 反馈 → 学习 → 适应管线

### 1.1 数据流全景

```
用户反馈 (Flutter)
  ↓
ResponseFeedbackService.submit_feedback()
  ├── DB 持久化 (ResponseFeedback 表, 唯一约束 user_id+response_id)
  ├── RunLedger 事件记录 (feedback_received)
  ├── PromptBandit.update() → Redis 状态 (Beta 分布 α/β 更新)
  ├── ContextPackFeedback → BudgetTuningService (预算策略调整)
  ├── PreferenceInferenceService (用户偏好推断)
  ├── AgentScoringService.apply_response_feedback() → Agent 质量映射
  ├── AgentMemoryService.infer_preferences_from_feedback() → Agent 记忆偏好
  └── ContentQualityEvaluator → 自动入库 (seed library)

挣扎检测 (异步)
  ↓
StruggleSignalAggregator.compute_struggle_score()
  ├── 6 维信号聚合: skip_rate / short_session / error_trend / overdue / streak / completion_gap
  ├── 加权评分 → Redis 缓存 (6h TTL)
  └── SocialSignalBridge → 问责信号发布

自适应干预
  ↓
JITAITrigger.generate_hints()
  ├── 偏差检测 (z-score / confidence 门控)
  ├── 模板匹配 (10 个维度 × 方向)
  ├── 冷却期 (默认 24h) + 日预算 (默认 3 次)
  ├── 误触发率 → 自动降级 (live → shadow)
  └── 事件总线发布 (user_id SHA256 哈希)

成长叙事
  ↓
ProgressNarrativeService.build_weekly_narrative()
  ├── 8 维数据聚合: tasks / errors / reflections / mastery / plans / aurora_corrections / achievements / study_days
  ├── 风格变体 (3 轮转) + 去重 (bigram overlap >= 0.82)
  └── Redis 缓存 (周粒度, +2 天宽限)
```

### 1.2 架构评价

**优点:**
- 反馈管线设计完整: 单次提交触发 7 个下游系统, 覆盖率充分
- Bandit 采用 Thompson Sampling, 理论上有收敛保证
- JITAI 有多层安全门控: 冷却期 + 日预算 + 误触发自动降级 + Kill Switch
- 挣扎信号聚合覆盖 6 个维度, 权重公开透明
- 成长叙事有去重机制和风格变体, 避免重复感

**架构风险:**
- 反馈提交是同步阻塞操作, 7 个下游系统串行执行, 延迟叠加
- 无事务补偿机制: 部分 downstream 失败后, 反馈已持久化但学习未完成
- Bandit 状态完全依赖 Redis, 无持久化回退
- 挣扎评分权重和 > 1.0 (0.30+0.20+0.25+0.15+0.10+0.35=1.35), 实际总分会超过 1.0

---

## 2. 问题报告

### P1-01: 挣扎评分权重总和超过 1.0, 评分可能虚高

- **严重度:** P1
- **位置:** `struggle_signal_aggregator.py:84-91`
- **描述:** WEIGHTS 字典中 6 个权重之和为 1.35 (0.30+0.20+0.25+0.15+0.10+0.35), 超过了标准归一化权重上限 1.0。`_score_from_signals` 方法使用加权求和, 理论上在所有信号同时为 1.0 时最大值可达 1.35。虽然 `_clamp` 会将结果截断到 [0, 1], 但这意味着在中等信号强度时, 评分已经会显著偏高。
- **影响:** 挣扎分数系统性偏高, 导致 (1) 过早触发干预消息, (2) 社交信号桥可能发布不必要的问责信号, (3) 用户感知系统"过度关心"或"误判状态"。
- **修复建议:** 将权重总和归一化到 1.0。最简单的方式是将 completion_gap_weight 从 0.35 降至 0.00 (因为 0.30+0.20+0.25+0.15+0.10 = 1.00), 或按比例缩放所有权重使总和为 1.0。

```python
# 当前 (总和 = 1.35)
WEIGHTS = {
    "skip_rate": 0.30,
    "short_session_rate": 0.20,
    "error_trend": 0.25,
    "overdue_weight": 0.15,
    "streak_weight": 0.10,
    "completion_gap_weight": 0.35,
}

# 建议: 归一化到 1.0
WEIGHTS = {
    "skip_rate": 0.22,
    "short_session_rate": 0.15,
    "error_trend": 0.19,
    "overdue_weight": 0.11,
    "streak_weight": 0.07,
    "completion_gap_weight": 0.26,
}
```

---

### P1-02: 反馈提交中 normalize_reasons 对非数字 reason 的静默丢弃

- **严重度:** P1
- **位置:** `response_feedback_service.py:180-185`
- **描述:** `submit_feedback` 方法接受 `reasons: list[str]`, 但在传播到 AgentMemoryService 时, 仅尝试将每个 reason 转为 int, 转换失败的直接 `pass`。这意味着如果 reasons 是 FEEDBACK_REASON_MAP 中的字符串键名 (如 "inaccurate"), 这些信息在 agent memory 传播中会被完全丢弃。
- **影响:** Agent 偏好推断收到的 reasons 列表可能为空, 导致学习信号丢失。用户反馈的负面原因无法传递到 agent 记忆系统, 阻碍个性化优化。
- **修复建议:** 在调用 `normalize_reasons` 前, 增加 reason 字符串到 int 的反向映射:

```python
# 增加反向映射
REVERSE_REASON_MAP = {v: k for k, v in FEEDBACK_REASON_MAP.items()}

# 在 submit_feedback 中:
safe_reasons = []
for r in (reasons or []):
    try:
        safe_reasons.append(int(r))
    except (ValueError, TypeError):
        # 尝试反向查找字符串 reason
        reverse = REVERSE_REASON_MAP.get(str(r))
        if reverse is not None:
            safe_reasons.append(reverse)
```

---

### P1-03: PromptBandit 状态仅存 Redis, 故障时退化为随机选择且状态丢失

- **严重度:** P1
- **位置:** `prompt_bandit.py:33-36, 66-69`
- **描述:** 当 `redis_client` 为 None 时, `_load_state` 直接返回默认状态 (所有 arm alpha=1, beta=1), 并且 `_save_state` 为空操作。这意味着: (1) 每次 select 调用都从均匀分布采样, 完全丢失学习历史; (2) 如果 Redis 重启/故障, 所有工作流的 bandit 学习状态全部丢失, 需要从零重新学习。
- **影响:** 在 Redis 不可用时, prompt 选择退化为完全随机, 已学习到的最优 prompt 版本被忽略, 可能导致用户体验质量突然下降。Redis 重启后需要大量反馈样本才能恢复到之前的水平。
- **修复建议:** (1) 在 `_load_state` 中增加 DB 回退逻辑, 从 ResponseFeedback 表中重建 bandit 状态; (2) 定期将 Redis 中的 bandit 状态快照到 DB; (3) 在 `get_debug_state` 中增加状态健康度指标, 监控状态丢失事件频率。

---

### P1-04: ContentQualityEvaluator.auto_seed_to_library 存在隐私泄露风险

- **严重度:** P1
- **位置:** `response_feedback_service.py:209-215`, `content_quality_evaluator.py:281-339`
- **描述:** `submit_feedback` 方法在收到反馈后自动调用 `ContentQualityEvaluator.evaluate_response_quality` 和 `auto_seed_to_library`。seed item 的 `content_data` 包含 `source_response_id`, 但整个流程没有任何 PII 脱敏步骤。如果原始 response 中包含用户姓名、邮箱等 PII, 这些信息会直接进入 seed library。
- **影响:** 用户在对话中可能包含敏感信息 (如 "我叫张三, 我的邮箱是..."), 这些信息如果被 AI 生成的回复引用, 会随 auto-seed 进入 seed library, 造成 PII 泄露。seed library 可能被其他用户或管理员查看。
- **修复建议:** (1) 在 auto_seed 之前调用 `app.aurora.privacy.redact_pii()` 对 response 内容进行脱敏; (2) 在 seed item 的 content_data 中记录脱敏状态; (3) 设置 seed library 访问权限, 确保只有系统级服务可以访问 auto-seeded 内容。

---

### P1-05: JITAI 误触发率统计基于全局计数器, 不区分用户维度

- **严重度:** P1
- **位置:** `jitai_trigger_service.py:263-276`
- **描述:** `_increment_rate_counter` 和 `_get_rate_counter` 使用 `jitai:rate:{kind}:{date}` 作为 Redis key, 这是一个全局日级计数器, 不包含 user_id。`_evaluate_auto_downgrade` 使用这个全局误触发率来决定是否将系统降级到 shadow 模式。
- **影响:** (1) 高活跃度用户的误触发会主导全局统计, 掩盖低活跃度用户的真实误触发率; (2) 一个用户的误触发可能导致所有用户的 JITAI 被降级; (3) 新用户在系统刚降级后无法获得任何干预, 即使他们对干预有正面响应。
- **修复建议:** 改为 per-user 误触发率 + 全局误触发率的双层评估:

```python
# 降级决策应综合考虑
global_rate = await self.get_misfire_rate(days_ago=offset, now=now)
# 如果全局率 > 阈值但 per-user 率正常, 仅对高误触发用户降级
# 而非全局关闭
```

---

### P2-01: 反馈提交是同步阻塞, 7 个下游系统串行执行

- **严重度:** P2
- **位置:** `response_feedback_service.py:133-215`
- **描述:** `submit_feedback` 方法在 DB commit 后, 串行调用 `_record_feedback_ts`, `_update_bandit`, `_handle_context_pack_feedback`, `AgentScoringService.apply_response_feedback`, `AgentMemoryService.infer_preferences_from_feedback`, `ContentQualityEvaluator.evaluate_response_quality` 等操作。其中部分操作有 try/except 但仅记录日志, 不影响主流程。
- **影响:** 反馈提交延迟高, 在 Redis 慢或 DB 查询慢时会直接影响用户感知的响应时间。agent memory 传播 (行 177-206) 包含循环调用 `infer_preferences_from_feedback`, 如果 linked_agents 很多, 延迟会线性增长。
- **修复建议:** 将下游系统改为异步事件驱动: 反馈持久化后发布 `FeedbackReceived` 事件到 event_bus, 各下游系统独立消费。这样主路径只包含 DB 写入 + 事件发布, 延迟可控。

---

### P2-02: Progress Narrative 未对用户输入内容做 PII 脱敏

- **严重度:** P2
- **位置:** `progress_narrative_service.py:654-690`
- **描述:** `_reflection_summary` 方法从 `TaskFeedback.reflection_payload` 中提取 `free_text` 和 `selected_option`, 以及 `feedback_text`。这些内容直接来自用户输入, 可能包含 PII (姓名、电话、学校名等)。提取后通过 `snippets` 字段进入叙事内容, 最终呈现给用户或缓存到 Redis。
- **影响:** (1) 用户在任务反馈中填写的个人信息可能原样出现在成长叙事中; (2) 这些叙事被缓存到 Redis (TTL 最长 120 天), PII 持续暴露; (3) 如果叙事被分享 (如群组成就展示), PII 会扩散。
- **修复建议:** 在 `_reflection_summary` 和 `_clean_text` 中增加 PII 脱敏步骤, 调用 `app.aurora.privacy.redact_pii()` 处理所有用户输入文本:

```python
from app.aurora.privacy import redact_pii

snippet = redact_pii(
    self._clean_text(payload.get("free_text"))
    or self._clean_text(payload.get("selected_option"))
    or self._clean_text(feedback_text)
)
```

---

### P2-03: 成长叙事中 task_titles 和 plan_names 直接嵌入, 可能包含敏感任务名

- **严重度:** P2
- **位置:** `progress_narrative_service.py:150, 479-488, 575-594, 720-740`
- **描述:** 叙事生成过程中, 任务标题 (`Task.title`), 错题章节 (`ErrorRecord.chapter`), 计划名称 (`Plan.name`) 等直接嵌入叙事文本。这些字段可能包含敏感内容 (如 "备考公务员", "戒除焦虑", "治疗计划" 等)。
- **影响:** 如果叙事被缓存、分享或导出, 用户的敏感目标/任务名称会泄露。特别是 `_build_report_actions` 生成的 deep_link 中包含未编码的任务标题。
- **修复建议:** (1) 在叙事缓存前对敏感字段做脱敏或泛化处理; (2) 确保 `_build_report_actions` 中的 deep_link 参数使用 `quote()` 编码 (当前 `node_name` 已做 quote, 但 `title` 字段未做)。

---

### P2-04: 挣扎检测的 completion_gap 使用硬编码阈值, 无个性化校准

- **严重度:** P2
- **位置:** `struggle_signal_aggregator.py:327-380`
- **描述:** `_completion_gap` 方法中, "两天无完成" (`no_completion_days >= 2`) 和 "近期无完成" (`recent_completion_count == 0`) 的判定阈值是硬编码的。对于低频学习用户 (如每周只学 2-3 天), 这个阈值几乎总是会触发, 产生大量假阳性。同样, `_score_from_signals` 中 "5 个任务中跳过 70%" 的硬编码阈值也对高频用户过于宽松。
- **影响:** 低频学习者频繁被标记为"挣扎", 收到不必要的关怀干预; 高频学习者即使确实遇到困难, 也可能因为阈值过高而未被检测到。
- **修复建议:** (1) 引入用户基线校准: 使用 `PlanState.adaptive_meta` 中存储的用户历史完成率作为基线, 将阈值设为基线的百分比偏差; (2) 区分 "计划类型" (高频密集 vs 低频长期), 不同计划使用不同阈值。

---

### P2-05: PromptBandit 无探索衰减机制, 冷启动阶段可能过早收敛

- **严重度:** P2
- **位置:** `prompt_bandit.py:71-81`
- **描述:** `select` 方法使用标准 Thompson Sampling (Beta 分布采样), 但没有探索衰减或最小探索保证。在冷启动阶段, 如果前几个反馈恰好都给了同一个 arm, 其 alpha 会快速增长, 导致其他 arm 几乎不再被选中。
- **影响:** 假设有 A/B 两个 prompt 版本, 如果前 5 个反馈中 A 恰好收到 4 个正面反馈 (alpha=5, beta=1), B 收到 1 个负面反馈 (alpha=1, beta=2), A 的 Beta(5,1) 采样值几乎总是在 0.6 以上, B 的 Beta(1,2) 采样值大多在 0.3 以下, B 几乎永远不会被再次选中。如果 B 实际上对某些场景更好, 这些场景永远不会被发现。
- **修复建议:** 增加 epsilon-greedy 混合策略:

```python
async def select(self, workflow_id: str, arms: list[str], *, epsilon: float = 0.1) -> str:
    if self.rng.random() < epsilon:
        return self.rng.choice(arms)
    # ... 原有 Thompson Sampling 逻辑
```

---

### P2-06: JITAI 模板消息全部硬编码中文, 无法国际化

- **严重度:** P2
- **位置:** `jitai_trigger_service.py:36-77`
- **描述:** `TEMPLATE_REGISTRY` 中所有消息都是硬编码的中文字符串。如果系统需要支持英文用户 (根据 CLAUDE.md 中的 `isChinese ? '中文' : 'English'` 双语策略), 这些消息无法被翻译。
- **影响:** 非中文用户会收到中文干预消息, 体验差。与项目的 i18n 策略不一致。
- **修复建议:** 将模板消息改为 ARB key 引用, 在运行时根据用户语言偏好加载对应翻译。

---

### P2-07: 反馈数据用于 auto-seed 但无用户知情同意机制

- **严重度:** P2
- **位置:** `response_feedback_service.py:209-215`
- **描述:** 用户提交反馈后, 系统自动评估 response 质量并将高质量回复 auto-seed 到 seed library。这个过程没有用户同意步骤, 也没有在反馈提交时告知用户其反馈数据可能被用于训练/种子库建设。
- **影响:** 虽然当前 seed library 标记为 "private", 但 (1) 用户不知道自己的反馈被用于此目的; (2) 未来如果 seed library 可见性变更, 存在合规风险 (GDPR/个人信息保护法); (3) auto-seed 的 response 内容可能包含用户与 AI 的完整对话片段。
- **修复建议:** (1) 在反馈提交时增加可选的 `consent_flags` 字段; (2) 只有用户明确同意的反馈才进入 auto-seed 流程; (3) 在隐私政策中披露反馈数据的使用方式。

---

### P2-08: StruggleSignalAggregator._last_active_text 包含硬编码中文, 与 i18n 策略冲突

- **严重度:** P2
- **位置:** `struggle_signal_aggregator.py:501-523`
- **描述:** `_last_active_text` 方法返回的时间描述全部是硬编码中文字符串 ("分钟前", "小时前", "天前", "暂无记录")。根据项目 CLAUDE.md 的双语策略, 这些字符串应通过 ARB l10n 管理。
- **影响:** 非中文用户看到的挣扎上下文包含中文时间描述。
- **修复建议:** 使用 ARB l10n key 替代硬编码字符串, 或在调用侧做国际化处理。

---

### P2-09: Feedback loop 无闭环验证 — 无法确认用户是否看到了反馈的改善效果

- **严重度:** P2
- **位置:** 整个反馈管线
- **描述:** 用户提交负面反馈后, 系统会更新 bandit / agent scoring / budget tuning 等, 但没有任何机制验证这些更新是否确实改善了后续体验。没有 "反馈后满意度追踪" 或 "反馈效果归因" 的闭环。
- **影响:** 无法量化反馈系统的实际效果。可能存在大量反馈被收集但未真正转化为体验改善的情况, 形成 "反馈黑洞"。
- **修复建议:** (1) 在用户提交负面反馈后的下一次交互中, 增加轻量级的 "这次体验是否更好?" 追踪; (2) 定期计算 "反馈后改善率" 指标; (3) 将改善率反馈到 JITAI 和 bandit 的 reward 信号中。

---

### P2-10: 学习系统无偏差检测 — 用户反馈偏差可能被放大

- **严重度:** P2
- **位置:** 全局 (response_feedback_service + prompt_bandit + preference_inference)
- **描述:** 系统通过用户反馈来调整 prompt 版本、agent 评分和用户偏好。但用户反馈本身存在系统性偏差: (1) 幸存者偏差 — 只有仍在使用系统的用户才会给反馈, 流失用户的声音缺失; (2) 确认偏差 — 用户倾向于给符合预期的回答正面反馈; (3) 位置偏差 — 用户可能对最后看到的选项给予更多关注。
- **影响:** Bandit 可能收敛到 "让用户满意但不是真正有效" 的 prompt 版本。Preference inference 可能强化用户已有偏好而非拓展学习路径。长期来看, 系统会越来越迎合用户舒适区, 而非推动真正的成长。
- **修复建议:** (1) 在 bandit reward 中引入 "客观学习效果" 信号 (如 mastery_delta), 不完全依赖主观反馈; (2) 定期审计 bandit 收敛状态, 检查是否存在所有 arm 收敛到同一策略的情况; (3) 增加反偏差探索: 定期向用户展示非最优策略, 收集真实效果对比数据。

---

### P2-11: JITAI 的 _evaluate_auto_downgrade 存在竞态条件

- **严重度:** P2
- **位置:** `jitai_trigger_service.py:210-221`
- **描述:** `_evaluate_auto_downgrade` 读取最近 3 天的误触发率, 如果全部超过阈值则降级。但 `get_misfire_rate` 的分子 (misfires) 和分母 (triggered) 来自不同的 Redis key, 读取不是原子操作。在高并发场景下, 可能读到不一致的 triggered/misfires 计数。
- **影响:** (1) 可能基于不一致的数据做出降级决策; (2) 降级操作 (将两个 feature mode 设为 shadow) 也不是原子的, 可能出现一个设为 shadow 另一个仍为 live 的中间状态。
- **修复建议:** (1) 使用 Redis Lua script 保证 rate 读取的原子性; (2) 在 `_evaluate_auto_downgrade` 中增加降级操作的原子性保证。

---

## 3. 问题汇总

| 编号 | 严重度 | 类别 | 位置 | 简述 |
|------|--------|------|------|------|
| P1-01 | P1 | 挣扎检测精度 | struggle_signal_aggregator.py:84-91 | 权重总和 1.35 > 1.0, 评分系统性偏高 |
| P1-02 | P1 | 反馈完整性 | response_feedback_service.py:180-185 | 非 int reason 在 agent memory 传播中被静默丢弃 |
| P1-03 | P1 | 学习系统韧性 | prompt_bandit.py:33-36 | Redis 故障时 bandit 状态全部丢失, 退化为随机 |
| P1-04 | P1 | 隐私安全 | content_quality_evaluator.py:281-339 | auto-seed 无 PII 脱敏, 可能将用户敏感信息入库 |
| P1-05 | P1 | JITAI 精度 | jitai_trigger_service.py:263-276 | 误触发率基于全局计数器, 单用户可影响全部用户 |
| P2-01 | P2 | 性能 | response_feedback_service.py:133-215 | 7 个下游系统串行阻塞, 延迟叠加 |
| P2-02 | P2 | 隐私安全 | progress_narrative_service.py:654-690 | 叙事中用户输入内容未做 PII 脱敏 |
| P2-03 | P2 | 隐私安全 | progress_narrative_service.py:479-488 | 任务标题/计划名直接嵌入叙事, 可能包含敏感信息 |
| P2-04 | P2 | 挣扎检测精度 | struggle_signal_aggregator.py:327-380 | 硬编码阈值无个性化, 低频用户假阳性高 |
| P2-05 | P2 | 学习系统 | prompt_bandit.py:71-81 | 无探索衰减, 冷启动可能过早收敛到次优策略 |
| P2-06 | P2 | 国际化 | jitai_trigger_service.py:36-77 | 模板消息硬编码中文, 无法国际化 |
| P2-07 | P2 | 合规 | response_feedback_service.py:209-215 | auto-seed 无用户知情同意机制 |
| P2-08 | P2 | 国际化 | struggle_signal_aggregator.py:501-523 | 时间描述硬编码中文 |
| P2-09 | P2 | 反馈闭环 | 全局 | 无反馈后效果追踪, 无法验证改善 |
| P2-10 | P2 | 学习偏差 | 全局 | 用户反馈偏差可能被放大, 无反偏差机制 |
| P2-11 | P2 | 竞态条件 | jitai_trigger_service.py:210-221 | 降级决策存在数据读取竞态 |

**统计:** P1 = 5, P2 = 11, 共 16 个问题

---

## 4. 优先修复建议

### 立即修复 (P1)
1. **P1-01:** 归一化挣扎评分权重到总和 1.0 — 一行改动, 影响面可控
2. **P1-04:** auto_seed 前增加 PII 脱敏 — 引用已有的 `redact_pii()` 函数
3. **P1-02:** 增加 reason 字符串到 int 的反向映射 — 恢复 agent memory 信号完整性
4. **P1-03:** 增加 bandit 状态 DB 回退 — 提升系统韧性
5. **P1-05:** JITAI 降级决策改为 per-user 粒度 — 避免单用户影响全局

### 计划修复 (P2)
1. **P2-02 + P2-03:** 叙事 PII 脱敏 — 统一使用 `redact_pii()`
2. **P2-01:** 反馈下游改为事件驱动 — 架构优化
3. **P2-04:** 挣扎阈值个性化 — 引入用户基线
4. **P2-05 + P2-10:** Bandit 探索策略 + 反偏差 — 学习质量提升
5. **P2-06 + P2-08:** i18n 合规 — 统一 ARB 管理
