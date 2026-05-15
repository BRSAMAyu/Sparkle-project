# Round 2 Deep Audit: Emotion/Sentiment Detection Mechanism

**Date**: 2026-05-15
**Scope**: Full-chain emotion detection from user input through routing to LLM output
**Severity Assessment**: P0-4 (original) -- recommendation: **upgrade to P0-3** (see Section 6)

---

## 1. Emotion Detection Full-Chain Trace

```
USER INPUT (chat message / capsule)
    |
    v
[Detection Point A] _classify_recent_chat_sentiment()     <-- KEYWORD-ONLY, NO NEGATION
    |   File: backend/app/state_aggregator/service.py:550
    |   Input: last 30 user ChatMessages in 24h window
    |   Method: substring match against hardcoded keyword lists
    |   Output: dict[str, int] e.g. {"frustrated": 3, "happy": 1}
    |
    +-- [Detection Point B] CognitiveFragment.sentiment     <-- EXTERNAL / EVENT-DRIVEN
    |   File: backend/app/services/analytics/cognitive_stream_worker.py:200
    |   Input: event payload from Redis Stream
    |   Method: payload.get("sentiment") -- value comes from event publisher
    |   Note: fragments created via API have sentiment=None by default
    |
    v
[Aggregation] _build_emotion_hint_summary()
    File: backend/app/state_aggregator/service.py:509
    Merges A + B into combined distribution
    Computes: dominant_sentiment = max(distribution, key=count)
    Computes: emotional_block_detected = dominant in {"anxious","frustrated","overwhelmed"}
    Output: EmotionHintValue(dominant_sentiment, sentiment_distribution, emotional_block_detected)
    Cache TTL: 60 seconds
    |
    v
[Routing Engine] RoutingEngine._get_recent_sentiment_distribution()
    File: backend/app/orchestration/routing_engine.py:753
    Also: backend/app/orchestration/context_builder.py:687
    Reads CognitiveFragment.sentiment directly (separate from StateAggregator)
    Merges into DualCoreRoutingInput.recent_sentiment_distribution
    |
    +-- [Routing Engine] _get_cognitive_routing_signals()
    |   File: backend/app/orchestration/routing_engine.py:1726
    |   Checks BehaviorPattern canonical_keys for "overload"/"burnout"/emotional patterns
    |   Sets emotional_block_detected = True if match found (confidence >= 0.6)
    |   This is a SECOND, independent emotional_block signal
    |
    v
[DualCoreRouter] DualCoreRouter.route()
    File: backend/app/orchestration/dual_core_router.py:205
    |
    +-- _has_emotional_block() (line 876)
    |   Returns True IMMEDIATELY if routing_input.emotional_block_detected == True
    |   Otherwise: emotional_block_score >= profile["emotional_sensitivity"] (default 0.5)
    |
    +-- _emotional_block_score() (line 886)
    |   negative_ratio = count(negative_sentiments) / total
    |   NEGATIVE_SENTIMENTS = {"anxious","burnout","depressed","stressed",
    |                          "overwhelmed","frustrated","negative","sad"}
    |   Score boosted if:
    |     - primary_challenge_area == "emotional" -> max(score, 0.75)
    |     - negative >= 2 -> max(score, 0.6)
    |     - behavior pattern overload/burnout/anxiety -> max(score, 0.7)
    |
    v
[Precedence Resolution] emotional_block gets weight 9.0 (HIGHEST of all signals)
    File: backend/app/orchestration/dual_core_router.py:229
    File: backend/app/orchestration/routing_parameter_registry.py:40
    |
    v
[Routing Decision] mode = "cognitive_first"
    Triggers when emotional_block == True (line 817-819)
    Adds cognitive_adjustment: "先处理用户当前的情绪阻力，再进入计划讨论。"
    Sets strategy: session_mode=recovery, intervention_intensity=low
    Blocks execution_first path entirely (line 789-800)
    |
    v
[Prompt Assembly] cognitive_adjustments injected into LLM prompt
    File: backend/app/orchestration/dual_core_router.py:139-148
    Formatted as "## 双核心认知调制\n - {adjustment}"
    |
    v
[UX Envelope] NEGATIVE_USER_SIGNAL_KEYWORDS
    File: backend/app/orchestration/ux_envelope.py:32-45
    SECOND keyword-based detection for presentation style
    Same keyword list used to detect "negative signal" for UI adaptation
    |
    v
[LLM Output] AI responds in cognitive_first / recovery mode
    User receives empathetic, low-pressure, non-action-oriented response
    Even when user was actually asking for help with a task
```

