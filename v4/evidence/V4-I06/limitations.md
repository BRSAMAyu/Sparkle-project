# V4-I06 · limitations（如实登记）

## 本卡不做 / 边界

1. **RAG 引用句面（"RAG引用可点原文；外部文本不变用户事实"）**：本卡交付的是回执与 selected/basis ref 的存储可解析性（`document://<file_id>` join `stored_files`；`memory://` join 记忆真源）。"引用可点原文"的句子级呈现与 C-04 `[S#]` citation 对齐归既有 C-04/citation_markers/context_funnel 权威——本卡不重建该面，仅保证回执 selected 集与呈现层引用集的 ⊆ 校验纪律（合同 C1）可机检。UI 层点击行为属移动端卡。
2. **why-now 本面为 null**：chat 装配面（ContextPackBuilder）无任务级 why-now 语义（合同 null 语义），`build_why_now` 词表/构造面已冻结可用；proposal_basis 角色的 why-now 数据流（Aurora 侧 `aurora_core_session.py` why_now → 字段位）归 X-01/B06 线，本卡只补契约位。
3. **I02 分支未合**：效用门接口为鸭子类型消费 `to_metric_payload()` 冻结形状；本分支无 `memory_utility_gate` 代码，`metadata["memory_utility_gate"]` 键缺席=门关语义（回执照常产生）。I02 合入时若在其接线中写入该键即自动生效；形状漂移需同步契约测试（已钉）。
4. **experience_memories（M-06）未入本面回执**：M-06 经验记忆装配在 context_builder stage34 另一面（`_attach_experience_memory_context`），本卡回执唯一生产点为 ContextPackBuilder.build。M-06 面的候选/拒用归因（exp:* ref）留待后续卡把该装配点接入 `assemble_pack_receipt`（该函数已按 section 泛化，`experience` kind 只需映射登记）。
5. **budget.selected_max 口径**：本装配面的选中上限由 token 预算裁剪决定，无独立整数上限；回执如实记录"实际扫描数 / 实际选中数"，非配置值。若未来引入整数选中上限，该字段语义需在合同 §2 budget 行下明确。
6. **非单行存储 scheme 判 unknown**：`user_state://`、`profile://`、`chat://`、`decision://`、`run://` 为投影/事件域（无单行属主表可 join），本轮装配亦未把它们作依据产生——来源验证如实 unknown（不伪造可点定位）。后续卡需要时在 `_resolve_scheme` 登记各自真源即可。
7. **读时验证 ≠ 写时改写**：「删除后旧receipt更新」采用读时验证语义（回执行只读，读面现场 join 反映删除/纠正/越权）。回执行本身从不改写（权威记录纪律）；若未来需要落库行级状态翻转（如批量失效标记），属新写路径需另立卡。
8. **ULID 单调性不作承诺**：`new_receipt_id` 为 48bit 毫秒 + 64bit 随机的 Crockford Base32，形态=合同 `csr_<ulid>`；幂等由 `receipt_id` 唯一约束 + 调用方"同一轮可重算不重复计数"语义承担（同轮重放跳过）。严格单调 ULID（同毫秒有序）如被后续卡依赖需升级实现。
9. **conftest 既有 I001 顺带修复**：`tests/conftest.py` 的 import 排序在主仓基线即不过 ruff（I001）；本卡在该文件新增 1 行 import 时由 `ruff --fix` 顺带归位（净效果：agent_run/action_proposal 两行换序）。无语义影响，登记避免审查误判为越界改动。
10. **迁移 JSON 列型**：迁移用 `sa.JSON()`（`JSONBCompat` 同款 sqlite 兼容变体）；PG 侧未用 JSONB 原生类型以对齐既有 `context_pack_runs` 先例的跨库行为。查询面如未来需要 JSONB 索引（如按 reason_code 聚合），需单独迁移升级列型。
