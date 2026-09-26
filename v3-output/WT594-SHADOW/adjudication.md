# WT594-SHADOW — V3-FIX-299 影子行甄别机制裁决材料

- 工位：wt594（只读研究，无代码修改）
- 日期：2026-09-25
- 上游：V3-FIX-292（FIXED@38a0e658 / b980e4bc，wt580 掌握度确定性重放）
- 目标缺陷：V3-FIX-299（台账行 261）——重放器对首条 payload 行之后的**无 payload 证据行**（exam-sprint 惩罚等绝对 set-point）不重套数值效果
- 本文性质：**裁决材料**，不是修复。供主会话裁决影子行甄别机制后立修卡。

---

## 0. 缺陷机制一句话版

`_load_prior_belief`（`backend/app/services/galaxy/stats_service.py:544`）全量重放时：payload 证据行（`reason=evidence:*`，`request_id=obs=…;conf=…`）走 Kalman 融合；无 payload 的 quiz 级行（`exam_sprint_diagnostic` / `post_exam_review_weak_node` 等，经 `GalaxyService.update_node_mastery` 写入）被判为 presence-only（`stats_service.py:603-611`）——**只计出现、不重放数值**。事件间隔内数值由存储链（`user_node_status.mastery_score`）兑现，但确定性重放的先验里这些行的 set-point 效果丢失，下一次融合从偏低的先验出发把存储值拉回，set-point 效果被抹掉。广义修法（按行重放 set-point）需要先回答：**哪些无 payload 行是 set-point 证据，哪些是 spark `task_complete` 影子行**（后者与证据行同 old/new 双写，重放会把融合结果二次钉值）。

---

## 1. 证据账本行形状普查（量化）

数据源：本机 live PG `sparkle` 库（127.0.0.1:5432，只 SELECT）；本地 sqlite 测试库为 `:memory:`（`tests/conftest.py:116`），无持久化文件可查。快照 2026-09-25，窗口 09-18 → 09-26。脚本：`/tmp/wt594_census.py`（分类逻辑直接 import wt594-shadow worktree 的 `classify_audit_reason` / `parse_observation_payload` / `recompute_evidence_state`，非人工转述）。

### 1.1 行形状总分布（394 行 / 57 用户 / 234 节点）

| 类别（按重放语义） | 行数 | 占比 | 构成 |
|---|---|---|---|
| payload 证据行（重放融合） | **12** | 3.0% | 全部 `evidence:task_outcome`（outcome absorber 写） |
| 无 payload 证据行（299 面） | **100** | 25.4% | 全部 `exam_sprint_diagnostic`，分布在 **100 个 (user,node) 对 / 12 用户** |
| 非证据行 | 282 | 71.6% | `task_complete` 225 + `sprint_task_completed` 35 + 错题本带后缀行 21（`error_review:remembered` 12 / `error_diagnosis:knowledge_gap` 6 / `error_review:forgotten` 3）+ `probe_inval_test` 1 |

### 1.2 V3-FIX-299 严格受影响面（今日快照）

| 指标 | 数值 |
|---|---|
| 同时持有 payload 锚点和**锚后**无 payload 证据行的 (user,node) 对 | **0** |
| 受影响用户 / 节点 / 行 | **0 / 0 / 0** |
| 锚前无 payload 行（已烘焙进锚点，无损失） | 0 |
| 有无 payload 证据行但**无 payload 行**的对（锚点回退=存量值，重放无数值面） | 100 对（即全部 exam_sprint 行） |

**结论：299 在 live PG 严格 bite 面 = 空。** 100 个 exam_sprint 对全是「纯 set-point 账本」：无 payload 行 → FIX-292 锚点回退存量值 → 重放是数值空转，set-point 效果由存储链完整兑现（前提已实证：72/100 对 stored == 末条 set-point 值 ±0.5；28 对偏离全部可归因——衰减服务已折旧（如 stored 29.72 vs set 100）或后续 legacy spark 抬升（1 对 set 0 后 stored 100））。

**但结构暴露是真实的**：任何一条 payload 证据（spark outcome / absorber）落到这 100 个节点之一，锚点即冻结；此后该节点每一条 `exam_sprint_diagnostic` / `post_exam_review_weak_node` 行都变 presence-only → 数值效果在下次融合时丢失。只要考试冲刺流与证据流在同节点交错，299 即咬人。触发面窄（规格判断正确），但是**时间问题，不是概率问题**。

