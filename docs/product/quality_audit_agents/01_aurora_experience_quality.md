# Quality Audit Agent Report: 01_aurora_experience_quality

Agent ID: ad344c116eea48794

I'll conduct a thorough UX quality audit of Aurora's experience. Let me start by reading all the relevant files in parallel.

---

Now let me read the memory service, context builder, and additional prompt sections for recent corrections rendering and memory denial paths.

---

Now let me check for memory decay mechanisms, the enforcement mechanism for language principles, and how corrections handle duplicates.

---

Now let me check for the l10n strings used in the correction bar and the memory decay logic.

---

Now let me check if there's an active memory decay/evolution service that uses the decay_policy field.

---

Let me find the freeform correction input UI to understand its discoverability.

---

Now I have all the data needed for a comprehensive audit. Here is my structured assessment.

---

# Aurora UX Quality Audit: Structured Assessment

## DIMENSION 1: "Aurora Really Understands Me" -- Memory & Calibration Quality

### 1. Memory Naturalness

**Rating: GOOD**

**Evidence:**

The memory rendering in `_format_natural_memory_context_section` (prompts.py lines 3731-3791) shows thoughtful design in several respects:

- **"When to reference" instructions are present and explicit** (line 3760): `"引用规则: 只在能推进当前目标、承接情绪或减少用户重复说明时使用；否则保持安静。"` This tells the model to reference memories only when they advance the goal, catch emotion, or save the user from repeating -- not just whenever a memory exists. This is well above average.

- **Expression guidance is natural** (line 3761): `"表达方式: 自然带入相关事实，不要用"我记得你说过..."开场，也不要像检索结果一样枚举。"` This specifically forbids the two most common AI memory failures: the "I remember you said" tic and bullet-point enumeration.

- **Low-confidence handling exists** (line 3762): Memories below 0.70 confidence get a `"confirmation_hint: 需要轻量确认，不要当成确定事实"` flag and the prompt instructs tentative phrasing.

- **Source attribution is human-friendly** (lines 3700-3714): Instead of raw source types like `"ai_inferred"`, the labels are `"从对话里推断的"`, `"你告诉我的"`, `"上下文里整理出的"`. This is a thoughtful touch -- though it is only in the prompt, not user-visible.

**Weaknesses:**

- The structured format of individual memory items (lines 3778-3790) still reads somewhat like a database record: `memory_1:`, `content:`, `time_ago:`, `source:`, `confidence: 0.82`. The `natural_line` field exists but is supplementary. The model sees both the structured data and the natural line, which somewhat undermines the "don't enumerate" instruction.

- **Memory denial path** (memory_service.py lines 1181-1193): When a user denies a memory reference, the system lowers confidence by 0.1 and stamps `reference_denied_at` with a reason on the evidence snapshot. This is solid. However, the denial only marks that particular episodic record -- there is no explicit instruction in the prompt system to stop referencing that specific memory in future turns. The 0.1 confidence decrement will eventually suppress it below 0.70, but it may take multiple denials.

- **Memory decay** is architecturally present but fragmented. The `EpisodicMemory` model has a `decay_policy` column, and there are separate decay services (`BehaviorPatternDecayService`, `InferredPreferenceDecayService`), but episodic memory retrieval (`list_recent_episodic`, lines 678-701) does not filter by confidence floor or apply any recency-weighted decay at query time. It simply selects non-deleted, non-archived records ordered by `occurred_at desc`. Old low-confidence memories can persist in results.

### 2. Calibration Receipt Quality

**Rating: GOOD**

**Evidence from `generate_calibration_receipt` (correction_feedback.py lines 185-256):**

- **The causal chain IS present.** The receipt has three sections: `what_changed` (what happened), `why_changed` (because of what), and `next_time` (consequence). Example for disconfirmation in Chinese: `"我把「下一步策略判断」的判断置信度从 0.82 下调到 0.67。 因为你纠正了我：「不是这个方向」。 下次出现类似信号时，我会把这个判断当作不那么确定，并先确认再提醒。"` This is a clear "because X, I changed Y, next time Z" structure.

- **Natural language is reasonably natural.** The Chinese phrasing uses proper human-like constructions: `"因为你纠正了我"` rather than `"Correction received: ..."`. The English variant is slightly more clinical (`"I lowered my confidence about [label] from X to Y"`) but still acceptable.

- **Bilingual support is thorough** (lines 244-255): Every receipt includes both `zh` and `en` i18n variants, which is good infrastructure.

**Weaknesses:**

- **Low variation across correction types.** The `_receipt_next_time` function (lines 171-182) has exactly three branches: `freeform_correction`, `disconfirmed`, and default (confirmed). After seeing 3-4 corrections, a user would notice the same "下次出现类似信号时..." phrasing. There is no template variation, randomization, or context-sensitivity in the wording.

