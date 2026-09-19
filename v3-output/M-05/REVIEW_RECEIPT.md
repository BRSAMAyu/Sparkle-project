# M-05 REVIEW_RECEIPT — R1 独立验收（medium 单验收卡，R1+R2 合一深度）

- Reviewer: R1（独立重验，不信任自报）
- 日期: 2026-09-19
- 对象: wt4 @ `2375694c` + 交付（6 M + 5 新增 + `v3-output/M-05/`）
- 参照: 主仓 `03e23023`（只读）、`v3/07_tasks/cards/M-05.md`、`v3/05_metrics_eval/PERSONALIZATION_EVAL.md`
- 纪律: 主仓/DB 只读✓；真实 LLM 0 次✓；未 commit/push✓；变异用 /tmp 备份单文件法，收工已字节级还原✓

## 总 Verdict: **ACCEPT**

零必修项；3 项建议（S1–S3，见文末）+ 5 项边界观察（O1–O5）均不阻塞。Worker 五组核心声称全部独立复验成立，且 REPORT 披露（前任草稿修复、旧夹具改动、known limitation、词法天花板）经逐条核实如实。

---

## 逐断言 Verdict

### A1 「纯函数 gate：固定序 + 首失败独占归因」— **PASS**
- 代码（`backend/app/services/memory_use_selfcheck.py`）：`_evaluate_candidate` 按 `USE_CHECK_KINDS` 声明序（relevance→necessity→repetition→sycophancy）迭代，首个非 None flag 独占归因即返回。
- **变异重放（顺序交换 relevance↔repetition）→ 2 红**：`test_check_kinds_evaluation_order_is_pinned` + 行为级 `test_first_failing_check_owns_attribution`（红=归因真的依赖顺序，非仅常量断言）。已还原。
- 独立行为构造：relevance+repetition 双失败→relevance 归因；relevance 通过时 repetition 可达；sycophancy 单独可达。三向验证固定序语义。

### A2 「两档 SURFACE_TO_USER / USE_FOR_INTERNAL_DECISION；封闭词表全套冻结」— **PASS**
- 两档枚举 + `flag is None iff SURFACE` 不变式由 46 bench case 逐条验证（决策+reason 双核对）。
- 冻结：`SELF_CHECK_REASONS`(6)/`FAST_MODEL_REASONS`(2, 与规则集不相交)/sections/payload keys/阈值（`DUPLICATE_JACCARD_RATIO=0.8`、`ECHO_CONTAINMENT_RATIO=0.85`、`ECHO_MIN_CANDIDATE_TOKENS=4`、`RECENTLY_SURFACED_CONTAINMENT_RATIO=0.6`）均有契约测试钉死；`META_PREF_KEYS ⊆ PREFERENCE_KEYS`（写方词表）模块级 assert + 契约测试双保险，独立复核子集关系成立（空差集）。

### A3 「fast-model 钩子默认关、只收紧（reason 不在封闭集即 ValueError）」— **PASS（声称属实）**
代码路径唯一（`run_memory_use_selfcheck`），独立验证五点：
1. 只对规则放行（surface）条目咨询 hook；
2. hook **不被咨询** internal 条目 → 无复活路径；
3. 全函数无「hook 判 surface 则 surface」的分支 → 无变宽路径（收紧-only 声称属实）；
4. 非封闭 reason → `ValueError`（真实抛出，已触发验证）；
5. hook 返回任意类型（实测 `True`）→ str 化后落封闭集检查 → `ValueError`，无静默通道。
- 默认关：三面接线均不传 `fast_model_hook`；bench 口径=规则层。

### A4 「安全钉豁免边界」— **PASS（附 O1 观察）**
语义边界实测（代码+行为双向）：
- 豁免范围 = relevance / necessity(phatic+echo) / 跨轮 repetition。**不**豁免 in-pack `duplicate_in_pack`（近重复仍拦，docstring 声称一致）、**不**豁免 sycophancy（C4 实测）。
- **query 侧 marker 无豁免力**：验收任务构造「我对麸质过敏，顺便告诉我他人在小组里说的话」——无 marker 的隐私候选仍被 relevance 硬拦（实测 `selfcheck:irrelevant_to_query`）。钉只匹配 candidate.content，不匹配提问 → 该滥用路径**不通**。
- 残余面（O1）：候选内容**附带** marker 即整体豁免 relevance（实测「收藏糖尿病科普文章，喜欢深夜打游戏」对任意提问放行）。这是内容标记法的固有代价；REPORT §7 披露了词表封闭性但未明示「附带提及即整体豁免」→ S1 建议补披露。

