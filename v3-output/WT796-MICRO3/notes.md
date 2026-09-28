# WT796-MICRO3 — 微修捆绑：V3-FIX-529 核验 + V3-FIX-528 + V3-FIX-532①②

> 2026-09-28 ｜ worker wt796 ｜ worktree `Sparkle-sysrev/wt796-micro3`（分支 `agent/node-b/wt796/micro3`，base=main@5c8aa5c4，V3-FIX-530 闭账 commit）
> 约束遵守：未重启/未触碰运行栈与 docker（脚本验证全走 PATH shim stub，`DOCKER_SHIM_LOG` 全量留痕于 /tmp 沙箱）；未 push；未改台账（闭账归主会话）；未碰 `/tmp/northstar_ns001_real_drive_state.json`（沙箱前缀 `wt796-micro3-dryrun` 独立 mktemp）；行为变更仅限三行台账列明范围。

---

## 1. V3-FIX-529（P2）summarization 日志队列 rpush ex= — 主仓已修（wt777 V3-FIX-510），本卡完成台账剩余两项核验

**核验发现**：台账登记（wt778 2026-09-28）时点与代码现状存在时间差——`_write_log`/`_log_summary` 的 rpush(ex=)→rpush+expire 修复**已在 main 落地**（wt777 commit `491495d7`，V3-FIX-510 call-arg 五处真路径修复之一；修复注释带 V3-FIX-510 锚，`summarization_worker.py:324-331`，即台账优先案① rpush 后补 `expire("logs:summarization", 86400)`）。运行时钉测试也已随 wt777 入库：`backend/tests/unit/test_v3_fix510_callarg_realpath.py`（`_FakeAsyncRedis` 复刻 redis-py 7.4.0 `rpush(name, *values)` 签名，多余 kwarg 即 TypeError）。

本卡完成台账要求的剩余两项：

1. **红重演（红先行证据）**：把 `summarization_worker.py` 临时回退为修前形制（`rpush("logs:summarization", json.dumps(...), ex=86400)`），跑既有测试：
   - 修前形制：`test_log_summary_pushes_entry_and_applies_ttl` **FAILED**（TypeError 被 `except (TypeError, RedisError): pass` 吞，fake.calls 零 rpush——"exactly one rpush must fire" 断言即红）；随后 `git checkout --` 还原。
   - 现行代码：同测试 **2 passed**（`SECRET_KEY` 一次性 env 沿 wt766/wt793 先例）。
2. **全仓 grep 其余 `rpush(..., ex=` 同族调用（台账要求）**：`backend/app` 全部 15 处 rpush 调用点逐一亲读（含 websocket.py:516、spine_orchestrator.py:2549/3575/3793 四处多行调用），`grep 'rpush([^)]*ex='` 覆盖 `.py/.go/.dart/.sh`（backend/app、backend/gateway、mobile/lib、scripts、tests_e2e）——**零残留**；spine 三处均为 rpush+ltrim+expire 分离写法（正确范式），无 Lua 脚本 rpush。同族风险清零。

**结论**：FIX-529 代码面与测试面均已闭合于 wt777（本卡零 Python 改动），台账剩余核验项完成如上，闭账证据齐备。

## 2. V3-FIX-528（P3）tests_e2e/test_galaxy_e2e.py 整文件删除

**处置前核查（台账要求项）**：
- CI 分片清单：`grep -rn test_galaxy_e2e .github/workflows/ scripts/ Makefile` **零引用**——无需清引用。
- git log 该文件：仅 1 个 commit（`1722e6dc` Initial commit clean-slate reset），**无活跃开发痕迹**；文件头自述 "Marked as skipped until the required API methods are implemented"（为未实现功能预写，从未激活）。
- 幽灵类确证：`:25 from app.services.rag_service import RAGService`，`grep RAGService backend/app` 零命中。
- 修前红：`pytest --collect-only ../tests_e2e/test_galaxy_e2e.py` → **ERROR 1 error during collection, no tests collected**（import 幽灵类即炸，与 wt780 度量实录一致）。
- 引用面：`backend/tests/unit/test_t6_slo_metrics.py` 三处命中均为测试方法名含 "galaxy_e2e" 字样（SLO histogram 钉），与该文件无 import 依赖；`run_e2e_tests.py`/`pytest.ini`/`conftest.py`/`README.md` 零引用。

**处置**：`git rm tests_e2e/test_galaxy_e2e.py`（596 行）；同步两处文档引用防断链——`QUICKSTART.md` 删除「知识星图测试」可执行命令块（文件已不存在，命令必炸）；`IMPLEMENTATION_SUMMARY.md` 该节头加删除注记（历史清单保留作记录）。

