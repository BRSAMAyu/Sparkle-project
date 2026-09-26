# WT572-CIREPRO — Backend Tests "冻结" CI 同构复现报告

- 工位：wt572 ｜ 分支：`agent/node-b/wt572/cirepro`（基线 9c4b2904）
- 日期：2026-09-27（本地 UTC+8）
- 任务：本地 CI 同构复现 `backend/tests/unit/spine/test_specialized_features.py` 的间歇性冻结；只诊断，不改产品代码/测试/CI 配置。
- 结论先行：**本地 10/10 次同构复现全部干净通过，未复现冻结；对 2026-09-24 至 09-26 期间 13 个 Backend Tests job（12 个已终态 + 1 个进行中）的 CI 数据逐条取证后，没有发现任何一次 pytest 进程真实停摆的证据。原"冻结"叙事与日志事实不符，更可能是"对运行中 job 的日志观测失明 + 全量套件变慢（75→84 分钟）+ 人工取消慢任务"三者叠加的误诊。** 详见下文，每一条数字都有出处。

---

## 1. 本地 CI 同构复现循环（10/10 干净）

### 1.1 方法

在 worktree `backend/` 下，用与 CI 一致的环境变量跑**整个文件**（非单测）：

```bash
cd <worktree>/backend
TZ=UTC TESTING=true \
DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v \
REDIS_URL=redis://localhost:6379/0 \
/Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python -m pytest \
  tests/unit/spine/test_specialized_features.py -v --cov=app --cov-report= \
  --timeout=300 --timeout-method=thread
```

- worktree 内**无 `.env`**（只有 `*.example`），无需改名，无还原项。
- 本机 redis 实例在 6379 端口存活（`nc -z` 通过），与 CI 的 redis service 同构。
- 外层防挂死：macOS 无 GNU `timeout`，用监控循环等价实现——每 5s 探活，≥320s 仍未退出则 `py-spy dump --pid` 抓栈（py-spy 已预装到 `/tmp/pyspy-wt572/bin/py-spy`），≥600s 硬杀。
- 单次 >120s 即记"可疑慢"。

### 1.2 结果（真实耗时，`/tmp/wt572-cirepro/summary.txt`）

| 轮次 | 退出码 | 外层耗时 | pytest 自报 | 结果 |
|---|---|---|---|---|
| 1 | 0 | 10s | 2.65s | 59 passed |
| 2 | 0 | 5s | 2.38s | 59 passed |
| 3 | 0 | 5s | 2.37s | 59 passed |
| 4 | 0 | 5s | 2.35s | 59 passed |
| 5 | 0 | 5s | 2.41s | 59 passed |
| 6 | 0 | 5s | 2.44s | 59 passed |
| 7 | 0 | 5s | 2.38s | 59 passed |
| 8 | 0 | 5s | 2.40s | 59 passed |
| 9 | 0 | 5s | 2.43s | 59 passed |
| 10 | 0 | 5s | 2.38s | 59 passed |

- **没有任何一次达到"可疑慢"阈值（120s），最慢 10s**；py-spy 从未触发（无一次存活到 320s）。
- 全量 10 轮总耗时 55 秒——本地单文件在 CI 同构条件下稳定 ~2.4s。本地采样窗口极短（相对 CI 84 分钟全量上下文），单凭本地无法证伪"长上下文才触发的停摆"，因此补做了下述 CI 日志取证。

### 1.3 与 CI 的环境差异（如实记录）

| 项 | 本地 | CI | 影响 |
|---|---|---|---|
| Python | 3.11.15 | 3.11（setup-python） | 无 |
| pytest | 9.0.2（venv 实装） | 9.0.3（requirements.lock） | 微小 |
| pytest-timeout | 2.4.0 | 2.4.0 | 一致 |
| y-py | 0.6.2 | lock 同版 | 一致 |
| coverage 扫描范围 | `--cov=app` | `--cov=backend/app`（同一路径的另一种写法） | 无 |
| `--cov-report=` | 空值不写盘 | `--cov-report=xml` | 只影响收尾写文件，不影响测试执行 |

---

## 2. CI 日志取证（2026-09-24 → 09-26，13 个 Backend Tests job 全查）

用 `gh api repos/BRSAMAyu/Sparkle-project/actions/runs/...` 逐 job 拉取结论、起止时间与完整日志（原始日志存 `/tmp/wt572-cirepro/`）。

### 2.1 Job 清单（真实起止与结论）