- **Confidence numbers are exposed to the model** (e.g., `"从 0.82 下调到 0.67"`) which risks the model leaking them into user-visible text. The language principles forbid internal terminology, but raw floats are not caught by the `INTERNAL_TOKEN_PATTERNS` regex. This is a gap.

### 3. Correction Loop Closure

**Rating: GOOD**

**Evidence of the full path:**

1. **Chip tap** triggers `_handleOptionTap` (contextual_correction_bar.dart line 145) which builds an `AuroraCorrectionPayload` and calls `onSendCorrectionPayload`.

2. **Backend processing** flows through `_process_aurora_correction_from_context` (orchestrator.py line 931) into `CorrectionFeedbackProcessor.process()` which updates StateRegister confidence, records in self_model, persists via AuroraSelfCorrector, updates routing profile, and writes a calibration receipt.

3. **Next conversation references correction** via `context_builder.py` lines 579-588: `recent_corrections = await memory_service.list_recent_calibration_receipts(user_uuid, limit=3)` which feeds into `cognitive_context["recent_corrections"]`.

4. **Prompt rendering** in `_format_recent_corrections_section` (prompts.py lines 2935-2957) renders up to 3 recent receipts as a `## 近期 Aurora 校准回执` section with the instruction: `"回应时自然体现这些校准；只有当前对话相关时才简短提及，不要暴露内部 state key 或 semantic token。"`

**Timeout/Decay:** Receipts are stored in Redis with `RECENT_CALIBRATION_RECEIPTS_TTL_SECONDS = 7 * 24 * 60 * 60` (7 days) and capped at 10 entries (line 311: `ltrim(recent_key, 0, 9)`). This is a reasonable decay -- 7 days means corrections will not dominate for months, though for some use cases 7 days may be too short for a correction the user cares deeply about.

**Duplicate corrections:** When the user corrects the same thing twice, each correction calls `StateRegister.lower_confidence` with a fixed -0.15 delta, and each creates a new `AuroraCorrection` record (appended via `lpush`). Corrections **stack**, not override. The list stores up to 50 correction records (`ltrim(key, 0, 49)` in aurora_spine_confluence.py line 386). Stacking means repeated corrections compound the confidence decrease -- this is reasonable behavior but could theoretically push confidence to the floor (0.05 minimum in StateRegister) rapidly.

### 4. Language Principles Adherence

**Rating: EXCELLENT**

**Evidence from `aurora_language_principles.py`:**

The seven principles are **actionable and specific**, not vague platitudes:

| Principle | Specificity |
|---|---|
| `observed_not_generic` | "温柔表达必须绑定一个具体观察" -- ties warmth to a concrete observation |
| `corrigible_judgment` | "把推断说成可校准判断，给用户一个轻量纠正口" -- makes every judgment correctable |
| `minimum_next_step` | "每次推动只给低成本、可立即开始的一步" -- one small step, not a plan |
| `friend_not_performer` | "不过度表演；不假装人类" -- explicitly forbids human pretense AND performer mode |
| `no_shame_no_moralizing` | "不把进度偏差写成人格或道德问题" -- directly targets the shame spiral |
| `plain_language` | "不要暴露模型、策略、状态机或配置字段" -- no internal jargon |
| `recognition_not_praise` | "承认用户已经做成的事，但不使用泛泛夸奖" -- concrete recognition, not "你真棒" |

Each principle has both a positive and negative example, which is excellent for prompt-based enforcement.

**Forbidden expressions** (lines 113-144) cover the five most common AI failure modes:
- Blind cheerleading (`"我相信你一定能成功"`)
- Empty praise (`"你真棒"`)
- Shaming (`"你又失败了"`)
- Generic consolation (`"别担心，一切都会好的"`)
- Human pretense (`"我想你了"`)

**Enforcement mechanism exists and is dual-layered:**

1. **Prompt-layer enforcement**: `render_aurora_language_contract()` (lines 214-235) injects the full contract into every system prompt as a dedicated section with priority 0 (highest, per prompts.py line 1334).

2. **Programmatic enforcement**: `validate_aurora_language_text()` (lines 238-251) and `assert_aurora_language_text()` (lines 254-257) provide runtime validators that catch forbidden expressions and internal token leaks using regex patterns. These are used in **tests** (test_aurora_language_principles.py lines 117, 136, 157, 173, 186, 191) to assert that Aurora-generated copy (chat fallbacks, checkpoint openings, core session openings, daily startup messages, push templates) all pass the contract.

3. **Scenario-specific profiles** (lines 159-195) adapt tone per surface (chat is "轻量、低压", core session is "更直接、更可校准", push is "克制、可忽略、尊重安静"). This prevents the one-size-fits-all problem.

**Weakness:** The programmatic enforcement (`assert_aurora_language_text`) is used in tests but there is no evidence of it being called at runtime in the services themselves (grep in `backend/app/services/` returned no matches). This means LLM-generated free-form responses are not validated against forbidden patterns at generation time. The contract relies entirely on prompt-following, which is good but not bulletproof.

