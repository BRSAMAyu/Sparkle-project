# TEST-HYGIENE 报告：测试环境治理三件

- Worker：wt121（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt121`，基于 main@2853ef5c）
- 交付：`v3-output/TEST-HYGIENE/changes.patch`（5 文件，+46/−21）+ 本报告
- 纪律：零产品代码改动（diff 仅触及 `backend/tests/` 下 5 个文件）；禁止 commit/push
- 验证环境：worktree 内 `bash scripts/generate_python_protos.sh && python3 scripts/sync_buf_python_stubs.py` 生成 `backend/app/gen/`（gitignored 生成产物，不入 patch）；pytest 统一 `SECRET_KEY=<哑值>`，pytest 9.0.2 / python3.11（/opt/homebrew）

---

## 件 1｜orchestration 测试 sys.modules 注入污染（ORCH-DEBT 申报）

**修法一句**：把 4 处裸 `sys.modules["app.services.shadow_prediction_service"] = 假模块` 全部改为 `monkeypatch.setitem(sys.modules, ...)`（测试结束自动还原），并删除下游 `test_sufficiency_preflight_resilience.py` 的「钉回真实模块」防御块（连带移除其失用的 `import sys`）。

**污染机制（复确认）**：`app/orchestration/validation_engine.py:256` 在 `_check_sufficiency` 内惰性 `from app.services.shadow_prediction_service import shadow_prediction_service`——假模块一旦进 sys.modules 且不回收，同进程内字母序靠后的测试全部命中假实现。ORCH-DEBT 测试正是因此被迫内置钉回防御。

**改动点**：
| 文件 | 改动 |
|---|---|
| `tests/orchestration/test_orchestrator_process_stream_integration.py` | 3 处注入（phase_a_hard_stops / phase_a_hard_stop_survives / sufficiency_gate_allows）改 monkeypatch.setitem，签名补 `monkeypatch` 参数 |
| `tests/integration/test_phase5_orchestrator_north_star_acceptance.py` | 第 4 处同型注入（cold_start 验收用例）一并修复——同为泄漏源，不修则移除防御钉回不安全 |
| `tests/orchestration/test_sufficiency_preflight_resilience.py` | 删除 L69-77 防御钉回块 + 失用的 `import sys`，留注释说明缘由 |

**验证**：
- `rg 'sys.modules\["app.services.shadow_prediction_service"\] =' tests/` → 0 残留；`monkeypatch.setitem(sys.modules, ...)` 恰 4 处
- resilience 文件移除防御后，在「污染者字母序先行」的目录全量跑与定向组合跑均通过
- orchestration 目录双跑（见下）失败集与基线**逐条一致**，无跨文件污染引发的新红

**范围外观察（未动，申报给主会话）**：`_install_import_stubs()` 本身以「不在 sys.modules 才装」方式全局注入 18 个假模块且同样不回收——这是该文件的既有设计（resilience 文件复用同一 fixture 模式，动它会牵连），超出本卡申报的 shadow_prediction 范围，建议后续单独立卡。

## 件 2｜test_experience_actuator 存量红（NBP23 申报）

**修法一句**：`_resolve_scoped_files` 真实签名新增必填 kwarg `include_group_documents` / `group_ids`，把两处 mock（`_fake_resolve_scoped_files`）签名对齐即可——测试语义完全有效，断言零改动。

**根因**：`app/tools/material_retrieval_tools.py:55` 的 `_resolve_scoped_files(db_session, *, user_id, requested_file_ids, include_group_documents, group_ids)` 漂移后，`app/orchestration/experience_actuator.py:547` 调用点带新 kwarg 调用，mock 不认 → TypeError 被 actuator 的 `except Exception` 兜底吞掉，status 落到 `file_resolution_failed` 而非 `grounded`。

**红→绿证明**（同环境同命令）：
```
修复前：pytest tests/unit/test_experience_actuator.py
  → tests/unit/test_experience_actuator.py ..F...   [100%]
  → FAILED ...auto_retrieves_user_material_grounding: assert 'file_resolution_failed' == 'grounded'
  → 1 failed, 5 passed