### 1.3 影子行实测（甄别机制的冲突对手方）

| 指标 | 数值 |
|---|---|
| `task_complete` 行总数 | 225 |
| 与证据行构成 spark 双写签名（同 user/node/old/new/created_at） | **0** |
| 独立存在（legacy 时长路径，outcome=None 的 spark） | 225（100%） |
| payload 对中同时存在 `task_complete` 行（非同事务） | 12/12 对 |
| 影子行与证据行 created_at 完全相同（ORDER BY 不稳定面） | 0 对 |

**live PG 里影子行双写从未发生**——`spark_node` 的 outcome 双写路径（`stats_service.py:190-225`：先 `task_complete` 行、后同 old/new 的 `evidence:*` 行）在 live 数据零痕迹，与 FIX-292 注记「重放在 aiosqlite 才真正执行」一致；该形状目前只存在于测试环境。冲突是**结构性的（写入代码现状如此），不是存量的**。

### 1.4 普查副产品：三条改变裁决权重的相邻事实

1. **读侧词表已两次实证漂移。** `QUIZ_EVIDENCE_REASONS`（`mastery_evidence.py:375`）精确匹配，但真实写串是：错题本写 `error_diagnosis:<type>` / `error_review:<perf>`（带后缀 → `classify_audit_reason` 判 None，连 presence 都不算，live 已有 21 行）；aurora 写 `aurora_completion_check_correct`（词表预期是 `correct_answer`，不匹配）。**读侧词表落后于写点是这个缺陷家族的第二个症状，299 本身就是第一个症状。**
2. **`reason` 是客户端可控自由串。** `/sync/mastery`（`api/v1/galaxy.py:114`，`request.reason` 默认 offline_sync，:157 透传）、`/nodes/{id}/mastery`（`:120,195`，`request.reason`/`request.source`）、gRPC `UpdateNodeMastery`（`galaxy_grpc_service.py:218`）三条入口把任意字符串写进审计行。G-01 R-1 收口只把已知非证据词 fail-closed 判 None；客户端今天就可以伪造 `reason=exam_sprint_diagnostic` 的行并获得 QUIZ presence 效果（摘 legacy 旗）。**一旦按行重放 set-point 数值，伪造面从 presence 升级为数值注入。**
3. **无 payload 证据行语义不齐。** `exam_sprint_diagnostic` / `post_exam_review_weak_node` 是绝对 set-point（写 `new_mastery`=考分/惩罚值）；错题本（`old+delta`）、`knowledge_service_increment`、aurora（`_increment_mastery`）是 delta 型。统一「assign new」或统一「re-apply delta」都对其中一类不成立——甄别机制必须能区分效果类型，而不只是区分证据 vs 影子。

---

## 2. 影子行甄别机制候选方案

记号：效果类型 = observation（payload 融合）/ set_point（绝对 assign）/ delta（相对 nudge）/ projection（影子行等，skip）。

### 方案 A：写入侧显式标记（`effect_kind` 列，服务端定性）

审计行加 `effect_kind` 列（`observation` | `set_point` | `delta` | `projection`），由**服务端**在写入点定性；重放器按列分支。

- **侵入面清单**：
  - Alembic 迁移 ×1（加列 + 394 行回填，回填规则=写点同款 reason→kind 映射）；`make sync-db` 重导出网关 `schema.sql` 快照。
  - 写点 ×4（全仓 `INSERT INTO mastery_audit_log` 仅此四处，已 grep 核实）：`stats_service.spark_node:192`（task_complete→projection）、`stats_service.spark_node:213`（evidence:*→observation）、`galaxy_service.update_node_mastery:3528`（**唯一咽喉**：按服务端 reason→kind 映射定性，自由串客户端 reason 一律 projection）、`outcome_absorption_service:234`（→observation）。
  - 读面：`stats_service._load_prior_belief` SELECT 加列 + 分支；`get_evidence_counts_by_node:640` 的真实证据判定改按 kind（顺带修复错题本/aurora 词表漂移——它们在咽喉处定性，词表死掉）。
  - 回填脚本进 `scripts/devtools/`；幂等/邻域测试。
