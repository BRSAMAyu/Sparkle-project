# Reviewer B — C06: Galaxy节点点击→节点详情→开始复习进入chat携带context
Timestamp: 2026-04-25T12:35:00Z
Chain Index: 2

## Chain Flow Summary
用户在星图上点击节点，`galaxy_screen.dart` 打开 `NodeDetailSheet` 模态框。Sheet 调用 `/galaxy/node/{node_id}/history` API 获取节点历史（mastery、学习次数、上次学习时间、相关错题）。Sheet 显示节点名称、掌握百分比（0 时显示"尚未学习"）、学习统计 chips、最近错题预览。用户点击"开始复习"按钮后，Sheet 关闭并通过 GoRouter 跳转 `/chat?prompt=带我复习「{label}」...&chat_mode=study_plan&review_node={id}&node_label={label}`，同时传递 `extra: {initial_context: {review_node, node_label}}`。routes.dart 合并 query params 和 extra 为 `initialExtraContext`。ChatScreen 将此 context 附加到首条消息的 `extra_context` 字段，经 WebSocket 发送到后端。Aurora 的 `_review_focus_from_context()` 检测到 `review_node` 后生成定点复习首条回复。

## Critical Issues 🔴

None found

## Major Issues 🟡

**`chat_screen.dart` — 无复习模式 UI 指示器**
- Expected: 用户能看到自己正在复习某个特定节点（头部标签、节点名称、特殊样式）
- Actual: 复习 session 与普通 chat 完全相同的 UI。首条消息 "带我复习「TCP流量控制」" 发出后，用户无法从界面知道当前是定点复习模式
- Evidence: `chat_screen.dart` 无 review header/banner/indicator；`chat_mode='study_plan'` 仅影响 prompt starters（`chat_screen.dart:1746-1750`），不影响 UI 布局
- Impact: 用户在多轮对话后可能忘记自己在复习哪个节点

**`node_detail_sheet.dart:129-132` — 仅传递 node_id 和 label，不传 mastery/study history**
- Expected: Chat/Aurora 接收完整节点上下文（mastery、学习次数、错题列表），生成更精准的复习内容
- Actual: `initial_context` 仅包含 `{review_node: nodeId, node_label: label}`。Aurora 需要通过 `_fetch_galaxy_baseline()` 自行获取 `weak_nodes`/`strong_nodes`，但不一定获取该特定节点的 mastery 值
- Evidence: `node_detail_sheet.dart:129-132` 构建 `{'review_node': widget.nodeId, 'node_label': label}`；`service.py:765-793` `_review_focus_from_context()` 只读取 `review_node` 和 `node_label`

## Minor Issues 🟢

**`node_detail_sheet.dart:342-348` — "开始复习"按钮在 0 mastery 时仍可用**
- 节点从未学习过（mastery=0）时，按钮文字仍为"开始复习"，导航提示语为 "带我复习「{label}」"。对全新节点应显示"开始学习"或不同 CTA
- Evidence: Sheet 在 mastery=0 时显示"尚未学习"文案（`node_detail_sheet.dart:278-282`），但按钮未做条件适配

**`node_detail_sheet.dart:206-321` — 节点描述和标签未渲染**
- API 返回 `description` 和 `keywords`（`galaxy.py:349-364`），但 Sheet 只显示名称、掌握度和统计。用户无法在 Sheet 内了解节点内容概述

## Working Well ✅

1. **端到端导航链路完整** — NodeDetailSheet → GoRouter → routes.dart（合并 query+extra）→ ChatScreen → chatProvider → WebSocket → Aurora `_review_focus_from_context()`，全链路接线
2. **Aurora 复习模式检测自动** — `service.py:765-793` 从 `request_extra_context["review_node"]` 自动检测并生成定点复习首条消息（含薄弱点定位+短练习承诺）
3. **0 mastery 友好处理** — 显示"尚未学习"而非 "0%"，进度条用灰色
4. **加载/错误状态完善** — Sheet 使用 FutureBuilder，loading 显示 spinner，error 显示"节点历史加载失败"+重试按钮
5. **双重 context 传递** — query params + extra data 双通道，确保 context 到达（即使 GoRouter deep link 只保留 query）
6. **API 返回丰富节点数据** — `/galaxy/node/{node_id}` 返回 mastery、学习次数、上次学习、相关错题、关联节点、相关任务和计划
7. **学习统计 chips 信息密度高** — 学习次数、上次时间、相关错题数三个维度一目了然

## Files Examined

- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart` (node tap → sheet launch)
- `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` (lines 65-187, 206-348, 476-512)
- `mobile/lib/app/routes.dart` (lines 172-217, chat route with review context merge)
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` (lines 68-79 constructor, 506-529 initial prompt dispatch)
- `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` (lines 1204, 1242 extra_context in message payload)
- `backend/app/api/v1/galaxy.py` (lines 240-279 history endpoint, 282-450 node details, 549-574 review suggestions)
- `backend/app/aurora/runtime_v1/service.py` (lines 443-454 review early return, 765-793 `_review_focus_from_context()`, 787-793 review first-turn message, 1839-1874 galaxy baseline)

## Confidence: High — 5 个 key_files 全部读取，导航链路从 NodeDetailSheet 到 Aurora service 全程追踪，context 传递通过 routes.dart 和 WebSocket 代码确认
