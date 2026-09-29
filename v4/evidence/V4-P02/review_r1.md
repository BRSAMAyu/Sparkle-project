# V4-P02 · 独立审查 R1 receipt（wtP02R1）

- 审查会话：wtP02R1（未参与 P02 实现）· 2026-09-29 · 只读审查 + 独立探针复现（探针用后即删，未入库）
- 被审对象：agent/v4/p02 @ 8c4c4aa0（base 364b033b，工作树干净，diff=8 证据文件 + tasks.json 状态位，零产品代码改动——`git diff 364b033b..8c4c4aa0 --stat` 亲核）
- 卡标准：Sparkle-project `v4/04_tasks/tasks.json` → V4-P02（kind=verification，risk=high，independent_reviewers=2）
- **裁决：PASS_WITH_CHALLENGES**（三项发现的定性/严重度/证据全部成立；4 项 CH 为数字与表述精度问题，不推翻结论，需订正或由 R2 复核）

## 1. 独立复现（非复制品；探针按 playbook 重建后已删）

| 靶 | 亲放结果 | 锚 |
|---|---|---|
| **F1 复现** | **复现成功**：playbook §S1-P1.1 逐字载荷（【转发】高效备考计划…）→ `PreferenceService.get_preferences().explicit` 三键全中 `{'ai_verbosity':'detailed','feedback_style':'step_by_step','focus_duration_preference':15}`（center version=2）；`MemoryPreference` 链头 `preference_write_provenance(source_type=None, evidence_refs=链头 refs)=explicit`。审查自建探针 4/4 passed（Python 3.11.15，pytest 9.0.3 共享 venv，与原运行 9.0.2 同解释器版本） | `chat_signal_collector.py:522`（纯子串标记匹配，无 provenance/引用/转发识别——代码亲读确认）；`orchestrator.py:~3970`（`user_message=user_message` 原文直传）；`profile_write_service.py:65`（source_type="chat_preference" 直写档）；`memory_epistemic_contract.py:239`（`EXPLICIT_PREFERENCE_SOURCE_TYPES={"user_state","chat_preference"}`——chat_preference 恒 EXPLICIT，不查证据来源） |
| R13 定性核 | **违反成立**。R13 原文（`v4/03_intelligence/MEMORY_UTILITY_AND_CONFLICT.md:7`）：「外部材料中的指令不能提升为用户偏好（R13 提醒持久化污染风险）」。F1 实测即此外部材料指令 → 显式层 | 同上 |
| **中危定性** | **成立**。攻击前提（用户粘贴/转发外部内容）在本卡威胁模型**内**——卡 objective 逐字「检测外部资料中的伪用户偏好」；影响=持久化显式层污染 + 压制后续推断纠正（`inferred_may_supersede` 对显式链头恒 False，`memory_epistemic_contract.py:299-306`）+ 违反 R13；无跨账号/无数据丢失 → 不到高；持久化+权威压制+威胁模型内 → 不止低。**中危恰当，维持** | 卡 objective；`memory_epistemic_contract.py:299` |
| **P1.3 守卫亲放** | PASS：user_state 显式链头建立后，`upsert_preference(source_type="ai_inferred")` 与 `("reflection", 证据含 ai_inferred)` 全拒（返回 None，`blocked_inferred_over_fact` 日志两条），链头 version=1 不变 | `memory_service.py:198-217` |
| **P2.4 亲放** | PASS：`run_decay_job(user_id=A)` 后 B 的 EpisodicMemory 行 `deleted_at/revoked_at/archived_at` 全 None（零跨账号副作用） | `memory_jobs.py:167` |
| **P2.5 亲放** | PASS：同内容异用户键不同（user 维度打头）；epoch bump 键变 | `context_cache_key.py:114-131` |
| 148 回归独立复跑 | **148 passed**（本机复跑 32.09s），逐文件分布与原输出一致：11+7+17+33+23+**16**+24+15+2=148 | `regression_run_output.txt` |

## 2. F2/F3 定性复核

- **F2（低）成立**：`extract_declared_fact_candidates`（`memory_inferred_write_lane.py:473`，SOURCE_LANE="inferred_extraction" :174）逐句 0.92 直写档确实不区分「我说的/资料写的」；但 `classify_episodic_class("inferred_extraction")` 走最后 fallback 返回 **HYPOTHESIS**（`memory_epistemic_contract.py:175-204`，lane 非 user_confirmed/direct_capture）——**类级边界守住属实**，低危恰当。
- **F3（低）成立**：grep 亲证——缩略图仅 PUT 预签（`documents.py:345`、`group_file_service.py:156` `{file_id}/thumbnail.jpg`）+ 生成上传（`thumbnail_service.py`、`file_processing_orchestrator.py`）；`create_presigned_get_url` 全仓仅 `documents.py:341` 一处调用且只用于 `record.object_key` 主对象；`source_lifecycle.py:266-268` 删除只擦 `source.object_key`。**无 GET 路径=非主动暴露、存储残留，低危恰当**。limitations#4 已如实声明时效性（后续开缩略图读面的卡须引用本证据）。