- **与 FIX-292 幂等断言兼容性**：完全兼容。重放仍是账本纯函数；锚点定义从「首条 payload 行 old_mastery」推广为「首条证据效果行（observation 或 set_point）old_mastery」——锚前效果行烘焙进锚（与现状同语义），锚后 set_point 行 assign、observation 行融合。对**现有全部账本重放结果逐位不变**（今日锚后 set-point 行=0，改动只对未来的交错账本生效）。
- **失败模式**：
  - 回填与写点定性规则不一致 → 同一账本不同时点重算不同（破坏幂等）。缓解：kind 映射单点定义（`mastery_evidence.py`），迁移回填 import 同一映射。
  - 未来新裸 SQL INSERT 忘写列 → NULL。缓解：读侧 NULL fail-closed 判 projection（宁丢效果不注入数值），INSERT 走 ORM 或补默认。
  - 错题本幂等键（`edi:`/`erv:` 部分索引）不受影响（动的是新列不是 request_id）。

### 方案 A′：写入侧标记但不加列（request_id 命名空间，如 `sp=<value>`）

镜像 `obs=`/`oc=` 编码，set-point 行在 `update_node_mastery` 咽喉处把 `request_id` 写成结构化载荷，读侧解析。

- **侵入面**：仅 `update_node_mastery` 写点 + `parse_observation_payload` 邻近加解析 + 重放分支。无迁移。
- **兼容性**：同 A。
- **失败模式**：(1) 存量 100 行无标记——要么对 append-only 账本做 UPDATE 回填（**违反账本即真源**；且 request_id 是错题本幂等键载体，重写有撞键风险），要么接受存量+近期行持续不可重放（299 拖尾）；(2) VARCHAR(100) 里 `obs=/conf=/oc=/tk=/sp=` 多段编码继续膨胀，解析脆弱；(3) 客户端可控 request_id 的入口仍可伪造 `sp=` 段——除非同样在咽喉处覆写，那时侵入面已等于 A 少了列。
- **工作量**：S–M。

### 方案 B：读取侧甄别（reason 词表 + 形状启发，零 schema 变更）

`mastery_evidence.py` 增 `SET_POINT_EVIDENCE_REASONS` / delta 词表，`classify_audit_reason` 前缀匹配扩展，重放器按词表分支；影子行靠现有 `NON_EVIDENCE_REASONS`（`task_complete` 已显式判 None）排除，不需要形状配对。

- **侵入面清单**：`mastery_evidence.py`（词表+分类）+ `stats_service._load_prior_belief`（分支）+ 测试。最小侵入。
- **与 FIX-292 幂等断言兼容性**：兼容（同纯函数重放，分支更多）。
- **失败模式**：
  - **词表漂移是已发生的现实**（§1.4.1 两例）：每新增一个写点都要回读端补词表，漏一个 = 静默丢效果 = 299 复发。该方案把缺陷从「修掉」变成「持续人工同步」。
  - **可伪造**（§1.4.2）：reason 三条客户端入口自由串；数值化后伪造 = 数值注入。today 只丢 presence 旗，明天可以被写掌握度。
  - delta/set-point 语义区分继续靠人工记词表，复杂度随通道数线性涨。
- **工作量**：S（实现），但带持续性正确性债务。

### 方案 C：重放语义重设计（「事件间已兑现」→ 混合重放）

顺序遍历账本：observation→融合、set_point→assign(`row.new_mastery`)、delta→nudge(`new-old`)、projection→skip，事件间衰减保持现契约；锚点取首条证据效果行 old_mastery。

- **定位**：C 不是独立方案——**它依赖甄别机制先行**（299 原文即此意），是 A/A′/B 之上的语义层配套。
- **侵入面**：`mastery_evidence.recompute_evidence_state`（签名+逻辑）、`_load_prior_belief`、两调用点测试、幂等断言扩展为「含 set-point 账本」版本。
- **兼容性**：仍是账本纯函数 → 幂等保持；锚点推广定义同 A。
- **失败模式**：(1) assign 面把**写入时刻的存量**钉进重放真值——对 set-point 可接受（考分/惩罚是外部事实，`row.new_mastery` 即观测），对 delta 面则固化当时存量（若写入时存量已被历史病态污染，污染被钉死）；(2) 衰减窗口要与 DecayService 现行为对齐，否则重放值与存储链持续发散（呈现为「每次重算掌握度都跳一点」）。
- **工作量**：M（叠加在甄别方案之上）。

