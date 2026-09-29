# FIX-577 R1 独立审查 receipt（2026-09-29，审查员 R1，未参与实现）

- 审查对象：`502f4e06`（fix），头 `3b09c16e`，base `48190526`，worktree `/Users/brsama/code/GitHub/wtF577`，分支 `fix/v4/f577-project-name-pinning`
- 红线遵守：零容器生命周期操作（docker 面仅 `compose config` 渲染、`docker ps/version` 只读、pytest 内 inspect）；up.sh 未执行（门语义用逐字 case 复刻验证）；临时哑值 `.env` 用后即删（收尾两 checkout `git status --porcelain` 均 0 行）；Makefile mutation 探针已还原（`git show HEAD:Makefile | cmp -s -` 通过）；主 checkout 全程零改动。
- 环境：macOS darwin 25.6.0 arm64，Docker Compose v5.0.2 / daemon 29.8.0（审查后半程 daemon 进入 "Docker Desktop is unable to start" 故障态，见发现 5）。

## VERDICT: PASS_WITH_CHALLENGES

七个审查靶全部实证通过，红线达成，证据五件套诚实（limitations 预登记了本审查多项挑战）。挑战均为 LOW/边界态，不阻塞闭账。

## 逐靶结论（按审查令顺序）

1. **钉死语义** ✔ /tmp 复刻 Makefile 结构实证五态：无 env 无 .env→`sparkle-project`；仅 .env→`.env` 值赢（设计声称成立）；仅外部 env→穿透；两者并存→**`.env` 赢过外部 env**（make 普通赋值覆盖环境，与 compose 原生优先序相反，见挑战 C1）；命令行→赢。真 Makefile `make -pn dev-up` 数据库 `COMPOSE_PROJECT_NAME = sparkle-project` 实录；`-f Makefile -f extra.mk` recipe 实收 `PIN=sparkle-project`。up.sh 与 Makefile 双源同值、无环（Makefile 不调 up.sh，up.sh 不调 make dev-up）。
2. **BYTE-IDENTICAL** ✔ 三向全量 `docker compose config`（哑 .env，用后即删）：主 checkout 裸=`sparkle-project_{default,6 卷}` ×7；wtF577 裸=**`wtf577_*` ×7 漂移复现**（缺陷形态，与 RUNBOOK「手工裸 compose 仍漂移」注记一致）；wtF577 经 make/经 env=`sparkle-project_*` ×7。`cmp wt_pinned.yml wt_make.yml` → BYTE-IDENTICAL；`diff main_bare wt_pinned` 64 行**全部**为 checkout 目录路径（bind/build context），非路径差异 0。
   ⚠ 方法论警示（C4）：Compose 5.0.2 下 `config --volumes` 子命令输出逻辑卷名、**不反映 project 名**（`COMPOSE_PROJECT_NAME=zzzprobe` 对照输出相同且顺序随机）——复核者若用 `--volumes` 会得到空洞的"零差异"。实现者证据用的是全量 config 的 `name:` 字段，方法论有效。
3. **门与 supervisor** ✔ 门 case 逻辑逐字复刻六象限：cosmos→die、ours→OK、absent→warn 放行、漂移前缀（wtf577_）→die（fail-loud 拦截漂移而非误放行）、自定义覆盖自洽、空值走 `:-` 默认（无 fail-open）。supervisor diff 48190526 仅 ：57 一行+docstring；默认值 `os.environ.get(...,"sparkle-project")+"_"` 与原硬编码 `"sparkle-project_"` 逐字节同；`scripts/tests/` 在 48190526..3b09c16e 零改动（空 diff 实证）。o05 restore **14 passed**；supervisor 族 **16 passed + 1 failed**——失败项 `test_once_cli_green_on_healthy_decoy` 报 `Docker Desktop is unable to start`（daemon 态）；**base 48190526 归档在 /tmp 同跑同败**（甚至 restart 测试亦间歇败）→ 环境归因非回归，实现者 17 passed（daemon 健康时）可信。
4. **弃用裁决** ✔ 严格子集属实：worker（同三队列，c=2 vs make c=4）、beat、flower（make FLOWER_ENABLE=1 门控等价）皆被覆盖；make 多 glm_batch worker/.env 真凭据（脚本硬编码 change-me）/自动 build/钉死网络。替代路径存在性实证：`celery-up:383`/`celery-logs-worker:424`/`celery-status:450`/`celery-stop:454`、`docker-compose.celery.yml` 在。残留核查：`sparkle-flutter_default` 可执行脚本面（除弃用封存正文）0 行。
5. **mutation 独立** ✔ 删除 `Makefile:13` 导出行（sed 临时）→ `PIN=`（空）、裸渲染与**经 make 渲染**均漂移回 `wtf577_*` ×7 → `git checkout -- Makefile` 还原，与 HEAD cmp 逐字节同，status 0 dirty。钉死行即生效变更，独立性成立。
6. **零改动面** ✔ 主 checkout（/Users/brsama/code/GitHub/Sparkle-project，main@8aaa655e）审查前中后 `git status --porcelain` 均 0 行；`502f4e06`/`3b09c16e` 仅存在于本 worktree 分支（`git branch --contains` 实证）；`docker-compose.yml` 在 base/head/main 三点零差异（渲染可比性前提成立）。
7. **RUNBOOK** ✔ 铁律节 FIX-577 注记与实证语义逐点一致（make 目标即安全/手工 compose 须 -p 或 export/worktree 裸命令仍漂移），来源行补 577。DYNAMIC_ISSUES 台账 FIXED@502f4e06 闭账行在位。

