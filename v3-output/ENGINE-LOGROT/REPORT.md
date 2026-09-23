# ENGINE-LOGROT — 引擎日志文件 sink 轮转（修复交付报告）

- Worker：C 纵队修复线 wt212（基线 `e5705147`，零 commit 零 push）
- 依据：`v3-output/PROD-LOG2/REPORT.md` ④-P3 ——「引擎日志无轮转：/tmp 单文件被重启顶掉（09:10 实例证据即因此丢失）」
- 交付物：本报告 + `changes.patch`（worktree 内代码改动见「实现清单」）

---

## ① 现状与设计裁决

### 现状（卡面前提的一处修正）

引擎两进程的 loguru 现状**并不对称**：

| 进程 | 入口 | 现状 sink | 重启后果 |
|---|---|---|---|
| uvicorn（FastAPI :8000） | `app/main.py:80-85`（`logger.remove()` + stderr sink，`level=LOG_LEVEL`、`serialize=not DEBUG`） | 仅 stderr → nohup 重定向 `/tmp/uvicorn_engine.log` | **旧文件被顶掉，证据链断（本卡真正的断点）** |
| gRPC（:50051） | `backend/grpc_server.py:94-99` | **自带文件 sink**：`logs/grpc_server_{time}.log`，`rotation="1 day"`、`retention="7 days"`、level=INFO（且 stderr 默认 sink 保留） | 落 `backend/logs/`（gitignored），实测有 879KB 历史文件——**已有轮转，不受重启顶掉影响** |

因此本卡实际修复面 = **uvicorn 进程**；gRPC 进程不动（见 ③ 冲突面与 ④ 诚实申报）。

### 设计裁决：显式开（默认关），不是默认开

- `LOG_FILE_PATH` 默认 `""` → 文件 sink **不挂载**，uvicorn 进程行为与本卡合入前**逐位一致**（已做真实 import 对照验证，见 ④）。
- 理由：
  1. 卡面硬约束「默认行为不破坏」只有默认关才能逐位成立；
  2. AGENTS.md 磁盘纪律（2026-09-19 立规）：默认落盘会让测试/CI/子 agent 环境意外产生文件且无人归口；
  3. 主会话是唯一合入方，路径由它在 `.env` 显式决定，可归口管理。
- 未采用「/tmp/sparkle_engine.log 级别缺省」：缺省路径等于默认开，违背 1；且 /tmp 是各卡收工即清的场所，放日志证据链反而易被误清。
- 量级：`LOG_ROTATION_MB` 默认 20、`LOG_RETENTION` 默认 10 个文件（按 PROD-LOG2 记录的日志量级：引擎 ~15k 行/1.5h、约 3-5MB/h，20MB×10 ≈ 数天证据窗口）。
- 文件 sink 与 stderr sink **双写**，`level`/`serialize` 语义完全镜像 stderr sink（`LOG_LEVEL` / `not DEBUG`）。
- 挂载失败（路径不可写等）只 `logger.warning` 降级，**不阻止引擎启动**（证据链是二级目标，可用性第一）。

## ② 实现清单

| 文件 | 改动 |
|---|---|
| `backend/app/core/logging_setup.py`（新增） | `format_rotation_size()`（MB→loguru 尺寸串，整数归一 `"20 MB"`、小数保留 `"0.05 MB"` 供小阈值测试，非正数拒绝）；`add_rotating_file_sink_if_configured()`（空路径=严格 no-op 返回 None；配置了则以 `rotation/retention/level/serialize` 挂载并返回 handler id） |
| `backend/app/config/settings.py` | `# Logging` 块追加 3 字段：`LOG_FILE_PATH:str=""`、`LOG_ROTATION_MB:float=20.0`、`LOG_RETENTION:int=10`（带作用域注释） |
| `backend/app/main.py` | import helper；stderr sink 原样保留，其后追加 `try: add_rotating_file_sink_if_configured(...)` 条件挂载 + 降级告警 |
| `backend/tests/unit/test_logging_file_sink.py`（新增，11 用例） | ① 参数形制 3 例；② 未配置严格 no-op（handler 集合不变）1 例；③ 配置挂载/level 过滤/小阈值真实轮转+零丢行 3 例；④ settings 默认值契约 1 例；⑤ AST 接线防回潮 3 例（main.py stderr sink 形制不变、helper 恰好接线一次且参数正确、grpc_server.py 自带 sink 不被误动） |

关键测试断言（`test_rotation_triggers_with_small_threshold_and_no_line_loss`）：0.05MB 小阈值 + 300 行（≈72KB，确定性跨一次阈值、远低于第二次）→ 恰好轮转出 2 个文件，且**全部 300 行分文不少**——轮转不得丢行正是本卡使命（证据链完整）的本质断言。

## ③ 冲突面声明