| run（attempts） | Backend Tests job | 起止（UTC） | 时长 | 结论 | pytest 实际状态 |
|---|---|---|---|---|---|
| 36015155771 a1（09-24） | 107688665034 | 14:53:00→15:33:17 | 40m17s | cancelled（人为取消） | **取消前 8 秒仍在 PASSED**（47%） |
| 36015155771 a2（09-24） | 107708947681 | 15:41:24→16:21:44 | 40m20s | cancelled（人为取消） | **取消前 3.5 秒仍在 PASSED**（51%） |
| 36178015150（09-25） | 108215382781 | 19:16:30→20:23:00 | 66m30s | failure | 跑完全量：139 failed, 12340 passed，1:00:03 |
| 36190201989（09-25） | 108255097236 | 21:18:05→22:39:35 | 81m30s | failure | 跑完全量：86 failed, 12552 passed，1:14:20 |
| 36198488067（09-25） | 108281055199 | 22:56:09→00:17:49 | 81m40s | failure | 跑完全量：88 failed, 12560 passed，1:15:19 |
| 36253679384 a1（09-26） | 108437426994 | 16:03:20→17:33:46 | 90m26s | failure | 跑完全量：13 failed, 12989 passed，1:24:05 |
| 36253679384 a2（09-26） | 108452479615 | 17:34:24→19:05:12 | 90m48s | failure | 跑完全量：13 failed, 12989 passed，1:24:03 |
| 36268994104 a1（09-26） | 108480275288 | 20:23:54→21:19:19 | 55m25s | cancelled（rerun 触发取消） | **取消前 8 秒仍在 PASSED**（67%，3s/个的稳定推进） |
| 36268994104 a2（09-26） | 108489071070 | 21:19:26→（本报告定稿时仍在跑） | — | in_progress | pytest 步 21:25:22Z 起，正常推进 |

另查 09-26 白天 4 个 cancelled job（36218978920 / 36230148802 / 36249150918 / 36251648705，27–42 分钟）：**每一个在取消瞬间 pytest 都活着且刚打出 PASSED**（进度 20%–42%），日志尾部均有 `Terminate orphan process: pid (…​) (pytest)`。

另有一个快速失败 run 36267475092（19:57:02→20:02:52Z，5m50s）：失败步为 `Apply database migrations (test schema parity)`，属迁移/基础设施失败，与测试停摆无关（后续同日 run 已恢复正常执行）。

**关键否定证据：**

1. **没有任何一份日志出现"输出断流后 job 继续挂着"的形态。** 所有 cancelled job 的最后一条 pytest 行时间戳与取消时间差 <10s；所有 failure job 都打出了完整 summary 行（`= N failed, M passed … in T =`）。
2. **pytest-timeout 从未触发过。** 其命中标志 `+++ Timeout +++` 在全部 9 个已终态 job 的日志中出现次数为 **0**。`--timeout=300 --timeout-method=thread`（ci.yml:124 已配置）的含义是：任何单个测试超过 300s 都会在日志里留下 `+++ Timeout +++` + 全线程栈并硬退出。一次都没出现 ⇒ **整个观测窗口内没有任何一个测试（含两次懒加载 import）卡到过 300 秒**。
3. 传闻中的两个冻结点在真实日志里的表现：
   - run 36253679384 a2：pytest 17:40:21Z 起；`test_crdt_mastery_merge_max_wins` PASSED 于 18:13:15.553Z，`test_age_gate_adult_allows_sensitive` PASSED 于 18:13:15.584Z，`test_data_deletion_request_creates` PASSED 于 18:13:15.586Z —— **三个"冻结点"测试在 33 毫秒内全部通过**，位于 pytest 启动后 **32m54s、进度 37%**。
   - run 36268994104 a1：pytest 20:29:34Z 起；同样三个测试在 20:58:03.513–03.545Z（**32 毫秒**）内全部 PASSED，位于启动后 **28m29s、进度 36%**，且该文件跑完后后续文件继续推进了 21 分钟直到被取消。

### 2.2 "冻结叙事"最可能的真实来源：运行中日志不可读（已两次现场复现）

对本报告定稿时仍在运行的 job 108489071070（attempt 2）做日志拉取：

- 21:31:06Z：`gh api .../actions/jobs/108489071070/logs` → **HTTP 404 `BlobNotFound`**；
- 21:38Z 再次：同样 `BlobNotFound`；
- `gh run view --job=… --log` → 空输出，CLI 提示 "run 36268994104 is still in progress; logs will be available when it is complete"。

即：**对这个仓库，job 处于 in_progress 时日志 blob 不存在（404），只能等 job 结束后拉全量日志。** 任何按"已完成 job"方式轮询日志的监控/自动化，会在整个 75–90 分钟运行期里得到"无输出/无日志"的观测，与"静默 20+ 分钟"的描述完全吻合。而两个被点名的测试恰好位于 30 分钟 / 36–37% 处——观察者拿到的最后快照停在哪个测试附近，取决于它开始轮询失败的时刻，两次观测落在同一位置带（~30min、~35%±5%）由此自然解释，无需假设 pytest 真的停在该处。

### 2.3 真实存在的问题（与"冻结"无关但值得记账）

