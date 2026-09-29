# FIX-567 · diff 叙证（实现 commit 5290e010，5 文件 +394/-20）

## 缺陷 → 修法映射

U01 一审 R1-1 三个事实点逐一收口：

| R1-1 事实 | 本卡处置 |
|---|---|
| 「唯一生产链 `context_pack.py` 硬编码 `selection_role="chat_context"`」 | 不动（chat 面归因正确）；resume 面新增**独立生产者**，同消费既有 `record_receipt` 落账链（幂等键 receipt_id 唯一约束、落库前 `validate_contract` fail-closed） |
| 「`latest_receipt` 不分角色返回最新一条」 | 不动（读面语义正确：角色判定归消费方——U01 CH-1 已裁角色门方向正确）；生产者补齐后 latest 自然翻转为 resume_view，新测 `test_latest_receipt_flips_to_resume_view_role_after_resume_flow` 钉死该翻转 |
| 「I01 端点只校验 ref scheme 不生产回执」 | 本卡主修：端点层在视图成功聚合后、HTTP 返回前落 `resume_view` 角色回执（B05 §2「receipt 在 resume view 返回之前」） |

## 三处产品代码 diff 要点

1. **`backend/app/orchestration/context_receipt_assembly.py`**（纯函数层）
   - 模块 docstring 从「ContextPack 单生产者」扩为「两个生产者」（归因判定序原文不动）；
   - `SELECTOR_VERSION_RESUME_VIEW = "episode_resume.v4-f567.v1"`（selector 版本位命名对齐 `context_pack.v4-i06.v1` 惯例）；
   - `assemble_resume_view_receipt(user_id, goal_id, task_id, goal_version, task_version, memory_epoch)`：
     候选 = `[task://<task_id> selected, goal://<goal_id> selected]`（视图依据权威；两 ref 可被 `verify_source_ref` join tasks/goals 真源属主校验——不是悬空 ref）；聚合无拒用机制 → 零 rejected 候选、不臆造归因；`policy_version=None`（本面未读）；`why_now=None`（视图 why-now 随视图本体交付，回执级 null = 合同 null 语义，与 pack 面同口径）；budget = 如实读数（scan=selected=2）。

2. **`backend/app/services/episode_resume_service.py`**（聚合服务——保持只读）
   - `ResumeSelectionObservations`（frozen dataclass）：goal_id/task_id/goal_version/task_version/memory_epoch——全部是服务真实读数的锚（goal/task 版本 token 用 house `version_token(updated_at)`，与 `_last_confirmed_step` 同源）；
   - `EpisodeResumeResult` 尾部追加可选字段 `observations`（默认 None）：成功聚合并过 `validate_resume_view_shape` 后填充；全部降级路径恒 None（无选择发生不产生回执，B05 §2）；
   - 服务类零新增方法——`test_service_is_read_only_surface` 纪律锚原样不动。

3. **`backend/app/api/v1/episode_resume.py`**（API 边界——生产挂点）
   - `_record_resume_view_receipt(db, *, user_id, observations)`：mode 门 `normalize_mode(settings.CONTEXT_SELECTION_RECEIPT_MODE) ∈ {shadow, live}`（off = V3 路径零变化）；纯函数装配 + `record_receipt` 落账；**fail-soft**：任何异常只 WARN（`FIX-567 resume_view selection receipt failed`）不阻断视图——与 `ContextPackBuilder.build` 面回执纪律逐字同口径；
   - 端点在 404 门之后、响应返回之前调用（`result.view is not None and result.observations is not None` 才产生）。

## 测试 diff（+6 测，全部可失败）

- `tests/unit/test_context_selection_receipt_wiring.py`：装配纯函数 2 测——角色值/词表成员/schema_version/receipt_id 前缀/候选逐条（ref+status+reason_code 三元组全等）/input_versions 六字段/why_now null/budget 计数/`validate_contract()==[]`；未读权威位 null 不冒充（合同 input_versions 纪律）。
- `tests/api/test_episode_resume_api.py`：端点 4 测——
  - 正例：live 模式端点调用后落恰好 1 条 resume_view 行（角色值/schema/receipt_id 前缀/候选三元组/input_versions 含版本 token 逐字段/budget/why_now 逐断言）+ **I06 `get_latest_context_receipt` 下发面断言**（mode/receipt.selection_role/receipt_id/schema_version 透传 + `source_verification` 双 resolved + `resolved_selected_count==2`）；
  - 反例×2：off 模式零回执（视图照常返回）；降级视图零回执（receipt ref 缺失 + goal 终态两形态，无选择发生不产生）；
  - 角色分流：预置 chat_context 回执（既有唯一生产者）→ latest 恒 chat_context（修复前恒态）→ resume 流后 latest 翻转 resume_view 且 selector_version 随之改变。

## 不做什么（负面清单）

- 不动 `proto/*.proto`、不动 `backend/gateway`（零 WS 帧携带 receipt——grep 亲验）；
- 不动 `context_pack.py` chat 链、不动 `latest_receipt` 读面、不动移动端任何文件（消费面已就绪）；
- 不动认证/授权（`get_current_user` 链原样）；I1 纪律：回执只证明「读与选」，不授予权限、不构成业务事实。
