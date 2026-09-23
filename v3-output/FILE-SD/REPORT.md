# FILE-SD 报告 — prometheus dev/prod 抓取目标 file_sd 解耦

> 轮次：D 纵队 · 部署运维线 ｜ 2026-09-23 ｜ worktree wt202（基线 4d353132）
> 债依据：wt186 `v3-output/D-DEPLOY-FIX/REPORT.md` ④.3「G1 的 dev 形制影响（关键坦白）」登记的
> 「两形制双绿的彻底解是 file_sd 按形制生成目标……**登记债务未实现**」——本卡即该债的真修落地。
> 交付物：本报告 + `changes.patch`（11 个文件：3 改 8 增）。**零 commit 零 push，零凭据，未重启任何运行容器。**

---

## ① file_sd 设计与两环境文件内容

### 设计核心：挂载面即形制开关

`monitoring/prometheus.yml` 仍被 dev（docker-compose.yml 基座）与 prod（docker-compose.prod.yml）共用，
但**环境相关的目标不再写死在本文件里**——一律改 `file_sd_configs` 指向容器内
`/etc/prometheus/targets/<名>.yml`，由各形制 compose 把自己的目标目录挂到同一路径：

- dev compose 挂 `./monitoring/targets/dev` → `/etc/prometheus/targets`（ro）
- prod compose 挂 `./monitoring/targets/prod` → `/etc/prometheus/targets`（ro）

规则文件与 Grafana 面板**零改动**；无需 PROMETHEUS_ARGS、无需配置双份、无环境变量选择逻辑。
新增环境 = 新增一个同名目录 + compose 改一行挂载。

### job 面变化（job_name 全部不变，wt186 保 job 名的口径延续）

| job | 改前（wt186 后） | 改后 | 说明 |
|---|---|---|---|
| sparkle_gateway | static: gateway_blue+green:8080 | file_sd → `gateway.yml` | dev 挂载后解析 `sparkle_gateway:8080`，prod 双实例蓝绿双抓 |
| sparkle_backend | static: backend:8000 | file_sd → `backend.yml` | dev 解析 `sparkle_api:8000` |
| sparkle_counterfactual / simulation_lab / safe_experiments / community_privacy | static: backend:8000 ×4 | file_sd → 共用 `backend.yml` | 四个模块 job 与主 job 同目标集，共用一份文件 |
| node / cadvisor | static: node_exporter:9100 / cadvisor:8080 | file_sd → `node.yml` / `cadvisor.yml` | prod 有真目标；dev **文件留空 `[]`**（见下） |
| prometheus（自抓）/ alertmanager / sparkle_agent_grpc | static | **static 保持不动** | 环境无关目标（sparkle_agent 两形制同名可解析，wt186 已认定） |

### 两环境目标文件内容（monitoring/targets/{dev,prod}/ 四件同名同构）

| 文件 | dev/（基座 compose 挂载） | prod/（prod compose 挂载） |
|---|---|---|
| `gateway.yml` | `sparkle_gateway:8080`（单实例，服务名=container_name） | `gateway_blue:8080` + `gateway_green:8080`（蓝绿双抓，任一掉线即 up==0 序列，wt186 G1 口径） |
| `backend.yml` | `sparkle_api:8000`（dev 引擎服务名） | `backend:8000`（prod 服务名，container_name=sparkle_backend） |
| `node.yml` | `[]`（dev 无此服务——**无序列而非常驻 down**） | `node_exporter:9100` |
| `cadvisor.yml` | `[]`（同上） | `cadvisor:8080` |

