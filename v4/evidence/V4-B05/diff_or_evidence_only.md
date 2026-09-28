# V4-B05 · diff_or_evidence_only

## 本卡为 design 卡：交付=合同文档，零产品码 diff

- `git diff 3c4618cc --stat`（除本 evidence 目录与 tasks.json 外为空）——红线"不改产品码"由空产品 diff 直接证明。
- 未越权项核对：未替用户批准色板/像素资产（§3 `asset_ref` 仅指向"已过审 token 集"，选择权留 V4 视觉线）；未替外部授权（§8 明确 off/shadow/live，无 live 声明）。

## 契约判定摘要（对应卡验收）

1. **每字段有来源/版本/unknown 语义；事件不能授予权限**：§1 权威映射表（每行 file:line）+ §2/§3/§4/§5 字段表（类型/必选/默认/unknown 语义四列齐备）；I1/E3 不变量 + 反例 `experience_event_grants_permission`。
2. **新旧客户端双读用例与 proto 生成入口明确**：§8——REST 面"旧客户端忽略未知可选字段 + v1 行为逐字节不变"双读断言；WS 面 `kind` 未注册一律忽略不当成功；proto 入口=`proto/websocket.proto` oneof 增 `ExperienceEventFrame` → `make proto-gen`，禁手改 gen/。
3. **5 种错误状态不混 committed；跨对象 ID 误用拒绝**：§6 五值 1:1 复用 `ACTION_ERROR_CODES`（action_command.py:164），E2 互斥不变量；I3/E4 + 反例 `cross_object_subject`。

## 复用 vs 新增判定（卡要求"列哪些字段现有可复用，缺项才迁移"）

- 复用 11 处权威（§1 表）：action_plan 词表/读门、action_command 链+错误码、AuroraDecision 不变量、校准回执四动作、纠正载荷、FIX-507 三写面、event registry、outcome 分级、memory epoch、理解条目读面、agent_run。
- 新增仅 4 处最小面：`context_selection_receipt.v1`、`experience_event.v1`、`episode_resume_view.v1`（聚合读模型）、`action_plan.v1.1` 的 `why_now` 字段位。
- 未重建 V3：无新服务、无新表（why_now 物理落点留给 contract-owner 二选一）、无第二真值/第二开关组。

## 后续

独立审查 ×2（卡要求）；V4-F03/B06+ 实现卡按 §8 生成入口与开关策略落地；实现卡需补：冻结词表测试断言、双读用例、shadow 开关登记。
