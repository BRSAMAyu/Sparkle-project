# V3-FIX-160 决策备忘 · 截断轮持久化语义三轨统一（产品裁决输入，不实现）

- 2026-09-25 · wt471 · 证据：base `310d6b22` 全链代码实证（file:line 见正文）+ Go 读结构反序列化探针（runtime 实证，探针未入库）+ 体例参照 `FIX97_DECISION_MEMO.md`
- 本文只做语义裁决输入，不改任何产品码；V3-FIX-155 既有修复（哨兵校验/error 帧/completed=false/truncated 标注）全部维持。

## 纠偏先行（台账 160 行机制归属勘误）

160 行表述「orchestrator `_finalize_turn_after_done` 仍把已流出的部分 assistant 文本当完整轮落 chat_sessions 历史」——**实证不成立**，实际载体在网关：

1. `_finalize_turn_after_done`（`backend/app/orchestration/orchestrator.py:1259-1300`）只经 `_write_turn_end_episodic_memory`（:1143）写 episodic 记忆（`MemoryService.create_episodic_memory`，orchestrator.py:1225），从不写 chat_messages/chat_sessions。
2. 普通 chat turn 的 task_completed 摘要为空（`_build_task_completion_memory_summary`，orchestrator.py:1071-1128，无任务完成标记时返回 `""`），命中 `if not summary: return`（orchestrator.py:1207-1216）早退——普通轮连 episodic 都不写。
3. 引擎通用 /ws/chat 图路径**没有 assistant 行落库调用**：`_persist_assistant_message` 全仓仅 3 个调用点（exam-sprint fast-track orchestrator.py:832、aurora runtime :1401、checkpoint debrief :2406），均非通用路径；通用路径唯一落库的用户行在 context_builder.py:2081。
4. **实际载体是网关**：chatflow `saveMessage`（`backend/gateway/internal/handler/chat_orchestrator_feedback.go:51-78`）→ Redis `chat:history:{sid}`（`backend/gateway/internal/service/chat_history.go:327-336`，RPush :333、LTrim 保尾 20 + TTL）→ persister 选通时才落 DB 行（`chat_history_persister.go:33`，仅 `(id, session_id, user_id, role, content, created_at, updated_at)`，无标注列；`CHAT_PERSISTER_ENABLED` 默认 false，`config.go:676`）。
5. 危害本身**成立**，只是机制不同：
   - 「后续轮 LLM 历史当它是完整回答」——引擎下一轮上下文读的就是网关写的同一 Redis 列表：`ContextPruner._load_chat_history`（`backend/app/orchestration/context_pruner.py:371-389`）只认 `role`+`content`，**无视任何 truncated 键**；
   - 「历史回放视其为完整回答」——读结构 `ChatHistoryMessage` 无 `truncated` 字段（chat_history.go:131-151），键被 `json.Unmarshal` 静默丢弃。Go 探针 runtime 实证：`truncated:true` 载荷 → 字段丢弃；`is_interrupted:true` 载荷 → 存活（`IsInterrupted=true`）。

## 新发现缺陷（已登记 V3-FIX-174）：网关 FIX-155 防线对引擎哨兵截断不可达

引擎哨兵判定的截断轮（T1：上游缺 finish_reason/[DONE]）在 /ws/chat 轨道**仍以"完整轮"形态过网关**：

- generation_node 置旗标+发 error 帧，但**不中止本轮**（`backend/app/agents/standard_workflow.py:2074-2103`）；部分文本无条件进 `state.messages`（`state.append_message("assistant", full_response)`，standard_workflow.py:2292；部分文本累积于 :2035）；
- `_build_final_response` 取最后一条 assistant 消息为 full_response（`backend/app/orchestration/response_builder.py:943-947`），旗标只进 metadata（:994-998，注释明言「终帧仍走既有 STOP done 契约」），终帧恒 `finish_reason=STOP`（:1533）；
- 网关侧 `sawUpstreamFinishReason` 对任何非 NULL finish_reason 置 true（`chat_orchestrator_chatflow.go:794-796`）→ `possiblyTruncated := !sawUpstreamFinishReason` = false（:988）→ **部分文本无标注落历史**（:1014-1022）且**语义缓存照写**（:1024-1035）——缓存命中会把部分文本当完整答案整段重投（:530-545，FullText+STOP）；
- 网关对引擎中游 error 帧零反应：recv 循环只透传（:831-855 switch 全量转发），无 `resp.GetError()` 分支（全文件 grep 无）。
- 同族暴露：graph 超时路径（orchestrator.py:3815-3827，ERROR 帧+部分已流文本）同样 `sawUpstreamFinishReason=true` → 部分文本照落照缓存。
- FIX-155 网关防线（truncated:true+缓存退出，chatflow.go:982-1021）实际只覆盖 T2（网关自身 EOF/recv-error 面，:748-762、:988）；T1 恰是哨兵修后截断的**主形态**。

## 三轨现状对照表（截断轮持久化语义）

