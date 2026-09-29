# V4-P02 · 独立审查 R2 receipt（wtP02R2）

- 审查会话：wtP02R2（未参与 P02 实现，未参与 R1）· 2026-09-29 · 只读审查 + 独立探针复现（自建代码，用后即删，`git log --all` 零残留）
- 被审对象：agent/v4/p02 @ 8c4c4aa0 + 一审 receipt 160485dc；`git status` 干净；变更面=8 证据文件 + tasks.json 状态位（`git diff 364b033b..8c4c4aa0 --name-only` 亲核）
- 卡标准：`v4/04_tasks/tasks.json` → V4-P02（kind=verification，risk=high，independent_reviewers=2）
- **裁决：PASS_WITH_CHALLENGES（R2 维持并确认 R1 裁决）**——F1 终审定性**中危，维持**；F2/F3 定性抽验通过；R1 四项 CHALLENGES 复核**全部确认为文档级**，不改结论；守卫抽检 2/2 通过；修复 (b)+(d) 可行性确认。两位独立审查到齐（R1 160485dc + 本 receipt），`independent_reviewers=2` 满足；CH 订正归作者会话落实。

## 1. F1 终审定性（首靶）——**中危，维持**

**独立探针重建与亲放**（非 R1 代码复制品；自建 4 探针，载荷按 playbook §S1-P1.1 逐字）：

- **R2-1（F1 全链）复现成功**：自建 `_FakeRedis` 桩 + `ChatSignalCollector.collect_signals(user_message=转发载荷, db_session=sqlite会话)` 直调（等价 `orchestrator.py:3970` 的逐字直传形态）→ `UserPreferencesCenter.explicit` 三键全中 `{'ai_verbosity':'detailed','feedback_style':'step_by_step','focus_duration_preference':15}`（version≥2）；`MemoryPreference` 三键链头 `preference_write_provenance(source_type=None, evidence_refs=链头refs)==EXPLICIT`，且链头 evidence_refs **全部为 `chat_turn`**——即证据维度不存在任何外部材料标记，下游门无法区分粘贴与本人陈述。**复现成立**（Python 3.11.15 / pytest 9.0.3，与 R1 同 venv；原运行 9.0.2）。
- **亲放诚实记录**：4 探针共跑 3 轮——前 2 轮失败均为**本审查探针自身缺陷**（evidence_refs 形状不合 `_normalize_evidence_refs`、`EpistemicClass` 枚举大小写断言），非产品行为；修正后 4/4 passed（5.25s）。产品代码零改动。
- **R13 违反独立复核**：原文亲读 `v4/03_intelligence/MEMORY_UTILITY_AND_CONFLICT.md:7`：「外部材料中的指令不能提升为用户偏好（R13提醒持久化污染风险）」——F1 实测即「外部材料指令 → 显式层」，逐字命中。
- **威胁模型内**：卡 objective 逐字「沿既有隔离检测**外部资料中的伪用户偏好**…」——用户粘贴/转发外部内容正是本卡声明要检测的攻击，非外推场景。
- **「中危不到高」推理核**：写路径全程 user_id 严格 scope（`upsert_preference` SELECT 按 user_id 过滤，R2-4 侧证 job 亦 user-scoped）→ **无跨账号升级**；污染为追加写、用户可以 user_state 显式纠正（`inferred_may_supersede(explicit, explicit)=True`）→ **无数据丢失**。但：落地为持久化显式链头 + `inferred_may_supersede(explicit, inferred)=False`（`memory_epistemic_contract.py:287`，R2-2 亲测阻断 2 例）形成**权威压制**（推断纠正永不上位）+ 违反 R13 → **不止低**。**中危恰当，终审维持**。
- **根因链亲读**：`chat_signal_collector.py:522 _extract_explicit_preferences`（纯子串标记匹配，无 provenance/引用/转发识别）→ `_persist_immediate_turn_learning` :172 `source_type="chat_preference"` → `profile_write_service.py:65` set_explicit_preferences 直写 live+历史；`memory_epistemic_contract.py:239 EXPLICIT_PREFERENCE_SOURCE_TYPES={user_state, chat_preference}` 恒 EXPLICIT；链头 provenance 按证据判（`memory_service.py:198-201`，source_type=None + chat_turn → EXPLICIT fallback）。与 R1 定位一致。

## 2. F2/F3 抽验

