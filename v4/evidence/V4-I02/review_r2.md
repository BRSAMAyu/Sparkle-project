# V4-I02 · 独立审查 receipt（整改复审 R2）

- 审查会话：wtI02R2（未参与 I02 实现与 R1 整改）
- 对象：`agent/v4/i02` @ `60b4a535`（fix(v4): I02 一审整改——集成面类型锚派生+FIX52 硬拒接线+高相关回归测；8 文件 +371/-23）
- 审查方式：只读 + 全量 diff 阅读 + 独立复跑 + 亲自 mutation（字节级还原，`git status` 干净 + sha256 对表）+ 静态检查抽验
- 日期：2026-09-28
- 环境备注：worktree 无 .venv，复跑借用主检出 `.venv` 解释器；已验证 `import app` 解析到 `/Users/brsama/code/GitHub/wtI02/backend/app/__init__.py`（非主检出），复跑有效。

## 总裁决：**整改闭环（PASS）——CHALLENGE-1 可销账**

R1 CHALLENGE-1（集成面硬门空心）已真实修复：`context_pack.build` 现派生并传入当次类型锚，FIX52 硬拒在 flag-on 集成面实际生效，探针同形态回归测钉死，可证伪性经本会话亲自 mutation 双向证实。无新增实质挑战；两条次级观察见文末（均不阻塞销账）。

---

## 逐靶结论

### 靶 1 · 整改真实性（派生源与降级路径）——**PASS**

`derive_current_type_anchors`（`backend/app/services/memory_utility_gate.py:433-473`）逐一核对：

- 派生源**仅**三类结构化声明：`plan_context["plan_type"]`、`plan_context["task_summary"]["by_type"]` 的**键**（isinstance dict 守卫）、`route_intent`（回退 `intent`）。**无自由文本猜类型**——函数根本不接触 query_text/content。
- 归一口径 `strip + lower` 与候选侧 `_type_anchors_from_tags`（`task_type:*`/`domain:*` tag）一致，交集判定同平面。
- 取不到 → 返回空 `frozenset`；`apply_history_utility_gate` 落 `metadata["current_type_anchors"]`（sorted 实际参与判定的锚）+ `metadata["anchors_unavailable"]=not anchors`（:511-512）——空锚如实申报，**不静默**。单测四态钉死：全源 / 回退链 / 空声明 / 畸形形状健壮跳过 + 锚可用性登记（`test_derive_current_type_anchors_*` ×4、`test_apply_history_utility_gate_records_anchor_availability`）。

### 靶 2 · 集成面不再空心——**PASS**

- `context_pack.py:1593-1601`：flag-on 分支内先 `derive_current_type_anchors(plan_context, route_intent=route_intent, intent=intent)` 再以 `current_type_anchors=_current_type_anchors` 传入门。`plan_context` 来自 `PlanContextBuilder`（结构化 dict）；生产主链 `app/api/v1/chat.py:1046` 恒传 `route_intent or intent`，空锚仅为降级登记路径（limitations 已如实分级）。
- 探针同形态回归在库且形态正确：`test_flag_on_high_relevance_cross_type_failure_hard_rejected_at_pack_surface`（wiring 测试，真 db_session 走 `builder.build` 集成面；essay_writing 失败 × math 查询，relevance **0.75/1.0 两档参数化**）。断言链完整：`selected is False` + `negative_transfer_cross_type ∈ reasons` + **`score > 0`**（软分阈上，整改前必入选——证明拦它的是硬门不是软分）+ relevance reason 对表 + 不进 `pack.episodic_memories`/`to_prompt_context()` + `current_type_anchors == ["chat"]` + `anchors_unavailable is False`。候选侧锚经 `tags=[f"task_type:{tag}"]`（`_add_episodic`），交集判定真实。
- 反向钉：`test_flag_on_without_type_anchors_keeps_soft_path_and_records_unavailable` 锚死无锚路径行为不变（软路径 + anchors_unavailable=true），防整改面外溢。
- AST 钉补第三条腿：`test_ast_build_derives_current_type_anchors`（删派生调用必红，与既有删接线/摘旗标钉同型，常量假守卫剪枝免疫）。

### 靶 3 · 断言纪律——**PASS（语义升级，非削弱）**

全 commit diff 逐块阅读：既有测试改动**仅一处**——`test_flag_on_suppresses_negative_transfer_keeps_good_recall` 中异类型失败的拒用 reason 断言 `utility_low_score` → `negative_transfer_cross_type`（同时**新增** `current_type_anchors == ["chat"]`、`anchors_unavailable is False` 两条强化断言）。