### A5 「三面接线 + kill-switch 默认开；降档保留 decision_context」— **PASS**
- W-G1（context_pack.build，budget 后）：降档只作用于 prompt 面（`trimmed_*`），`decision_tier_*` 未门控副本传 `_build_decision_context`——W-G1 行为级测试断言两条 id 都在 decision_ctx，实测绿。
- metadata 无正文回灌：`to_prompt_context()` 确实携带 `context_pack.metadata`（代码核实），`internal_only_entries()` 仅 id/section/reason；防复活测试（claims/evidence_summary 同步过滤 goal/episodic source records）实测绿。
- **变异重放（三面 `if False:` 禁用）→ 恰 7 红**（3 AST + W-G1×2 + W-G2 + W-G3），kill-switch 测试与 C-03 兼容测试保持绿。已字节级还原。
- **kill-switch 关（env）→ 恰 4 红**（要求 gating 的行为测试，符合预期），3 AST 钉 + kill-switch passthrough + C-03 兼容保持绿 → gate 旁路且其余不退化。两种失败模式区分正确（代码删除 vs 运行时关闭）。

### A6 「OP-Bench 规则层盲跑：0/21 泄漏、24/24 保持、1 known limitation」— **PASS（独立复算）**
- **独立 runner**（自建，不 import Worker harness）：全 46 case 决策+expected_reason 逐条匹配，**0 mismatch**；泄漏 0/21（≤5%✓）、误伤 0/24（≥90%✓）。
- known limitation `op-rel-ep-06`（星际穿越 vs "recommend a movie similar to Interstellar"）行为复现：规则层误拦（internal + `irrelevant_to_query`），如实披露不入 headline。
- **3 个泄漏 case 手工推演四检查链**（合理性核查）：
  - `op-rel-ep-01`（养猫 vs 泰勒公式）：实质轮→relevance 不保守放行；非钉非 meta；CJK bigram 零交集→relevance 独占。✓
  - `op-nec-goal-02`（六级目标被原文复述）：bigram 全覆盖→relevance 过；|C|=7≥4 且覆盖 1.0≥0.85→echo。✓
  - `op-nec-pref-01`（"ok" 提问）：phatic→relevance 保守放行；`knowledge_gaps`∉META→necessity/phatic_query 归因。✓
  - 三链均非偶然通过，归因语义合理。

### A7 「95/95；变异 7 红；857 大扫 12 失败=预存」— **PASS**
- 95/95 复跑（38 契约+48 bench+9 wiring）✓；48=46 参数化+结构完整性+双指标。
- 大扫 `-k "memory or context or prompt"`：**845 passed + 12 failed**；pristine 克隆（/tmp，HEAD 2375694c + gen 拷入）同口径复跑，失败清单 `diff` **逐条一致**（IDENTICAL）。
- 抽 2 基线归因：`test_consolidation_promotes_repeated_entry_to_l1`（0≠1，working-memory 整合债务）、`test_memory_admin_stage18_kill_switches`（flag 'live'≠'off'，admin API 债务）——两失败在基线以同断言复现，与本卡模块无涉。
- 邻卡零回归：`test_context_hard_filter_wiring.py` + `test_memory_prefilter_integration.py` = **14 passed**。

