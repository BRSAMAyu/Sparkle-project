# V4-I01 · limitations（如实登记，不美化）

## 1. 「目标内容级变更」检测受限于无 goal 版本绑定列

卡验收「目标改变……退回明确校准」中，本卡可判定的「目标改变」权威面是：

- goal 终态（completed/archived/cancelled）；
- task 计划 `source_refs` 中 `goal://` 与解析 goal 不一致；
- 视图 `expires_at` 过期 / `freshness` epoch 变更（版本过期面）。

**goal 行内容被编辑（如改标题/标准）但状态仍活跃时，本读模型无法区分「计划签发时的 goal」与「现在的 goal」**——`tasks`/`plans` 上不存在「计划绑定 goal 版本」列。按铁律本卡**不新增**该绑定列（那是一次 schema 变更，且 B05 §4 已声明 why_now 物理落点由 contract-owner 二选一，同类决策应同owner做）。缓解：视图带 TTL（默认 30min）+ `freshness` 钉 epoch，过期即重算；但「重算出的仍是活跃 goal 下的现计划」——内容级漂移需后续卡（若产品裁定需要）以「计划签发时钉 goal version」字段位承接。

## 2. why_now 物理落点未绑死，本卡以 `getattr(task, "why_now", None)` 前向兼容读取

B05 §4 明示 `action_plan.v1.1` 的 why_now DB 落点（独立 nullable JSONB 列 vs 并入 plan JSONB 块版本化子键）由 contract-owner 二选一。本卡读侧按**列形态**读取（`getattr`，属性缺失即 v1 行 → null）。若 owner 最终选「plan JSONB 块子键」形态，本卡需一行级适配（从 plan 块取子键喂同一 `normalize_why_now`）——判定与降级逻辑零改动。v1 行 null 语义、字段级降级、过期不复用均已测试钉死，落点适配不影响行为契约。

## 3. `context_receipt_ref` 只绑 ref，不实现 ContextSelectionReceipt 本体

B05 §2 的 receipt 本体（候选集/reason_code/selector_version 等）归后续实现卡。本端点要求调用方传入本轮 `context_selection://` ref 并只做 scheme 校验；**无法验证该 ref 指向的 receipt 真实存在**（那是 receipt 读取面落地后的事）。在 receipt 本体落地前，API 入口的 receipt 门是「scheme 形态门」而非「存在性门」——已如实命名 `context_receipt_missing` 并在 docstring 标注。

## 4. `last_valid_outcome` 为有界扫描，非全账本索引

按任务关联取最新 outcome 复用 `OutcomeLedgerService.query` 公共读面（100/页 × 最多 3 页 keyset 续传）。若某 task 的最新关联 outcome 之前压着 **300+ 条**更晚的用户级 outcome，本次扫描取不到 → 视图 `last_valid_outcome=null`（诚实缺失，不报错不臆测）。首页接续卡场景（近期 episode）下不构成实际风险；全索引需账本侧提供 task 关联谓词下推（账本 owner 域），本卡不越界改其查询层。

## 5. `pending_human_step` 来源单一（X-01 计划），未融合 X-07 run awaiting step

「等待人类步骤」取 X-01 ActionPlan 的 `smallest_useful_step`（其形状恰好承载 B05 §5 要求的 `cognitive_ownership`+`execution_mode` 词表位）。在途 run 的 X-07 awaiting step（`run_steps.v1`，owner/handoff 词表）**不**并入：两套词表不同源，跨表转写会制造第二语义。消费面表现：run_ref 非空时 UI 可同时看到 run 的 awaiting step（`GET /runs/{id}` 既有读面）与视图的 pending 步。若产品裁定视图需内联 run awaiting 步，属 episode_resume_view 词表扩展（v1.x bump + reviewer），不在本卡夹带。

## 6. gateway 代理面与挂账

`/episode-resume` 网关组按 house `registerREST` 全动词注册（裸路径 5 动词为 helper 统一形态，引擎侧仅 GET 子路径，多余动词 405 透传）——与 `visual-elements` 等既有组同款，已按守卫规程在 `GATEWAY_ONLY` 挂账 1 行（含日期与理由）。移动端消费接线归 F 线卡，本卡不越权改 UI。

## 7. 环境性说明

- 本地 mypy 计数 55 < 基线文件 77（ratchet 注释已说明平台代际差：CI linux 权威较高值）；零漂移按「改动前后同口径计数持平（55→55）且 episode_resume 相关 0 条」口径登记。
- AQ/BG 守卫初跑失败为 worktree 缺 proto 生成产物（生成物不入库），`make proto-gen` 补齐后 86 规则全绿；本卡零 proto 契约变更。