---

## DIMENSION 2: Correction Chip UX Quality

### 5. Correction Chip UX

**Rating: GOOD**

**Natural language labels:**

| Chip | Label | Subtitle | Assessment |
|---|---|---|---|
| Fallback: Direction | "不是这个方向" | "判断偏了" | Natural, friend-like |
| Fallback: Shorter | "更短一点" | "收短回复" | Natural, concise |
| Fallback: Practice | "直接出题" | "切到练习" | Direct, clear intent |
| Fallback: Recalibrate | "重新校准" | "深度检查" | Slightly more clinical but acceptable |
| Dynamic: Freeform | "Aurora 理解错了？" | "我来说明" | Friendly, inviting |

These labels feel conversational. "判断偏了" is something a friend would actually say. The freeform entry "Aurora 理解错了？/ 我来说明" frames correction as a collaborative act rather than an error report.

**Freeform text entry discoverability:**

The freeform path has two entry points:

1. **Dynamic mode**: The predicted reply group's `freeformOption` renders as a chip with label "Aurora 理解错了？" and an `edit_note_rounded` icon. Tapping it triggers `_promptForAuroraCorrection` which opens an `AlertDialog` with a TextField, title "想让 Aurora 知道什么？", and hint "哪里判断错了？说说你的纠正...". This is a standard dialog, reasonably discoverable but not in-situ -- the user must tap a chip, then a modal appears. The "我来说明" subtitle hints that this is the "explain yourself" path.

2. **Fallback mode**: If no predicted groups exist, the freeform entry is hidden behind "重新校准" which triggers the full recalibration flow. This means freeform is less discoverable when the backend does not provide predicted replies -- the user must infer that "深度检查" leads to freeform input.

**Visual weight:**

- The chip bar uses `Wrap` with `spacing: DS.spacing6` and `runSpacing: DS.spacing4`, with left padding of `DS.spacing40`. This places it below the message, aligned to the left.
- Chip sizing: minimum 44x44 touch target (line 573), content constrained to `maxWidth: 190`. Font size is 11px label / 10px subtitle -- deliberately small.
- Colors: non-accent chips use `DS.surfaceSecondary` at 0.5 alpha; accent uses `DS.brandPrimary` at 0.08 alpha. These are deliberately muted.
- The acknowledgement widget uses `DS.semanticSuccess` at 0.1 alpha -- a subtle green confirmation.

This is well-calibrated visual weight: small, low-contrast, positioned to not dominate the conversation. The 44px touch target ensures accessibility despite the compact visual size.

**Immediate feedback:**

Yes, there is immediate feedback. The `_showAcknowledgement` method (lines 134-143) replaces the correction bar area with a `_CorrectionAcknowledgement` widget showing a green checkmark, title "已收到", and subtitle "Aurora 正在更新理解". This acknowledgment auto-dismisses after 4 seconds. The feedback appears instantly on tap (line 156 calls `_showAcknowledgement` before the async payload is sent), so the user gets instant confirmation that their correction was received.

**Weaknesses:**

- After the 4-second acknowledgement disappears, there is no persistent indicator that a correction is pending or was applied. The next conversation turn would need to demonstrate the correction took effect for the user to have closure.

- The `_buildFallback` static chips are only shown when `predictedReplyGroups` is null or empty. In practice, if the backend is slow or fails, the user sees the static chips which may not be contextually relevant. There is no loading state for the correction bar.

---

## Summary Scorecard

| # | Dimension | Rating | Key Evidence |
|---|---|---|---|
| 1 | Memory Naturalness | **GOOD** | Strong "when to reference" instructions; natural source labels; structured format undermines naturalness slightly; no query-time decay filter |
| 2 | Calibration Receipt Quality | **GOOD** | Clear what-why-next causal chain; bilingual; low template variation across correction types; raw floats risk leaking |
| 3 | Correction Loop Closure | **GOOD** | Full path traced from tap to next conversation; 7-day TTL decay; corrections stack (not override); recent_corrections rendered in prompt with natural-use instructions |
| 4 | Language Principles | **EXCELLENT** | 7 specific, actionable principles with examples; 5 forbidden expression patterns; dual enforcement (prompt + programmatic tests); scenario-specific profiles; gap: no runtime assertion on LLM output |
| 5 | Correction Chip UX | **GOOD** | Natural conversational labels; immediate acknowledgement with 4-second confirmation; good visual weight calibration; freeform discoverability is weaker in fallback mode; no persistent post-correction indicator |

**Overall Assessment: The Aurora UX is built with genuine product taste.** The system consistently avoids the most common AI companion failure modes -- empty praise, shame-based motivation, human pretense, and database-dump memory. The language contract is one of the strongest I have seen in a production system, with specific positive/negative examples, forbidden expression patterns, and test enforcement. The biggest gaps are at the margins: memory decay at query time, receipt template variation, and freeform discoverability when the backend does not provide predicted replies.