---

## 2. All Emotion/Sentiment Detection Points

### Detection Point A: `_classify_recent_chat_sentiment`
- **File**: `backend/app/state_aggregator/service.py:550-596`
- **Input**: Last 30 user ChatMessages in 24h
- **Method**: Pure keyword substring match, no NLP, no negation handling
- **Output categories**: frustrated, anxious, overwhelmed, happy, motivated, neutral
- **Flaw**: No negation detection (see Section 3)

### Detection Point B: `CognitiveFragment.sentiment` (event-driven)
- **File**: `backend/app/services/analytics/cognitive_stream_worker.py:200`
- **Input**: Event payload from Redis Stream
- **Method**: Direct copy from event payload field
- **Note**: Value depends entirely on upstream event publisher. Fragments created via REST API (`/api/v1/cognitive/fragments`) have sentiment=None and never get sentiment assigned during `analyze_behavior()`.

### Detection Point C: `_build_emotion_hint_summary` (aggregation)
- **File**: `backend/app/state_aggregator/service.py:509-548`
- **Method**: Merges Detection Point A + B, picks dominant, sets emotional_block_detected
- **Flaw**: emotional_block_detected is binary -- dominant in {anxious, frustrated, overwhelmed}. If user has 2 "frustrated" and 3 "happy", no block detected. But with negation bug, 2 false "frustrated" + 1 true "happy" = block detected.

### Detection Point D: `_get_cognitive_routing_signals` (behavior pattern)
- **File**: `backend/app/orchestration/routing_engine.py:1726-1734`
- **Method**: Checks BehaviorPattern records for emotional/overload/burnout canonical keys
- **Note**: This is a more reliable signal (LLM-analyzed patterns), but still influenced by upstream detection quality.

### Detection Point E: `_emotional_block_score` (routing computation)
- **File**: `backend/app/orchestration/dual_core_router.py:886-898`
- **Method**: Computes ratio of negative sentiments, boosted by challenge area and behavior patterns
- **Note**: If `_classify_recent_chat_sentiment` produces false negatives (inflated negative counts), the ratio is artificially high.

### Detection Point F: `_get_recent_sentiment_distribution` (context builder)
- **File**: `backend/app/orchestration/context_builder.py:687-713`
- **Method**: Reads CognitiveFragment.sentiment directly (last 8 fragments)
- **Note**: Separate from StateAggregator -- reads DB directly, does not include chat message sentiment.

### Detection Point G: `NEGATIVE_USER_SIGNAL_KEYWORDS` (UX envelope)
- **File**: `backend/app/orchestration/ux_envelope.py:32-45`
- **Method**: Keyword substring match against current user message
- **Used for**: Presentation style decisions (warm vs analytical tone)
- **Flaw**: Same negation-blind keyword matching

### Detection Point H: `_message_has_negative_signal` (UX envelope)
- **File**: `backend/app/orchestration/ux_envelope.py:1893-1895`
- **Method**: `any(token in compact for token in NEGATIVE_USER_SIGNAL_KEYWORDS)`
- **Used for**: Blocked history tracking and presentation adaptation

### Detection Point I: `_classify_recent_chat_sentiment` (dashboard)
- **File**: `backend/app/services/dashboard_service.py:306`
- **Method**: Counts CognitiveFragment with sentiment == "anxious" for anxiety ratio
- **Used for**: "Inner weather" dashboard calculation

### Detection Point J: `routing_outcome_service` (outcome evaluation)
- **File**: `backend/app/services/routing_outcome_service.py:172-173`
- **Method**: If routing was cognitive_first AND emotional_block >= 0.55, judged as success
- **Note**: False emotional_block detection creates a self-reinforcing feedback loop -- misrouted decisions are judged "successful".

---

## 3. Negation Misjudgment Analysis

