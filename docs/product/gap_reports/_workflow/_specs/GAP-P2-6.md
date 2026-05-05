# GAP-P2-6: 设置页 5 个子版块 — Implementation Spec

> **Mode**: spec->you | **Level**: L2 (Flutter only, some backend touch points) | **Effort**: M (5-7 days)
> **Source**: UX-010 gap report (`01_flutter_mobile_experience.md`)
> **Status**: Spec ready for user implementation

---

## 1. 目标 (Objectives)

在 `UnifiedSettingsScreen` 中补全 5 个缺失的子版块，让用户能精细控制 Sparkle 的行为偏好。

### 5 个子版块

| # | 子版块 | 英文名 | 当前状态 |
|---|--------|--------|---------|
| 1 | 记忆管理 | Memory Management | Partial — `MemorySettingsScreen` 已存在且有独立路由，但从设置页入口不直观（藏在 `SettingsDataControlsCard` 内） |
| 2 | 社群智能 | Community Intelligence | Missing — 后端 `UserSettings.community_intelligence_enabled` 字段已存在，Flutter 完全无 UI |
| 3 | 资料权限 | Material Permissions | Missing — 后端无专用模型，Flutter 完全无 UI |
| 4 | 提醒偏好 | Reminder Preferences | Partial — `TaskReminderSettingsScreen` + `SmartPushSettingsScreen` 已存在，设置页有部分提醒 toggle 但缺统一入口 |
| 5 | 关系偏好 | Relationship Preferences | Partial — "Aurora Preferences" 折叠区已包含部分沟通偏好，但缺全局关系风格选择 |

### 核心目标

1. 为 5 个子版块在 UnifiedSettingsScreen 中创建入口卡片（同现有 Accessibility / Visual Elements / Sync Center 等入口一致的 list tile）
2. 补齐 Missing（社群智能 + 资料权限）的专用设置页面
3. 改进入口导航：提升 Memory Management 和 Reminder Preferences 的可见性
4. 新增 ~40 个 i18n key
5. 所有新增 UI 只依赖现有 Riverpod provider + API 端点，不引入新的后端服务

---

## 2. 现状评估 (Current State Assessment)

### 2.1 已存在的基础设施

**后端 (Python Engine):**

| 能力 | 文件 | 状态 |
|------|------|------|
| `UserSettings.community_intelligence_enabled` | `backend/app/models/user_settings.py:19` | ✅ 已存在 |
| `UserSettingsUpdate.community_intelligence_enabled` | `backend/app/schemas/user_settings.py:16` | ✅ 已存在 |
| `PATCH /user/settings` 端点 | `backend/app/api/v1/user_settings.py` | ✅ 已存在 |
| `MemorySettingsModel` (Dart model) | `mobile/lib/core/models/memory_models.dart:509` | ✅ 已存在 |
| `MemoryApiService` | `mobile/lib/core/services/memory_api_service.dart` | ✅ 已存在 |
| `MemorySettingsScreen` (完整页面) | `mobile/lib/features/memory/presentation/screens/memory_settings_screen.dart` | ✅ 已存在 |
| `ResearchConsentRecord` (consent 表) | `backend/app/models/research_consent.py` | ✅ 已存在 |
| `ConsentTracker` / `ConsentRecord` | `backend/app/signals/research_mode.py:820-897` | ✅ 已存在 |
| `AgentProfile.persona_archetype` | `backend/app/core/agent_profiles.py:130` | ✅ 已存在 |
| `AgentPersona.communication_style` | `backend/app/core/agent_persona.py:67` | ✅ 已存在 |
| `AuroraPreferencesProvider` (Riverpod) | `mobile/lib/features/aurora/presentation/providers/aurora_preferences_provider.dart` | ✅ 已存在 |

**Flutter 已有页面:**

| 页面 | 路由 | 用途 |
|------|------|------|
| `MemorySettingsScreen` | `/profile/memory-settings` | 记忆管理（已完整，含 capture level / social toggles / blocked prefs） |
| `TaskReminderSettingsScreen` | `/profile/task-reminders` | 任务提醒设置（已完整，含 time slots / timezone / permission） |
| `SmartPushSettingsScreen` | 无独立路由 | 智能推送设置（含 persona type / daily cap / active slots） |
| `PartnerObservationSettings` | 嵌入 accountability hub | 伙伴观察权限 widget（可复用为社群智能的一部分） |

### 2.2 实际缺口

| # | 缺口 | 严重程度 | 描述 |
|---|------|---------|------|
| G1 | **无社群智能 UI** | 🔴 High | 后端 `community_intelligence_enabled` 已存在，但 Flutter 完全无 UI 暴露此设置 |
| G2 | **无资料权限设置** | 🔴 High | 无任何 UI 控制哪些资料可以被 Aurora 使用；SourceTray 排除是本地 per-turn 的且未被持久化 |
| G3 | **记忆管理入口不显眼** | 🟡 Medium | 现有入口在 `SettingsDataControlsCard` 底部的 "Open Memory Settings" 小按钮内，用户很难发现 |
| G4 | **提醒偏好缺统一入口** | 🟡 Medium | TaskReminderSettings + SmartPushSettings + Notification settings 分散在三处，用户无统一入口页面 |
| G5 | **关系偏好缺全局风格选择** | 🟡 Medium | "Aurora Preferences" 折叠区有 directness / explanation level 等但不完整，无 cheerleader vs strategist 等关系风格选择 |