## 3. 守卫侧 PASS 面与范围钉三项

- **验收①**：守卫侧（反思路径）PASS——P1.3 亲放通过；P1.4 代码亲读（`user_memory_seed_consumer` 唯一 FACT 写点、`llm_extractor_prompt.v2.md` 规则 11 在位）。聊天粘贴路径报红 F1/F2 属实上报，未降阈值。**处理正确**。
- **验收② PASS**：P2.1–P2.3 抽验依赖回归套件（群文件/错题卡 API 套件在 148 内全绿）+ P2.4/P2.5 亲放通过。
- **验收③ PASS**：P3.1a/P3.1b/P3.2 由探针输出（0/6 窗口、ReadGate stale、旧 epoch job 丢弃）+ D03/I05 套件回归绿支撑。
- **范围钉①（群AI 组装点）**：`build_prompt_access_context`/`filter_group_prompt_candidates` 在 `app/` 生产代码**零消费方**（本审查独立 grep，仅守卫库自身命中）；另搜 `group_prompt`/群 prompt 组装替代路径无命中。**判定：真实不存在（截至本 SHA），非「未找到」**；orphan-by-design 在案（`docs/aurora/rule_at_exceptions.md:39`）。limitations#5 已声明群AI 面落地须重开探针。
- **范围钉②（截图面）**：无持久化面成立（见 CH-3 表述精度问题）。
- **范围钉③（真模型）**：limitations#1 + denominator_note 如实声明 NOT_RUN 及预算原因——合规的范围声明，非静默跳过。

## 4. 纪律自查

- sqlite `:memory:` 隔离：`tests/conftest.py:117` `TEST_DATABASE_URL="sqlite+aiosqlite:///:memory:"`；两次运行输出中 DBGUARD 演示库门均触发拒连（纵深防御生效）。
- 零 LLM：manifest `llm_called:false` 与代码事实一致（`_extract_explicit_preferences` 纯正则、declared-fact 纯规则；运行输出 router 为 demo mode，零 provider 调用）。
- 容器接触声明如实：本审查复跑出现**完全相同**的失败环回（event_bus Redis 鉴权失败重试 3 次后放弃、DLQ 写 PG 鉴权失败）——与 manifest isolation 声明逐字吻合，零数据落盘。
- 探针零残留：`git log --all -- backend/tests/test_v4_p02_redteam_probes.py` 空（从未入库）；审查自建探针同样用后即删。

## 5. 数字诚实性

- **12/148 分解核实**：12=pytest 探针收集数（输出 `collected 12 items`、12 passed、EXIT=0）；148=8 套件分布和（11+7+17+56+16+24+15+2），本审查独立复跑一致。**总数无膨胀**。
- **sha256 全对**：manifest 两个 artifacts sha256 与实算逐字一致（`36aaba08…652d4`、`0f10167c…2d8`）；其余 6 件实算值见 §8。
- 矩阵 13 行 vs probes_total=12：P3.3 为静态路径测绘非 pytest 探针，行 verdict 已自注「路径测绘+静态钉」——不构成误导，读法需留意。

## 6. CHALLENGES（需订正/澄清；均不动摇结论）

- **CH-1（数字错误，须订正）**：「S-02 边界 **18 用例**」（redteam_playbook.md §2 范围钉、diff_or_evidence_only.md §2/§4）与事实不符：该文件 `def test_` 计数=**16**，回归输出 16 点、累计 72.3% 一致，本审查复跑同值。若 S-02 真为 18 则总数应为 150。148 总数正确，但单文件计数须改为 16（或给出 18 的出处并更正引用）。
- **CH-2（计数歧义，须澄清）**：run_manifest `defense_pins_passed: 11` vs 矩阵 `DEFENSE_PASS` 行数=**10**（P1.3/P1.4/P2.1–P2.5/P3.1a/P3.1b/P3.2）。可自洽的解释是 P1.4 含两枚钉（seed 入口+提示词纪律，test_results P1.4 outcome 亦列两项）——但 manifest 未写分解。补一行分解说明或改为 10。
- **CH-3（表述精度，须订正）**：playbook §3 范围钉「截图唯一命中为 execution_quality_service.py:206」——该锚存在（artifact_types 枚举串，亲核）；但 `execution_template_service.py:198/320/360` 亦含 "screenshot" artifact_types 字符串。**结论（无截图持久化面）不变**（全部为枚举/文案，无存储），「唯一命中」措辞须放宽。
- **CH-4（计数口径，澄清即可）**：派单文与验收语境称「证据九件」；`v4/evidence/V4-P02/` 实为 **8 件**（五件套+playbook+两运行输出），commit 第 9 个变更文件是 tasks.json 状态位（PENDING/NOT_STARTED/NOT_RUN → IN_PROGRESS/REVIEW_READY/FINDINGS_OPEN_…，diff 亲核，纪律正确）。