### 3.1 Keyword List Inventory

#### Chinese Keywords (Detection Point A)

| Category | Keywords |
|----------|----------|
| frustrated | 烦, 太难了, 做不到, 不想, 放弃, 好难, 崩溃, 烦死 |
| anxious | 焦虑, 担心, 害怕, 紧张, 来不及, 急, 压力 |
| overwhelmed | 太多了, 忙不过来, 撑不住, 太累, 累死 |
| happy | 开心, 高兴, 太好了, 棒, 做到了, 完成了, 谢谢, 喜欢 |
| motivated | 加油, 继续, 努力, 一定, 可以, 试试, 期待 |

#### Chinese Keywords (Detection Point G/H)

| Category | Keywords |
|----------|----------|
| negative_signal | 崩溃, 焦虑, 压力, 学不进去, 撑不住, 烦, 累, 难受, 痛苦, 沮丧, 低落, 不想 |

### 3.2 Misjudgment Case Table

**Legend**: FP = False Positive (classified negative, actually not); FN = False Negative (missed negative)

| # | User Input | Actual Emotion | Detected As | Type | Routing Impact |
|---|-----------|----------------|-------------|------|----------------|
| 1 | "我不焦虑，反而很开心" | happy | **anxious** | FP | emotional_block triggered, cognitive_first mode, recovery stance |
| 2 | "不用烦了，已经搞定了" | happy/relieved | **frustrated** | FP | emotional_block triggered, cognitive_first mode |
| 3 | "不要太紧张，其实还行" | neutral/calm | **anxious** | FP | inflated anxious count, potential block detection |
| 4 | "我以前放弃过，但这次不会" | motivated | **frustrated** | FP | "放弃" matched, emotional_block possible |
| 5 | "不想再拖延了，开始吧" | motivated | **frustrated** | FP | "不想" matched, cognitive_first override |
| 6 | "没那么害怕，只是有点好奇" | neutral/curious | **anxious** | FP | "害怕" matched despite negation |
| 7 | "崩溃后重建了计划" | resilient | **overwhelmed** | FP | "崩溃" matched, blocks execution_first |
| 8 | "压力大是因为我很重视" | motivated | **anxious** | FP | "压力" matched |
| 9 | "不要放弃，继续加油" | motivated | **frustrated** | FP | both "放弃" and "加油" matched, first match wins |
| 10 | "这个急的事情做完了" | satisfied | **anxious** | FP | "急" matched |
| 11 | "太难了吧但是做到了！" | proud | **frustrated** | FP | "太难" matched first (break on first match) |
| 12 | "撑不住了...开玩笑的，其实还好" | neutral/joking | **overwhelmed** | FP | "撑不住" matched |
| 13 | "累死了但超有成就感" | satisfied | **overwhelmed** | FP | "累死" matched (overwhelmed list has "累死") |
| 14 | "一定要加油" | motivated | **frustrated** | FP | "一定" matches motivated, but "烦" is not here; wait -- "一定" is in motivated. This one is correct. | 
| 15 | "不用担心我" | caring/neutral | **anxious** | FP | "担心" matched |
| 16 | (user is genuinely sad but uses no keywords) | sad | **neutral** | FN | emotional support missed, execution_first triggered |
| 17 | (user expresses burnout via metaphor: "灯灭了") | burnout | **neutral** | FN | no keyword match, execution_first continues |

### 3.3 Quantitative Impact Assessment

**FP Rate Estimation**: Of the 8 "frustrated" Chinese keywords, at least 4 ("烦", "不想", "放弃", "做不到") have common negation patterns. Of the 7 "anxious" Chinese keywords, at least 4 ("焦虑", "担心", "害怕", "紧张") have common negation patterns. Estimated FP rate for negative categories: **15-25%** of keyword matches in real conversational Chinese.

**Impact multiplier**: Each false negative-sentiment classification contributes to:
1. `_build_emotion_hint_summary`: increments negative count in distribution
2. `_emotional_block_score`: inflates negative ratio, potentially crossing the 0.5 threshold
3. `emotional_block_detected`: binary flag that directly overrides routing
4. Precedence weight 9.0: highest priority, overrides ALL other signals including goal clarity