### 2.3 工作量分级（按子版块）

| 子版块 | 存量 UI | 新 UI 工作量 | 后端工作量 | 总估 |
|--------|---------|-------------|-----------|------|
| 记忆管理 | 100% | 0.5d（入口卡片） | 0 | 0.5d |
| 社群智能 | 0% | 1-1.5d（新 page） | 0（已有 API） | 1.5d |
| 资料权限 | 0% | 1.5-2d（新 page + widget） | 0.5d（简单持久化端点） | 2.5d |
| 提醒偏好 | 70% | 1d（统一入口页） | 0 | 1d |
| 关系偏好 | 40% | 1d（扩展已有 section） | 0（已有 Aurora prefs API） | 1d |
| **合计** | | | | **6.5d** |

---

## 3. 文件清单 (File Inventory)

### 修改文件

| 文件 | 变更 | 涉及子版块 |
|------|------|-----------|
| `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart` | 在现有 sections 之间插入 5 个入口卡片，提升记忆管理入口位置 | 全部 |
| `mobile/lib/features/user/user_routes.dart` | 新增 3 个路由：社群智能、资料权限、关系偏好 | 全部 |
| `mobile/lib/l10n/app_en.arb` | 新增 ~40 个 i18n key | 全部 |
| `mobile/lib/l10n/app_zh.arb` | 新增 ~40 个 i18n key（中文翻译） | 全部 |

### 新建文件

| 文件 | 用途 | 涉及子版块 |
|------|------|-----------|
| `mobile/lib/features/settings/presentation/screens/community_intelligence_settings_screen.dart` | 社群智能设置页面 | 社群智能 |
| `mobile/lib/features/settings/presentation/widgets/community_intelligence_tiles.dart` | 社群智能各 toggle 子组件 | 社群智能 |
| `mobile/lib/features/settings/presentation/screens/material_permissions_settings_screen.dart` | 资料权限设置页面 | 资料权限 |
| `mobile/lib/features/settings/presentation/widgets/material_permission_row.dart` | 资料权限单行组件 | 资料权限 |
| `mobile/lib/features/settings/presentation/screens/reminder_preferences_screen.dart` | 提醒偏好统一入口页面 | 提醒偏好 |
| `mobile/lib/features/settings/presentation/screens/relationship_preferences_screen.dart` | 关系/沟通偏好设置页面 | 关系偏好 |
| `mobile/lib/features/settings/presentation/widgets/relationship_style_picker.dart` | 关系风格选择 widget（cheerleader/strategist/coach） | 关系偏好 |
| `backend/app/api/v1/material_permissions.py` | 资料权限持久化 API 端点 | 资料权限 |

---

## 4. 子版块详细设计

### 4.1 记忆管理 (Memory Management)

**当前状态：**
- 完整页面 `MemorySettingsScreen` 已存在（`features/memory/presentation/screens/memory_settings_screen.dart`），提供：
  - 长期记忆启用/关闭 toggle
  - 捕获强度（low/medium/high）
  - 记忆分类 toggle（preferences / goals / episodic / inferred_episodic）
  - Social semantics toggle（self / person_mention / relationship / commitment）
  - 阻塞的 pref key 列表（可勾选）
  - 阻塞的来源类型（chat / task / error）
  - Push opt-in 设置
- 路由：`UserRoutes.memorySettings` = `/profile/memory-settings`
- i18n key 已存在（`memorySettingsTitle`, `memorySettingsDescription`, `memorySettingsEnableTitle` 等）

**需要做的：**
1. 在 `UnifiedSettingsScreen` 中，将记忆管理入口从 `SettingsDataControlsCard` 底部提升为独立的 `ListTile` 入口卡片
2. 放置位置：在现有 "Accessibility" 卡片之后，"Behavior Explanation" 之前
3. 入口卡片样式：使用 `GraphiteCardSurface` + `ListTile`，与现有入口卡片（Accessibility、Visual Elements、Study Materials）一致

**入口卡片 UI：**
```dart
GraphiteCardSurface(
  child: ListTile(
    contentPadding: EdgeInsets.zero,
    leading: const Icon(Icons.psychology_outlined),
    title: Text(l10n.memorySettingsTitle),
    subtitle: Text(l10n.memorySettingsDescription),
    trailing: const Icon(Icons.chevron_right),
    onTap: () => context.push(UserRoutes.memorySettings),
  ),
),
```

**工作量：** 0.5d
**i18n key：** 0 新 key（全部已存在）

---

### 4.2 社群智能 (Community Intelligence)

**当前状态：**
- 后端 `UserSettings` 表已有 `community_intelligence_enabled` 字段（boolean, default true）
- `PATCH /user/settings` 端点已支持 `community_intelligence_enabled`
- Flutter 端 `UserRepository` 已有 `updateSettings()` 方法
- `settings_provider.dart` 已有 `SettingsNotifier` 和相应的 provider
- Flutter 完全无社群智能设置 UI
- `PartnerObservationSettings` widget 已存在（在 accountability hub 中），可复用其模式

**需要做的：**

**Step 4.2.1：新建 `community_intelligence_settings_screen.dart`**

设置页面内容：

