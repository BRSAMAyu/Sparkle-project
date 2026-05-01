# Aurora 智能闭环 — 完整修复规格书

**日期**: 2026-05-02
**前置**: Aurora 会话状态恢复已修复（commit `aa543d728`）
**本文档**: 覆盖 9 项改进，从工程缺陷到产品方向决策

---

## P1: 工程缺陷（必须修）

### FIX-10: 校准收据对路由器不可见

#### 问题背景
用户校正 Aurora 后，`CorrectionFeedbackProcessor` 正确更新了 4 个子系统（self_model、StateRegister、Bayesian learner、routing_profile）。但 `UserStateV1`（路由器的输入）没有"最近校准"相关字段。路由器看不到"这个用户最近纠正了我 3 次"，因此下一次路由决策不受校准影响。

#### 当前代码
**`backend/app/state_aggregator/schema.py:9-30`** — `UserStateFieldName` 定义了 20 个字段，没有 correction/calibration 相关字段：
```python
UserStateFieldName = Literal[
    "commitment_summary",
    "pending_policies",
    "recent_reflections",
    ...
    "emotion_hint",
]
```

**`backend/app/state_aggregator/schema.py:285-313`** — `UserStateV1` dataclass 有 20 个可选字段，没有 correction 相关。

**`backend/app/state_aggregator/service.py:84`** — `FIELD_TTLS_SECONDS` 映射了 20 个字段的 TTL，没有 correction 字段。

#### 修复方案

**Step 1: 定义新的 Value 类型**（`schema.py`）
```python
@dataclass(frozen=True)
class RecentCorrectionsSummaryValue:
    count_7d: int                    # 最近 7 天校正次数
    last_correction_at: datetime | None
    top_topics: tuple[str, ...]      # 校正涉及的主题 ("time", "difficulty", ...)
    avg_confidence_delta: float      # 平均 confidence 变化
```

**Step 2: 扩展 UserStateFieldName**（`schema.py:9`）
在 Literal 中添加 `"recent_corrections_summary"`。

**Step 3: 添加字段到 UserStateV1**（`schema.py:313`）
```python
recent_corrections_summary: StateFieldEnvelope[RecentCorrectionsSummaryValue] | None = None
```

**Step 4: 在 service.py 中实现 fetcher**
添加 `_get_recent_corrections_summary` 方法：
- 从 Redis 读取 `calibration_receipt_dismissed_*` 或 working memory 中 `subject_type="aurora_correction"` 的条目
- 统计 7 天内的校正次数、主题分布
- TTL 建议: 3600 秒（1 小时）

**Step 5: 在路由器中消费**
`dual_core_router.py` 中读取 `recent_corrections_summary`，当 `count_7d >= 3` 时提升 calibration_available 信号优先级。

#### 涉及文件
1. `backend/app/state_aggregator/schema.py` — 新类型 + 字段扩展
2. `backend/app/state_aggregator/service.py` — fetcher 实现 + TTL 注册
3. `backend/app/orchestration/dual_core_router.py` — 消费新字段
4. `backend/app/orchestration/session_state_mixin.py` — 将字段注入上下文

#### 注意事项
- 新增字段需要在 `FIELD_TTLS_SECONDS` 和 `_FIELD_FETCHERS` 中注册
- `UserStateV1.schema_version` 需要升为 `"user_state.v1.14"`

---

### FIX-11: Self-model 30 天 TTL 无 PG 备份

#### 问题背景
`self_model.py:11` 设置 `SPARKLE_SELF_MODEL_TTL_SECONDS = 30 * 24 * 60 * 60`。Self-model 存储在 Redis，包含 strategy_confidence、known_assumptions（时间/难度/时长）、failure_streak 等关键校准数据。

大学生暑假 2 个月不登录，回来后 self-model 已过期，所有校准归零。前一轮修复（`aa543d728`）解决了 FSM/L3 session 的 PG 持久化，但 self-model 的长期数据没有 PG 备份。

