# V4-I09｜diff_or_evidence_only

**结论：DIFF（新行为 + 顺手修一处正交组装点缺陷；开关默认关，关闭时既有链路零变化）**

## 做了什么

B06 t3 实证「问候语仍走真模型」（流式 400 → rescue 二次上游调用 → 合成估算 44 tok 记账、客户端零 usage 帧），即 LATENCY_COST_RUNTIME 的 L0 铁律「已知问候/状态不走分类+生成双调用」在现行代码不成立。本卡交付真正零模型的确定性快路与快慢分层：

1. **零模型快路判定器**（`backend/app/orchestration/deterministic_lane.py`，新增）：纯规则识别可零模型应答形态——问候/在吗（greeting）、确认/致谢/语气附和（acknowledgment）、告别/晚安（farewell）。剥词校验：去掉命中词与标点/语气词后必须零实质字符，否则一律回落慢路。快路应答为版本化模板（v1），形态对齐 B06 t3 真模型问候输出。
2. **分层绑定真实路径**（四点，全部零上游调用）：
   - `router_node`（standard_workflow）：快路轮免路由——跳过 RouterNode 的 embedding 相似度调用（隐含模型 attempt），直接落 generation；
   - `generation_node`：快路轮短路——零模型选择、零 prompt 组装、零生成调用，模板 delta 直出（对齐 memory_answer 既有短路先例与 WT373 拆帧契约）；
   - `generation_review_node`（review_nodes）：`chat_lane=deterministic` 显式跳过 review/reflection（不再依赖 <80 字符长度启发式）；
   - `response_builder._cleanup`：快路轮跳过合成 token 估算，账面 0+0 真实 token 直达 `no_generation_model` 桶（B06 实证的「模板直出却记 44 tok 估算」计量污染不再产生）。
3. **快慢分层可观测**：
   - lane 契约 `context_data["chat_lane"]` ∈ `deterministic` / `model`（`model` 在真实模型生成链显式标记）；
   - 快路 status 帧 metadata 携带 `chat_lane=deterministic` + `deterministic_lane_kind`；终帧 metadata 透传 `chat_lane`（缺省不带键 = 既有行为）；
   - 新 metric `sparkle_chat_deterministic_lane_total{kind,trigger}`（封闭枚举）+ `[DeterministicLane]` 结构化日志。
4. **行为开关**：`ENABLE_DETERMINISTIC_FAST_LANE`（`settings.py`，默认 **False**，release_flags 同族模式——权威在 Settings 单例；关闭时本卡全部行为点零触发）。
5. **顺手修（卡面授权：快路正交路径上的组装点修正）**：`llm_secure_io.secure_messages` 组装点角色归一化——大写角色（如 `USER`，网关/枚举名回显形态）归一为小写白名单角色后上行。这是全部 provider 调用的共享组装 choke point；dashscope 对大写角色回 400（B06 t3 流式失败根因线索）。同时修复潜在既有缺陷：大写角色消息此前绕过 user 内容消毒分支。**该修复与快路完全正交（只影响真模型慢路），且属防御性归一化，不改变任何合法输入行为。**

## 验收逐条（卡面）

1. **L0 token=0 且无隐含模型 attempt**：满足（开旗时）。单测以 fail-if-called 桩断言零模型选择/零 prompt 组装（`test_generation_node_greeting_zero_model_with_lane_marker`）；路由层零 RouterNode 构建（`test_router_node_skips_router_on_deterministic_turn`）；记账面 0+0（`test_cleanup_zero_model_lane_records_no_synthetic_tokens`）；客户端零 usage 帧断言在场。快路 context_data 不写 generation_model_key → 计量归 `no_generation_model` 桶。
2. **有效首内容不以 stage/ack/模板鸡汤抵扣**：满足。剥词校验保证任何带实质请求的轮次（含「你好+请求」复合句、疑问句、工具/个人数据/深度词、超长刷屏）回落真模型；确认类在助手上一条消息以问句/提案收尾时让位（「好的」= 应允提案，需模型执行动作）；对/是的/继续等上下文依赖词有意不进词表。
3. **路由与降级不损工具/授权合同**：满足。planned_tool_sequence / 非 standard chat_mode / 文档 / 专家 / 显式角色 / deep 模式 / 文档级检索任一在场 → 永不快路（与 capability_lane deliberate 触发同源共享常量，无抄写清单）；fallback 链路未触碰。

## 快路形态清单（v1，trigger 为封闭词表）

| kind | 例（词表节选） | 模板行为 |
|---|---|---|
| greeting | 你好/您好/hello/hi/hey/哈喽/嗨/早上好/中午好/下午好/晚上好/在吗/在么/在嘛/在 | Sparkle 问候+开放邀请（对齐 B06 t3 真模型输出形态） |
| acknowledgment | 好的/好/嗯/嗯嗯/ok/okay/kk/收到/明白/了解/知道了/懂了/没问题/谢谢/多谢/感谢/thanks/哈哈/嘿嘿/嘻嘻/呵呵 | 附和应答；致谢子族回「不客气」 |
| farewell | 再见/拜拜/回见/下次见/晚安/bye/byebye/good night | 告别应答 |
| （排除） | 对/是的/没错/行/可以/中/继续/go on/no | 有意不进词表：上下文依赖（提案应允/续写/拒绝），必须走真模型 |

守卫：≤24 字符；剥词后零实质字符；无深度词/工具意图/个人数据意图（capability_lane 同源常量）；无 deliberate 上下文事实；确认类无待提案。

## 与既有事实的关系

- 不重建 V3：快路短路复用 memory_answer 先例（同帧协议同 __end__ 语义）；capability_lane（E-02 fast/deliberate）原样保留——其表述的是「模型深度轴」，本卡 lane 表述「是否零模型」，两轴正交并存。
- 本卡无 DB 迁移、无 proto 变更、无生成代码改动、无 HEAVY。
- 计量面：真模型慢路的「带 token 的 no_generation_model 检出器」缺口（B06 A3/estimate_cost 错价 A4）属 I10 工作面，本卡未越界；本卡只保证快路自身零估算污染。

## 交付物索引

`run_manifest.json`（命令/exit/环境/零模型预算声明）、`test_results.json`（271 passed 明细）、`review_receipt.json`（PENDING，待独立会话在集成 SHA 复验）、`limitations.md`。