```
┌─────────────────────────────────────┐
│  社群智能设置                        │
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 启用社群智能         [toggle]    ││
│  │ 允许系统使用匿名社群数据来优化     ││
│  │ 推荐和学习策略                    ││
│  └─────────────────────────────────┘│
│                                     │
│  [若启用时显示以下选项:]              │
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 群体对比分析         [toggle]    ││
│  │ 与相似目标用户的模式比较，         ││
│  │ 用于提供"同侪经验"类建议           ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 伙伴观察粒度                     ││
│  │                                 ││
│  │ (radio) 仅学习时间               ││
│  │ (radio) 学习时间+任务内容         ││
│  │ (radio) 学习时间+任务+情绪状态    ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 匿名贡献数据         [toggle]    ││
│  │ 我的学习模式脱敏后用于社群洞察     ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 推荐接收                         ││
│  │ 来自社群的推荐类型：               ││
│  │ ☑ 策略推荐 (来自同目标群体)       ││
│  │ ☑ 资料推荐 (来自同领域群体)       ││
│  │ ☐ 伙伴匹配推荐                   ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

**Step 4.2.2：建立 provider**

```dart
// 在 settings_provider.dart 中已有 SettingsNotifier.communityIntelligenceEnabled
// 需要扩展: 增加 cohortComparisonEnabled / anonymizedContribution / observationGranularity / recommendationTypes

// 或者新建 provider:
final communityIntelligenceProvider = StateNotifierProvider<CommunityIntelligenceNotifier, CommunityIntelligenceState>(...);
```

方案选择：建议扩展 `SettingsNotifier`（在 `settings_provider.dart` 中），因为 `PATCH /user/settings` 是统一的。但为了职责分离，也可以新建 `CommunityIntelligenceNotifier`。

**推荐方案：** 新建 `CommunityIntelligenceNotifier` + `community_intelligence_data_provider`，通过现有 `UserRepository.updateSettings()` 写入 `PATCH /user/settings`。

**Step 4.2.3：状态持久化策略**

- `community_intelligence_enabled` → 存入 `UserSettings`（已支持）
- `cohort_comparison_enabled`、`anonymized_contribution_enabled` → 存入 `ResearchConsentRecord`（需通过 `ConsentTracker` 或直接通过 `consent_type` 写入）
- `observation_granularity` → 存入 user preferences JSON（或扩展 `UserSettings` 加字段）

**简化方案（V1）：** 将全部子偏好作为 JSON blob 存入 `UserSettings` 的一个新字段。具体方法：
- 后端：在 `UserSettings` 中添加 `community_intelligence_preferences` JSON 列
- 前端：读写整个 JSON blob 通过 `PATCH /user/settings`

**工作量：** 1.5d
**i18n key：** ~12 个

---

### 4.3 资料权限 (Material Permissions)

**当前状态：**
- 后端 `SourceTrayState` / `SourceTraySelection` 已有 per-turn 排除能力（source_tray_integration.py）
- `SourceEffectivenessTracker` 记录用户纠正
- Flutter 端 `SourceExplanationCard` 有 per-source correction
- 无全局"资料权限"持久化设置
- 无 UI 让用户管理默认的资料访问权限
- 无文档类型级别的 include/exclude 规则

**需要做的：**

**Step 4.3.1：新建 `material_permissions_settings_screen.dart`**

设置页面内容：

```
┌─────────────────────────────────────┐
│  资料权限设置                        │
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 默认资料访问                     │
│  │                                 ││
│  │ (radio) 自动（根据任务上下文）     ││
│  │ (radio) 手动（每轮让我选择）       ││
│  │ (radio) 关闭（不检索资料）         ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 允许使用的文档类型                ││
│  │                                 ││
│  │ ☑ 幻灯片 (slides)               ││
│  │ ☑ 教材 (textbook)               ││
│  │ ☑ 笔记 (notes)                  ││
│  │ ☑ 试卷 (exam_paper)             ││
│  │ ☑ 作业 (homework)               ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 永久排除的文档                    ││
│  │ (列出已排除的 source title，      ││
│  │  可点击移除排除)                  ││
│  │                                 ││
│  │ 当前没有排除的文档。              ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 还原所有排除       [button]      ││
│  │ 清除所有资料的排除状态            ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

**Step 4.3.2：新建 `backend/app/api/v1/material_permissions.py`**

后端端点：
```python
# GET /material-permissions — 获取资料权限设置
# POST /material-permissions/default-mode — 设置默认访问模式 (auto/manual/off)
# POST /material-permissions/allowed-types — 设置允许的文档类型
# GET /material-permissions/excluded-sources — 获取永久排除列表
# POST /material-permissions/excluded-sources — 添加永久排除
# DELETE /material-permissions/excluded-sources/{source_id} — 移除排除
# POST /material-permissions/reset — 还原所有排除
```

**简化方案（V1）：** 将资料权限设置为纯 JSON 键值，存入 `UserSettings` 的新字段 `material_permissions`（JSON 列）。不需要新表或复杂模型。

**Step 4.3.3：数据模型和 provider**

```dart
// material_permissions_models.dart
class MaterialPermissionsModel {
  final String defaultMode;       // auto / manual / off
  final Set<String> allowedTypes; // slides, textbook, notes, exam_paper, homework
  final List<String> excludedSourceIds;
}

// material_permissions_provider.dart
final materialPermissionsProvider = StateNotifierProvider<MaterialPermissionsNotifier, AsyncValue<MaterialPermissionsModel>>(...);
```

