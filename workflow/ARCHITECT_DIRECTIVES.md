# 架构师指令通道 · 最高优先级

> **说明**：本文件是人类架构师（Opus + 人）对三专家工作流的唯一干预入口。每个 loop 的第一步（紧跟 lock 检查后）必须读这里，凡出现 `status: active` 且 `priority: override` 的指令，立即暂停本角色当前 loop 的常规计划，转而执行指令内容。执行完毕写 `## ACK by <role>` 段并把 status 改为 `done`。
>
> 三专家**禁止**在本文件追加与"执行指令"无关的内容；长背景/方案放到 `architect/decisions/<id>.md`。

---

## 使用说明（架构师写指令时）

指令 id 规则：`DIRECTIVE-YYYYMMDD-NN`，NN 从当天 01 起。

`priority`：
- `override`：暂停正常队列，本 loop 必须先处理
- `elevated`：优先级拔高到当前队列头部，但不阻断常规流程
- `advisory`：只读提示，不强制执行

`target_roles`：`[auditor]` / `[fixer]` / `[verifier]` / `[auditor, fixer, verifier]` / `[all]`

`scope`：可选，限定作用切片或 ISSUE，例如 `slice:03-plan_review` 或 `issue:ISSUE-20260424-007`

`expires_at`：可选。过期后即使未 done 也视为失效，三专家写 `status: expired`。

---

## 活动指令

<!-- 架构师在下方追加新指令。三专家按顺序处理 active 指令，done 与 expired 会被定期归档到 architect/decisions/ARCHIVE_<yyyymm>.md -->

### DIRECTIVE-EXAMPLE-00 (样例，架构师启动前删除或保留作格式参考)
- status: advisory
- issued_at: 2026-04-24T15:00:00+08:00
- target_roles: [all]
- priority: advisory
- scope: none
- expires_at: never

#### 内容
这是一个样例指令。真实指令请严格按此结构书写：`status / issued_at / target_roles / priority / scope / expires_at` 六个元数据缺一不可；内容段用 `#### 内容` 四级标题；ACK 段用 `#### ACK by <role>`。

#### ACK by example
（三专家看到 advisory 不强制执行，但若是 override 则必须在此处回执）

---

## 归档
已完成与已失效指令每周由 Verifier 在最后一次 loop 迁移至 `architect/decisions/ARCHIVE_<yyyymm>.md`，本文件只保留活动指令 + 最近 48h 已完成指令，保持精简。