#### 当前代码
**`backend/app/aurora/runtime_v1/self_model.py:10-11`**:
```python
SPARKLE_SELF_MODEL_KEY_TEMPLATE = "aurora:self_model:{user_id}"
SPARKLE_SELF_MODEL_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
```

Self-model 的数据结构（从 `get_readout_summary` 推断）：
- `strategy_confidence`: float 0-1
- `known_assumptions`: dict of assumption_id → {confidence, evidence: [...], ...}
- `harness_effectiveness`: {context_hit_rate, task_completion_rate, user_corrections_count, task_shape}
- `failure_streak`, `timeout_count`: int
- `processed_signal_ids`: set (capped at 100)

#### 修复方案

**方案: PG 快照 + Redis 优先读取**（与 FSM/L3 同模式）

**Step 1: 创建 Alembic migration**
新表 `aurora_self_model_snapshots`：
```sql
CREATE TABLE aurora_self_model_snapshots (
    id GUID PRIMARY KEY,
    user_id STRING(128) NOT NULL,
    payload JSONB NOT NULL,          -- 完整 self-model JSON
    strategy_confidence FLOAT,       -- 冗余字段便于查询
    task_shape STRING(32),
    failure_streak INT,
    snapshot_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME
);
CREATE UNIQUE INDEX ... ON aurora_self_model_snapshots(user_id);
```

**Step 2: 在 self_model.py 中添加 PG 持久化**
```python
async def _persist_snapshot(self, user_id: str, model_data: dict) -> None:
    """在每次 update 后异步写入 PG 快照。"""
    ...

async def _load_from_pg(self, user_id: str) -> dict | None:
    """Redis miss 时从 PG 恢复最新快照。"""
    ...
```

**Step 3: 修改读写路径**
- `record_task_outcome()` / `record_user_correction()` — 更新 Redis 后调用 `_persist_snapshot()`
- `get_readout_summary()` — Redis miss 时调用 `_load_from_pg()` 并回填 Redis

#### 涉及文件
1. `backend/alembic/versions/c12_20260502_add_self_model_snapshots.py` — 新表
2. `backend/app/aurora/runtime_v1/self_model.py` — 读写路径
3. `backend/app/aurora/runtime_v1/models.py` — SQLAlchemy model

#### 注意事项
- Self-model 更新频率高（每次 task outcome），PG 写入应该是 `flush` 而非每次 `commit`
- 考虑用 `db_session.flush()` + 事务性批量提交
- PG 快照不需要实时，可以接受 1-2 次交互的延迟

---

## P2: 体验提升（应该修）

### FIX-12: 记忆衰减声明但未执行

#### 问题背景
`EpisodicMemory` 模型有 `decay_policy` 字段，但没有 Celery 任务实现衰减。记忆无限累积。

#### 当前代码
搜索 `decay_policy` 的所有用法：
- 模型定义中有 `decay_policy` 字段
- 写入时设置了 `decay_policy` 值（如 "gradual_30d"）
- **没有任何地方读取并执行**这个 policy

#### 修复方案

**Step 1: 创建 Celery task**
新文件 `backend/app/tasks/memory_decay.py`：
```python
@celery_app.task(name="memory.apply_decay")
def apply_memory_decay():
    """降低老旧记忆的 importance_score 和 confidence。"""
    # 1. 查询 decay_policy IS NOT NULL AND updated_at < now - interval '7 days'
    # 2. 对每条记忆：
    #    - gradual_30d: importance *= 0.95, confidence *= 0.98 (每 7 天衰减一次)
    #    - aggressive_7d: importance *= 0.8 (每周衰减)
    #    - preserve: 跳过
    # 3. importance < 0.1 的记忆标记为 retracted
```