**工作量：** 2.5d（Flutter 1.5-2d + 后端 0.5d）
**i18n key：** ~10 个

---

### 4.4 提醒偏好 (Reminder Preferences)

**当前状态：**
- `TaskReminderSettingsScreen` 已存在（路由 `/profile/task-reminders`）提供：
  - 任务提醒启用/关闭
  - 提醒时间槽选择
  - 每日提醒上限
  - 通知权限检查
- `SmartPushSettingsScreen` 已存在（无独立路由）提供：
  - 推送 persona 类型（coach / cheerleader / etc.）
  - 每日推送上限
  - 活跃时间槽
- 通知设置 section 在 UnifiedSettingsScreen 中已存在：
  - 系统通知 toggle
  - 干预通知 toggle
  - 各类通知 toggle（reminder / spaced_repetition / weekly_report / milestone）
  - 通知级别（minimal / standard / verbose）
  - 静默时间设置

**需要做的：**
1. 在 UnifiedSettingsScreen 中把提醒偏好整合为一个独立入口卡片
2. 新建 `reminder_preferences_screen.dart` 作为统一入口页面，连接到现有各个已存在的设置页面

**统一入口页面内容：**

```
┌─────────────────────────────────────┐
│  提醒偏好                            │
│                                     │
│  > 任务提醒设置                  ▸   │
│  > 智能推送设置                  ▸   │
│                                     │
│  ─── 快速开关 ───                   │
│  ┌─────────────────────────────────┐│
│  │ 接收智能推送       [toggle]      ││
│  └─────────────────────────────────┘│
│  ┌─────────────────────────────────┐│
│  │ 每日提醒上限                     ││
│  │ [slider: 0-20] 当前: {n} 条     ││
│  └─────────────────────────────────┘│
│                                     │
│  ─── 各类型开关（快速访问） ───      ││
│  │ 任务提醒          [toggle]       ││
│  │ 间隔复习提醒      [toggle]       ││
│  │ 周报              [toggle]       ││
│  │ 里程碑通知        [toggle]       ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

**路由：** `UserRoutes.reminderPreferences = '/profile/reminder-preferences'`

**工作量：** 1d
**i18n key：** ~5 个（大部分已存在）

---

### 4.5 关系偏好 (Relationship Preferences)

**当前状态：**
- "Aurora Preferences" 折叠区已包含：
  - 分析深度（Light / Deep）
  - 沟通方式（Direct / Guided）
  - 解释详细程度（Detailed / Brief）
  - 压力提醒风格（Gentle / Motivating）
- 后端 `AgentPersona.communication_style` 字段已存在（gentle / direct / warm / etc.）
- 后端 `AgentProfile.persona_archetype` 已存在（balanced_mentor / calm_conductor / warm_tutor / etc.）
- 无专门的"关系偏好"设置页面
- 无全局关系风格选择

**需要做的：**

**Step 4.5.1：新建 `relationship_preferences_screen.dart`**

设置页面内容：

```
┌─────────────────────────────────────┐
│  关系与沟通偏好                       │
│                                     │
│  ┌─────────────────────────────────┐│
│  │ Aurora 的关系风格                ││
│  │                                 ││
│  │ (radio with description)        ││
│  │ ● 鼓励型 (Cheerleader)          ││
│  │   多肯定、多鼓励，适合需要动力时   ││
│  │                                 ││
│  │ ○ 策略型 (Strategist)           ││
│  │   直接建议，聚焦效率和方法        ││
│  │                                 ││
│  │ ○ 教练型 (Coach)                ││
│  │   平衡鼓励和策略，默认风格         ││
│  │                                 ││
│  │ ○ 引导型 (Facilitator)          ││
│  │   引导自我发现，不做直接判断       ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 沟通方式          (复用现有)      ││
│  │ ○ 直接安排我 / ● 引导我          ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 解释详细程度      (复用现有)      ││
│  │ 多解释原因 / 简洁                 ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 压力提醒风格      (复用现有)      ││
│  │ ● 不用压力 / 可用压力             ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │ 分析深度          (复用现有)      ││
│  │ 少分析我 / 多分析我               ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

**Step 4.5.2：新建 `relationship_style_picker.dart`**

4 种关系风格：
- **cheerleader** — 鼓励型：多肯定和鼓励，适合需要动力维持的用户
- **strategist** — 策略型：直接给建议，聚焦效率和方法
- **coach** — 教练型：平衡鼓励和策略，默认风格
- **facilitator** — 引导型：引导用户自我发现，不做直接判断

**持久化策略：** 通过现有 `AuroraPreferencesProvider` / `PATCH /user/settings` 扩展 `relationship_style` 字段。

**简化方案（V1）：** 在 `UserSettings` 中添加 `relationship_style` String 列（nullable, default "coach"），通过 `PATCH /user/settings` 读写。

从 Flutter 端直接读取和写入现有 `AuroraPreferencesProvider`（已支持自定义 key-value preference），或扩展 `UserRepository.updateSettings()`。

**工作量：** 1d
**i18n key：** ~13 个

---

## 5. UnifiedSettingsScreen 修改方案 (Phase 0)

### 5.1 入口卡片顺序