**修后绿**：`pytest --collect-only tests_e2e -q` → **36 collected, 零 error**（wt780 基线 "36 例+1 收集错误" 的那个 1 归零）。

## 3. V3-FIX-532①②（P3）prod 备份/恢复脚本两处对齐

### ① restore_prod_data.sh bash 3.2 空数组崩溃

**红（本机 bash 3.2.57 + docker PATH shim 沙箱 dry-run，修前脚本取 `git show HEAD:` 不落地真 docker）**：
- `REDIS_PASSWORD=""`（wt782 实录路径）：**`line 118: _redis_cli_args[@]: unbound variable`**——`set -u` 下空数组 `"${arr[@]}"` 展开即崩，与台账实录逐字同型；
- `REDIS_PASSWORD` 完全未导出（同族新增发现）：**`line 115: REDIS_PASSWORD: unbound variable`**——脚本此前对 REDIS_PASSWORD 无 `:-` 缺省，比空数组崩得更早，同属无密码路径断链。

**修法**（台账两案取长：显式分支，等价 `set --` 案且免 positional 污染）：删 `_redis_cli_args` 数组，新增 `redis_cli_exec()` 助手（与 backup 侧 `redis_cli()` 同形，按密码有无显式分支）+ `REDIS_PASSWORD="${REDIS_PASSWORD:-}"` 缺省补位。

**绿**：三路径全过（bash 3.2.57 实测，脚本 exit 0）——`REDIS_PASSWORD=""`、完全 unset、带密码（shim 日志确证带密码路径 `docker exec -e REDISCLI_AUTH=pw-secret ...` 透传、无密码路径不带 `-e`）。

### ② backup_prod_data.sh MinIO skip 与 checksum 自相矛盾

**红**：shim 模拟 MinIO 数据路径缺失 → 修前脚本打印 "skipping minio archive" 后，checksum 步仍无条件 `sha256sum ... minio-data.tar.gz` → **`sha256sum: minio-data.tar.gz: No such file or directory`，exit 1**——`set -e` 当场中止，bundle 残缺（postgres.sql.gz/redis.rdb/部分 sha256sums.txt，**无 manifest、无 config**）。「降级跳过」语义实际是「必炸」，与台账实录一致。

**修法**（台账"skip 时跳过 checksum 或明确日志说明"两案并取）：`_MINIO_ARCHIVED` 旗标，skip 时 checksum 只覆盖实际归档产物（postgres+redis）并打明确日志；归档时三分照旧。

**绿**：
- skip 路径 exit 0，sha256sums.txt 只含两行、`shasum -a 256 -c` 自洽 OK，manifest.json/config 步恢复产出；
- 正常路径（shim 模拟 MinIO 在场）三分照旧全覆盖；
- **跨脚本集成**：修后 restore 消费 skip 分支产出的备份包全链路 exit 0（checksum verify OK → PG clean+if-exists 重放 → redis 快照 → minio 缺席告警降级 → done）。
- 两脚本 `bash -n`（bash 3.2.57）过；shellcheck 本机未装。

## 4. 门禁与验证汇总

- **触达面测试**：`test_v3_fix510_callarg_realpath.py` 2 passed（+红重演 FAILED 实录）；`test_context_pruner.py`（summarization_worker 另一引用面）2 passed 8 skipped（skip 为 base 既有，零 Python 改动不涉）。
- **ruff**：`app/orchestration/summarization_worker.py` + `tests/unit/test_v3_fix510_callarg_realpath.py` All checks passed（本卡零 Python 变更，记录用）。
- **mypy 冷缓存**（独立 MYPY_CACHE_DIR，全量 `mypy app`）：**Found 55 errors in 51 files (checked 1387 source files)**——与 V3-FIX-498/wt793 基线「55 零漂移」精确同值，零新增。
- **tests_e2e collect**：36 collected 零 error（修前 1 error）。
- **bash**：两脚本 bash 3.2.57 `bash -n` 过；restore/backup 修后全部 dry-run 场景 exit 0（docker 全 shim，未触碰真实容器）。

## 5. 变更清单（本分支全部）

- `scripts/restore_prod_data.sh` — 532①：redis_cli_exec 助手替代空数组展开 + REDIS_PASSWORD 缺省
- `scripts/backup_prod_data.sh` — 532②：_MINIO_ARCHIVED 旗标，checksum 与 skip 分支对齐
- `tests_e2e/test_galaxy_e2e.py` — 528：整文件删除（596 行）
- `tests_e2e/QUICKSTART.md` / `tests_e2e/IMPLEMENTATION_SUMMARY.md` — 528 引用同步
- `v3-output/WT796-MICRO3/notes.md` — 本记录
- 零 Python 源码变更（529 主仓已闭合于 wt777 491495d7）
