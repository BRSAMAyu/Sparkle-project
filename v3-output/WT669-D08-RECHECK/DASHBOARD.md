# WT397 · D-08 数据飞轮纵向评估 — Dashboard（程序化生成）

- spec `d08_flywheel_spec.v1` · metrics `d08_flywheel_metrics.v1` · population 10

## 验收总览（逐 persona ≥1 条 adaptation 因果链）

- 通过 10/10（链型计数 {"memory_quieter": 10, "journey_correction": 4}）
- 未通过者保留在案：[]
- 无效/无效力个性化台账：**5 条（保留不筛）**

## Fleet 级五维状态迁移（Day0 → Day7，按 persona 计数）

- **coverage**: {"unknown->ok": 10}
- **correctness**: {"ok->ok": 10}
- **scope_precision**: {"unknown->ok": 10}
- **freshness**: {"unknown->ok": 10}
- **utility**: {"unknown->unknown": 10}

- 被跟随决策匹配分均值：Day0 `0.6` → Day7 `0.7`

## 逐 persona 配对结果

| persona | 验收 | 经由 | 链 | 无效台账 | 对照侵入(fly/no_fb) |
|---|---|---|---|---|---|
| p01_experience_reinforce | PASS | memory_quieter | policy_patch×;memory_quieter✓;policy_patch× | 2 | 0/0 |
| p02_experience_hysteresis | PASS | journey_correction+memory_quieter+journey_correction | journey_correction✓;policy_patch×;memory_quieter✓;journey_correction✓;policy_patch× | 0 | 0/0 |
| p03_explicit_difficulty | PASS | journey_correction+memory_quieter | journey_correction✓;policy_patch×;memory_quieter✓;policy_patch× | 0 | 0/0 |
| p04_ambiguous_weak | PASS | journey_correction+memory_quieter | journey_correction✓;policy_patch×;memory_quieter✓;policy_patch× | 1 | 0/0 |
| p05_correction_loop | PASS | memory_quieter | memory_quieter✓ | 0 | 0/0 |
| p06_structural_gap | PASS | memory_quieter | memory_quieter✓ | 0 | 0/0 |
| p07_plan_drift_entry | PASS | memory_quieter | memory_quieter✓ | 0 | 0/0 |
| p08_skill_repeat | PASS | memory_quieter | policy_patch×;memory_quieter✓;policy_patch× | 2 | 0/0 |
| p09_choice_feedback | PASS | memory_quieter | memory_quieter✓ | 0 | 0/0 |
| p10_quiet_then_tooling | PASS | memory_quieter | memory_quieter✓ | 0 | 0/0 |

## 五维逐 persona（Day0 → Day7 配对差）

### p01_experience_reinforce

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match primary->primary, followed explain->explain
- outcome: associations +2

### p02_experience_hysteresis

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match wrong->wrong, followed practice->remind
- outcome: associations +2

### p03_explicit_difficulty

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match secondary->secondary, followed practice->practice
- outcome: associations +2

### p04_ambiguous_weak

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match secondary->primary, followed practice->split
- outcome: associations +2

### p05_correction_loop

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match None, followed None
- outcome: associations +0

### p06_structural_gap

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match None, followed None
- outcome: associations +0

### p07_plan_drift_entry

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match None, followed None
- outcome: associations +0

### p08_skill_repeat

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match primary->primary, followed practice->practice
- outcome: associations +2

### p09_choice_feedback

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match None, followed None
- outcome: associations +0

### p10_quiet_then_tooling

- coverage: unknown->ok(0.3333)
- correctness: ok->ok(0.3333)
- scope_precision: unknown->ok(1.0)
- freshness: unknown->ok(0.2)
- utility: unknown->unknown
- memory: stale_surfaced True->False, stale_confidence None
- intervention: match None, followed None
- outcome: associations +0


（内容摘要 sha256[:16] = eb3cf6b8163f7188）
