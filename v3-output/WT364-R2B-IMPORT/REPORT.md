# WT364 卡 R2-B 交付报告 — 打断 plan_context↔prompts↔context_pack 循环 import

- **Worker**: wt364 ｜ **日期**: 2026-09-25 ｜ **分支**: `wt364-r2b-import`
- **Base SHA**: `f644de3a`（main @ wt358 U-06）
- **卡源**: v3-output/WT355-HUNT-R2/REPORT.md「卡 R2-B」（台账 C-01 升格 H3，wt348/355 双轮复核确认）

## 一、问题与环拓扑（干净进程独立复现）

三入口 `import app.core.plan_context` / `import app.orchestration.prompts` /
`import app.core.context_pack` 在干净进程全部 ImportError（本 worktree 逐条复现，
exit=1，与 WT355 H3 判定一致）。完整环：

```
app.core.plan_context:27 (from app.models.plan import Plan)
  → app/models/__init__.py:111 (community_privacy)
  → app/models/community_privacy.py:9 (from app.aurora.runtime_v1.models import JSONBCompat)
  → app/aurora/runtime_v1/__init__.py:186,221 (checkpoint_runtime / chat_adapter)
  → app/aurora/runtime_v1/chat_adapter.py:20 (from app.orchestration.prompts import ...)
  → app/orchestration/prompts.py:44 (from app.core.plan_context import merge_plan_context)
  → partially initialized app.core.plan_context → ImportError
```

环中指向 plan_context 的模块级边只有一条：prompts.py:44。conftest/main 先载
app.models 的正常入口不触发，故进程内 import 断言无效——冒烟测试必须 subprocess
干净进程（tests/conftest.py 顶层预载 app.models 已核实）。

## 二、方案选择：延迟导入（二选一中取最小侵入）

- **选定**：prompts.py 删除顶层 `from app.core.plan_context import merge_plan_context`，
  下沉为唯一调用点 `build_system_prompt` 内的函数级延迟导入（全仓该符号仅此一处调用，
  grep 证实无任何模块经 prompts 转 re-export 该符号）。
- **理由**：① 环只需打断一条边，延迟导入改动 1 文件 4 行；② 共享下沉需新建叶子模块 +
  plan_context/prompts 两处改动 + 兼容 re-export，侵入更大；③ 无 try/except 包
  ImportError 掩盖、无 API 签名/行为变更（Forbidden 双合规）；④ 同模式既有先例
  （graph_rag.py:2042 "Import here to avoid module-load cycles"）。运行时行为不变：
  首次调用后模块缓存生效，后续调用为 dict 查找。

## 三、红绿证据（三入口 × 干净进程）

| 入口 | 修复前（红） | 修复后（绿） |
|---|---|---|
| `import app.core.plan_context` | exit=1（partially initialized） | exit=0 |
| `import app.orchestration.prompts` | exit=1（同环） | exit=0 |
| `import app.core.context_pack` | exit=1（经 plan_context:50 入环） | exit=0 |

可证伪性：新测试 `backend/tests/unit/test_wt364_r2b_import_cycles_smoke.py`
（3 参数化用例，subprocess + `sys.executable -c "import <entry>"`，cwd=backend 根）。
修复前跑同测 **3/3 FAILED**（回传 stderr 含循环 import 栈），修复后 **3/3 PASSED**；
还原实验为单文件粒度（prompts.py 备份至 /tmp → checkout 还原 → 复红 → 回填），
符合并发验收工作树安全条款。

## 四、改动文件清单

| 文件 | 改动 |
|---|---|
| `backend/app/orchestration/prompts.py` | 删顶层 import :44；`build_system_prompt` 唯一调用点改延迟导入（+2 行注释说明环拓扑） |
| `backend/tests/unit/test_wt364_r2b_import_cycles_smoke.py` | 新增：三入口干净进程 import 冒烟（C-01 可证伪判据） |
| `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md` | C-01 置 **CLOSED WITH EVIDENCE**（✅ 已处理表加行 + 原登记节追加闭合注记） |

不碰：task_event_consumer（wt360 战区）、函数签名、任何生成代码。

## 五、验证矩阵（全部实测）

| 门 | 结果 |
|---|---|
| 三入口干净进程 import | 3/3 exit=0 |
| 冒烟红测（修复前） | 3/3 FAILED（红证） |
| 冒烟红测（修复后） | 3/3 PASSED |
| 相关面回归 pytest | 1058 passed 0 failed（plan_context/context_pack 簇 21 + prompts 面 45 + startup_smoke/wt355 探针/situation_brief/signal_spine 989 + 冒烟 3），DATABASE_URL=sqlite+aiosqlite:///:memory: |
| ruff（被碰文件 + I001） | All checks passed |
| 冷 mypy（rm -rf .mypy_cache） | **1103** = quality/mypy_baseline.txt 当前值 1103，未推高 |
| 守卫 `run_all_rule_guards.sh` | **84/84 PASS，exit 0**（worktree 补拷 mobile/gateway gen 后实测） |

## 六、遗留与交接

- 无行为变更、无 schema/proto 变更、无新文档目录；台账已闭合。
- 本 worktree 的 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen` 为主仓
  `cp -RL` 拷贝（gitignored 环境件），不入交付。
