# V4-I09 一审 receipt（独立审查 R1）

- **审查会话**：wtI09R（未参与 I09 实现；只读审查 + 本 receipt 提交，未 push）
- **受审对象**：分支 `agent/v4/i09` @ `7818ba809a6fab8efbf86b016d5078d8abe0d7bd`（基线 `c67e45a3`）
- **裁决**：**PASS_WITH_CHALLENGES**（R1-C1 须修正证据措辞或立后续卡；R1-C2/C3 记录在案，词表迭代卡消化）
- **审查日期**：2026-09-28

## 复跑证据（本会话实跑，非转抄）

| 命令（`cd backend` + `SECRET_KEY=test-secret-key-for-local-run REDIS_URL=redis://localhost:6379/0`） | 结果 |
|---|---|
| `pytest tests/unit/test_deterministic_lane.py -q` | **48 passed** |
| `pytest tests/unit/test_stage37_llm_safety_kill_switch.py -q`（secure_messages 既有消毒语义回归） | **7 passed** |
| `pytest tests/unit/test_capability_lane.py -q`（共享常量同源面回归） | **61 passed** |
| `pytest tests/unit/test_standard_workflow_generation_routing.py tests/unit/test_review_skip_logic.py -q`（router 改动与 review skip 邻接面） | **36 passed** |
| 纯函数对抗探针 16 例（`resolve_deterministic_lane` 直调，零模型零上游） | 见下节 |

与交付自报（271 passed / 16 文件）一致方向；本审抽 5 文件 152 用例全绿，含 secure_messages 既有消毒分支全部既有断言。

## 审查点逐条

### 1. 零模型断言真实性 —— 属实（有边界，见 R1-C1）

- **generation 短路点位置**（`standard_workflow.py:1564-1590`）：位于全部模型选择分支（`get_configured_llm_service*` 各档）与 `build_system_prompt` 之前；命中即 `record → status 帧 → delta 帧 → append → __end__`。短路前只有纯函数（`_resolve_recent_memory_answer`、slim 判据、`resolve_capability_lane`——均零模型，读码核实）。fail-if-called 桩（`test_generation_node_greeting_zero_model_with_lane_marker`）在 runtime 证实零模型选择/零 prompt 组装/零 usage 帧——不是「调了但没结果」，是根本不进入该代码路径。
- **router 免路由**（`standard_workflow.py:3828-3841`）：跳过分支位于 `from app.routing.router_node import RouterNode`（:3843，惰性导入）**之前**——命中时 RouterNode 类从不构造（`test_router_node_skips_router_on_deterministic_turn` 以构造即炸桩证实）。router 只打日志不落计数，遥测单点在 generation 执行——无双计。
- **但见 R1-C1**：graph 顺序 `context_builder → retrieval → router`（:3688-3689），快路轮 **retrieval_node 仍先于 router 执行**，其中 `retrieve_context → hybrid_search` 在 embedding 供应商已配置时会发起上游 embedding 模型调用。

### 2. 误触发风险 —— 剥词校验是真实安全网（16 例实跑）

实测（`resolve_deterministic_lane` 直调）：

| 对抗样例 | 结果 | 机理 |
|---|---|---|
| 「好的，那我们开始深度学习吧」（任务书点名） | SLOW | 「深度」非深度词、剥「好的」后残留「那我们开始深度学习吧」实质字符 → 剥词校验拦截 |
| 「在吗？我有个问题」 | SLOW | 剥词残留 |
| 「broker」/「this」（英文子串陷阱：含 ok/hi） | SLOW | 词表子串命中后剥词残留 `bre`/`ts` 实质字符——剥词校验兜住了裸 `in` 匹配的天然缺陷 |
| 「好的 3 点见」（数字残留） | SLOW | `_SUBSTANTIVE_RE` 含数字 |
| 「ok我明白了」 | SLOW | 剥词残留「我」 |
| 提案后「好的」（助手上一条含「…吗？」） | SLOW | 待提案守卫让位 |
| 陈述后「好的」（上一条无问句/提案标记） | FAST | 符合设计 |
| 提案后「晚安」 | FAST | 守卫只限 acknowledgment 类——greeting/farewell 语义不因问句反转，合理 |
| 「对的」「是的」「继续」「行不行」 | SLOW | 有意排除词不在词表，裸词无匹配；复合句由剥词校验回落 |

待提案守卫语义核实（`_pending_proposal_in_history`）：取 `conversation_context.messages` 中**最后一条非空 assistant 消息**，含 `？/?/吗/要不要/需要我/要我/是否` 任一即让位。「吗」为任意位置子串匹配——偏保守方向（宁可慢路），与卡验收 2 优先级一致。

### 3. 有意排除词表 —— 代码中真实生效

对/是的/没错/行/可以/中/继续/go on/no 确不在三个词表内（`deterministic_lane.py:152-156` 注释与实现一致）；「对的，但是…」类复合句经剥词校验自然回落慢路（注释声明语义与实现核实相符）。实测「对的」「是的」「继续」均 SLOW。