- **F2（低）抽验通过**（R2-3 亲放）：`extract_declared_fact_candidates` 对粘贴资料正文逐句产出 2 条候选（confidence=0.92、`source_lane="inferred_extraction"`、evidence 全 `chat_turn`）；`classify_episodic_class("inferred_extraction")=="HYPOTHESIS"`（`memory_epistemic_contract.py:204` fallback）；`inferred_may_supersede("explicit","inferred") is False` 亲测。**类级边界守住属实，低危恰当**。
- **F3（低）双 grep 通过，且比 R1 记录更强**：`thumbnail.jpg` 全仓仅 2 处 PUT 预签（`documents.py:345`、`group_file_service.py:156`）+ 生成上传（`file_processing_orchestrator.py:102` → `thumbnail_service`）；`create_presigned_get_url` 调用方实测 **3 处**（`documents.py:341`、`group_file_service.py:152`、`file_processing_orchestrator.py:259`）——R1 称「全仓仅 documents.py:341 一处」**计数不准**，但三处全部只签主对象 `object_key`，**缩略图零 GET 服务路径的结论不变**；删除路径亲读 `source_lifecycle.py:266-270` 仅擦 `source.object_key`（`erasure_receipt` 亦只挂 `:object_delete_pending`）。**存储残留、非主动可访问面，低危维持**。

## 3. R1 四项 CHALLENGES 复核——全部确认，均为文档级

| CH | R2 复核结果 | 处置 |
|---|---|---|
| CH-1（S-02 计数 18→16） | **确认**。`def test_` 亲数=16；本审查重跑该文件 16 passed；原回归输出 :29 累计 [72%]（84/148=56.8% 若为 18 则矛盾，:28 为 experience_strategy 折行 33+23=56，全量分解 11+7+17+56+16+24+15+2=148 自洽） | playbook §2 范围钉、diff_or_evidence_only §2/§4 的「18 用例」订正为 16 |
| CH-2（defense_pins 11 vs 10） | **确认**。矩阵 `DEFENSE_PASS` 行亲数=10；P1.4 含两钉（seed 唯一写点+提示词纪律，test_results P1.4 observed 列两项）是唯一自洽分解 | manifest 补分解说明（11=P1.3+P1.4×2+P2.1–P2.5+P3.1a/1b/3.2）或改 10 |
| CH-3（截图「唯一命中」） | **确认并加宽**。screenshot 命中实测 6 处：`execution_quality_service.py:206` + `execution_template_service.py:198/320/360`（artifact_types 枚举串）+ `openclaw/intent_translator.py:13/31`（意图文案）。「唯一命中」措辞须放宽；**全部非持久化面，结论不变** | playbook §3 范围钉措辞订正 |
| CH-4（证据件数） | **确认**。`git ls-tree 8c4c4aa0 v4/evidence/V4-P02/` = **8 文件**；diff 第 9 文件=tasks.json 状态位 | 口径澄清：实现证据 8 件 + tasks.json 状态位 + 后续审查 receipt |

四项均不动摇 F1/F2/F3 定性与三项验收判定。**本审查不代改作者证据文件**（保持 R1 已验证的 sha256 链完整），订正归作者会话随收口落实。

## 4. 守卫面抽检（P1.3 与 P2.4 双探针亲放，超出「抽 1」要求）

- **P1.3**（R2-2）：user_state 显式链头（version=1）建立后，`upsert_preference(source_type="ai_inferred")` 与 `("reflection", evidence=[ai_inferred])` **全拒**（返回 None，`blocked_inferred_over_fact` 日志 2 条），链头唯一性保持——守卫 PASS。
- **P2.4**（R2-4）：`run_decay_job(user_id=A)` 后 A 行 `importance_score` 1.0→0.98（证明 job 实际执行且 scope 到 A）；B 行 importance 与 `deleted_at/archived_at/retracted_at/revoked_at` 全不动——**零跨账号副作用 PASS**。
- **O-1 复核通过并精化**：`"reflection"` 不在 `INFERRED_SOURCE_TYPES`（`memory_epistemic_contract.py:231`）；且进一步发现 **`"reflection"` 也不在 `ALLOWED_EVIDENCE_TYPES`**（`memory_service.py:49`）——reflection 型证据 ref 在 `_normalize_evidence_refs` 即抛 `ValueError`，根本到不了 provenance 门；真实 fallthrough 窗口=`source_type="reflection"` + 白名单类型证据（如 chat_turn），亲测落 EXPLICIT 且成功顶掉链头（version 1→2）。生产面复查：`upsert_preference` 全仓仅 2 调用方（`profile_write_service.py:109/229`）；显式上游 14 站全部 `source_type="user_state"`，1 站 `"system"`（见 N-1），**零 `"reflection"` 入参**——验收①对全部实际调用方成立，钉注建议（R1 O-1）维持。

## 5. 修复建议可执行性独立评估（靶 5）

