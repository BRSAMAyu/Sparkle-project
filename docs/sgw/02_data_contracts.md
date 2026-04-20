# SGW v2 数据契约

> 版本: 1.1 | 日期: 2026-04-21 | 状态: FROZEN (审查修订版)
> 这些 JSON schema 定义了跨阶段的数据落盘格式。所有 Phase 代码必须遵循。

---

## 1. 存储层：SQLite

文件位置：`.sgw_state/sgw_runs.db`

### 1.1 runs 表

```sql
CREATE TABLE runs (
    run_id          TEXT PRIMARY KEY,          -- UUID
    scenario_id     TEXT NOT NULL,             -- "stage_16_rule_y"
    config_hash     TEXT NOT NULL,             -- SHA-256 of full config
    git_sha         TEXT NOT NULL,
    started_at      TEXT NOT NULL,             -- ISO 8601
    ended_at        TEXT,                      -- ISO 8601, NULL if running
    status          TEXT NOT NULL DEFAULT 'running',  -- running|completed|failed|stopped
    scenario_config TEXT NOT NULL,             -- JSON: full config snapshot
    prompt_hashes   TEXT NOT NULL,             -- JSON: {prompt_file: sha256}
    model_versions  TEXT NOT NULL,             -- JSON: {role: model_name}
    summary         TEXT                       -- JSON: final metrics
);
-- CHECK constraints for ISO 8601 timestamps
-- SQLite doesn't have native datetime, but we enforce format via application layer
```

### 1.2 sessions 表

```sql
CREATE TABLE sessions (
    session_id      TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    task_id         TEXT NOT NULL,             -- UUID
    role            TEXT NOT NULL,             -- "persona" | "adversarial"
    seed_persona_id TEXT,                      -- 来源 persona ID
    persona_sample  TEXT NOT NULL,             -- JSON: full PersonaSample
    arc_id          TEXT,                      -- ConversationArc ID
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending|running|completed|failed
    target_turns    INTEGER NOT NULL DEFAULT 12,
    turns_completed INTEGER NOT NULL DEFAULT 0,
    -- NOTE: transcript removed from sessions; reconstruct via turns table JOIN
    detected_memory_ids TEXT,                  -- JSON: [memory_id]
    revoke_scheduled INTEGER DEFAULT 0,        -- boolean
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    completed_at    TEXT
);
```

### 1.3 turns 表

```sql
CREATE TABLE turns (
    turn_id         TEXT PRIMARY KEY,          -- "{session_id}_{turn_index}"
    session_id      TEXT NOT NULL REFERENCES sessions(session_id),
    turn_index      INTEGER NOT NULL,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),

    -- 对话内容
    user_message    TEXT NOT NULL,
    ai_response     TEXT NOT NULL,

    -- 状态机决策
    turn_decision   TEXT,                      -- JSON: TurnDecision
    state_machine_state TEXT,                  -- 当前 beat / 阶段
    ai_behavior_class TEXT,                    -- AIBehaviorClass

    -- 元数据
    latency_ms      INTEGER,                  -- AI 回复延迟
    model_used      TEXT,                      -- 使用的表达层模型
    created_at      TEXT NOT NULL
);
```

### 1.4 audits 表

```sql
CREATE TABLE audits (
    audit_id        TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    session_id      TEXT REFERENCES sessions(session_id),
    target_id       TEXT NOT NULL,             -- memory_id or session_id
    audit_type      TEXT NOT NULL,             -- "compliance" | "authenticity"
    status          TEXT NOT NULL DEFAULT 'pending',

    -- 评分
    scores          TEXT,                      -- JSON: {dimension: float}
    overall         REAL,
    is_violation    INTEGER,                   -- boolean (soft violation / not authentic)
    reason          TEXT,

    -- 审计模型
    audit_model     TEXT NOT NULL,
    audit_provider  TEXT NOT NULL,

    created_at      TEXT NOT NULL,
    completed_at    TEXT
);
```

### 1.5 violations 表

```sql
CREATE TABLE violations (
    violation_id    TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    session_id      TEXT REFERENCES sessions(session_id),
    turn_id         TEXT REFERENCES turns(turn_id),
    code            TEXT NOT NULL,             -- "SGW-H001" ... "SGW-H007"
    severity        TEXT NOT NULL,             -- "hard" | "soft"
    context         TEXT,                      -- JSON: violation details
    created_at      TEXT NOT NULL
);
```

### 1.6 experiments 表（Phase 4 时创建，Phase 1 不创建）