当前 sections 顺序（简化）：
1. 感官反馈 (Sensory Feedback) — 折叠区
2. 无障碍 (Accessibility) — 卡片入口
3. Behavior Explanation — 独立 widget
4. 学习模式 (Learning Mode) — 折叠区
5. 视觉元素 (Visual Elements) — 卡片入口
6. 资料库 (Study Materials) — 卡片入口
7. BGM — 折叠区
8. 主题与 AI (Theme & AI) — 折叠区
9. Aurora 沟通偏好 (Aurora Preferences) — 折叠区
10. 通知权限卡片
11. 通知设置 — 折叠区
12. 透明模式 + 系统反馈
13. 同步中心 — 卡片入口
14. OpenClaw — 卡片入口
15. SettingsDataControlsCard（包含记忆管理入口小按钮）
16. 语言

**修改后顺序：**
1. 感官反馈 — 折叠区（不变）
2. **记忆管理 → 新卡片入口**（替代原藏在 SettingsDataControlsCard 的小按钮）
3. **社群智能 → 新卡片入口**
4. **资料权限 → 新卡片入口**
5. **提醒偏好 → 新卡片入口**
6. **关系偏好 → 新卡片入口**（替代原 Aurora Preferences 折叠区的一部分）
7. 无障碍 — 卡片入口（不变）
8. Behavior Explanation — 独立 widget（不变）
9. 学习模式 — 折叠区（不变）
10. BGM — 折叠区（不变）
11. 主题与 AI — 折叠区（不变）
12. 通知 — 折叠区（不变）
13. SettingsDataControlsCard（移除记忆管理小按钮，保留数据导出/删除）
14. 其余不变

### 5.2 入口卡片模板

```dart
GraphiteCardSurface(
  child: ListTile(
    contentPadding: EdgeInsets.zero,
    leading: const Icon(Icons.<icon>),
    title: Text(l10n.<titleKey>),
    subtitle: Text(l10n.<subtitleKey>),
    trailing: const Icon(Icons.chevron_right),
    onTap: () => context.push(UserRoutes.<routeName>),
  ),
),
```

每个卡片之间用 `const SizedBox(height: DS.spacing16)` 分隔。

---

## 6. 文件修改详细计划

### 6.1 `unified_settings_screen.dart`

- 在 `_SensoryExpanded` 折叠区之后、Accessibility 卡片之前插入 5 个新卡片（记忆管理、社群智能、资料权限、提醒偏好、关系偏好）
- 从 `SettingsDataControlsCard` 中移除或淡化记忆管理入口（保留小按钮作为快捷方式也可）
- 删除已废弃的 `_memoryHidden` 相关代码（之前是隐藏/显示记忆面板的 toggle，非记忆管理本身）

### 6.2 `user_routes.dart`

新增路由：
```dart
static const String communityIntelligence = '/profile/community-intelligence';
static const String materialPermissions = '/profile/material-permissions';
static const String reminderPreferences = '/profile/reminder-preferences';
static const String relationshipPreferences = '/profile/relationship-preferences';
```

导入新 page 并在 `routes` getter 中添加对应的 GoRoute。

### 6.3 `app_en.arb` / `app_zh.arb`

新增 ~40 个 key（详见第 9 节）。

### 6.4 后端

- `backend/app/api/v1/material_permissions.py` — 新建（~80 行）
- `backend/app/api/v1/router.py` — 注册新 router
- 可选：在 `UserSettings` 模型中添加 `material_permissions`（JSON 列）+ `relationship_style`（String 列）

---

## 7. 测试计划 (Test Plan)

### Flutter Widget Tests (15 tests)

| 测试 | 子版块 | 描述 |
|------|--------|------|
| `test_community_intelligence_enabled_toggle` | 社群智能 | 启用/关闭 toggle 正确反映状态 |
| `test_community_intelligence_toggles_disabled` | 社群智能 | 关闭主开关时子选项不可用 |
| `test_community_intelligence_save_and_load` | 社群智能 | 设置保存后 reload 正确恢复 |
| `test_material_permissions_default_mode` | 资料权限 | 三种默认模式 radio 选择正确 |
| `test_material_permissions_allowed_types` | 资料权限 | 文档类型 checkbox 列表正确渲染 |
| `test_material_permissions_reset_all` | 资料权限 | 重置按钮确认流程正确 |
| `test_reminder_preferences_unified_nav` | 提醒偏好 | 统一页面的导航链接正确跳转 |
| `test_reminder_preferences_quick_toggles` | 提醒偏好 | 快速开关正确反映设置 |
| `test_reminder_preferences_daily_cap_slider` | 提醒偏好 | 每日上限滑块正确更新值 |
| `test_relationship_style_picker_renders_all` | 关系偏好 | 4 种风格 radio 全部渲染 |
| `test_relationship_style_picker_selects` | 关系偏好 | 选择风格后正确标记 selected |
| `test_settings_card_memory_management_nav` | 记忆管理 | 记忆管理卡片导航到正确路由 |
| `test_settings_card_community_intelligence_nav` | 社群智能 | 社群智能卡片导航到正确路由 |
| `test_settings_card_material_permissions_nav` | 资料权限 | 资料权限卡片导航到正确路由 |
| `test_settings_card_relationship_nav` | 关系偏好 | 关系偏好卡片导航到正确路由 |

### Flutter Provider Tests (5 tests)