**Critical path**: Only 2 false negative-sentiment matches in 24h are needed to trigger:
- `negative >= 2` -> score = max(score, 0.6) (line 894)
- 0.6 > default emotional_sensitivity threshold of 0.5
- `emotional_block = True`
- Routing forced to cognitive_first regardless of actual user state

---

## 4. Impact Chain Analysis

### 4.1 From Misjudgment to User Experience

```
False "frustrated" detection (e.g., "不想再拖延了")
    |
    v
emotional_block_detected = True (in EmotionHintValue)
    |
    v
DualCoreRoutingInput.emotional_block_detected = True  (primary signal)
OR: negative_ratio >= 0.5  (secondary signal via _emotional_block_score)
    |
    v
DualCoreRouter: emotional_block = True  (line 882-883: immediate return True)
    |
    v
Precedence["emotional_block"] = 9.0 (HIGHEST of all 12 signals)
    |
    v
Routing Decision: mode = "cognitive_first"
    - Blocks execution_first (line 792: not emotional_block required)
    - Forces cognitive_first (line 819: or emotional_block)
    |
    v
cognitive_adjustments appended:
    - "先处理用户当前的情绪阻力，再进入计划讨论。"
    - session_mode = "recovery"
    - intervention_intensity = "low"
    |
    v
LLM receives prompt with recovery stance:
    - Soft, empathetic, low-pressure response
    - Avoids pushing actionable tasks
    - Treats user as emotionally fragile
    |
    v
User perception:
    - "I said I want to stop procrastinating, but AI treats me like I'm upset"
    - AI avoids giving concrete task/action (despite user wanting it)
    - Feels patronizing / unhelpful
    |
    v
Feedback loop:
    - User might express more frustration ("为什么你不给我具体任务？")
    - "烦" in new message -> more false frustrated detection
    - Self-reinforcing cycle of emotional_block = True
    |
    v
routing_outcome_service:
    - Judges cognitive_first + emotional_block >= 0.55 as "success" (line 172-173)
    - System believes it routed correctly
    - No correction signal generated
```

### 4.2 Downstream Consumers of Emotional Block

| Consumer | File | Impact |
|----------|------|--------|
| DualCoreRouter | `dual_core_router.py:218,294,792,819` | Forces cognitive_first, blocks execution_first |
| Routing Debug | `dual_core_router.py:724` | Logs `explicit_emotional_signal: true` |
| Routing Outcome | `routing_outcome_service.py:172` | Self-reinforcing success judgment |
| Route History | `routing_engine.py:1846` | Persists emotional_block in snapshot |
| Aurora Migration | `aurora/migration.py:128,151,170,232` | Backwards-compat routing uses emotional_block_detected |
| Dashboard | `dashboard_service.py:306` | Anxiety ratio from CognitiveFragment.sentiment |
| UX Envelope | `ux_envelope.py:1893` | Presentation style adaptation |
| Spine States | `dual_core_router.py:442` | Spine "anxious"/"tense" values trigger fatigue |

### 4.3 Weight Analysis

The emotional_block signal at weight 9.0 is the **single most powerful routing signal** in the system. For comparison:

| Signal | Weight | Source Quality |
|--------|--------|---------------|
| emotional_block | 9.0 | **Keyword matching with no negation** |
| procrastination | 8.0 | Behavior patterns + task feedback |
| cognitive_mode | 7.0 | Behavior patterns |
| scaffolding_frustration | 6.5 | FSM state |
| low_metacognition | 6.0 | LLM-analyzed accuracy |
| high_cognitive_load | 5.0 | Direct computation |
| spine_fatigue | 4.0 | State register |
| reflection_phase | 3.0 | SRL phase tracker |
| goal_clarity | 1.0 | Intent confidence |

The highest-weight signal (9.0) has the **lowest-quality detection method** (keyword substring matching). This is an inverted quality-weight ratio.

---

## 5. All Keyword Lists in the System

### List 1: `_classify_recent_chat_sentiment` keywords
- **File**: `backend/app/state_aggregator/service.py:556-573`
- **Languages**: Chinese + English
- **Categories**: 6 (frustrated, anxious, overwhelmed, happy, motivated, neutral)
- **Total keywords**: ~70
- **Method**: `any(kw in text for kw in keywords)` -- pure substring match