**默认文件选择策略**：prod compose 挂 `targets/prod/`、dev 基座 compose 挂 `targets/dev/`，
路径都落在 `/etc/prometheus/targets`，prometheus.yml 无感知形制。dev 的 node/cadvisor 留空文件
而非缺文件：Prometheus 对 file_sd 缺文件会在启动日志/UI 报 FAILED 并持续重试（噪音），空 `[]`
则干净地零目标。dev 侧 node/cadvisor 由此从「目标不可解析→常驻 down 序列」变为「无序列」——
已核对全部 6 个规则文件：**无任何规则引用 `job="node"`/`job="cadvisor"`、全仓无 `absent()` 规则**，
无告警面变化（wt186 对该项的「既有现状」登记随之消除）。

## ② 实现清单

| # | 文件 | 变更 | 对应 |
|---|---|---|---|
| 1 | `monitoring/prometheus.yml` | 头注改写为 file_sd 解耦机制+默认策略说明；9 个环境相关 job 的 static_configs → file_sd_configs（backend.yml 由 5 个 job 共用）；环境无关 3 job 与 celery 注释段原样保留 | 卡主体 |
| 2 | `monitoring/targets/dev/{gateway,backend,node,cadvisor}.yml` | 新增 ×4（node/cadvisor 为空 `[]` + 留注） | dev 形制目标 |
| 3 | `monitoring/targets/prod/{gateway,backend,node,cadvisor}.yml` | 新增 ×4 | prod 形制目标 |
| 4 | `docker-compose.yml` | prometheus 服务 volumes 增加一行 `./monitoring/targets/dev:/etc/prometheus/targets:ro`（L554-556） | dev 挂载面 |
| 5 | `docker-compose.prod.yml` | prometheus 服务 volumes 增加一行 `./monitoring/targets/prod:/etc/prometheus/targets:ro`（L738-740） | prod 挂载面 |
| 6 | `v3-output/FILE-SD/changes.patch` | 上表 1-5 共 11 文件统一补丁（基线克隆 `git apply --check` 通过） | 交付 |

净改动：3 文件修改 + 8 文件新增，约 +100/−45 行（prometheus.yml 头注占大头）。

## ③ 冲突面声明

本轮只动 `monitoring/`（prometheus.yml + targets/ 新目录）与两个 compose 的 prometheus 服务
volumes 段，逐卡声明：

- **wt198（northstar_eval）**：评测域，零重叠；
- **wt200（mobile/模拟器实测）**：mobile/ 域 + 实测报告，零重叠；
- **wt201（纯复审）**：无树变更，零重叠；
- **wt197（LOG-HEALTH，已合入 05a24707，含于本卡基线 4d353132）**：其 hunk 位置为
  docker-compose.yml **L7-127**（db/redis/minio 的 logging 与慢查询 command）、
  docker-compose.prod.yml **L568-622**（同域三服务 + prod redis command 列表化/AOF）；
  本卡 hunk 位置为 docker-compose.yml **L554-556**（prometheus 服务 volumes 段）、
  docker-compose.prod.yml **L738-740**（同段）——**hunk 位置无重叠**（基线已含 wt197，
  实测 `git diff` 干净分离）。

基线 4d353132 之上 `git status` 申报：modified ×3（docker-compose.yml / docker-compose.prod.yml /
monitoring/prometheus.yml）+ untracked ×1（monitoring/targets/ 整目录）+ untracked 交付物
v3-output/FILE-SD/，无其他漂移。

## ④ 诚实申报

1. **promtool 验证双口径**：先以本机既有 `prom/prometheus:latest`（wt186 同款做法）跑双形制
   check config 全 SUCCESS；因运行镜像是 `quay.io/prometheus/prometheus:v2.53.4`，又临时拉取
   **v2.53.4 精确版本**复跑双形制——同样全 SUCCESS（config 语法 + 6 规则文件 81 规则），用完即删镜像。
   promtool 经一次性 `--rm` 容器执行（无端口、即退，不属任何栈）。
2. **目标 × 服务名语义核对**（promtool 不覆盖的解析面）：脚本解析 prometheus.yml 各 job 的
   effective targets（static + file_sd 文件），逐项对照所在形制 compose 的服务名/container_name
   全集——dev 9 目标、prod 11 目标全部可解析，零 MISS（详见验证记录；`localhost` 自抓为 SELF）。