## 发现列表

- **C1 | LOW | Makefile:13+16** 覆盖序语义：经 make 路径下 `.env` 值**赢过外部环境变量**（make 普通 `=` 覆盖环境），与 docker compose 原生优先序（shell env > .env）相反——同一仓库状态下经 make 与裸 compose 对同一 .env+外部 env 组合可解析出不同 project。复现：/tmp 复刻 case4（`COMPOSE_PROJECT_NAME=fromshell make print` + `.env` 内 `fromdotenv` → 输出 `fromdotenv`）。纯边界态（需两处同时设值），设计声称".env/外部显式仍可穿透"各自为真，不阻塞。
- **C2 | LOW | scripts/devtools/start_celery.sh:20-23、scripts/devtools/README.md:8、QUICK_START_CELERY.md 方式 B** 弃用指向 `make celery-up` 未带 F578 警示：该替代路径自身受已登记的 `sparkle_redis:6379` DNS 悬空回归（V3-FIX-578，已派 wtF578 在飞）影响，redis URL 债修复前 celery worker 起而连不上。limitations.md §1.1 已如实声明本点（"未声称该路径立即可用"），但指针三处（DEPRECATED 块/README 行/QUICK_START）读者不可见该 caveat。建议 F578 收口时同步回填三处，不阻塞本卡。
- **C3 | LOW | scripts/ops/service_supervisor.py:57** 空串边界：`os.environ.get("COMPOSE_PROJECT_NAME", "sparkle-project")` 对**已设但为空**的变量返回 `""` → 前缀退化为 `"_"`（匹配任意含下划线 mounts，假阳 OK）；up.sh:17 的 `${:-}` 则把空串当未设走默认。两脚本空值语义不一致。理论态（需显式 `COMPOSE_PROJECT_NAME=` 空导出），登记不修。
- **C4 | INFO | 审查方法论** Compose 5.0.2 `config --volumes` 子命令对 project 名盲（见靶 2）；后续任何本族复核须用全量 `config` 的 `name:` 字段或 json `--format`。
- **C5 | INFO | Makefile:391-416（既有，非本卡 diff）** celery 族 `--network sparkle-project_default` 为字面硬编码，不随 `COMPOSE_PROJECT_NAME` 显式覆盖联动（覆盖者经 make celery-up 会把 worker 挂到字面网络而 compose 服务在 `<覆盖值>_default`）——与钉死的覆盖自由度存在残留缝隙，属 F578/后续 ops 脚本收口面，本卡未声明修复。
- **C6 | INFO | 审查环境** 审查后半程 Docker daemon 进入 "unable to start" 态（伴随宿主磁盘 <400MB 压力），真机 inspect 类用例（17 测中 1 项）此刻无法绿；以 base 同败归因闭环。建议 daemon 恢复后补跑一次 17 测作确认（非本卡义务）。

## 命令与 exit code 清单（关键项）

| 命令 | exit |
|---|---|
| `make -pn dev-up`（grep COMPOSE_PROJECT_NAME） | 0 |
| /tmp 语义复刻 case1-5（?=/​.env/外部/并存/CLI） | 0×5 |
| `docker compose -f docker-compose.yml config`（主裸/wt裸/wt env-pin/wt make-pin，哑 .env） | 0×4 |
| `cmp wt_pinned.yml wt_make.yml` | 0（BYTE-IDENTICAL） |
| `diff main_bare.yml wt_pinned.yml` 非路径差异计数 | 0 行 |
| `make -f Makefile -f extra.mk f577-pin`（修复态/mutation 态/还原态） | sparkle-project / 空 / sparkle-project |
| mutation 后裸/经 make 渲染卷名前缀 | wtf577 ×7 / wtf577 ×7 |
| `git checkout -- Makefile` + `git show HEAD:Makefile | cmp -s -` | 0 |
| `pytest test_service_supervisor.py test_supervisor_probe.py`（head / base 归档） | 1 failed 16 passed / 同因失败 |
| `pytest test_o05_restore_consistency.py` | 14 passed |
| `bash -n` ×2 / `py_compile` / `ruff check supervisor` / `make -n dev-up` | 全 0 |
| `git status --porcelain`（wtF577 收尾 / 主 checkout ×3） | 0 行 |
| `git branch --contains 502f4e06` | 仅本 worktree 分支 |

— R1（2026-09-29）