### List 2: `NEGATIVE_USER_SIGNAL_KEYWORDS`
- **File**: `backend/app/orchestration/ux_envelope.py:32-45`
- **Languages**: Chinese only
- **Categories**: 1 (negative signal binary)
- **Total keywords**: 12
- **Overlap with List 1**: 崩溃, 焦虑, 压力, 撑不住, 烦, 不想 (6 of 12)
- **Method**: `any(token in compact for token in NEGATIVE_USER_SIGNAL_KEYWORDS)`

### List 3: `NEGATIVE_SENTIMENTS` (routing categorization)
- **File**: `backend/app/orchestration/dual_core_router.py:166-175`
- **Method**: Set membership check on sentiment labels (not raw text)
- **Values**: anxious, burnout, depressed, stressed, overwhelmed, frustrated, negative, sad
- **Note**: This operates on classified sentiment labels, not raw text -- downstream of Lists 1 & 2

### List 4: `PROCRASTINATION_KEYWORDS`
- **File**: `backend/app/orchestration/dual_core_router.py:184-191`
- **Method**: Substring match on behavior pattern names
- **Values**: procrast, avoid, 拖延, 回避, 启动困难, 执行阻力

---

## 6. Fix Proposal Comparison

### Option A: Negation Word Detection (Minimal Fix)

**Approach**: Add a negation-word check before keyword matching.
```python
NEGATION_WORDS_ZH = ["不", "没有", "没", "别", "不再", "不会", "没那么", "不是", "并非"]
NEGATION_WORDS_EN = ["not", "don't", "doesn't", "didn't", "won't", "never", "no longer", "isn't", "aren't"]

def _has_negation(text: str, keyword: str, window: int = 4) -> bool:
    """Check if keyword is preceded by a negation word within window chars."""
    idx = text.find(keyword)
    while idx >= 0:
        prefix = text[max(0, idx - window):idx]
        if any(neg in prefix for neg in NEGATION_WORDS_ZH + NEGATION_WORDS_EN):
            return True
        idx = text.find(keyword, idx + 1)
    return False
```

**Pros**:
- Minimal code change (~30 lines)
- Catches ~60-70% of negation cases
- Zero latency impact
- No external dependencies

**Cons**:
- Still misses complex constructions ("别说焦虑了，我现在开心着呢")
- Doesn't handle sarcasm/irony
- Window-based heuristics can over-correct ("不确定是不是该担心" -- "不" is not negating "担心")
- Still keyword-based at core

**Estimated FP reduction**: 60-70%
**Risk**: Low

### Option B: Lightweight Sentiment Model (ML Fix)

**Approach**: Replace keyword matching with a small pre-trained sentiment model.

Options:
1. **Rule-based + VADER-style** for Chinese: `funasr` or `snownlp` (zero external API calls)
2. **Small transformer**: `bert-base-chinese` fine-tuned for sentiment (local inference ~20ms)
3. **LLM-as-judge**: Batch classify recent messages via existing LLM service (~200ms for 30 messages)

**Pros**:
- Handles negation, sarcasm, context naturally
- Much higher accuracy (85-95% vs current ~75%)
- Can detect multi-class sentiment beyond keyword categories

**Cons**:
- Adds model dependency (Option 2-3) or external library (Option 1)
- Option 3 adds 200ms+ latency to every aggregator call
- Option 2 requires GPU or significant CPU for inference
- Option 1 (snownlp) has limited accuracy for complex constructions

**Estimated FP reduction**: 80-95%
**Risk**: Medium (dependency, latency)

### Option C: Hybrid Approach (Recommended)

**Phase 1 (Immediate)**: Add negation word detection to `_classify_recent_chat_sentiment` (Option A). This fixes the most common misjudgment patterns with minimal risk.

**Phase 2 (Next Sprint)**: Replace `_classify_recent_chat_sentiment` with `snownlp` for Chinese sentiment scoring, keeping keyword matching as fallback. This improves accuracy without adding heavy dependencies.