### 4. 分层可观测 —— 接线真实，无命名冲突

- 写点：generation 短路写 `chat_lane=deterministic`（:1582）；真模型链路出口写 `chat_lane=model`（:1992-1994）——两轴互斥、开关关闭时不写任何键（回归测试证实）。
- 透传：status 帧 metadata + 终帧 metadata（`response_builder.py:992-996` 读 `context_data`）。
- 计数器 `sparkle_chat_deterministic_lane_total{kind,trigger}`（`metrics.py:725-731`）：与引擎既有 `sparkle_chat_capability_lane_total`、B06 面及网关 `sparkle_ws_*`/`sparkle_gateway_*`/`sparkle_grpc_*` 无冲突；`kind` 封闭枚举 × `trigger` 封闭词表（~60），基数有界。

### 5. 顺手修边界（secure_messages 大写 USER）—— 正交防御，语义只增不减

- 归一化只动 `role` 键：白名单 `{system,developer,user,assistant,tool,function}` 内小写化；白名单外 fail-closed 回 `user`（比原样上行大写角色给 provider 更安全——原行为必 400）。
- **消毒分支核实**：大写 `USER` 此前 `role != "user"` → 走 `redact_secrets` 弱分支（绕过 `sanitize_text_for_llm`）；归一化后进 user 分支，消毒面**只增不减**。`system/tool` 角色大小写变体同理归位。bypass 分支（安全总开关关）仅同步归一化 role，content 处理（`_redact_string_values`）逐字未动。
- 既有测试全绿：`test_stage37_llm_safety_kill_switch.py` 7 passed（本会话实跑）。

### 6. 复跑 —— 全绿（见顶部表格）

## CHALLENGED

### R1-C1（中）｜「无隐含模型 attempt」在 embedding 已配置环境不成立——快路轮仍有一次上游 embedding 调用

- **证据链**：graph 边 `context_builder → retrieval → router`（`standard_workflow.py:3688-3689`）→ `retrieval_node` 无条件执行 `ks.retrieve_context`（db_session/user_id/query 在场即执行）→ `galaxy/retrieval_service._execute_hybrid_search` 调 `embedding_service.get_embedding`（上游 DashScope/SiliconFlow API，`retrieval_service.py:285-287`）；且语义缓存查找本身先嵌 query（`semantic_cache_service.py:387-389`）。B06 探针环境 dashscope 已配置（t3 实证），即生产形态下**快路轮先烧一次 embedding，再被 router/generation 短路**。
- **断言冲突**：模块 docstring 与 diff doc 验收 1 称「命中即 token=0 且**无任何隐含模型 attempt**」——而实现自己把 RouterNode 的 embedding 定义为「隐含模型 attempt」并跳过之；同一标准下 retrieval 更早的 embedding 未被跳过，断言自相矛盾。`limitations.md` #4 披露了「context_builder/retrieval 仍会执行」但将其表述为「DB/Redis 读、确定性检索决策」，漏掉 embedding 模型调用面。
- **成立范围**：记账面 token=0 成立（embedding token 不入 chat token 记账，0+0 直达 `no_generation_model` 为真）；「无隐含模型 attempt」仅在 embedding 未配置（E-05 fail-closed 词法降级）环境成立。
- **裁决影响**：不否决交付（机制按设计工作、开关默认关、limitations 有部分披露），判 PASS_WITH_CHALLENGES。**要求二选一**：(a) 修正 `limitations.md` #4 与 diff doc 验收 1 措辞（明示 embedding 已配置时每快路轮一次上游 embedding 调用）；(b) 立后续卡把确定性分流提前到 retrieval 之前（process_stream 层），真省掉该调用。

### R1-C2（低）｜`_SUBSTANTIVE_RE` 未覆盖全角数字等字符面

`[0-9a-zA-Z\u4e00-\u9fff]` 不含全角数字（FF10-FF19）等；实测「好的１２３」**FAST**。真实频率极低，但与「剥词后任何实质字符回落」的声明意图不符。建议词表迭代卡将判据收紧为「剥词后 remainder 去空白非空即回落」。

### R1-C3（info）｜混合词 kind 归属错位（装饰性）

「谢谢，再见」命中 acknowledgment（matched 按 len desc + 元组序，ACK 先于 FAREWELL）→ 回「不客气」，对告别语境轻微错位。应答仍属诚实模板，不阻塞；词表迭代时可按最长词/ farewell 优先修正。

## 残余风险（交付已如实披露，本审确认）

- 开关默认关，行为未被真实整链验证（limitations #1）——本审不要求，启用卡面处理。
- 待提案守卫为启发式，陈述式邀请（「你可以试试番茄钟」→「好的」）仍走模板（limitations #3）——已在 limitations 如实记录。
- `chat_lane` 网关/移动端消费未实现（limitations #8）。

## 结论

机制真实、守卫保守方向正确、测试可失败且全绿复现、记账与观测面接线属实。C1 为证据措辞/范围问题而非机制缺陷，修措辞或立后续卡后可销账 DONE_REVIEWED。
