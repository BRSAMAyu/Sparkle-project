# Sparkle AI Memory & Profile — Privacy Explanation

> Created: 2026-05-01 | Target audience: Users and privacy reviewers
> Purpose: Explain in plain language what Sparkle's AI learns about you, how it's stored, and how you control it

## 1. What Sparkle Learns About You

Sparkle is designed to be a perceptive companion — not a passive tool. To personalize its responses, it builds a profile from your interactions:

### Explicit Preferences (You Told Sparkle Directly)
| Example | How It's Learned |
|---------|-----------------|
| "I prefer short, direct answers" | Stated as a preference during chat |
| "Don't call me 'student', call me by my name" | Correction in conversation |
| "I study best in the morning" | Profile setting or stated in planning |
| "I'm visual learner" | Self-described in onboarding or settings |

### Inferred Patterns (Sparkle Noticed Over Time)
| Example | Confidence Level | Status |
|---------|-----------------|--------|
| You consistently complete tasks with concrete deadlines more often than open-ended ones | Medium | Tentative (shown for your confirmation) |
| You tend to abandon tasks assigned to weekends | Low | Tentative |
| Your motivation dips when tasks involve group coordination | Low | Tentative |

### What Sparkle Does NOT Learn
- It does NOT build a personality profile to sell or share.
- It does NOT infer sensitive attributes (political views, religious beliefs, sexual orientation).
- It does NOT create a "permanent record" that follows you across services.
- It does NOT use your data to train models for other users.

## 2. Where Your AI Memory Lives

```
Your Device                    Sparkle Servers
    │                                │
    │  ┌─────────────────────┐      │  ┌──────────────────────────┐
    │  │ Chat messages        │──────│▶│ PostgreSQL                │
    │  │ (encrypted in transit)│     │  │ - profile_preferences    │
    │  └─────────────────────┘      │  │ - cognitive_fragments    │
    │                                │  │ - user_settings          │
    │  ┌─────────────────────┐      │  │ - correction_history     │
    │  │ Local cache          │      │  └──────────────────────────┘
    │  │ (device only)        │      │
    │  └─────────────────────┘      │  ┌──────────────────────────┐
    │                                │  │ Redis (temporary)        │
    │                                │  │ - Bayesian posterior     │
    │                                │  │ - Session context        │
    │                                │  │ - Routing state          │
    │                                │  └──────────────────────────┘
```

All AI memory data lives on Sparkle's servers, not on third-party AI provider infrastructure. When you chat with the AI, only the current conversation context (with PII redacted) is sent to the LLM provider. Your learned profile stays within Sparkle.

## 3. How Memory Affects Your Experience

### Before AI Memory (Week 1):
- Generic responses
- Same tone for everyone
- No awareness of your history

### After AI Memory (Weeks 2+):
- Responses reference your stated goals and preferences
- Tone adapts to your communication style
- Sparkle notices when you're stuck and adjusts suggestions
- Proactive nudges are timed to your patterns

### The "Why Did Sparkle Do That?" Guarantee
Every AI behavior influenced by learned memory includes:
- **Proactive reason**: When Aurora initiates a nudge, the notification includes a human-readable reason (e.g., "Based on your pattern of completing tasks before 10am...").
- **Correction path**: You can always say "that's wrong" and Sparkle records the correction.
- **Transparency**: You can ask "what do you know about me?" and Sparkle will summarize its learned profile.

## 4. Your Controls

### In-App Controls (Implemented)
| Control | Where | What It Does |
|---------|-------|-------------|
| Set preferences explicitly | Chat: "I prefer X" | Writes durable preference with high confidence |
| Correct AI | Chat: correction chips or "that's wrong" | Records correction, adjusts future behavior |
| Adjust AI reasoning mode | Settings → AI Preferences | balanced / creative / precise |
| Adjust transparency level | Settings → AI Transparency | How much Sparkle explains its reasoning |
| Delete account | Settings → Account → Delete | Anonymizes immediately, purges after 30 days |
| Export all data | API: GET /api/v1/me/export | Downloads complete ZIP archive |

### Controls Tracked for Future Release
| Control | Priority | What It Would Do |
|---------|----------|-----------------|
| View learned profile | P1 | See all preferences Sparkle has learned about you |
| Delete individual learned item | P1 | Remove a specific learned preference |
| Disable AI memory learning | P1 | Stop Sparkle from learning new preferences |
| Reset AI memory | P2 | Clear all learned preferences at once |
| Memory retention period | P3 | Choose how long Sparkle remembers interactions |

## 5. Privacy by Design: Aurora PII Redaction

Before any text reaches an external AI provider, Sparkle's Aurora privacy layer redacts:

| Original | Sent to LLM |
|----------|------------|
| "My email is alice@university.edu" | "My email is [EMAIL]" |
| "Call me at +86 138-1234-5678" | "Call me at [PHONE]" |
| "My ID is 110101199003071234" | "My ID is [CN_ID]" |
| "Use card 6222-1234-5678-9012" | "Use card [BANK_CARD]" |

This redaction operates in **live mode** for all production requests. Telemetry records only category statistics (e.g., "1 email, 1 phone redacted"), never the raw PII values.

## 6. Data Lifecycle

```
Interaction
    │
    ▼
Profile Learning (real-time)
    │
    ▼
Persistent Storage (PostgreSQL)
    │
    ▼
Used for Personalization (your sessions only)
    │
    ▼
Anonymized on Account Deletion (Day 0)
    │
    ▼
Permanently Purged (Day 30)
```

No data is retained after account deletion beyond the 30-day grace period. No data is sold, shared for advertising, or used for cross-user model training at any point.

## 7. FAQ

**Q: Can Sparkle read my mind?**
A: No. Sparkle infers patterns from your explicit interactions (chat messages, task completions, corrections). It does not access your device sensors, browsing history, or other apps.

**Q: What if Sparkle learns something wrong about me?**
A: Tell it. Sparkle's correction system records your explicit corrections and adjusts its profile. Low-confidence inferences are marked "tentative" and shown for your confirmation.

**Q: Does my university/professor/parents see my Sparkle data?**
A: No. Your Sparkle data is private to you. Community features are opt-in per post. Even in accountability partnerships, you choose what to share.

**Q: Can I use Sparkle without AI memory?**
A: Currently, AI memory is core to the personalized experience. A "disable memory learning" toggle is tracked as a P1 priority. In the meantime, you can delete your account at any time.

**Q: Where are the servers?**
A: [Deployment region TBD]. Data may be transferred across borders to the deployment region per our Privacy Policy.