1. **全量套件在 coverage 下耗时持续恶化：** 09-25 傍晚 1:00:03 → 09-25 深夜 1:14–1:15 → 09-26 1:24。job 全长 ~90 分钟，高于多数并行 job 一个数量级，这是反复被人工取消/重跑的直接诱因（09-24 链两条 attempt 都在 40 分钟被取消；09-26 20:23 链在 55 分钟被 rerun 取消）。
2. **真实测试失败在累积后收敛：** 139 failed (09-25 19:16) → 86/88 (09-25 深夜) → 13 failed (09-26，两次 attempt 完全一致的 13 failed, 12989 passed)。**当前真正该修的是这 13 个红**（含 `test_struggle_signal_aggregator.py::test_compute_struggle_score_high_skip_rate_crosses_trigger_threshold`、`test_statistics_daily_alignment.py` 等），与任何冻结无关。
3. 任务书中"1 次全量通过 12889 passed"未能在近 60 个 run 中找到对应成功 job（近期唯一 success 列表里无 main 的 Backend Tests；最接近的实测数字是 12989 passed）。如实记录，不采信该数字为本次分析依据。

---

## 3. 假设检验

| 原假设 | 检验结果 | 证据 |
|---|---|---|
| H1：懒加载 import 中的 C 扩展（y_py/redis.asyncio）阻塞主线程导致冻结，thread 法超时无法中断 | **不支持** | (a) 本地 10/10 干净且总采样 55s；(b) CI 全部 9 个已终态 job 日志中 `+++ Timeout +++` 为 0——若 import 卡 >300s 必然留下该标志（pytest-timeout thread 法 = `faulthandler.dump_traceback_later(…, exit=True)`，其转储/硬退出在独立线程完成，**即使主线程卡在 C 层也会触发**，"C 层冻结令 thread 法失效"的前提本身不成立）；(c) 每个 cancelled job 取消瞬间 pytest 都在推进，从未在半路抓到静止进程 |
| H2：托管 runner 回收抖动（两次冻结均在 run 启动后 ~30min、进度 ~35%±5% 带） | **不支持（被更好的解释取代）** | "30min/~35%" 这个位置带在两份完整日志中恰好是 test_specialized_features.py 的真实执行位置（28m29s/36% 与 32m54s/37%），但它每次都在毫秒级通过；同位置带内另有 24%–67% 的多次取消，不符合"固定回收带"；且 09-26 20:23 链在 55 分钟、67% 处仍被 GitHub 正常服务（job 心跳、日志落盘、步骤状态全部正常），无回收迹象 |
| H3（新）：**观测失明误诊** —— in_progress 日志 API 返回 404/空 + 套件 84 分钟超长 + 人对慢任务取消/重跑，三者叠加造成"间歇性冻结"的叙事 | **支持，且观测失败模式已两次现场复现** | §2.1 关键否定证据 1–2 + §2.2 |

---

## 4. 建议按优先级

1. **不要改 `--timeout-method=signal`、不要拆 `test_specialized_features.py`、不要加 skip/标记。** 三者都是针对一个日志上不存在的行为开药。若仍想加固，唯一有意义的观测增强是：pytest-timeout 触发时（`+++ Timeout +++`）日志里本就自带全线程栈——保留现状即可，无需 signal 法（signal 法反而无法中断 C 层阻塞，方向是反的）。
2. **修冻结监测的观测面（真正的修复点）：** 判活用 Jobs API 的 `steps[]`（本报告多次用它确认 in_progress 步骤正常推进）或 webhook 的 `status` 事件，**不要用日志 blob 的有无/尾部时间戳判活**——in_progress 期间 blob 是 404。给舰队监控脚本加这条规则可一次性消除"假冻结"告警。
3. **治理真实痛点——套件时长：** 全量 84 分钟且在变慢。建议：分片（如 `tests/unit`、`tests/services`、contract/workflow 分 job 并行）、`pytest --durations=50` 找慢测试、评估 `-n auto`（pytest-xdist，需评估与 coverage/顺序依赖的兼容）。这同时把"取消重跑浪费 40–90 分钟"的代价降下来。
4. **修 13 个真实失败**（09-26 两次 attempt 结果完全一致，可稳定复现，归实际卡片处理，不属本工位）。
5. 若未来再次出现"疑似冻结"：立刻抓 **job steps API 快照**（证明步骤是否仍在推进）+ 等该 job 终态后拉日志核对最后输出时间与取消/失败时间差（<10s = 活着被取消）。GitHub runner 内可加一步 `pip install py-spy && py-spy dump --pid $(pgrep -f pytest)` 的事后取证步（仅诊断用，勿常驻）。

---

## 5. 证据清单

- 本地循环脚本与产物：`/tmp/wt572-cirepro/loop.sh`、`summary.txt`、`run_1..10.log`（git 不入库，符合"会话产物不入库"）
- CI 原始日志（已下载，9 份终态 job 全量/比对 + 1 份进行中 job 的 steps 快照）：`/tmp/wt572-cirepro/{frozen90m,attempt1_frozen,a1_90m,a0924_1,a0924_2}.log` 等
- 关键 API 查询：`runs/{id}/jobs`、`runs/{id}/attempts/{n}/jobs`、`jobs/{id}`（steps 快照）、`jobs/{id}/logs`
- 本报告不修改任何产品代码/测试/CI 配置；worktree 变更仅本文件。