| 轨道 | 截断事件源 | 落库/落历史什么 | 标注 | 消费方 | 结论 |
|---|---|---|---|---|---|
| REST `/stream`（引擎 FastAPI SSE） | 引擎哨兵 T1 | **不落库**：`stream_interrupted` → done `completed=false,reason=upstream_stream_truncated` 后 `return`，先于 `save_chat_message`（`backend/app/api/v1/chat.py:729-738、836-843`；save 在 :846-855，user+assistant 两行一起写 :1233/:1244）→ **user 行也不落** | done 帧显式 completed=false（docstring 契约 :659-663） | 客户端按契约不渲染/不入历史 | **已闭环**（155）；残留不对称：user 行一并丢失，后续轮上下文看不到这次提问 |
| /ws/chat（网关 WS → 引擎 gRPC StreamChat） | T1（引擎哨兵，**主形态**） | 部分文本进 Redis `chat:history:{sid}`（网关 saveMessage :1014-1022）+ persister 选通时 DB chat_messages 行（content only）+ **语义缓存写入**（:1024-1035） | **无**：终帧 STOP 使 `truncated` 键不写；metadata `generation_stream_truncated` 仅随 gRPC 终帧透传（response_builder.py:998），网关不读 | Redis 列表 → 引擎下一轮 LLM 上下文（context_pruner.py:371-389，**污染主通道**）+ 网关 GetMessages 回放（读结构丢键，chat_history.go:131-151）；DB 行 → 回放 DB fallback（无标注列可读） | **核心缺口**：部分文本冒充完整轮进后续上下文与回放 |
| /ws/chat | T2（网关 EOF/recv-error） | 部分文本落 Redis+DB（chatflow.go:748-762、:1014-1022） | saveExtra `truncated:true`（:757、:1019）+ 缓存退出（:1024 起 if 取反） | **零消费方**：读结构无字段（探针实证）；DB INSERT 不含该键（persister.go:33） | 标注写了没人读，且 Redis TTL/DB 回填后彻底消失 |
| gRPC 直连（无网关） | T1 | **什么都不落**：通用路径引擎侧无 assistant 落库（见纠偏先行#3）；160 行「gRPC 轨道部分文本落历史无标注」对通用路径不成立 | metadata `generation_stream_truncated`（response_builder.py:994-998）+ error 帧（standard_workflow.py:2086-2103） | 客户端自决；审计面已有 | 语义上已对齐 A（不落库），契约面已具备 |
| 三轨子路径（fast-track/aurora/debrief，`_persist_assistant_message` 三调用点） | 不经 llm_service 流哨兵 | assistant 文本照常落 chat_messages（persistence_layer.py:55-137） | 无（也不存在截断态） | 同上 | 与本议题正交，不在 160 范围 |

关键共享事实：`chat:history:{sid}` 的**唯一写者是网关**（chat_history.go:332、:809-811 回填），引擎只读（context_pruner.py:372）；`chat_messages` 无 metadata 列（gfix03 迁移删除，getMessagesFromDB 手写 SQL 仅六列，chat_history.go N-2 注释）——这是历史面上任何「标注」方案的硬约束。既有可复用通道：`is_interrupted` 全链已通——网关 DTO 出口（handler/chat_history.go:38、:138）→ `GET /api/v1/chat/history/:conversation_id`（cmd/server/setup.go:592）→ mobile 解析（chat_message_model.g.dart:42）→ 气泡中断标记渲染（chat_bubble.dart:1247-1263，l10n chatInterrupted）；但**服务端无人写入**（全仓仅结构字段定义，无写点）。客户端本地已有部分文本保留语义：M6-09 取消/失败时非空部分以 `isInterrupted:true` 落本地消息（chat_provider.dart:343-364）。

## 候选方案

### A · 三轨统一「截断轮不落库」（对齐 REST，最严格）

- **机制**：/ws/chat 网关增加 T1 感知并跳过截断轮 assistant 持久化+缓存写入；gRPC 面已天然满足；REST 已闭环。
  - T1 感知二选一（推荐前者，顺带修 V3-FIX-174 超时同族）：① recv 循环对 `resp.GetError() != nil` 置 `sawEngineError`（chatflow.go:831-855 加一个分支），error 帧 present 即视为非完整轮；② 读终帧 metadata `generation_stream_truncated`（map 值为字符串化布尔）。
  - 判定为截断轮 → 跳过 :1014-1022 saveMessage 与 :1024-1035 缓存写，照发 synthetic STOP done（客户端终态契约不破坏，shouldEmitSyntheticDone :961 保留）；客户端体验不变（error 帧已失败态+本地部分文本保留，chat_provider.dart:343-364）。
