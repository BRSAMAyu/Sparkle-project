# PHASE5-COLD 报告：phase5 cold_start 排序依赖存量红清偿

- Worker：wt136（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt136`，基线 0575219d）
- 交付：`v3-output/PHASE5-COLD/changes.patch`（1 文件，+13/−0）+ 本报告
- 纪律：零产品代码改动（diff 仅触及 `backend/tests/integration/` 下 1 个测试文件）；禁止 commit/push
- 验证环境：worktree 内从主仓拷贝 `backend/app/gen/`（gitignored，不入 patch）；pytest 统一 `SECRET_KEY=test`，pytest 9.0.2 / python3.11（`/opt/homebrew/bin/pytest`），全部单进程

---

## ① 复现剧本（顺序敏感的确切命令序列 + 红绿输出）

登记源：TEST-HYGIENE 报告「新发现的存量排序依赖」条目。定位结果：

- **污染者**：`tests/integration/test_phase5_orchestrator_north_star_acceptance.py`（phase5 cold_start 验收用例 `test_phase5_orchestrator_cold_start_plan_asks_one_question_instead_of_planning`，经其 `_install_import_stubs()` 残留全局态）
- **受害者**：`tests/orchestration/test_orchestrator_process_stream_integration.py::test_process_stream_review_required_drains_queue_before_return`（L1502）

```bash
cd /Users/brsama/code/GitHub/Sparkle-sysrev/wt136/backend

# 剧本 A（污染者先）→ 红
SECRET_KEY=test /opt/homebrew/bin/pytest \
  tests/integration/test_phase5_orchestrator_north_star_acceptance.py \
  "tests/orchestration/test_orchestrator_process_stream_integration.py::test_process_stream_review_required_drains_queue_before_return" -q
# 修前输出：FAILED ...::test_process_stream_review_required_drains_queue_before_return
#           TypeError: orchestrator_factory.<locals>._GraphStub.invoke() got an unexpected keyword argument 'resume_policy'
#           1 failed, 1 passed, 1 skipped
# 修后输出：2 passed, 1 skipped

# 剧本 B（受害者先 / 单独跑）→ 绿（修前修后同绿）
SECRET_KEY=test /opt/homebrew/bin/pytest \
  "tests/orchestration/test_orchestrator_process_stream_integration.py::test_process_stream_review_required_drains_queue_before_return" -q