- **(b) 粘贴形态门——可行**。实现面收敛在 `chat_signal_collector._extract_explicit_preferences`（纯 classmethod、纯字符串逻辑，零 LLM）+ `_persist_immediate_turn_learning` 的落库路由分支：命中粘贴特征（转发/引用标记【转发】、来自、> 引用；句数阈值 `re.split(r"[。！？!?\n]+")`；总长/行数阈值）时，把显式直写改为 inferred lane HYPOTHESIS 候选。**「既有确认车道」经亲证真实存在**：episodic HYPOTHESIS 类 + `memory_storage_gate.py:1133 PENDING_CONFIRMATION_TAG` 待确认标注 + `app/api/v1/memory.py:376 confirm_episodic_memory` 确认 API——(b) 无需新契约、纯后端、确定性可测，可立即部署。
- **(d) 数值偏好第一人称共现——可行**。同一纯函数面内实现（如 `(\d{1,3})分钟` 命中句内要求「我」共现），正则可承载，零模型调用；作为 (b) 检测器内启发式合并交付合理。
- **误报面评估**：用户在长文/多句消息中真实陈述偏好会被降级为待确认——代价是一次确认交互，不是数据错误（fail-safe 方向正确）；**漏报残留**=短第一人称粘贴文本与本人陈述在纯文本面不可区分，结构性不可消除——支持 R1 的排序：(a) 来源标注贯穿（客户端转发/引用标记 → orchestrator 单点 provenance 门，同修 F2）为后续跨层卡。R1 排序（b)+(d) 近期、(a) 结构性、(c) 不作主防线——**R2 独立评估同意**。
- **F3 修复**（`delete()` best-effort 删 `{source.id}/thumbnail.jpg` + 失败挂 `:thumbnail_delete_pending` 回执）与 `source_lifecycle.py:270` 既有 `:object_delete_pending` 先例同构，可行。

## 6. 纪律与数字（靶 6）

- **148 回归升级为全量独立复跑**（原计划抽批，实际 8/8 套件全跑）：42+33+73 = **148 passed**（pytest 9.0.3 / Python 3.11.15 / 共享 venv，分三轮 EXIT=0），逐文件计数 11/7/17/56/16/24/15/2 与原输出**逐字一致**（56 为 33+23 折行，亲核原输出 :27-28）。
- **sha256 全对**：8 件证据实算与 manifest 两件及 R1 §8 表逐字一致（`36aaba08…652d4`、`0f10167c…2d8`、`4b8b08ca…cb5b`、`d88df773…924e`、`379ab73a…df17`、`25597c92…7538`、`c9f711f0…9cba`、`4b9990d2…4fb8`）。
- **zero-LLM 声明吻合**：原 probe 输出含 `demo mode` 激活日志与 router 无 key 注销日志；代码亲读证三路探针均为确定性规则路径（`_extract_explicit_preferences` 纯正则 classmethod；`extract_declared_fact_candidates` 纯规则、`del user_id` 纯函数注释在位；upsert/decay 纯 DB）；本审查复跑同进 demo mode、零 provider 调用。
- **隔离**：sqlite `:memory:`（`tests/conftest.py:117`）；原回归输出头部 DBGUARD 演示库拒连门可见；本审查探针运行未观察到容器连接尝试。
- **探针零残留**：`git log --all` 对作者探针与本审查探针均空；本审查探针已 `rm`，`git status` 干净。

## 7. 新观察（不改裁决）

- **N-1**：`planning_workflow.py:5056` 以 `source_type="system"` + `{"type":"system"}` 证据写偏好历史链——按 F6 语义（machine-ish writer 保持 evidence-decided）落 EXPLICIT fallback。其载荷来自用户自身规划流程、非外部材料，不在 F1 威胁模型内，且组合快照键被 PREFERENCE_KEYS 白名单挡在历史域外（`profile_write_service.py` 白名单注释在位）。登记防误读，不构成新发现。

## 8. 裁决

**PASS_WITH_CHALLENGES**（同口径，R2 确认 R1）：

1. **F1 终审：中危，维持**——本审查以自建探针（4/4 绿）零修改复现显式写入链；R13 原文与卡 objective 逐字核验在威胁模型内；无跨账号、无数据丢失 → 不到高；持久化显式链头 + `inferred_may_supersede` 权威压制 + 违反 R13 → 不止低。修复归口后续实现卡，与本验证卡收口不互斥。
2. F2/F3 抽验通过（F3 的 GET 路径 grep 面 R2 实测 3 处主对象预签，较 R1 记录更全，结论同向）。
3. R1 四项 CHALLENGES 全部确认为文档级（计数/措辞/口径），订正归作者会话；本 receipt 第 3 节表格可直接作为订正清单。
4. 守卫抽检 P1.3/P2.4 双亲放 PASS；O-1 精化（reflection 需白名单证据类型才达 fallthrough 窗口）并钉注建议维持。
5. 修复 (b)+(d) 近期方案可行性确认（纯后端、既有确认车道在位、误报面 fail-safe）；(a) 结构性方案排序同意。

无 BLOCKED 事项；本审查未 push，新增仅本 receipt 与 review_receipt.json 的 R2 回填。