> **FUTURE**: 这些表在 Phase 4 进入实现时才创建。Phase 1-3 只使用 runs/sessions/turns/audits/violations 五张表。

```sql
CREATE TABLE experiments (
    experiment_id   TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    hypothesis_id   TEXT REFERENCES hypotheses(hypothesis_id),
    status          TEXT NOT NULL DEFAULT 'planned',

    -- 实验设计
    control_config_hash  TEXT NOT NULL,
    treatment_config_hash TEXT NOT NULL,
    manipulated_variable TEXT NOT NULL,
    controlled_variables TEXT NOT NULL,         -- JSON array
    sample_size     INTEGER NOT NULL,

    -- 结果
    result          TEXT,                      -- JSON: ExperimentResult
    conclusion      TEXT,                      -- "adopt" | "reject" | "inconclusive"
    created_at      TEXT NOT NULL,
    completed_at    TEXT
);
```

### 1.7 hypotheses 表（Phase 4 时创建）

> **FUTURE**: 同 experiments 表。

```sql
CREATE TABLE hypotheses (
    hypothesis_id   TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    statement       TEXT NOT NULL,
    evidence_refs   TEXT NOT NULL,             -- JSON: [session_id/turn_id]
    affected_dimensions TEXT,                  -- JSON array
    affected_persona_axes TEXT,                -- JSON
    candidate_causes TEXT NOT NULL,            -- JSON: [{cause_id, description, likelihood}]
    status          TEXT NOT NULL DEFAULT 'proposed',
    created_at      TEXT NOT NULL,
    verified_at     TEXT
);
```

### 1.8 iterations 表（Phase 4 时创建）

> **FUTURE**: 同 experiments 表。

```sql
CREATE TABLE iterations (
    iteration_id    TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    timestamp       TEXT NOT NULL,

    -- 触发
    trigger         TEXT NOT NULL,             -- "scheduled" | "threshold" | "manual"
    trigger_data    TEXT,                      -- JSON

    -- 假设和实验
    hypothesis_ids  TEXT,                      -- JSON: [hypothesis_id]
    selected_hypothesis TEXT,
    experiment_id   TEXT REFERENCES experiments(experiment_id),

    -- 决策
    action_taken    TEXT NOT NULL,             -- "config_updated" | "no_change" | "escalate"
    config_changes  TEXT,                      -- JSON: what changed
    reason          TEXT,

    -- 多样性
    diversity_metrics TEXT,                    -- JSON
    diversity_alert  INTEGER DEFAULT 0,        -- boolean

    -- 完整报告
    report_path     TEXT                       -- Markdown 文件路径
);
```

### 1.9 索引

```sql
-- Phase 1 核心索引
CREATE INDEX idx_sessions_run ON sessions(run_id);
CREATE INDEX idx_sessions_run_status ON sessions(run_id, status);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_persona ON sessions(seed_persona_id);
CREATE INDEX idx_turns_session ON turns(session_id);
CREATE INDEX idx_turns_session_turn ON turns(session_id, turn_index);
CREATE INDEX idx_turns_run ON turns(run_id);
CREATE INDEX idx_turns_behavior ON turns(ai_behavior_class);
CREATE INDEX idx_audits_run ON audits(run_id);
CREATE INDEX idx_audits_run_type ON audits(run_id, audit_type);
CREATE INDEX idx_audits_type ON audits(audit_type);
CREATE INDEX idx_audits_target ON audits(target_id);
CREATE INDEX idx_violations_run ON violations(run_id);
CREATE INDEX idx_violations_code ON violations(code);

-- Phase 4+ 索引（创建表时一并创建）
CREATE INDEX idx_experiments_run ON experiments(run_id);
CREATE INDEX idx_hypotheses_run ON hypotheses(run_id);
CREATE INDEX idx_iterations_run ON iterations(run_id);
```