# 1 passed in 0.87s
```

关键日志（修前剧本 A，受害者段）：`ERROR | app.orchestration.execution_engine:_plan_and_validate:2635 - LangGraph planning error: '_LangGraphPlannerStub' object has no attribute 'pop_rendered_plan_artifact'` → 走 direct-mode 兜底 → `should_return=False` → Step13 启动图 → `_GraphStub.invoke(resume_policy=...)` TypeError。**TEST-HYGIENE 疑似的 `shadow_predictor.redis` 残留不成立**——真因是 planner stub 方法面漂移（见②）。

## 根因（逐行）与修法

**根因链（三类顺序依赖里的「模块级可变状态泄漏」变体：sys.modules 假模块 + import 期类绑定固化）**：

1. `tests/integration/test_phase5_orchestrator_north_star_acceptance.py:160` `_install_import_stubs()` 以「不在 sys.modules 才装、装后不回收」方式注入 18 个假模块，其中修前行号 L182-215 装入假 `app.orchestration.lang_graph_planner`（其 `_LangGraphPlannerStub` **缺 `pop_rendered_plan_artifact`**）。
2. phase5 用例内 `importlib.import_module("app.orchestration.orchestrator")` 完成进程内首次导入：`app/orchestration/orchestrator.py:98` 的模块级 `from app.orchestration.lang_graph_planner import LangGraphPlanner` 把 **phase5 的 stub 类固化**进 orchestrator 模块属性——orchestrator 模块此后常驻 sys.modules，该绑定**不随测试结束还原**（删 sys.modules 条目也无效）。
3. 受害者文件的同名安装器（`test_orchestrator_process_stream_integration.py:275` 起同款守卫）见模块已存在→跳过装自己的 stub；其 fixture 构造的 `ChatOrchestrator` 拿到 phase5 版 stub 实例。用例只 per-instance mock 了 `.plan`，而 `execution_engine.py:2172` 还要调 `pop_rendered_plan_artifact(session_id)` → AttributeError 被 L2635 的 `except` 兜底吞掉 → 计划作废、审查流程被跳过 → 图被启动 → 红刀口表现为 `resume_policy` TypeError。
4. 旁证：两文件 stub 安装器逐行 diff，planner 族唯一差异就是这一个方法；两文件 plan_review stub 逐字相同故无漂移（execution_engine.py:43 import 期绑定的单例与 sys.modules 中对象恒为同一对象，patch 恒命中）。

**修法（污染者侧补齐方法面 + 契约注释，1 文件 +13 行）**：

- `tests/integration/test_phase5_orchestrator_north_star_acceptance.py:223` 给 `_LangGraphPlannerStub` 补 `pop_rendered_plan_artifact`（实现逐字镜像受害者 stub 语义：`del session_id; return None`），使两个 stub 族的消费面等价——此后无论谁先导入 orchestrator，下游拿到的 stub 都满足其流程调用面，顺序不再改变行为。
- `_install_import_stubs()` 增补 docstring，写明「本文件 stub 会被下游同名安装器复用且 orchestrator 类绑定不还原」这一跨文件契约，防再次静默漂移。

**为何不选另两条路（论证）**：
- *monkeypatch 隔离 18 个 stub*：单独做治不了本红——sys.modules 还原后 orchestrator 模块内固化的 stub 类绑定仍在（见根因 2），受害者依旧红；且 phase5 之后的 integration 文件现行可能隐性复用其残留 stub，改动回收语义爆炸半径大。TEST-HYGIENE 已将「安装器不回收」申报为全库既有设计，非本卡（micro）应重构的面。
- *受害者侧防御重绑*：受害者拿「sys.modules 当时的 LangGraphPlanner」重绑，在 phase5 先行场景下取到的仍是 phase5 stub，除非强制装自己的假模块——又会改变受害者目录内「真实类先行」场景的行为，风险更高。

## 前后对比（零新增、零残留）

| 场景 | 修前 | 修后 |
|---|---|---|
| 剧本 A（phase5 → 受害用例） | 1 failed（resume_policy TypeError） | **2 passed, 1 skipped** |
| 剧本 B（受害用例 → phase5 / 受害用例单独 / phase5 单独） | 全绿 | 全绿（不变） |
| phase5 全文件 → 受害者全文件 | 未跑全量（pair 修前已证此顺序下 drains_queue 必红） | 6 failed, 20 passed, 1 skipped；失败集与受害者单独跑**逐条 diff 为空**（即仅 6 个 TEST-HYGIENE 在册 process_stream 存量红：fast_track / modeling_complete / planning_bypass / planning_sidecar×3；drains_queue 绿） |
| `pytest tests/integration` 全目录 | 34F / 114P / 40E（74 条在册存量） | **逐条 diff 为空**（34F / 114P / 40E，不变） |
| `pytest tests/orchestration` 全目录 | 35F / 160P / 26E（61 条在册存量） | **逐条 diff 为空**（不变） |
| `pytest tests -k "phase5 or cold_start" --ignore=tests/northstar_eval` | 62 passed, 5 skipped | 62 passed, 5 skipped（不变，相邻 phase5/cold_start 域零回归） |

存量红全部为基线在册（TEST-HYGIENE 清单 + shop/DB fixture 族），本卡零新增、目标红清偿。

## Worker 五要素（其余四项）

**② 红线面**：`changes.patch` 仅 1 文件 +13/−0，全部位于 `backend/tests/integration/test_phase5_orchestrator_north_star_acceptance.py`（stub 方法补齐 + docstring 契约注释）。零产品代码改动；`app/orchestration/*`、`app/services/*` 未触碰。lint：black/ruff 在该文件报的 I001 与 3 处 reformat 均在基线同文件同位置（456/722/895 行区域），与本次 +13 行无交集，全为存量。

**③ 冲突面**：在途卡 wt131（llm/orchestration）、wt132（galaxy）、wt133（mobile）、wt135（调查）。本卡唯一改动文件是 `tests/integration/` 下的测试文件，与 wt131 的 orchestration 生产域（`app/orchestration/`）**无任何文件交集，无需逐 hunk 声明**；与其余各卡域无交集。

**④ 诚实申报**：
- 调查中临时创建过探针文件 `tests/orchestration/test_zz_probe_identity.py`（验证单例同一性），已删除，不入 patch。
- 未清偿的相邻债务（申报，未越权）：(a) 两文件 `_install_import_stubs()` 的「不回收」全局注入模式仍在——TEST-HYGIENE 已在案，建议将来以「进程级 stub 注册表 + 显式作用域」单独立卡；(b) 反向漂移点：受害者 stub 的 `ProgressNarrativeService`/`PlanProgressService` 为裸 type、phase5 版为带方法的类——当前两向全量实测均绿（缺方法方的流程未被调用），属潜在反向顺序风险，与在册债务 (a) 同根；(c) execution_engine.py:2172 对 planner 的 `.plan`/`pop_rendered_plan_artifact` 隐式方法面契约没有单一事实来源，建议后续给 planner 协议补 Protocol 定义（生产代码改进，本卡不动）。
- TEST-HYGIENE 报告中「疑似 shadow_predictor.redis 被换成 _MemoryRedis」的猜想经证据否定，真因如②，主会话可据实更新台账。

**⑤ 收工核查**：`git status --short` 仅 1 个预期修改文件 + 2 个交付新文件（`v3-output/PHASE5-COLD/`），无杂散；探针文件已删；`/tmp` 自建产物（stub diff 副本、基线/修后失败清单、探针脚本）已删；无独立端口进程、无模拟器、无浏览器实例；Docker 共享容器（sparkle_db/redis/minio）未触碰；`app/gen/` 为主仓拷贝的 gitignored 运行时依赖，随 worktree 生命周期回收。