**Step 2: 注册到 Celery beat**
在 `celery_config.py` 或 beat schedule 中添加：
```python
"memory-decay-weekly": {
    "task": "memory.apply_decay",
    "schedule": crontab(day_of_week=1, hour=3, minute=0),  # 每周一凌晨 3 点
}
```

#### 涉及文件
1. `backend/app/tasks/memory_decay.py` — 新文件
2. `backend/app/config/celery_config.py` — beat schedule 注册

---

### FIX-13: 校正维度只覆盖时间/难度

#### 问题背景
用户校正"你对我的压力判断不对"时，`self_model.py:241-243` 的关键词匹配只检查 `_TIME_KEYWORDS` 和 `_DIFFICULTY_KEYWORDS`。压力、情绪、社交关系等维度的校正落入 default 分支，调整错误的 assumption。

#### 当前代码
**`backend/app/aurora/runtime_v1/self_model.py:34-35`**:
```python
_TIME_KEYWORDS = ("时间", "分钟", "小时", "daily", "time", "schedule", "90")
_DIFFICULTY_KEYWORDS = ("难", "太难", "简单", "太简单", "基础", "难度", "difficulty", "baseline")
```

**`self_model.py:241-243`** — 校正主题分类：
```python
if any(token in lowered for token in _TIME_KEYWORDS):
    ...
if any(token in lowered for token in _DIFFICULTY_KEYWORDS):
    ...
# 压力/情绪/社交 维度：没有匹配 → 走 default
```

**`correction_feedback.py:108`** — Aurora state 定义中有 `affective_pressure` 维度：
```python
"affective_pressure": "你当前压力或焦虑程度",
```

#### 修复方案

**Step 1: 添加新关键词组**
```python
_STRESS_KEYWORDS = ("压力", "焦虑", "紧张", "情绪", "心情", "stress", "anxious", "overwhelmed", "burnout")
_SOCIAL_KEYWORDS = ("关系", "朋友", "社交", "孤独", "social", "lonely", "friend")
```

**Step 2: 添加对应 assumption**
```python
_STRESS_ASSUMPTION = "affective_pressure"
_SOCIAL_ASSUMPTION = "social_context"
```

**Step 3: 扩展匹配逻辑**
在 `self_model.py` 的校正主题分类中添加新的关键词匹配分支。

**Step 4: 扩展 StateRegister 映射**
确保 `correction_feedback.py` 的 `StateRegister` confidence 降低逻辑覆盖新维度。

#### 涉及文件
1. `backend/app/aurora/runtime_v1/self_model.py` — 关键词 + assumption 扩展
2. `backend/app/aurora/runtime_v1/correction_feedback.py` — StateRegister 映射

---

### FIX-14: Bayesian learner 冷启动期

#### 问题背景
`learner.py:127` 初始化 α=1, β=1（均匀先验）。新用户前几次交互时 `policy_calibration` 的 uncertainty 高（接近 0.5），`calibrated = mean * (1 - 0.35 * uncertainty)` 的衰减因子接近 0.825。这意味着前 5-10 次校准对实际行为的影响被不确定性稀释了 17.5%。

#### 当前代码
**`backend/app/aurora/bayesian/learner.py:44-62`**:
```python
@dataclass
class AuroraPosterior:
    alpha: float = 1.0   # 均匀先验
    beta: float = 1.0

    @property
    def observations(self) -> int:
        return max(0, int(round((self.alpha + self.beta) - 2)))

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def uncertainty(self) -> float:
        # Beta 分布的方差
        denominator = (self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1)
        return (self.alpha * self.beta) / denominator
```

**`learner.py:148`** — calibration 计算：
```python
calibrated = posterior.mean * (1.0 - 0.35 * posterior.uncertainty)
```

当 α=1, β=1: mean=0.5, uncertainty=0.0833, calibrated=0.5*0.97=0.485 — 几乎没有信息量。

#### 修复方案

**方案 A: 基于初始调查问卷的信息性先验**（推荐）