### 1.10 Schema 初始化

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;           -- 并发读写
PRAGMA synchronous = NORMAL;         -- 性能和安全平衡
```

---

## 2. 文件格式

### 2.1 PersonaSample JSON

```json
{
  "sample_id": "ps_a1b2c3d4",
  "seed_persona_id": "core_middle_exam_fragmented",
  "rng_seed": 42,
  "behavior": {
    "compliance": 0.3,
    "digression_rate": 0.4,
    "challenge_tendency": 0.2,
    "responsiveness": 0.7,
    "emotion_intensity": 0.5
  },
  "narrative": {
    "opening_motivation": "考试失利",
    "arc_shape": "decline_then_recovery",
    "topic_jump_probability": 0.15,
    "beats": [
      {
        "beat_id": "beat_1",
        "turn_range": [1, 3],
        "emotional_vector": "低落",
        "topic_hint": "抱怨最近的考试",
        "allow_skip": false,
        "transition_triggers": ["ai_gives_encouragement", "user_asks_for_help"]
      },
      {
        "beat_id": "beat_2",
        "turn_range": [4, 7],
        "emotional_vector": "好奇",
        "topic_hint": "试探性地尝试 AI 的建议",
        "allow_skip": true,
        "transition_triggers": ["user_encounters_difficulty", "user_changes_topic"]
      },
      {
        "beat_id": "beat_3",
        "turn_range": [8, 12],
        "emotional_vector": "振奋",
        "topic_hint": "有点进展但不确定，寻求确认",
        "allow_skip": false,
        "transition_triggers": []
      }
    ]
  },
  "expression": {
    "sentence_length": "short",
    "colloquialisms": ["嗯", "就是", "反正"],
    "emoji_rate": 0.05,
    "typo_rate": 0.02,
    "code_switch_rate": 0.0
  }
}
```

### 2.2 TurnDecision JSON

```json
{
  "direction": "回应建议",
  "target_reference": "AI 刚才提到的第一步",
  "emotional_tone": "半信半疑",
  "must_include": [],
  "must_avoid": ["empty_acknowledgment"],
  "source": "state_machine",
  "confidence": 0.85
}
```

### 2.3 ComplianceAuditResult JSON

```json
{
  "audit_id": "aud_x1y2z3",
  "target_record_id": "mem_abc123",
  "dimensions": {
    "metadata_correctness": 0.92,
    "semantic_fidelity": 0.88,
    "entity_boundary": 0.75,
    "time_anchor_validity": 0.95,
    "confidence_calibration": 0.85
  },
  "overall": 0.87,
  "is_soft_violation": false,
  "reason": "entity_boundary 偏低：系统将用户的第三人称描述推断为被提及者的状态",
  "audit_model": "glm-4.7",
  "audit_provider": "zhipu"
}
```

### 2.4 AuthenticityAuditResult JSON

```json
{
  "audit_id": "aud_auth_x1y2",
  "session_id": "ses_abc123",
  "dimensions": {
    "conversational_responsiveness": 0.85,
    "persona_consistency": 0.90,
    "arc_progression": 0.75,
    "emotional_authenticity": 0.80,
    "linguistic_naturalness": 0.88
  },
  "overall": 0.84,
  "is_authentic": true,
  "failure_patterns": [],
  "audit_model": "claude-opus-4-6",
  "audit_provider": "anthropic"
}
```

### 2.5 IterationReport Markdown（文件路径格式）

```
docs/sgw/iterations/{YYYY-MM-DD}_iter_{N}.md
```

模板：
```markdown
# Iteration {N} — {YYYY-MM-DD}

## Trigger
{为什么触发这次迭代}

## Hypotheses
1. {假设1}: {证据}
2. {假设2}: {证据}
3. {假设3}: {证据}

## Selected: {选中的假设}
{为什么选这个}

## Experiment
- Control: {config_hash}, {N} sessions
- Treatment: {改了什么}, {N} sessions
- Metric: {看什么指标}

## Result
- Control: {metric} = {value}
- Treatment: {metric} = {value}
- p-value: {value}, effect size: {value}

## Decision
{采纳/拒绝/不确定}。原因：{...}

## Config Changes
```json
{具体改了什么参数}
```

## Diversity Check
{persona 轴覆盖率、AI 行为分布等}
```

---

## 3. 向后兼容

### 3.1 与现有 checkpoint 的兼容

`sgw_checkpoint.json` 继续存在，但 Phase 1 完成后同步写入 SQLite。

迁移策略：
1. Phase 1 上线时，`_checkpoint()` 同时写 JSON + SQLite
2. `_load_checkpoint()` 优先读 SQLite，fallback 到 JSON
3. 一个 Phase 后废弃 JSON checkpoint

### 3.2 与现有 metrics 的兼容

`MetricsCollector` 继续用于实时进度报告，但所有持久化走 SQLite。
`metrics_collector.py` 增加一个 `flush_to_db()` 方法。

### 3.3 与现有 report 的兼容

`SPARKLE_AURORA_STAGE16_SGW_REPORT_2026-04-20.md` 格式保留。
增加一份新格式的详细报告，从 SQLite 查询生成。