3. **验证边界**：全部为解析级（promtool 双形制）、渲染级（compose config + 渲染产物确认挂载
   source/target）、干跑级（`config -q` 占位 env，fake 值）、单测级（T6 配置回归）——
   **未起任何栈、未重启/未触碰任何运行容器、未实抓 up 序列**。file_sd 运行期行为
   （目标加载、蓝绿双抓实抓）属合入后真机验证，与 wt186 报告 §5 同口径。
4. **T6 回归的运行口径**：`backend/tests/unit/test_t6_slo_metrics.py::TestSLOPrometheusConfig`
   直接读 monitoring/prometheus.yml 断言 rule_files——真实 pytest 需 backend Settings 环境，
   以 fake `SECRET_KEY` 等环境变量跑通：**1 passed**（该测试只查 rule_files，本卡未动）。
5. **file_sd 细节取舍**：`refresh_interval` 用默认 5m——目标集只随形制挂载变化，而挂载变化
   本身就要重建容器（compose 检测 volumes 变化自动 recreate），无需更短刷新；目标文件刻意
   **不写 labels**，job 标签由 job_name 统一赋值（防改写 job 标签连锁破坏告警/面板的口径写进头注）。
6. **未动面**：alertmanager envsubst、celery 注释段（9808 待部署债）、prometheus-celery.yml
   （游离文件，两 compose 均未挂载，另案）、`--web.enable-lifecycle` 参数、depends_on（
   prometheus 依赖的服务名两形制都真实存在）全部原样。
7. **零凭据**：占位 env 全 fake 值（fakepass/fake-tag 等），基座 compose 校验用的一次性 `.env`
   已删、prod 用 /tmp env 文件已删。

## ⑤ 收工核查

- [x] 无 `git commit` / `git push`；交付物 = 本报告 + `changes.patch`（基线克隆 apply --check 通过）
- [x] 未重启/未触碰任何运行容器；一次性 promtool 容器 `--rm` 即退；临时拉取的 v2.53.4 镜像已删
- [x] /tmp 自清：`/tmp/filesd-prod-env.txt`、`/tmp/filesd-baseline/` 基线克隆已删
- [x] worktree 根一次性 `.env` 占位文件已删（gitignore 内，未入 patch）
- [x] 零凭据入交付物
- [x] job_name 零变化、规则文件与 Grafana 面板零改动（T6 配置回归通过）
- [x] dev 目标文件服务名对齐 dev compose 真实服务名（sparkle_gateway/sparkle_api，语义核对零 MISS）

## 合入方步骤（部署动作不执行，仅流程说明）

1. **常规合入**：备份 → `git apply --3way v3-output/FILE-SD/changes.patch` → 定向测试对比法
   （`cd backend && SECRET_KEY=<fake> python -m pytest tests/unit/test_t6_slo_metrics.py::TestSLOPrometheusConfig`）
   → commit → push。
2. **生效方式（关键）**：两 compose 的 prometheus 服务各新增一个 volume 挂载，**仅 reload 不够，
   必须 recreate**——`docker compose up -d prometheus`（dev）/
   `docker compose -f docker-compose.prod.yml up -d prometheus`（prod）会自动判定 volumes 变化
   重建容器，config 随启动加载。
3. **合入后真机验证**（本卡未执行）：`curl -s http://127.0.0.1:9090/api/v1/targets` 逐 job 核对
   `health=up`——dev 形制应见 sparkle_gateway/sparkle_api 双绿（此前 no-data 的两 job 复绿）、
   node/cadvisor 无序列；prod 形制应见 gateway_blue+green 双抓 + backend + node_exporter + cadvisor 全绿。
4. **回滚**：revert 本 patch 即回到 wt186 形制（prod 全绿/dev 两 job no-data），目标目录残留无害。