| 测试 | 描述 |
|------|------|
| `test_community_intelligence_notifier_initial_state` | 初始状态正确 |
| `test_community_intelligence_notifier_toggle_enabled` | toggle 后状态更新 |
| `test_material_permissions_notifier_load_and_save` | load 和 save 正确调用 repository |
| `test_relationship_style_notifier_update` | 风格变更后状态反映到 provider |
| `test_reminder_preferences_notifier_unified_state` | 统一偏好状态聚合正确 |

### Backend API Tests (3 tests，针对 material_permissions)

| 测试 | 描述 |
|------|------|
| `test_get_material_permissions_returns_defaults` | 新用户获取到默认值 |
| `test_set_default_mode_persists` | 设置默认模式后持久化 |
| `test_toggle_allowed_types` | 文档类型切换正确保存 |

---

## 8. 验收标准 (Acceptance Criteria)

### 记忆管理 (Memory Management)
- [ ] UnifiedSettingsScreen 中显示"记忆管理"入口卡片，带图标、标题、副标题和右箭头
- [ ] 点击入口卡片导航到 `/profile/memory-settings`，加载 `MemorySettingsScreen`
- [ ] 记忆管理卡片位置在设置页前部（无障碍之前），替代原来隐藏在 SettingsDataControlsCard 中的小按钮
- [ ] 向后兼容：SettingsDataControlsCard 中的 `onOpenMemorySettings` 按钮可保留作为快捷方式

### 社群智能 (Community Intelligence)
- [ ] 新建 `CommunityIntelligenceSettingsScreen` 完整页面（含 NavigationBar + 标题）
- [ ] 主开关 "启用社群智能" 读写 `UserSettings.community_intelligence_enabled`
- [ ] 开启后显示子选项：群体对比分析 toggle、伙伴观察粒度 radio、匿名贡献 toggle、推荐类型 checkbox
- [ ] 子选项的 onChanged 可正确保存和恢复
- [ ] 所有 UI 文本双语覆盖

### 资料权限 (Material Permissions)
- [ ] 新建 `MaterialPermissionsSettingsScreen` 完整页面
- [ ] 三种默认访问模式（auto/manual/off）通过 radio 选择
- [ ] 文档类型 checkboxes 正确列出所有 5 种类型并持久化
- [ ] "还原所有排除"按钮有确认对话框
- [ ] 后端 `GET /material-permissions` 和 `POST /material-permissions/*` 端点正确工作

### 提醒偏好 (Reminder Preferences)
- [ ] 新建 `ReminderPreferencesScreen` 作为统一入口页面
- [ ] 导航到 `TaskReminderSettingsScreen` 和 `SmartPushSettingsScreen` 的链接正确
- [ ] 快速开关（智能推送、各类型通知）正确读写现有 setting provider
- [ ] 每日上限滑块正确绑定到 `pushPrefs.dailyCap`

### 关系偏好 (Relationship Preferences)
- [ ] 新建 `RelationshipPreferencesScreen` 页面
- [ ] 4 种关系风格（cheerleader / strategist / coach / facilitator）通过 radio 选择
- [ ] 沟通方式、解释详细程度、压力提醒风格、分析深度设置均从现有 `AuroraPreferencesProvider` 复用到新页面
- [ ] 关系风格通过 `PATCH /user/settings` 持久化到 `UserSettings.relationship_style`
- [ ] 所有设置保存成功后显示 snackbar

### 质量门禁
- [ ] `flutter analyze` 无新增 warning / error
- [ ] 全部 20 个 widget + provider test 通过
- [ ] 现有设置页功能无回归（各折叠区开关、滑块、dropdown 不受影响）
- [ ] 无硬编码 secrets/tokens/URLs
- [ ] i18n 双语覆盖所有新增 UI 文本（~40 key）
- [ ] 全新安装用户能看到默认值正常显示
- [ ] 路由注册在 GoRouter 中正确，route 名不冲突

---

## 9. i18n Key 清单

### 入口卡片 (5 keys)

| Key | EN | ZH |
|-----|----|----|
| `settingsMemoryManagementTitle` | Memory Management | 记忆管理 |
| `settingsMemoryManagementSubtitle` | Control what and how Aurora remembers | 控制 Aurora 记忆的内容和方式 |
| `settingsCommunityIntelligenceTitle` | Community Intelligence | 社群智能 |
| `settingsCommunityIntelligenceSubtitle` | Manage how community data shapes your experience | 管理社群数据如何影响你的体验 |
| `settingsMaterialPermissionsTitle` | Material Permissions | 资料权限 |
| `settingsMaterialPermissionsSubtitle` | Control which materials Aurora can access | 控制 Aurora 可以访问哪些资料 |
| `settingsReminderPreferencesTitle` | Reminder Preferences | 提醒偏好 |
| `settingsReminderPreferencesSubtitle` | Task reminders, push notifications, and quiet hours | 任务提醒、推送通知和静默时间 |
| `settingsRelationshipPreferencesTitle` | Relationship Preferences | 关系偏好 |
| `settingsRelationshipPreferencesSubtitle` | Choose how Aurora interacts and communicates with you | 选择 Aurora 如何与你互动沟通 |

### 社群智能 (12 keys)

