# Sparkle (星火) Privacy Policy

> Version: 1.0.0 | Effective: 2026-05-01 | Language: English (中文摘要见末尾)

## 1. Introduction

Sparkle ("we", "our", "the App") is an AI Growth Companion designed to help university students achieve goals, reduce internal friction, and gain fulfillment. This Privacy Policy explains what data we collect, why we collect it, how we use it, and what controls you have.

## 2. Data We Collect

### 2.1 Account Data
- **Registration**: Email address, nickname, avatar (optional), and authentication provider identifiers (Google, Apple, WeChat) when you sign up.
- **Profile**: Self-described goals, interests, learning preferences, and study habits you voluntarily provide.

### 2.2 Interaction Data
- **Chat Messages**: Conversations with the AI companion, including text, images, and documents you upload.
- **Task & Plan Data**: Goals you set, tasks you create, due dates, completion status, and reflections.
- **Knowledge Graph**: Learning materials, notes, error-book entries, and structured knowledge you build.
- **Community Activity**: Posts, shares, accountability partnerships, group memberships, and interactions with other users.

### 2.3 Behavioral & Learning Data
- **Cognitive Signals**: Interaction patterns, learning phase transitions, motivation states, and emotional tone inferred from your language (processed on-device where possible).
- **Progress Metrics**: Task completion rates, study session duration, goal achievement trajectories.
- **Correction Feedback**: When you tell the AI it was wrong, we record what was corrected to improve future responses.

### 2.4 Device & Technical Data
- **Device Info**: Device model, OS version, app version, and language preference.
- **Connection Data**: IP address, connection timestamps, and WebSocket session metadata (retained for rate limiting and abuse prevention).

### 2.5 What We Do NOT Collect
- Precise location / GPS data
- Contacts or address book
- Browsing history from other apps
- Biometric identifiers (beyond what your device OS provides for authentication)
- Camera roll / photo library (except when you explicitly select images to upload)

## 3. How We Use Your Data

| Purpose | Data Used | Legal Basis |
|---------|-----------|-------------|
| Provide AI coaching, planning, and reflection | Chat, tasks, plans, goals | Contractual necessity |
| Personalize AI behavior to your preferences | Profile, cognitive signals, correction feedback | Legitimate interest (personalization) |
| Generate learning insights and progress reports | Behavioral data, progress metrics | Legitimate interest (service improvement) |
| Enable community features (sharing, accountability) | Community activity, profile | Consent (opt-in per post/share) |
| Improve AI model quality | Anonymized interaction patterns, correction statistics | Legitimate interest (R&D) |
| Prevent abuse and ensure security | Connection data, rate-limit counters | Legitimate interest (security) |
| Send notifications and proactive nudges | Task due dates, goal milestones, Aurora state | Legitimate interest (service functionality) |

**AI Memory & Profile Learning**: Sparkle learns your preferences, study patterns, and communication style from interactions. This learning is:
- **Transparent**: You can see what Sparkle has learned about you in Settings → AI Memory.
- **Controllable**: You can delete individual learned preferences or reset the entire profile.
- **Tentative**: Low-confidence inferences are marked as tentative and shown for your confirmation before being applied.
- **Never sold or shared**: Your learned profile is used exclusively to improve your personal Sparkle experience.

## 4. Data Storage & Security

- **Primary Storage**: Your data is stored in PostgreSQL databases with encryption at rest.
- **Caching**: Frequently accessed data (chat history, session state) is temporarily cached in Redis.
- **File Uploads**: Documents and images are stored in S3-compatible object storage (MinIO).
- **Encryption**: All data in transit is encrypted via TLS. Passwords are hashed (bcrypt). AI chat context is encrypted at rest.
- **Access Control**: Internal services authenticate via JWT and API keys. No public database access is exposed.
- **Retention**: Active account data is retained while your account is active. Deleted accounts are anonymized within 24 hours and permanently purged after 30 days.

## 5. Data Sharing & Third Parties

We do NOT sell your personal data.

Data may be shared in these limited contexts:
- **AI Model Providers**: Chat messages are sent to LLM providers (Anthropic, OpenAI, or locally configured) to generate AI responses. Messages are processed per API call and not used by providers for model training (per their data usage policies).
- **Authentication Providers**: Google, Apple, or WeChat (only the provider you choose to sign in with) receive authentication tokens.
- **Infrastructure Providers**: Database, object storage, and monitoring services that host Sparkle's backend.
- **Legal Obligations**: When required by applicable law or valid legal process.