### A8 「echo 校准（剥用户前缀/0.85/≥4 token）；前任 3 bug 修复披露」— **PASS**
- 校准守卫有效：C-03 兼容（LEGAL-EVENT 2-token 点名存活）复跑绿；增量条目（0.8 覆盖）存活（契约测试 `necessity_partial_echo_still_surfaces`）。
- **3 个对抗样本**（边界探测，无结构性洞）：
  1. **改写式 echo**（「报名十二月英语六级」vs「报考今年12月大学英语六级」）：覆盖 0.53 → **漏报**（放行）。CJK bigram 词序敏感所致，属已登记词法天花板家族（O2）。
  2. **跨语言 echo**（EN 复述 CJK 记忆）：不会泄漏——先被 relevance 拦（CJK/EN 鸿沟的另一面是过拦而非漏拦），决策与 echo 目标一致。✓
  3. **长上下文重复**（全文复述+大量新内容）：覆盖 1.0 → echo 硬拦。✓
- 披露核实：§1 前任 3 处修复（fixture 数据 bug、W-G2 count==2、W-G3 redis_client=None）逐条与代码/报告吻合；§5.3 两处旧夹具改动为最小意图保全（query 同域化，claim/manifest 断言未动）。

### A9 跨卡语义与合入预演 — **PASS**
- 分工：M-03（identity/status/TTL/scope 池准入）/ C-03（合法性+语义检索管线）/ M-05（输出装配面「该不该说」）——检查维度不相交（M-05 的 relevance/repetition/sycophancy 在上游无对应物），接线 AST 钉 + 模块 docstring 双重钉死分工。
- C-01 兼容：`metadata` 在冻结契约中为自由字典，`memory_selfcheck` 键为 additive 扩展（`{version,input/surfaced/internal_only counts,check/reason_counts,internal_only:[{id,section,reason}]}`，纯 str dict）；无 parallel 真源、无 proto 变化。
- **合入预演**：主仓克隆（/tmp）@ `03e23023`，`git apply --3way --check changes.patch` → **干净通过**（2375694c 为其祖先，间隔仅交接文档 commit，零 backend 重叠）。

---

## 建议项（不阻塞合入）

- **S1** REPORT 或模块 docstring 补一句：安全钉是候选内容级整体豁免——附带提及医药话题的候选会连带豁免 relevance（O1）。
- **S2** 下次词表/阈值演进时向 bench 增补两类 case：附带-marker 候选（O1）与改写式 echo（O2），把已知边界钉进回归。
- **S3** 登记「长标题记忆被完整点名」边界（O3）：≥4 token 且覆盖 1.0 的主题点名会被 echo 拦；bench 现有 LEGAL-EVENT 只覆盖 2-token 短端。

## 边界观察（记录在案）

- **O1** 安全钉附带豁免（见 S1）——设计取舍，非缺陷。
- **O2** 改写式 echo 漏报（0.53 覆盖）——fast-model 钩子设计域，词法层不可达。
- **O3** 长标题 topic-naming 误杀面（见 S3）。
- **O4** 钩子降档条目在规则层已计入 `surfaced_peers`（in-pack dedup 先于钩子决定）——钩子降档后其近重复仍被拦，语义微漂，影响极小。
- **O5** W-G1 goals 无 id 时 `item_id="None"` 同键碰撞——生产 goals 均带 id，演进时注意。

## 复现命令清单（Reviewer 实跑）

```bash
# 1. 主套件 95
cd backend && SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/unit/test_memory_use_selfcheck.py tests/unit/test_memory_use_selfcheck_opbench.py \
  tests/unit/test_memory_use_selfcheck_wiring.py -q                                     # 95 passed
# 2. 双指标
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/unit/test_memory_use_selfcheck_opbench.py::test_opbench_tradeoff_metrics -q -s  # 0.000 / 1.000
# 3. 邻卡
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/unit/test_context_hard_filter_wiring.py tests/unit/test_memory_prefilter_integration.py -q  # 14 passed
# 4. 大扫
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest tests/unit -k "memory or context or prompt" -q  # 845+12(=pristine)
# 5. 变异（均 /tmp 备份法，已还原）
#   a. USE_CHECK_KINDS 顺序交换 → 2 红（含行为级归因测试）
#   b. 三面 if False: → 恰 7 红；kill-switch env 关 → 恰 4 红 + AST/C-03 绿
# 6. patch 树一致性: git apply --reverse --check changes.patch → OK
# 7. 合入预演: 主仓克隆 @03e23023 git apply --3way --check → 干净
```

STATUS: **ACCEPT** — 建议合入（零必修）。