| Key | EN | ZH |
|-----|----|----|
| `communityIntelligenceTitle` | Community Intelligence | 社群智能 |
| `communityIntelligenceEnabledTitle` | Enable community intelligence | 启用社群智能 |
| `communityIntelligenceEnabledDesc` | Allow the system to use anonymized community data to optimize recommendations and learning strategies | 允许系统使用匿名社群数据来优化推荐和学习策略 |
| `communityIntelligenceCohortToggle` | Cohort comparison | 群体对比分析 |
| `communityIntelligenceCohortDesc` | Compare patterns with similar-goal users for peer-experience suggestions | 与相似目标用户进行模式比较，用于提供同侪经验建议 |
| `communityIntelligenceObservationLabel` | Partner observation granularity | 伙伴观察粒度 |
| `communityIntelligenceObsStudyTime` | Study time only | 仅学习时间 |
| `communityIntelligenceObsTaskContent` | Study time + task content | 学习时间 + 任务内容 |
| `communityIntelligenceObsFull` | Study time + tasks + emotional state | 学习时间 + 任务 + 情绪状态 |
| `communityIntelligenceAnonymizedToggle` | Anonymized contribution | 匿名贡献数据 |
| `communityIntelligenceAnonymizedDesc` | My learning patterns (de-identified) enrich community insights | 我的学习模式（脱敏后）用于丰富社群洞察 |
| `communityIntelligenceRecommendLabel` | Recommended content types | 推荐内容类型 |

### 资料权限 (10 keys)

| Key | EN | ZH |
|-----|----|----|
| `materialPermissionsTitle` | Material Permissions | 资料权限 |
| `materialPermissionsDefaultMode` | Default access mode | 默认资料访问 |
| `materialPermissionsModeAuto` | Automatic (based on task context) | 自动（根据任务上下文） |
| `materialPermissionsModeManual` | Manual (ask each turn) | 手动（每轮让我选择） |
| `materialPermissionsModeOff` | Off (no retrieval) | 关闭（不检索资料） |
| `materialPermissionsAllowedTypes` | Allowed document types | 允许使用的文档类型 |
| `materialPermissionsExcludedDocs` | Permanently excluded documents | 永久排除的文档 |
| `materialPermissionsNoExcludedDocs` | No excluded documents | 当前没有排除的文档 |
| `materialPermissionsResetAll` | Reset all exclusions | 还原所有排除 |
| `materialPermissionsResetConfirm` | This will remove all exclusion records for all documents. Continue? | 这将清除所有文档的排除记录，确定继续？ |

### 提醒偏好 (5 keys)

| Key | EN | ZH |
|-----|----|----|
| `reminderPreferencesTitle` | Reminder Preferences | 提醒偏好 |
| `reminderPreferencesTaskReminders` | Task reminder settings | 任务提醒设置 |
| `reminderPreferencesSmartPush` | Smart push settings | 智能推送设置 |
| `reminderPreferencesDailyCapLabel` | Daily reminder cap | 每日提醒上限 |
| `reminderPreferencesDailyCapHint` | {count} per day | 每日 {count} 条 |

### 关系偏好 (13 keys)

| Key | EN | ZH |
|-----|----|----|
| `relationshipPreferencesTitle` | Relationship & Communication | 关系与沟通偏好 |
| `relationshipStyleLabel` | Aurora's relationship style | Aurora 的关系风格 |
| `relationshipStyleCheerleader` | Cheerleader | 鼓励型 |
| `relationshipStyleCheerleaderDesc` | More affirmation and encouragement, best when you need motivation | 多肯定、多鼓励，适合需要动力时 |
| `relationshipStyleStrategist` | Strategist | 策略型 |
| `relationshipStyleStrategistDesc` | Direct advice, focused on efficiency and methods | 直接建议，聚焦效率和方法 |
| `relationshipStyleCoach` | Coach | 教练型 |
| `relationshipStyleCoachDesc` | Balanced encouragement and strategy, default style | 平衡鼓励和策略，默认风格 |
| `relationshipStyleFacilitator` | Facilitator | 引导型 |
| `relationshipStyleFacilitatorDesc` | Guide self-discovery without making direct judgments | 引导自我发现，不做直接判断 |
| `relationshipPreferencesCommunicationLabel` | Communication style | 沟通方式 |
| `relationshipPreferencesExplanationLabel` | Explanation level | 解释详细程度 |
| `relationshipPreferencesPressureLabel` | Pressure style | 压力提醒风格 |
| `relationshipPreferencesAnalysisLabel` | Analysis depth | 分析深度 |

**总计：45 个新 key**

---