### 方案对照

| | A（effect_kind 列） | A′（request_id 编码） | B（读侧词表） | C（混合重放，依赖前三者） |
|---|---|---|---|---|
| 侵入面 | 迁移+4 写点+读分支 | 1 写点+读分支 | 2 文件读侧 | 重放核 |
| 伪造抗性 | 服务端定性，闭合 | 咽喉覆写才闭合 | 无（可注入数值） | 继承所配方案 |
| 漂移抗性 | 写点定性即生效 | 同左 | 无（已两次实证漂移） | 同左 |
| 存量账本 | 迁移回填，逐位不变 | 回填违 append-only 或拖尾 | 天然在册（词表现成） | 语义层天然 |
| FIX-292 幂等 | 保持 | 保持 | 保持 | 保持 |
| 工作量 | **M** | S–M | S（+持续债务） | M（叠加） |

---

## 3. 推荐

**A + C：写侧 `effect_kind` 列定性 + 读侧混合重放（observation 融合 / set_point assign / delta nudge / projection skip）。** 「写侧定性、读侧定量」。

理由：

1. **信任边界是决定性的。** `reason` 经 REST/gRPC 三条入口客户端可控（§1.4.2）；set-point 数值化后，读侧词表（B）从「可能漏行」升级为「可被注入掌握度」。服务端定性只有 `update_node_mastery` 一个咽喉 + 两个直写点，闭合面小且可枚举（全仓 INSERT 四处已核实）。
2. **漂移已经发生两次**（错题本后缀、aurora 串）。B 的每一行代码都在把 299 的病根（读侧识别落后于写点）制度化；A 在写点定性后词表消亡，错题本/aurora 行顺带归位。
3. **紧急度低允许做对。** live 严格受影响面=0 行、结构暴露=100 行/12 用户（§1.2），M 级工作量可排常规卡，不值得为省一次迁移背上 B 的持续债务。迁移面廉价：394 行、单列、无协议/网关行为变化。
4. **FIX-292 语义零破坏**：账本仍是单一真源，重放仍是纯函数（幂等断言原样成立），锚点定义是推广不是改写；对现有全部账本重放逐位不变（锚后 set-point 行今日为 0）。

修卡建议拆两条验收面：(a) 既有账本重放恒等（现 52 绿幂等套件原样过）；(b) 构造「锚后 exam_sprint 惩罚行」账本，红：修前重放丢 set-point → 绿：修后 assign 生效且多次重算恒等；另加「伪造 reason=exam_sprint_diagnostic 的自由串行仍判 projection」负例。

工作量：**M**（迁移+回填、4 写点、重放分支、幂等/邻域回归；`make sync-db` 重导出快照）。

---

## 附：证据与脚本

- 普查脚本：`/tmp/wt594_census.py`（只读；分类逻辑 import 自本 worktree `backend/app/services/galaxy/mastery_evidence.py`）
- 关键代码：
  - 重放咽喉：`backend/app/services/galaxy/stats_service.py:544`（`_load_prior_belief`，presence-only 分支 :603-611）
  - spark 双写（影子行源头）：`backend/app/services/galaxy/stats_service.py:190-225`
  - set-point 写点：`backend/app/services/exam_sprint_diagnostic_service.py:1555`、`backend/app/services/exam_sprint_review_service.py:1596`
  - 唯一写咽喉：`backend/app/services/galaxy_service.py:3170`（update_node_mastery）、审计 INSERT :3528
  - absorber 直写：`backend/app/services/galaxy/outcome_absorption_service.py:234`
  - 词表与漂移：`backend/app/services/galaxy/mastery_evidence.py:375-398`、`backend/app/services/error_book_mastery_sync_service.py:208,282`、`backend/app/aurora/runtime_v1/service.py:69`
  - 客户端可控 reason：`backend/app/api/v1/galaxy.py:114,120,157,195`、`backend/app/services/galaxy_grpc_service.py:218`
- FIX-292 实现：b980e4bc（38a0e658 为台账登记）