如果用户在注册时完成了学习风格/压力水平的初始问卷，用问卷结果设置初始 α/β：
- 用户自报"容易焦虑" → affective_pressure: α=1, β=2 (prior leans toward needing cognitive support)
- 用户自报"学习习惯稳定" → time_management: α=2, β=1 (prior leans toward execution-capable)

**方案 B: 降低冷启动期的 uncertainty 衰减因子**

```python
# 修改 policy_calibration
if posterior.observations < 5:
    # 冷启动期：减少 uncertainty 惩罚
    calibrated = posterior.mean * (1.0 - 0.15 * posterior.uncertainty)
else:
    calibrated = posterior.mean * (1.0 - 0.35 * posterior.uncertainty)
```

**方案 C: 用 self-model 的初始 confidence 作为先验**

从 `SparkleSelfModelService.get_readout_summary()` 读取 `strategy_confidence`，用它作为 Bayesian 先验的 warm start。

#### 涉及文件
1. `backend/app/aurora/bayesian/learner.py` — 先验设置逻辑
2. `backend/app/aurora/runtime_v1/self_model.py:717-719` — calibration 消费点

---

## P3: 产品方向决策（需要你的裁定）

### FIX-15: Reinforce → 路由桥接

#### 我的深度思考

**当前状态**：AchievementEngine 处理 19 种事件（TaskCompleted、TaskAbandoned 等），产出 badge + photon + notification。这些事件通过 Event Bus 广播，但没有任何消费者将它们桥接到路由器。

**支持的论点**：
1. 连续 7 天打卡的用户和第 1 天的用户收到相同的路由策略——这在产品上不敏感
2. Achievement 数据已经在 `UserStateV1.achievement_summary` 中聚合了（schema.py:167-185），路由器有条件读取
3. 一个 streak=14 的用户可能已经建立了稳定的学习习惯，路由器可以考虑从 `balanced` 偏向 `execution_first`（减少认知干预、增加执行推进）

**反对的论点**：
1. **过度适配风险**：streak 本身就是正确路由策略的证明。如果因为 streak 高就减少认知支持，可能恰恰在用户需要帮助时撤掉了安全网
2. **相关性 vs 因果性**：streak 高可能是因为用户本身就自律，而不是因为 Aurora 的策略好。将 streak 作为路由信号，可能是在用一个与路由效果无关的信号
3. **实现复杂度**：需要在 dual_core_router.py 中新增一个信号维度，而这个维度的权重和阈值都需要调优。错误的权重可能比没有这个信号更糟
4. **产品直觉**：一个 AI 教练如果因为你表现好就减少关注，用户体验可能反而变差——感觉被"抛弃"

**我的判断**：**不建议做**。Streak/achievement 是展示层的激励，不应该成为 AI 决策层的输入。如果未来要做，应该先做 A/B 测试验证"streak 高 + 减少认知干预"是否真的好于"streak 高 + 维持当前策略"。

**替代方案**：如果一定要让 achievement 影响行为，更好的路径是通过 **self-model** 间接影响。Task outcome 已经在更新 self-model 的 strategy_confidence 和 task_shape，这些自然会反映到路由决策中。Achievement unlock 只是 task outcome 的一个后处理步骤，不需要单独桥接。

---

### FIX-16: 自动反思触发

#### 我的深度思考

**当前状态**：`TaskReflectionService` 只在用户提交负面任务反馈（TOO_DIFFICULT / abandoned / plan_stall 等）时触发。顺利完成所有任务的那天，不会产生任何反思。

**支持的论点**：
1. 成功经验也需要反思——"为什么这次成功了？什么因素可以复用？"这种反思对成长有价值
2. 7 阶段成长环的 Reflect 阶段在成功场景下是空白的，不是一个完整的闭环
3. 自动反思可以生成正面的 episodic memory，丰富用户画像