- **改动面清单**：仅网关 chatflow 一个文件（检测分支+跳过分支）+ Go 单测（T1 mock 流：断言无 saveMessage/无 SetExact；T2 行为回归）+ V3-FIX-174 一并闭环。估算 **1 卡**。
- **契约/迁移影响**：零 proto 变更、零 DB 迁移、零 mobile 变更；REST docstring 契约语义（completed=false 轮不入历史，chat.py:662）顺势成为三轨事实标准。
- **核心危害覆盖度**：**最高**——部分文本不再进 Redis 历史/DB/语义缓存，「冒充完整回答污染后续 LLM 上下文」与「回放当完整答案」「缓存重投递」三条通路一并切断。
- **回退成本**：极低，revert 单文件即回到现状。
- **已知残留**：①截断轮 user 行仍在历史（网关 :374 先于引擎调用落库，无法无痕撤销）——见拍板问题 2；②服务端不再留存截断轮任何痕迹（审计靠引擎日志 standard_workflow.py:2084-2089 + metadata 旗标），若产品要求服务端可回放截断轮则需转 B。

### B · 三轨统一「落库 + truncated 标注」（历史完整可见）

- **机制**：网关对截断轮照落，但标注全链可消费：写侧键对齐 `is_interrupted`（或读侧加 `truncated` 字段映射）→ `ChatHistoryMessage` 加字段（chat_history.go:131-151）→ persister 落列（chat_messages 加 `truncated boolean`，Alembic 迁移；有 `parse_degraded` 先例 models/chat.py:68）→ getMessagesFromDB/repair/backfill 带列（chat_history.go）→ 引擎 ContextPruner 按键过滤或降权（context_pruner.py:371-389）→ DTO/移动端零改（is_interrupted 通道已在）。
- **改动面清单**：网关 4 文件 + 迁移 1 + 引擎 pruner 1 + 契约锁测试；估算 **2–3 卡**。
- **契约/迁移影响**：DB 迁移（分区表 chat_messages，PK 含 created_at）；gfix03/DF-2「chat_messages 保持薄列、富元数据归引擎管道」的既有决策被部分翻转（persister.go DF-2 注释），需在 ADR 记录；proto 不动（metadata 旗标已够）。
- **核心危害覆盖度**：**不彻底**——回放面有标注可渲染（复用 chatInterrupted），但后续轮 LLM 上下文若「带标注保留」，LLM 仍把部分文本当 assistant 回答消费（污染只增标记不减害）；若 pruner 直接过滤，则上下文面收敛回 A 语义，标注只剩回放价值，为回放付迁移+全链成本。语义缓存仍需单独排除（同 A 的 T1 检测工作量一点不少）。
- **回退成本**：中——迁移需回滚脚本，读侧字段可向后兼容保留。

### C · 维持现状仅补消费方

- **机制**：只做「truncated 键 → DTO `IsInterrupted` 映射 + ContextPruner 过滤」，不动 T1 检测、不迁移。
- **改动面清单**：网关读侧 2 文件 + pruner 1；估算 **0.5–1 卡**。
- **契约/迁移影响**：零迁移零 proto。
- **核心危害覆盖度**：**接近零**——T1（引擎哨兵，截断主形态）根本不写 truncated 键（见对照表），补的消费方是死代码；仅 T2（网关自身断连，小概率）在 Redis TTL 窗口内有标注，DB/回填后消失。单独实施无意义；叠加 T1 检测即退化为「B 去掉 DB 耐久性」，标注随 TTL 蒸发，不如直接选边。
- **回退成本**：低。

## 推荐（明确排序）

**A > B > C。** A 以 1 卡、零迁移零 proto 的代价把 REST 已上线的「截断轮不落库」语义推平三轨，是唯一同时切断「后续轮上下文污染 / 回放冒充完整 / 缓存重投递」三条通路的方案；用户可见的部分文本损失已由客户端 M6-09 本地保留（带 isInterrupted 标记）兜住。B 的标注解决回放观感但不解决 LLM 上下文污染（过滤则与 A 等效而代价更高），且翻转 gfix03 薄列决策、动分区表迁移，仅当用户裁决「服务端必须可回放截断轮」时升级。C 单独无效应否决。A 落地应与 V3-FIX-174（网关 T1/T2 检测统一，含 graph 超时同族）合并为一张卡验收：mock 哨兵截断流 → 断言 Redis 历史/DB/语义缓存三处均无部分文本、客户端仍收 error+done 终态帧。

## 需要拍板

1. **截断轮的服务端历史可见性**：部分回答是否要求服务端可回放/审计？不要求 → **A**（客户端本地已保留带标记部分文本，服务端不留痕，审计走引擎日志+metadata 旗标）；要求 → **B**（接受 chat_messages 迁移+gfix03 决策翻转+2–3 卡），A 中网关跳过逻辑改为标注逻辑。
2. **截断轮 user 行去留（两轨一致性）**：A 落地后 /ws/chat 截断轮保留 user 行（网关 :374 已先行落库，无法无痕撤销），REST 截断轮连 user 行也不落（chat.py:836-843 先于 save）——是否接受「保留 user 行」为准（推荐：用户提问是真实意图，后续轮上下文需要它；REST 差异另开小卡对齐即可），还是强制两轨一致删除（/ws/chat 需 tombstone 机制，代价显著，不建议）？