## 10. 设计决策 (Design Decisions)

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口卡片样式 | 统一使用 `GraphiteCardSurface` + `ListTile` + `chevron_right` | 与现有 Accessibility / Visual Elements / Sync Center 卡片一致，零学习成本 |
| 记忆管理入口提升 | 从 `SettingsDataControlsCard` 底部按钮提升为独立卡片 | 记忆管理是 5 大子版块之一，应有同等入口；原位置太隐蔽 |
| SettingsDataControlsCard 保留 | 保留数据导出/删除部分，可保留记忆管理小按钮作为快捷方式 | 向后兼容；数据导出/删除与记忆管理本质不同（数据主权 vs 记忆偏好） |
| 社群智能 provider | 新建 `CommunityIntelligenceNotifier` 而非复用 `SettingsNotifier` | 职责分离；社群智能有多个子偏好，不适合与通用设置混在一起 |
| 资料权限后端 | 新建 `material_permissions.py` + `UserSettings.material_permissions` JSON 列 | GAP-P2-1 的 SourceTrayState 处理 per-turn/scope 排除，这里的资料权限是全局默认设置 |
| 提醒偏好统一页 | 新建导航入口页，子页面复用已有 page | 已有 `TaskReminderSettingsScreen` 和 `SmartPushSettingsScreen`，不应重写 |
| 关系偏好持久化 | 扩展 `UserSettings.relationship_style` 列，通过现有 `PATCH /user/settings` 端点 | 最简单且与现有架构一致；不需要新端点 |
| 关系风格提取 | 将 Aurora Preferences 中的沟通偏好迁移到新页面 | 原 Aurora Preferences 折叠区承载了过多职责（系统偏好 + 个人关系偏好） |
| 旧 Aurora Preferences 折叠区保留 | 保留但不重复显示迁移走的条目，或保留为"高级"入口 | 向后兼容；部分用户可能已经习惯原有位置 |
| 5 个卡片位置 | 集中放在 sensory feedback 之后、accessibility 之前 | 这 5 个是"人格化/个性化"设置，放在前面符合从个性到通用（a11y）到系统的顺序 |

---

## 11. 依赖与阻塞 (Dependencies)

- **社群智能 (Phase 1):** 无阻塞，后端 `community_intelligence_enabled` 已存在。子偏好存储方式需要决定（V1 JSON blob 还是扩展 ResearchConsentRecord）
- **资料权限 (Phase 2):** 需要新建后端端点（0.5d）。依赖 GAP-P2-1 的 SourceAsset/SourceTrayState 数据模型（已存在）
- **提醒偏好 (Phase 3):** 无阻塞，`TaskReminderSettingsScreen` 和 `SmartPushSettingsScreen` 已存在
- **关系偏好 (Phase 4):** 需要扩展 `UserSettings` 模型加 `relationship_style` 列（或使用 JSON blob）
- **i18n (Phase 5):** 可与 Phase 1-4 并行
- **入口卡片 (Phase 0):** 无阻塞，纯 UI 修改

### 交叉依赖
- 资料权限设置如果复用 GAP-P2-1 的 `SourceTrayState`，需要 GAP-P2-1 的 `SourceAssetModel` 先就绪
- 社群智能的 "伙伴观察粒度" 设置可复用 `PartnerObservationSettings` widget 模式

---

## 12. 开放问题 (Open Questions)

1. **社群智能子偏好存储：** 是否扩展 `UserSettings` 表加 JSON 列，还是通过 `ResearchConsentRecord` 管理每个子偏好？V1 建议 JSON 列（最快），长期应该使用 ResearchConsentRecord（有审计日志）。

2. **资料权限与 SourceTrayState 的关系：** 全局默认权限（auto/manual/off）和 per-turn 的 SourceTrayState.mode 如何互操作？建议：全局设置是默认值，chat 轮次中的 SourceTrayState 选择可以覆盖当前轮次但不影响全局默认。

3. **关系风格对已有 Aurora 偏好的影响：** 如果用户之前设置了 directness="direct" 然后选择关系风格 "cheerleader"，哪个优先？建议：关系风格是更上层的设置，它会联动下层的 directness / explanation_level / pressure_style 等子选项。手动调整子选项后，关系风格变为 "custom"。

4. **向后兼容处理：** "Aurora Preferences" 折叠区迁移到独立页后，旧折叠区是否应显示为 "快捷入口" 并引导用户到新页面？建议：保留旧折叠区但加 "查看更多" 入口到新页面。

5. **提醒偏好统一页中的快速开关：** 是否直接从现有 provider 读写（yes — pushPrefs, notificationPreferenceSettingsProvider 都已存在），还是需要新建聚合 provider？

6. **SettingsDataControlsCard 的未来：** 移除记忆管理入口后，这个卡片只剩数据导出/删除，是否应该重命名为 "数据管理"？建议 Phase 1 不做改名，留待后续。

---

## 13. 实现路线图

```
Phase 0 (0.5d): 入口卡片
  - unified_settings_screen.dart 插入 5 个新 ListTile
  - user_routes.dart 注册新路由
  - 确认路由不冲突

Phase 1 (1.5d): 社群智能（纯 Flutter + 后端已有 API）
  - community_intelligence_settings_screen.dart
  - community_intelligence_tiles.dart
  - community_intelligence_provider (新的 StateNotifier)
  - i18n key: ~12 个

Phase 2 (2.5d): 资料权限（需要新后端端点）
  - 后端：material_permissions.py + router.py 注册
  - Flutter：material_permissions_settings_screen.dart
  - Flutter：material_permission_row.dart
  - Flutter：material_permissions_provider
  - i18n key: ~10 个

Phase 3 (1d): 提醒偏好（纯 Flutter，复用已有页面）
  - reminder_preferences_screen.dart（导航入口页）
  - 绑定现有 provider
  - i18n key: ~5 个

Phase 4 (1d): 关系偏好（纯 Flutter + 后端已有 API）
  - relationship_preferences_screen.dart
  - relationship_style_picker.dart
  - 复用 AuroraPreferencesProvider
  - i18n key: ~13 个

Phase 5 (并行): i18n 更新
  - app_en.arb + app_zh.arb 新增 ~45 个 key
  - 可在 Phase 0-4 任意阶段并行
```

---

*Spec generated 2026-05-06 by Plan Agent (Opus)*
