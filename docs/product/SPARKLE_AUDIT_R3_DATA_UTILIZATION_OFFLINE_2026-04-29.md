# Sparkle 深度审查报告 #3 — 数据利用与离线同步缺口

> **审查日期**: 2026-04-29
> **审查者**: Claude (审查角色)
> **范围**: 全系统数据利用审计 + 离线/同步能力审计
> **前置**: [`SPARKLE_AUDIT_R2_CODEX_VERIFICATION_2026-04-29.md`](SPARKLE_AUDIT_R2_CODEX_VERIFICATION_2026-04-29.md)

---

## 审查结论概览

| 级别 | 数量 | 说明 |
|------|------|------|
| **P1 High** | 2 | 重要数据源未接入 AI 上下文 / 离线消息丢失 |
| **P2 Medium** | 3 | CRDT 未实现 / 任务离线不可用 / Focus 重连不同步 |
| **OK** | 4 | Achievement/Calendar/ErrorBook 已闭环 |

---

## A. 数据利用审计

### OK — 已良好接入的数据源

| 数据源 | 接入路径 | 状态 |
|--------|----------|------|
| Achievement System | `context_manager.py:601-683` → `prompts.py:3051-3091` | ✅ 完整闭环: 成就事件 → AI 上下文 → prompt 注入 |
| Calendar | `context_manager.py:685-789` → 时间压力信号 | ✅ 完整闭环: 日历事件 → AI 感知时间压力 |
| Error Book | `ErrorReplanBridge` → 错题信号 → 计划调整 | ✅ 闭环: 错题 → 认知胶囊 → 知识惩罚 → 计划重规划 |
| Behavior Signals | `behavior_signal_collector.py` → Spine | ✅ 行为模式检测接入 Spine |

### D-01 (P1): Notification 交互历史未接入 AI

**文件**: `mobile/lib/features/notification_center/` + `backend/app/api/v1/notifications.py`
**发现**:
- 通知有完整的 CRUD + 已读/未读状态
- 但用户与通知的**交互行为**（打开率、点击时间、忽略频率）从未回流到 AI
- 代码注释明确标注这是 "architectural decision" — 但这意味着 AI 无法学习"什么通知对用户有效"
**影响**: Push Scheduler (T1.1.3) 和 NotificationDirective (Spine Layer 7) 无法根据用户实际通知偏好优化
**修复方向**: 在 `notification_service.py` 中记录用户交互事件到 EventBus，由 BehaviorSignalCollector 消费

### D-02 (P1): Photon/积分消费记录未接入 AI

**文件**: `backend/app/services/photon_service.py`
**发现**:
- Photon 系统有完整的赚取/消费/余额管理
- 积分消费模式（购买了什么、何时购买、消费频率）是极强的用户偏好信号
- 但 `context_manager.py` 和 `prompts.py` 均未引用 photon 相关数据
**影响**: AI 不知道用户是"积分储蓄型"还是"积分消费型"，无法在激励策略上个性化
**修复方向**: 在 `context_manager.py` 中添加 photon 消费摘要（最近 7 天消费类别分布）

---

## B. 离线/同步能力审计

### O-01 (P1): OfflineChatMessage 存在但未使用 — 消息丢失

**文件**: `mobile/lib/features/chat/data/models/offline_chat_message.dart`
**发现**:
- `OfflineChatMessage` 模型已定义，含 sender/content/timestamp/session_id 字段
- 但 `websocket_chat_service_v2.dart` 的断连处理中**未使用此模型**
- 断连期间用户发送的消息直接丢失，无本地缓存
- 重连后无消息回补机制
**影响**: 弱网环境下用户消息丢失，严重影响体验
**修复方向**:
1. 断连时将待发消息写入 OfflineChatMessage + SQLite
2. 重连后从本地读取未发送消息，通过 WebSocket 补发
3. 服务端通过 `chat_history.go` 返回断连期间的消息

### O-02 (P2): CRDTSyncManager 未实现

**文件**: `mobile/lib/core/services/sync/crdt_sync_manager.dart`
**发现**:
- 文件头部注释明确标注 "NOT YET IMPLEMENTED"
- 当前同步策略是简单的 HTTP pull/push，无冲突解决
- 多设备场景下可能出现数据覆盖
**影响**: 多设备用户的数据一致性无保障
**修复方向**: Phase 5-6 实现 CRDT 或 last-write-wins 策略

### O-03 (P2): 任务完成无离线支持

**文件**: `mobile/lib/features/task/`
**发现**:
- 任务完成操作直接调用 API，无离线队列
- 网络不可用时任务状态变更丢失
- 与 OfflineChatMessage 同样的问题模式
**影响**: 弱网环境下用户完成任务后刷新会丢失状态
**修复方向**: 实现本地 optimistic update + 同步队列

### O-04 (P2): Focus 会话重连不同步

**文件**: `mobile/lib/features/focus/`
**发现**:
- Focus 会话本地持久化已实现（T1 已修复）
- 但重连后不会自动同步本地会话到服务端
- 需要用户手动触发同步
**影响**: 多设备场景下 Focus 会话可能不一致
**修复方向**: 在 app 从后台恢复时自动触发 sync

---

## 与 Roadmap 的关联

| 发现 | 建议 Roadmap 位置 | 优先级 |
|------|-------------------|--------|
| D-01 Notification 交互 | Phase 2.2 (Directive Audit) | P1 |
| D-02 Photon 消费模式 | Phase 3 (Aurora↔Spine) | P1 |
| O-01 离线消息丢失 | Phase 4 (活体验打磨) | P1 |
| O-02 CRDT 未实现 | Phase 6 (规模化) | P2 |
| O-03 任务离线 | Phase 4 (活体验打磨) | P2 |
| O-04 Focus 重连 | Phase 4 (活体验打磨) | P2 |

---

## 三轮审查总结

| 报告 | P0 | P1 | P2 | OK |
|------|----|----|----|----|
| R1 信号流 | 3 | 4 | 3 | 5 |
| R2 验收复查 | 0 (1已修, 2未修) | 0 | 0 | 4 |
| R3 数据+离线 | 0 | 2 | 3 | 4 |
| **累计** | **2 未修** | **6** | **6** | **13** |

### 仍待修的 P0 (最高优先级)
- C-01: OutcomeTracker 接线到生产代码
- C-03: multi_agent_adapter 传入 Spine context

---

> **总结**: 数据利用方面，Achievement/Calendar/ErrorBook 三个核心数据源已闭环，但 Notification 交互和 Photon 消费是两个重要的盲区。离线能力方面，OfflineChatMessage 已有模型但未接线是最紧迫的问题。下一步应先修复 R1/R2 遗留的 2 个 P0，再处理本报告的 P1 项。