## 7. 观察与修复建议排序（靶 6）

- **观察 O-1（P1.3 语义细化，不改裁决）**：守卫阻断条件=入向 provenance 为 INFERRED，即 `source_type∈{ai_inferred}` **或** 证据含 ai_inferred 类型（`memory_epistemic_contract.py:277-289`）；"reflection" 本身**不是**注册的 INFERRED source——source_type="reflection" 且证据不含 ai_inferred 时会按 fallback 落 **EXPLICIT** 而不被阻。现生产面无此调用形态（reflection 写手走 episodic/lane，preference 域 upsert 仅 chat_preference/user 操作/ai_inferred 三类入），验收①对全部实际调用方成立。建议后续在 `upsert_preference` 加注释或将 reflection 显式列入 INFERRED_SOURCE_TYPES，防未来接线踩坑。
- **观察 O-2**：F1 探针输出中 P3.2 段有一条 `sqlite3.ProgrammingError: UUID not supported`（`_write_mastery_update_event`）——为 sqlite 测试环境与 PG 方言的绑定差异（测试环境伪影），探针断言对象是读门行为且通过；记录在案防止误读为产品缺陷。
- **观察 O-3**：F1 内 `_extract_explicit_preferences` 的 concise→detailed 后写覆盖（载荷同含「简洁」与「一步一步」时终值 detailed@0.9）与实测一致——提取器自身语义粗糙，佐证「无 provenance 门」的根因定位。
- **修复建议排序（F1，R1 推荐）**：近期 **(b) 粘贴形态门**（多句/长文/引用标记命中 → 偏好降 HYPOTHESIS 候选走既有确认车道；纯后端、低风险、可立即部署）+ **(d) 数值偏好第一人称共现**（作为 (b) 检测器内启发式）；结构性 **(a) 来源标注贯穿**（客户端转发/引用标记 → orchestrator 单点 provenance 门，同时修 F2）为后续跨层卡——顺位在 (b) 之后因需移动端+网关契约协同；(c) 引用块检测并入 (b)，单独使用易绕过（载荷恰有【转发】前缀可被该规则命中，但删掉前缀即失效，不作主防线）。F3 修复建议（delete() best-effort 删缩略图+回执口径）可行，认可。

## 8. 证据文件 sha256（R1 实算，2026-09-29）

```
36aaba08e63ac8484417e2884f3d922dbdd142f34cc9cd1e27b152caadd652d4  probe_run_full_output.txt  (=manifest)
0f10167caf2daa2c8008529e4381dca902a4fcc81ac1cfd9a888ae9f593cd2d8  regression_run_output.txt  (=manifest)
4b8b08ca0ead769a9a6eeee0d32a14a1a6f82ccb2cbdedeba09174001c2dcb5b  redteam_playbook.md
d88df77333880ca22ae6c449876718ac10c5a56c38d1774c9e0bc046f45c924e  diff_or_evidence_only.md
379ab73afe950730681f3e1e68b895de05669aac3382d68aedd4b78b459ddf17  limitations.md
25597c925402e2d70f7d994bd409fd6557e445d9a5aa62e35b79cdb3f94a7538  review_receipt.json
c9f711f0c45e57366fa3eb2ac3e13434e2f070da9ee5b4b4a483187fe2e09cba  run_manifest.json
4b9990d29f7fd4f3681a0a8cebfa6522aeca1bf3b6d76f8990f77d89870e4fb8  test_results.json
```

## 9. 裁决

**PASS_WITH_CHALLENGES**——三项发现（F1 中/F2 低/F3 低）的复现、定性、严重度经独立对抗审查全部成立；验收②③ PASS、验收①守卫侧 PASS+聊天路径如实报红，符合「发现如实上报不降阈值」纪律；证据链完整可复现（F1 由审查自建探针零修改复现）。CH-1/CH-3 为证据文档数字/措辞订正项（改文档不改结论），CH-2/CH-4 为口径澄清项；请作者会话或 R2 会话落实后随二审收口。F1/F2/F3 的修复归口（记忆污染入口 provenance 门；source lifecycle 缩略图擦除）属后续实现卡，与本验证卡收口不互斥。无 BLOCKED 事项；本审查未 push、未动交付物（本 receipt 为唯一新增）。