- **本卡触碰面**：`app/config/settings.py`（仅 `# Logging` 块 +6 行）、`app/main.py`（import 区 +1 行、模块级 loguru 配置段 +12 行）、新增 2 文件。不触碰任何 handler/service/proto/迁移。
- **与 wt210（metacognition/checkpoint/security_monitor/llm_router）**：已核对 wt210 分支相对基线 `e5705147` 的 `git diff --name-only`——**未触碰 settings.py / main.py / config 任何文件**。若其后续给 Settings 追加字段，属不同区块的纯增量 hunk，与本卡 `# Logging` 块相距约 900 行，3-way 合并冲突概率极低；万一相撞，双方均为加行，取双方即可。
- **与 wt207（onboarding/趋势/光子）、wt211（concurrency/llm_service/celery）**：无文件交集。说明：`app/core/celery_app.py` 自身用 loguru（celery worker 进程仍走 nohup 重定向）——不在本卡范围，未动；若舰队后续想给 worker 落盘，直接复用 `add_rotating_file_sink_if_configured` 即可。

## ④ 诚实申报

1. **卡面前提修正**：卡写「引擎日志走 loguru→stdout 重定向 /tmp/*.log」——gRPC 进程其实早有自带轮转文件 sink（`grpc_server.py:94-99`），真正断链的只有 uvicorn 进程；本卡修 uvicorn、不动 gRPC。gRPC 的 sink 写相对路径 `logs/`（随 CWD 解析），属既有债务，本卡不扩大战线。
2. **验证范围**：定向验证（新 11 用例 + 既有 loguru 治理守卫 `test_loguru_exc_info_migration.py` 3 用例 + 真实 import 对照 + 干净基线克隆 apply 验证），未跑引擎全量测试（遵守「定向不宽扫」纪律）。pytest 计数：14 passed, 0 failed。
3. **真实 import 对照**（等价现网模块级路径）：未配置 → active sinks `[StreamSink]`（与合入前一致）；`LOG_FILE_PATH=/tmp/logrot-wt212/probe_engine_uvicorn.log` import → `[StreamSink, FileSink]`、文件落盘含引擎 boot 日志、父目录自动创建。
4. **retention 语义边界**：loguru 的 retention 修剪是**异步定时任务**，进程存活期内按保留数收敛，`remove()` 瞬间不保证文件数已封顶——单测因此断言「单次轮转 + 零丢行」，不断言即时封顶。稳态下 20MB×10 即约 200MB 封顶。
5. **相对路径解析**：`LOG_FILE_PATH` 相对路径按进程启动 CWD 解析（Makefile :338 `cd backend && uvicorn ...`，即 `backend/`）；报告推荐绝对路径或 `logs/` 前缀由合入方自选。
6. **环境借用申报**：测试用主仓 `backend/.venv`（只读借用，python3.11 + loguru 0.7.3 + pytest 9.0.2）；worktree 缺 gitignored 的 `app/gen` 生成物，从主仓 symlink 借用做 import 验证（**收工已删**，不入 patch）；`SECRET_KEY` 用一次性假值（非凭据）。
7. **未做**：未给 celery worker / 一次性 scripts 接文件 sink（超卡面）；未动 `.env.example`（`LOG_LEVEL` 本就不在其中，无一致性守卫约束 logging 变量；合入方如需示例可自行加注释行）。

## ⑤ 收工核查

- [x] 零 commit 零 push（`git log` 仍停在 `e5705147`；改动全部在工作区）
- [x] `git status --short` 与清单一致：M settings.py / M main.py / ?? logging_setup.py / ?? test_logging_file_sink.py / ?? v3-output/ENGINE-LOGROT/（交付物）/ ?? app/gen（symlink，收工已删）
- [x] 干净基线克隆（`git clone` HEAD→/tmp）`git apply --check` 通过、apply 后 11/11 测试通过（对比法）
- [x] 定向 pytest 带 `--timeout` + sqlite env，一次一个文件
- [x] /tmp 自清：`/tmp/logrot-probe`、`/tmp/logrot-wt212`、`/tmp/logrot-wt212-baseline` 已删
- [x] 无模拟器/Gradle/浏览器/构建产物；磁盘 `df` 无新增压力

## 合入方步骤（主会话执行）

1. 备份 → `git apply --3way v3-output/ENGINE-LOGROT/changes.patch`；
2. 定向回归：`cd backend && SECRET_KEY=<一次性值> DATABASE_URL="sqlite+aiosqlite:///:memory:" .venv/bin/python -m pytest tests/unit/test_logging_file_sink.py tests/unit/test_loguru_exc_info_migration.py --timeout=120 -q`（预期 14 passed）；
3. `backend/.env` 追加（默认关，加行即开）：
   ```bash
   # ENGINE-LOGROT：uvicorn 进程日志落盘（gRPC 进程自带轮转，无需配置）
   LOG_FILE_PATH=logs/engine_uvicorn.log   # 建议放 backend/logs/（已 gitignore，不随 /tmp 清理丢失）；也可用绝对路径
   LOG_ROTATION_MB=20
   LOG_RETENTION=10
   ```
4. 重启 uvicorn 进程（`Makefile:338` 自带 `--env-file .env`，gRPC 进程无需动）；
5. 验收探针：启动后确认 `backend/logs/engine_uvicorn.log` 出现 boot 行；**再重启一次**，确认旧文件被改名为 `engine_uvicorn.<时间戳>.log` 保留（而非被顶掉）——PROD-LOG2 断链场景复现消失，即本卡验收通过。