## 6. Your Rights & Controls

| Right | How to Exercise |
|-------|----------------|
| **Access** | View your data in-app via Settings → Profile, or use the data export API (`GET /api/v1/me/export`) to download all data as a ZIP file. |
| **Rectify** | Edit your profile, preferences, and learned AI memory items directly in Settings. |
| **Delete** | Delete your account via Settings → Account → Delete Account. This triggers soft-deletion (immediate anonymization) followed by permanent data purge after 30 days. |
| **Export** | Download your complete data archive as a structured ZIP file via Settings → Privacy → Export Data. |
| **Restrict Processing** | Disable AI memory learning, notifications, or community features in Settings. |
| **Withdraw Consent** | Opt out of community features, analytics, or AI personalization at any time. |

### Data Export Format
The data export (`GET /api/v1/me/export`) produces a ZIP file containing:
```
sparkle_export_[timestamp]/
├── profile.json              # Your account and profile data
├── plans.json                # All goals and plans
├── tasks.json                # All tasks with status
├── error_book.json           # Error-book / learning entries
├── focus_sessions.json       # Study focus session records
├── calendar_events.json      # Calendar entries
├── chat_sessions.json        # Chat conversation metadata
├── achievements.json         # Unlocked achievements
├── notifications.json        # Notification history
└── user_settings.json        # Preference configuration
```

### Account Deletion Flow
1. **Request deletion** → Account immediately deactivated and anonymized (username, email, social IDs replaced with deletion markers).
2. **30-day grace period** → Data is retained in anonymized form. You can contact support to restore your account during this period.
3. **Permanent purge** → After 30 days, all remaining data is permanently and irreversibly deleted.

## 7. PII & Sensitive Data Handling

Sparkle's Aurora privacy system (`backend/app/aurora/privacy.py`) redacts personally identifiable information before it reaches external AI providers:

| PII Type | Example | Handling |
|----------|---------|----------|
| Email addresses | user@example.com | Redacted → `[EMAIL]` |
| Phone numbers | +86 138-xxxx-xxxx | Redacted → `[PHONE]` |
| Chinese ID numbers | 11010119900307xxxx | Redacted → `[CN_ID]` |
| Bank card numbers | 6222-xxxx-xxxx-xxxx | Redacted → `[BANK_CARD]` |
| Person names (explicit) | 张三, John Smith | Redacted → `[PERSON]` |

PII redaction operates in three modes:
- **Live**: PII is redacted from all external AI provider requests. Telemetry records redaction statistics (categories detected, no raw text).
- **Shadow**: PII is redacted from external requests AND telemetry records only category statistics (no raw PII in logs or telemetry).
- **Off**: Debug-only mode. Not available in production.

## 8. Children's Privacy

Sparkle is designed for university students (typically 18+). We do not knowingly collect data from children under 13. If you believe a child under 13 has provided personal data, please contact us for immediate deletion.

## 9. International Data Transfers

Sparkle servers are currently deployed in [region TBD]. If you access Sparkle from outside this region, your data will be transferred and processed in the deployment region. We implement Standard Contractual Clauses (SCCs) where required.

## 10. Breach Notification

In the event of a data breach affecting your personal data, we will notify affected users via email and in-app notification within 72 hours of confirmation, per applicable regulations.

## 11. Changes to This Policy

We will notify you of material changes to this policy via email and in-app notice at least 14 days before they take effect. Continued use after the effective date constitutes acceptance.

## 12. Contact

For privacy-related questions, data requests, or complaints:
- **Email**: privacy@sparkle.app
- **In-app**: Settings → Help → Privacy Request

---

## 中文摘要 (Chinese Summary)

星火（Sparkle）是一款面向大学生的AI成长伴侣。本隐私政策说明：

1. **我们收集什么**：账号信息、对话内容、任务/计划数据、学习行为信号、设备基础信息。我们不收集精确位置、通讯录、浏览历史或生物识别信息。

2. **我们如何使用**：提供AI教练服务、个性化体验、生成学习洞察、社区功能、安全防护。AI学到的偏好仅用于改善你自己的体验，绝不会出售或共享。

3. **你的权利**：随时查看、更正、导出或删除你的数据。账号注销后30天内可恢复，30天后永久删除。

4. **安全措施**：传输加密(TLS)、密码哈希(bcrypt)、AI对话上下文加密、PII自动脱敏。

5. **联系方式**：privacy@sparkle.app 或 App内设置→帮助→隐私请求。
