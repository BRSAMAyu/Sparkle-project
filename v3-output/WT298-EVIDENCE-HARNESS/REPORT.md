# WT298-evidence-harness 回执报告

> 2026-09-24 ｜ C 线小卡·evidence_resolve 测试装配缺失修复 ｜ 工作树：wt298-evidence-harness
> 上游：wt294 实锤存量（`test_evidence_resolve.py::...memory_backed_review_payload` 红，1/45）

## 一、根因分叉结论（①）

**卡面给的分叉 (a) harness 装配缺失 / (b) 生产装配链缺件，两皆不是。真因是 (c) worktree 环境缺 gitignored 生成产物 `backend/app/gen/`**：

- 复现真失败路径：`AttributeError: module 'app.services' has no attribute 'error_book_mastery_sync_service'`——`unittest.mock.patch`（经 `pkgutil.resolve_name`）解析 patch 目标时需导入该子模块，而其 import 链为：
  `error_book_mastery_sync_service.py:37 → adaptive_replanner → card_protocol/__init__ → card_snapshot_service → task_service.py:29 → from app.gen.sparkle.inference.v1 import inference_pb2 → ModuleNotFoundError: No module named 'app.gen'`
  → 导入失败 → `app.services` 包属性缺失 → 误导性 AttributeError，被上游两卡误读为「service 装配缺失」。
- **生产侧无罪**：`ErrorBookMasterySyncService` 模块存在、类存在；生产调用点（`error_book_service.py:421/1308`）为惰性 import + try/except 兜底，装配链完整。主仓（有 app/gen）只读探针：直接 import OK（前后 `git status` 计数不变，未写入主仓）。
- **「存量红」证伪**：wt294 的基线克隆是 `git clone`，天然不含 gitignored 产物，故「基线同红」——同因同源，非代码存量缺陷。主仓/CI（跑过 make proto-gen 的环境）该测试应为绿。
- 硬规则 1 对照：gen 产物唯一合法入口 `make proto-gen`，未手改任何 gen 文件。

## 二、修法（②）

1. **环境补齐（本卡主修复）**：在本树按正规入口补齐 Python 生成产物——`bash scripts/generate_python_protos.sh`（grpc_tools 本地生成，无 docker/网络依赖）+ `python3 scripts/sync_buf_python_stubs.py`。产出 `backend/app/gen/`（gitignored，不进 commit）。Go/Dart gen 未生成（见④守卫段）。
2. **harness 韧性（1 行代码交付）**：`tests/unit/test_evidence_resolve.py` 顶部显式 `from app.services import error_book_mastery_sync_service  # noqa: F401`，把「gen 缺失」的失败形态从误导性 AttributeError 变为诚实 `ModuleNotFoundError: No module named 'app.gen'`，后续舰队不再误诊。变异实验闭环：移走 app/gen → 采collection 期即报 `ModuleNotFoundError`（改前同状态为 AttributeError）；还原 → 全绿。
3. 顺手：该文件 HEAD 存量 1 个 I001（import 块顺序）一并归一。

## 三、测试结果（③）

- **定向**：`DATABASE_URL=sqlite+aiosqlite:///:memory:` 下 `tests/unit/test_evidence_resolve.py` **3 passed**（修前 1 failed）。
- **evidence 簇邻域回归（10 文件，超盖 wt294 那批 45）**：**126 passed, 0 failed, 20.8s**——含 test_belief_fusion_engine 19（wt294 修复面不回退）、test_error_book_mastery_sync_service 39、mastery idempotency 8 / concurrency 4 / loop 13、test_error_book_service 9、test_error_loop 3、review_500_fix 7、galaxy sync integration 21、evidence_resolve 3。
- **ruff**：改动文件 `ruff check` 全绿（净效果 -1：修掉 HEAD 存量 I001，零新增；tests/ 目录其余 2852 条为存量噪声，未触碰）。
- **守卫**（exit-checked）：`run_all_rule_guards.sh` **exit=1，唯一失败项 BG**——Go/Dart 生成产物缺失（`gateway/gen`、`mobile/lib/gen`，同为 gitignored 环境产物，与本卡 Python 面无关；BG001 清单纯 Go/Dart 文件，先于本卡存在）。**AQ（app.gen 可导入性）已由本卡补齐产物转绿**（wt294 时 AQ+BG 双红）。BG 环境红沿 wt294 先例「主仓为准」；如需彻底绿可跑全量 `make proto-gen`（需 docker/网络，本 LIGHT 卡未扩面）。

## 四、资源峰值（④）

LIGHT 卡全程：无模拟器/Gradle/浏览器/全库扫描；pytest 单文件与 10 文件簇串行（峰值 ~21s）；无 docker、无网络拉取；磁盘仅新增 gitignored 的 app/gen（约百 KB 级）；/tmp 探针产物已清（守卫日志、HEAD 基线文件）；未起任何常驻进程。

## 五、交接（⑤）

1. **交付物**：worktree 1 文件改动（`backend/tests/unit/test_evidence_resolve.py`）+ 本 REPORT + `changes.patch`；分支本地 commit，未 push。
2. **合入预期**：主仓已有 app/gen，合入后行为不变（纯测试文件 1 行韧性改动）；主会话对比法验证跑定向 `pytest tests/unit/test_evidence_resolve.py` 应 3 passed。
3. **舰队启示（建议入 FLEET-BRIEF 或新 worker onboarding）**：**新 worktree 必须先跑 `make proto-gen`（或至少 python/dart/go 三段生成）再跑测试与守卫**；`app.gen`/`gateway/gen`/`mobile/lib/gen` 均为 gitignored 环境产物，缺失时的红是环境红不是代码红。本案 AttributeError 形态曾连续误导读为「装配缺失」（wt292/wt294），已由本卡 1 行修复根治报错形态。
4. **BG 守卫遗留**：属全舰队 worktree 环境共因，若主会话认为值得，可开一张机械卡统一补 Go/Dart gen 或调整 BG 在 worktree 场景的口径。
5. 无生产代码改动，无迁移，无 proto 变更；DB-HEAD 等守卫全绿不受影响。