- 判定依据：该条目「不得入选」的断言始终在（含 pack 与 prompt 两面），改的只是拒用**机制**归因——从弱机制（软分恰好压下）改为强机制（硬拒）。整改前该 reason 归因是锚恒空的副产物（硬门结构性不可触发），整改后归因与验收①语义一致。0 条断言删除或放宽；`existing_tests_modified=1` 在 test_results.json/run_manifest.json 如实登记，与 diff 事实一致。其余全部为纯新增。

### 靶 4 · 可证伪性声明——**PASS（两条均亲自 mutation 证实，已字节级还原）**

- **Mutation A**（删 `current_type_anchors=_current_type_anchors` kwarg，保留派生调用）：恰 **3 红** = 探针两档 + `test_flag_on_suppresses_negative_transfer_keeps_good_recall`；AST 钉保持绿（调用仍在）。失败形态即 CHALLENGE-1 复发：`AssertionError: ['math exercise plan with word count all failed overdue']`——异类型失败经验重新进 pack。「删传参 kwarg→探针红」证实。
- **Mutation B**（派生调用 + kwarg 一并删）：恰 **4 failed, 30 passed** = Mutation A 3 红 + `test_ast_build_derives_current_type_anchors`。「删派生调用→4 测红」证实。
- 还原：两次均 `git checkout --` 后 `git status --porcelain` 空、`git diff 60b4a535` 0 行、`shasum -a 256 backend/app/core/context_pack.py` = `2fe4e1aeeb76a4e54329edb0f10887b3c699f8d4e9ed79b3e767f49bcc287300` 与 test_results.json 登记哈希一致——字节级还原成立。

### 靶 5 · 复跑——**PASS**

- `SECRET_KEY=ci-test-key DATABASE_URL=sqlite:// pytest tests/unit/test_memory_utility_gate.py tests/unit/test_memory_utility_gate_wiring.py -q` → **34 passed in 3.90s**（25 单测 + 9 新增：1 AST 钉 + 5 派生/登记 + 探针 2 档 + 无锚钉），与声称一致。
- 受影响面抽验（manifest r1-2 同组 11 文件，含 prefilter/context_pack/hard_filter_wiring/selfcheck/funnel/ranking/pipeline/context_manager）→ **182 passed in 11.34s**，与登记完全一致。

### 靶 6 · 静态检查抽验——**PASS（两条次级观察，不阻塞）**

- ruff 4 文件：All checks passed ✓。black 3 文件：unchanged ✓。
- mypy 受触两文件：`context_pack.py`/`memory_utility_gate.py` 自身 **0 error**（30 条 error 全部在传递导入的第三方文件，与登记的 "30" 一致）✓。
- `scripts/ci/mypy_ratchet.sh`（从 worktree 根）→ **53 / baseline 77，exit 0**。
- `scripts/run_all_rule_guards.sh` → **all rule guards passed (86 rules)**；ENUM-PARITY FAIL=0 WARN=7（既有 WARN）——与 r1-9 逐字一致 ✓。

## 次级观察（不阻塞销账，登记供后续卡）

1. **mypy ratchet 计数 53 vs 登记 55**：两者均 < baseline 77 且方向有利（更少）；差额属环境/缓存噪声，非本 diff 回归（受触文件自身 0 error 已独立证实）。另：manifest r1-8 的「worktree vs 主检出逐行 identical」本次**不可复现**——主检出（集成分支）当前 mypy 在导入链早期失败（`errors prevented further checking`），属集成面漂移，与本分支 diff 无关。
2. **`derive_current_type_anchors` 未列入模块 `__all__`**（`memory_utility_gate.py:532-552`）：context_pack 为显式具名导入，功能零影响，纯导出面卫生项；下张触碰该模块的卡顺手补即可。
3. （已在 limitations.md #2 如实登记，此处确认）派生锚为路由/计划类别词表，与候选侧 `task_type:*`/`domain:*` 自由 tag 按 strip+lower 字面交集判定——词表不对齐时偏保守（多拒），FIX52 语义（失败只在声明同类型放行）如此，同词表对齐归写入侧卡。

## 证据完整性

test_results.json `artifacts_sha256` 登记的 7 个哈希全部重算**逐一吻合**（diff_or_evidence_only.md / run_manifest.json / limitations.md / memory_utility_gate.py / test_memory_utility_gate.py / test_memory_utility_gate_wiring.py / context_pack.py）。整改表述与代码事实无失实：diff_or_evidence_only.md 验收①已改述为整改后事实并保留 R1 FAIL 历史；limitations.md #2 已删除 R1 判失实的全称表述，残留限制分级如实。

## 销账建议

- CHALLENGE-1：**销账**（remediation verified at commit `60b4a535`）。
- V4-I02 整卡：按验收模型维持「普通任务 DONE = 独立审查 + 集成 SHA 可失败测试」，R2 复审通过后可走 DONE_REVIEWED。