**反对的论点**：
1. **打扰风险**：用户顺利完成所有任务后，最不想看到的就是"让我们反思一下为什么成功"。这打破了流畅的体验
2. **反思疲劳**：如果每次成功都触发反思，用户会快速产生"反思厌恶"，连带负面反思也一起忽略
3. **不是所有成功都值得反思**：完成一个简单的"复习第 3 章"任务不需要反思。反思应该是有选择性的
4. **当前设计可能是有意的**：只在不顺利时反思，是一种"最小干预"策略——只在用户需要帮助时才打扰

**我的判断**：**有条件支持**。不应该做"每次成功都反思"，但可以做以下变体：

**变体 A — 里程碑触发**（推荐）
只在达到里程碑时自动触发反思：
- 连续 7 天完成任务
- 完成一个阶段的所有任务
- plan 整体完成度 > 80%

触发方式：不弹对话框，而是在 chat 中自然地提及（"你连续完成了一周的任务，我觉得有些值得记录的观察..."）

**变体 B — 周回顾**
每周一次的自动反思（周一早上），回顾过去 7 天的 task outcome 模式。这不是实时触发，而是定时总结。

**变体 C — 会话结束触发**
当用户的会话持续超过 10 轮且完成了 ≥2 个任务时，在会话结束前触发轻量反思。

**风险评估**：变体 A 的打扰风险最低，因为它只在显著事件时触发。变体 B 的风险是如果用户没有足够数据，反思内容会很空洞。变体 C 的风险最高，因为频繁触发。

---

### FIX-17: Context pruner 关键词升级

#### 问题背景
`context_pruner.py:223` 的 `_is_high_importance_message` 使用 8 个硬编码关键词判断消息重要性：
```python
high_priority_keywords = ["计划", "任务", "阶段", "里程碑", "目标", "记住", "注意", "修改", "变更"]
```

"我最近压力很大，想调整一下学习节奏" 这句话不包含任何关键词，会被 Tier 2 压缩。

#### 修复方案

**方案 A: 扩展关键词列表**（XS，5 分钟）
添加情绪/压力/社交相关关键词：
```python
high_priority_keywords = [
    # 现有的
    "计划", "任务", "阶段", "里程碑", "目标", "记住", "注意", "修改", "变更",
    # 新增
    "压力", "焦虑", "情绪", "困惑", "迷茫", "不行", "放弃", "调整", "节奏", "状态",
    "反思", "回顾", "总结", "感受", "担心", "紧张",
]
```

风险：列表膨胀、维护成本高。

**方案 B: 使用消息来源标记**（S，30 分钟）
当消息是由 Aurora 的反思/校正/情绪检测等功能生成时，在消息 metadata 中标记 `high_importance=True`。Pruner 直接检查 metadata。

风险：需要在所有生成重要消息的地方添加标记。

**方案 C: 保留 tool_calls 判断 + 方案 A**（推荐）
现有逻辑已经保留所有 tool_calls 消息（line 220）。情绪相关消息通常伴随 Aurora 的认知干预（tool call），所以可能已经被保留。方案 A 作为补充覆盖即可。

---

### FIX-18: 校正端到端效果量化

#### 问题背景
校正后 self-model confidence 降 0.05，但不知道这个变化是否足以让路由器改变模式。可能需要积累多次校正才能产生实际行为变化。

#### 修复方案

**不是代码修复，是验证任务**：

创建一个端到端测试（或 acceptance script），模拟：
1. 用户状态初始化（strategy_confidence=0.7）
2. 连续 3 次校正（disconfirming）
3. 观察每次校正后路由器的 `DualCoreDecision.mode` 是否变化
4. 记录从 `execution_first` 切换到 `cognitive_first` 需要的校正次数

这可以作为 `backend/scripts/ai_correction_effect_acceptance.py` 实现。

#### 涉及文件
1. `backend/scripts/ai_correction_effect_acceptance.py` — 新文件
