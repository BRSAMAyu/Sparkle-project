# FIX-577 verification — 命令与 exit code 实录（2026-09-28，wtF577）

## 1. 基线与钉死证明（compose config 静态渲染；config=只读，不 up）

临时哑值 `.env` 注入后渲染（`env_file:` 指令要求 `.env` 存在；三种基线渲染后均即删，未入库）：

```
# 基线（修复前，内容=main@48190526）
cd Sparkle-project && docker compose -f docker-compose.yml config              # exit 0（裸命令，project=目录名）
cd wtF577          && docker compose -f docker-compose.yml config              # exit 0（裸命令 → 漂移复现）
cd wtF577          && COMPOSE_PROJECT_NAME=sparkle-project docker compose … config   # exit 0（钉死参照渲染）

# 修复后（wtF577）
COMPOSE_PROJECT_NAME=sparkle-project docker compose -f docker-compose.yml config > postfix_env.yml   # exit 0
make -f Makefile -f extra.mk f577-render > postfix_make.yml                                          # exit 0（经 Makefile 导出环境渲染）
make -f Makefile -f extra.mk f577-pin    # 输出 sparkle-project（worktree 内 make recipe 实收环境变量）
```

### 卷名前后对照（红线：主 checkout 行为逐字节不变）

| 渲染 | 卷名（`name:` 字段，7 项） |
|---|---|
| 修复前·主 checkout 裸命令 | `sparkle-project_{default,sparkle_backend_cache,sparkle_backend_logs,sparkle_backend_uploads,sparkle_minio_data,sparkle_postgres_data,sparkle_redis_data}` |
| 修复前·wtF577 裸命令（**漂移复现**） | `wtf577_*` 同构 7 项——即 FIX-563R1 发现2 的缺陷形态 |
| 修复前·显式 pin 参照（wtF577） | `sparkle-project_*` 7 项 |
| 修复后·wtF577 经 Makefile 导出环境 | `sparkle-project_*` 7 项 |

- **逐字节**：`cmp postfix_env.yml 基线pin参照` → BYTE-IDENTICAL；`cmp postfix_make.yml 基线pin参照` → **BYTE-IDENTICAL**（0 差异）。
- **worktree 一致性**：`diff <(卷名·主checkout基线) <(卷名·修复后worktree make渲染)` → 零差异（钉死生效证明：worktree 渲染卷名与主 checkout 完全一致）。
- 全文件对照中主 checkout 基线与 worktree 渲染的**唯一**差异为 bind-mount 绝对路径（checkout 目录不同使然，与卷名/数据面无关）。
- 红线闭环：主 checkout 目录名本就小写化为 `sparkle-project`，pin 值=该默认值 → 主 checkout 行为逐字节不变（上表第 1、4 行卷名同集），数据面零迁移延续。

## 2. 门逻辑隔离验证（bash，无 docker）

`case "$mounts" in *"$COMPOSE_VOLUME_PREFIX"*)` 模式匹配实测：prefix=`sparkle-project_` + mounts=`sparkle-project_sparkle_postgres_data` → `OK(ours)`；prefix=`wtf577_`（模拟未钉死漂移）同 mounts → 落 `*)` die 分支（漂移可被门拦截，而非误放行）。

## 3. 语法与测试

| 项 | 命令 | 结果 |
|---|---|---|
| make 解析 | `make -n dev-up`（wtF577） | exit 0 |
| bash -n ×2 | `bash -n scripts/dev/up.sh scripts/devtools/start_celery.sh` | 全 OK |
| python 编译 | `python3 -m py_compile scripts/ops/service_supervisor.py` | OK |
| ruff | `ruff check scripts/ops/service_supervisor.py` | All checks passed（exit 0） |
| supervisor 门测试 | `python3.11 -m pytest scripts/tests/test_service_supervisor.py scripts/tests/test_supervisor_probe.py -q` | **17 passed**（1.58s；断言零改动——env 默认值路径与原硬编码语义等价，`DATA_VOLUME_OWNER_PREFIX` 默认分支逐字节同值） |
| o05 恢复守卫 | `python3.11 -m pytest scripts/tests/test_o05_restore_consistency.py -q` | **14 passed**（0.10s） |

## 4. 真机只读复核（红线：不触碰）

- 本卡零 up/down/restart/run；docker 面仅 `compose config` 渲染与 pytest 内 `docker inspect`（read-only owner 预检真机用例，随 17 passed 通过）。
- 主 checkout（`/Users/brsama/code/GitHub/Sparkle-project`）收尾 `git status --porcelain` = 0 行，无 `.env` 残留。