修复后：→ tests/unit/test_experience_actuator.py ......  [100%] → 6 passed in 2.83s
```
**判据说明**：6 个用例断言全部原样保留，语义仍有效（mock 镜像真实签名、行为分支不变），非改写测试目的。附带发现并修正一个隐性 mock 腐坏：`keeps_core_adjustments_when_grounding_sidecar_fails` 修复前之所以「绿」，是 TypeError 恰好替代了它想注入的 RuntimeError 走进同一兜底分支——签名对齐后才真正走到声明的异常路径。

## 件 3｜zsh 通配族「no tests ran」防护

**修法一句**（选型：最小侵入的运行时钩子）：在 `backend/tests/conftest.py` 末尾加 `pytest_collection_finish` 钩子——收集结果为 0 时打印醒目 WARNING（回显 invocation args + 「先 `rg --files -g 'test_*.py'` 确认真实文件名再传确切路径」提示），**不改变退出码语义**。

**选型论证**：相比「README/Makefile.test 加惯例说明 + 给 3 个常被猜错的文件加注释」，钩子在出错当下、在每个人（尤其 agent 合并会话）眼前报警，不依赖有人先读过文档；且仅 tests/conftest.py 一个文件 18 行、零产品代码、无新依赖，侵入面最小。文档方案对「事件发生时无人在读文档」这一核心痛点无效，故弃。两者不互斥，若主会话仍要文档惯例可后补，本卡不堆叠。

**实现要点**：pytest 9.x 中 `session.testscollected` 在该钩子**之后**才赋值（源码 `perform_collect`：先 `hook.pytest_collection_finish(session=self)` 再 `self.testscollected = len(items)`），故判空用 `getattr(session, "items", None)`——第一版用 `testscollected` 曾出现「6 passed 也误报」的假阳性，已修正并回归。

**验证**：
- 正常跑（6 passed）：无 WARNING，exit 0
- `-k` 全剔除（25 deselected / 0 selected）：WARNING 触发，exit code 仍为 **5**（no tests ran 语义不变，CI 判定不受影响）

---

## 总验证与收工核查

**orchestration 双跑（件 1 要求）**：`tests/orchestration/` 连续两遍，`36 failed, 158 passed, 26 errors` 两遍完全一致；失败集与 **基线克隆**（`git clone wt121 /tmp/wt121-hygiene-baseline`，天然 HEAD=2853ef5c）逐条 diff **完全一致** → 改动零新增失败、双跑无顺序漂移。基线还做了第 3 遍复核（PASS3 == baseline）。

**存量红清单（全部基线在案，非本卡引入，未越权修）**：
- process_stream 文件 6 个存量红（fast_track / modeling_complete / planning_bypass / planning_sidecar×3）——建议后续立卡
- `test_orchestrator_state_transitions.py` 全量 failed/error（26 errors 疑似依赖测试库 fixture）
- `test_r2_04_orchestration_source_has_no_exc_info`（源码级 lint 型用例）
- **新发现的存量排序依赖**：`tests/integration` 的 phase5 cold_start 验收用例跑在 `test_process_stream_review_required_drains_queue_before_return` 之前时后者必红——基线克隆复证同红（1 failed, 1 passed），非本卡引入；疑似 phase5 用例经真实单例残留全局态（如 `orchestrator.shadow_predictor.redis` 被换成 _MemoryRedis），建议立卡
- lint：ruff（I001/F401×2）与 black 「would reformat」在基线同文件完全相同，全为存量；本卡新增行已逐行核验 ≤120 列且不引入新违规

**收工清单**：`git status --short` 仅 5 个预期改动文件，无杂散文件；`/tmp` 自建产物（wt121_baseline.txt、wt121_after_change.txt、wt121_after_pass2.txt、wt121_after_pass3.txt、wt121_targeted2.txt、wt121-hygiene-baseline 克隆）已删除；无独立端口进程、无模拟器；Docker 共享容器（sparkle_db/redis/minio）未触碰。