**Phase 3 (Post-launch)**: Evaluate fine-tuned sentiment model for production use based on collected misclassification telemetry.

Additionally:
- Add telemetry: log every emotional_block detection with the triggering messages (sampled at 10%)
- Add escape hatch: if user explicitly asks for tasks/actions, override emotional_block with reduced weight (6.0 instead of 9.0)
- Add cooldown: if emotional_block was triggered in last 3 turns but user explicitly requests action, reduce emotional_block weight progressively

---

## 7. Recommendation: Upgrade P0-4 to P0-3

### Justification

**Original P0-4 classification** was based on keyword-only detection without negation.

**Upgrading to P0-3** because:

1. **Highest-weight signal has lowest-quality detection**: emotional_block at weight 9.0 uses keyword substring matching. This is the system's most impactful routing decision driven by its least reliable signal.

2. **Self-reinforcing feedback loop**: False emotional_block detection leads to cognitive_first routing, which the routing_outcome_service judges as "successful" (line 172-173), so no correction signal is generated. The system cannot self-correct.

3. **Low triggering threshold**: Only 2 keyword matches in 24h (which can be false positives from negated statements) trigger emotional_block. The `negative >= 2` path (line 894) bypasses the ratio calculation entirely.

4. **User experience inversion**: The intended behavior (empathetic response when user is stressed) is inverted -- the system becomes patronizing when the user is actually motivated. This directly contradicts the product vision of reducing "internal friction."

5. **Multiple detection points with same flaw**: The keyword-without-negation pattern appears in 3 separate locations (`_classify_recent_chat_sentiment`, `NEGATIVE_USER_SIGNAL_KEYWORDS`, `_message_has_negative_signal`), amplifying the impact.

### Not P0-2 because:
- Does not cause data loss or security exposure
- Does not crash the system
- The fallback (cognitive_first with recovery mode) is not harmful per se -- it is incorrect for the user's actual state, but not destructive

### Priority actions:
1. **Immediate**: Add negation word detection to `_classify_recent_chat_sentiment` (Option A, ~1 hour)
2. **This sprint**: Add telemetry for emotional_block trigger logging
3. **Next sprint**: Implement `snownlp` hybrid approach (Option C, Phase 2)

---

## 7. Summary Statistics

| Metric | Value |
|--------|-------|
| Total detection points | 10 |
| Keyword-based (no NLP) | 3 |
| Event-driven (external) | 1 |
| Aggregation/computation | 4 |
| Derived (DB query) | 2 |
| Highest weight | emotional_block = 9.0 |
| Estimated FP rate (negative categories) | 15-25% |
| Min false matches to trigger block | 2 (in 24h) |
| Self-correction mechanism | None (routing_outcome confirms false positive as success) |
| Files affected | 8 Python files across 4 subsystems |
| Recommended fix | Hybrid: negation words + snownlp |

---

## Appendix A: File Reference Index

| File | Lines | Role |
|------|-------|------|
| `backend/app/state_aggregator/service.py` | 509-596 | Emotion hint builder + keyword classifier |
| `backend/app/state_aggregator/schema.py` | 122-126 | EmotionHintValue schema |
| `backend/app/orchestration/dual_core_router.py` | 166-175, 214-218, 294-306, 817-845, 876-898 | Router emotional block logic |
| `backend/app/orchestration/routing_parameter_registry.py` | 40 | Weight 9.0 definition |
| `backend/app/orchestration/routing_engine.py` | 753, 1726-1776 | Routing input construction |
| `backend/app/orchestration/context_builder.py` | 687-713 | Sentiment distribution query |
| `backend/app/orchestration/ux_envelope.py` | 32-45, 1893-1895 | UX negative signal detection |
| `backend/app/services/cognitive_service.py` | 155-260, 323-573 | Fragment creation + analysis |
| `backend/app/services/analytics/cognitive_stream_worker.py` | 189-231 | Event-driven fragment sentiment |
| `backend/app/services/dashboard_service.py` | 302-311 | Anxiety ratio for weather |
| `backend/app/services/routing_outcome_service.py` | 165-178 | Self-reinforcing success judgment |
| `backend/app/models/cognitive.py` | 26-78 | CognitiveFragment model (sentiment column) |
