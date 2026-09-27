# §9 度量快照补全 —— 代码规模 / 模块依赖图 / 测试覆盖分布 / FIX 台账统计（wt780）

> **用途**：补 [V3-COMPLETE-STATUS-FOR-V4.md](../../V3-COMPLETE-STATUS-FOR-V4.md) §9「⏳ v0.2 补：代码规模统计、模块依赖图、测试覆盖分布」与 §5 第 7 条「⏳ v0.2 将补：完整族谱分布统计（P1-P4 数量、按模块热点图）」。可直接引用本文数字，或按 §5 建议文本回填交接文档。
>
> **测量基线**：分支 `agent/node-b/wt780/metrics`（基于 `main`@`9a4ea3d4e201518a02ec940cd3355491b160d955`），独立 worktree，主仓只读。测量时点 2026-09-28 03:00–04:00（本机 macOS arm64）。
> **工具口径**：Python 3.11.15 + pytest 9.0.2（主仓 venv）；Go 1.25.7；全部数字为本机实测（`git ls-files`+`wc` / AST import 扫描 / `pytest --collect-only` / Python 解析台账），零引用旧报告。

---

## 1. 代码规模统计（git ls-files + wc 实测）

| 侧 | 范围（tracked 文件口径） | 文件数 | 行数 | 测试文件数 | 测试行数 |
|---|---|---:|---:|---:|---:|
| **backend（Python）** | `backend/**/*.py`（排除 `backend/gateway/`） | 3,169 | 960,611 | 1,443¹ | — |
| ├ 其中生产 `backend/app/`（排除 `gen/`） | `backend/app/**/*.py` | 1,356 | 532,979 | 0（生产码） | — |
| ├ 其中 `backend/tests/` | 全部 .py（1,401 个为 pytest 命名可收集） | 1,490 | 383,465 | 1,401 | — |
| ├ 其中 backend 根散置 `test_*.py` | dev 脚本（`testpaths=["tests"]` 之外，不进收集） | 42 | — | 42 | — |
| **gateway（Go）** | `backend/gateway/**/*.go`（tracked 247，其中生成 1） | 246（非生成） | 64,241 | 141（`*_test.go`） | 26,550 |
| └ └ 生产面 | 非 gen 非 test | 105 | 37,691 | — | — |
| **mobile（Dart）** | `mobile/**/*.dart`（tracked 2,098） | — | — | — | — |
| ├ 排除 vendored `third_party_plugins/`（311 文件 / 117,322 行，fork 不计本仓产出） | | 1,787 | 720,965 | — | — |
| ├ 排除生成物（`*.g.dart`/`*.freezed.dart` 57 文件 / 37,655 行） | **手写口径** | **1,730** | **683,310** | **518²** | 110,355 |
| └ 其中生产 `mobile/lib/` | 手写 | 1,187 | 564,295 | — | — |

¹ backend 测试命名文件 1,443 = `backend/tests/` 1,401 + 根散置 dev 脚本 42。
² mobile 测试文件 = `mobile/test/**` + `mobile/integration_test/**` 下 `*_test.dart`，仅手写口径。

**一句话**：手写生产代码约 **113.5 万行**（backend/app 53.3 万 + gateway 3.8 万 + mobile/lib 56.4 万），测试资产 1,443(py 命名)+141(go)+518(dart) 文件，覆盖测试代码合计约 **50 万行**（backend/tests 38.3 万 + gateway 测试 2.7 万 + mobile 测试 11.0 万）。

---

## 2. 模块依赖图（backend/app 顶层包 import 扫描）

**方法论**：对 `backend/app` 全部 1,356 个 .py（排除 `gen/`）做 AST 级 import 扫描（`import` / `from … import` / 相对导入按包语义解析；`__init__.py` 的相对导入按其自身包归属），映射到顶层包粒度，统计「有 ≥1 条跨包 import 的文件数」作为边权。0 个解析失败。

**规模**：35 个顶层包/模块，**192 条跨包依赖边**，其中 **34 对双向依赖**。

### 2.1 包体量（文件数 / 行数，降序）

| 包 | 文件 | 行数 | 包 | 文件 | 行数 |
|---|---:|---:|---|---:|---:|
| services | 546 | 233,061 | workers | 6 | 1,049 |
| orchestration | 96 | 72,256 | sprint_packs | 4 | 745 |
| api | 128 | 50,228 | semantic | 2 | 642 |
| core | 101 | 42,701 | db | 6 | 632 |
| aurora | 80 | 35,998 | checkpoint | 2 | 522 |
| signals | 73 | 34,175 | task_assistant | 6 | 492 |
| agents | 28 | 13,994 | working_memory | 3 | 426 |
| models | 112 | 13,104 | scaffolding | 4 | 388 |
| schemas | 42 | 8,653 | consumers | 8 | 388 |
| tools | 23 | 7,114 | utils | 4 | 385 |
| learning | 21 | 3,502 | causal | 3 | 326 |
| data | 5 | 2,858 | scenario_packs | 4 | 305 |
| config | 5 | 1,887 | visualization | 3 | 270 |
| tasks | 10 | 1,680 | middleware | 1 | 261 |
| state_aggregator | 3 | 1,628 | profile | 2 | 238 |
| adapters | 7 | 1,540 | task_guidance | 3 | 121 |
| routing | 10 | 1,368 | event_publishers | 1 | 39 |
| 根模块（main.py 等 4 个） | 4 | 1,359 | | | |

### 2.2 依赖重心（边权=引用文件数）

**被依赖最多（in-degree top6）**：core 523 ｜ models 505 ｜ services 213 ｜ config 195 ｜ db 140 ｜ schemas 122
**依赖最多（out-degree top6）**：services 954 ｜ api 451 ｜ orchestration 159 ｜ core 86 ｜ aurora 67 ｜ agents 50

**最重 10 条边**：

```
services → core 314        services → models 310      api → models 105
api → services 99          services → config 99       api → core 71
services → schemas 71      api → db 51                orchestration → core 49
api → schemas 40
```

**粗粒度分层读法**（V4 设计者视角）：

```
api(128) ──────────────┐
orchestration(96) ─────┼─→ services(546) ─→ core(101) ←─ models(112) ←─ db(6)
agents(28) tools(23) ──┘        │              ↑
aurora(80) signals(73) ─────────┘        config(5，被 195 文件引用)
```

- `core`/`models`/`config`/`db`/`schemas` 是全系统地基（in-degree 全部 ≥122）；`services` 是巨型业务汇聚层（546 文件、out-degree 954、约 57% 文件直接 import core）。
- **双向依赖 34 对**（包级互依，非分层严格单向）：最重的前几对——core↔services（14/314）、schemas↔services（2/71）、orchestration↔services（32/33）、core↔orchestration（3/49）、aurora↔services（12/17）、core↔models（19/6）。即 `services` 与地基层之间存在成环的静态依赖，V4 若做分层治理，这些是首批解环对象。

### 2.3 方法论与局限（引用时必须带上）

- 粗粒度静态 import 扫描：只测「文件是否 import 了某顶层包」，**不等于**运行时调用强度、不区分轻重依赖（类型引用与真实调用同权）。
- 动态导入（`importlib`/字符串拼接）、monkey-patch、事件总线等隐式耦合不在图内；`from app.X import Y` 的子模块归属按 X 顶层包计。
- `app/gen/`（proto 生成物）排除；gen 排除后 0 解析错误，扫描对源码只读。
- 边权去重到文件级：同一文件 import 同一包 10 次只计 1。

---

## 3. 测试覆盖分布（pytest --collect-only 分目录实测）

**口径**：`pytest tests --collect-only -q`（backend 目录，`-o addopts=""` 清除继承的 `-v`）。环境=CI 同款公开 workflow 默认值（`ci.yml` env 的 `SECRET_KEY`/`JWT_SECRET`，非真实凭据）；worktree 无 `.env`，TEST-DBGUARD 打印提示横幅不拦截。**collect-only 为静态收集，不触碰任何数据库**；套件运行期 fixture 默认库=sqlite 内存（`backend/tests/conftest.py:116` `TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"`），符合 sqlite 内存口径。
**测量卫生注**：首次收集因 worktree 缺 `backend/app/gen/`（未入库 proto 产物）得到 11,619 收集 + **250 收集错误**（全部 `ModuleNotFoundError: app.gen.*`）；按台账先例（FIX-147 行注记）从主仓 `cp -RL backend/app/gen` 后复测。**worktree 测量必须带 gen，否则收集数失真**。

### 3.1 backend/tests：13,799 用例，0 收集错误

| 子目录 | 用例数 | 子目录 | 用例数 |
|---|---:|---|---:|
| **unit/** | **9,763** | e2e/ | 35 |
| （tests 根散置文件） | 525 | tools/ | 33 |
| services/ | 996 | v3_scenario_eval/ | 27 |
| api/ | 454 | ai_face_eval/ | 25 |
| aurora/ | 406 | phase5/ | 25 |
| core/ | 332 | load/ | 24 |
| contract/ | 304 | chaos/ | 21 |
| integration/ | 284 | context_eval/ | 17 |
| orchestration/ | 208 | test_api/ | 15 |
| benchmark/ | 88 | v3_action_eval/ | 12 |
| security/ | 84 | golden/ | 11 |
| northstar_eval/ | 66 | q04_personal_redteam/ | 10 |
| profile/ | 9 | memory_eval/ | 7 |
| agents/ | 5 | schemas/ | 4 |
| test_e2e/ | 4 | workflow/ | 4 |
| performance/ | 1 | | |

分布形态：unit 单层占 70.8%（9,763/13,799），评估/验收型目录（northstar_eval、context_eval、ai_face_eval、v3_*_eval、q04_redteam、memory_eval 等）合计约 160——与「多数卡 headless/单测级证据」的交接文档 §8 表述一致。

### 3.2 其余套件

| 套件 | 实测 | 口径 |
|---|---|---|
| `tests_e2e/`（根，独立 rootdir） | **36 收集 + 1 收集错误** | `pytest ../tests_e2e --collect-only`。错误=`test_galaxy_e2e.py` import `app.services.rag_service` 已不存在（ModuleNotFoundError）——**模块删除后 E2E 未跟进的存量断链，V4 应修或删** |
| `v3/tests/` | 4 | 同法（test_pack.py） |
| `scripts/tests/` | 30 | 同法（O-05 恢复一致性/UX 约定/BGM 策展 3 文件） |
| gateway（Go） | **746 个 Test 函数**（141 个 `*_test.go`） | 静态 grep `^func Test`（`go test -list` 需 gateway `gen/` proto 产物，worktree 未生成，故用静态口径；744 个带 `t *testing.T` 签名） |
| mobile（Flutter） | **2,628 个测试调用**（testWidgets 1,130 + test 1,498） | 静态 grep `mobile/test` + `mobile/integration_test`（flutter 无 collect-only；与交接文档 §6 「2,636 用例」同量级互证，差值=group 包裹/参数化计数口径） |

**总貌**：Python 收集面 13,799+36+34=**13,869**（含 1 条 e2e 收集错误）；Go 746 函数；Dart 2,628 调用。collect-only 数≠通过数：本测量不含任何运行结果，运行态以 CI 与各卡 review receipt 为准。

---

## 4. FIX 台账统计（v3/06_agent_fleet/DYNAMIC_ISSUES.md，Python 逐行解析）

**台账规模（本机实测@main 9a4ea3d4）**：文件 **396 行**，数据行 **351 条**（`| V3-FIX-NNN |` 表行），ID 覆盖 V3-FIX-001→**511**（号段有跳号，351 个 ID 无重复）。
> 交接文档 v0.5 头部写「台账 339 行」、§5 写「V3-FIX-001→497（493 已 FIXED）」——**493 是 ID 非数量**；且台账在 v0.5 写作后仍在增长（339→396 行）。引用本文数字为准。

### 4.1 状态分布（按行尾状态格的最后一个状态 token 分类）

| 状态 | 行数 | 占比 |
|---|---:|---:|
| **FIXED**（含 FIXED@SHA / FIXED@wt 指针） | **276** | 78.6% |
| **OPEN**（含 `OPEN [wt474分诊:…]` 三态标注） | **71** | 20.2% |
| CLOSED@（替代指针闭合，FIX-16/45/47） | 3 | 0.9% |
| WONTFIX | 1 | 0.3% |

闭合合计（FIXED+CLOSED+WONTFIX）= **280 / 79.8%**。

### 4.2 P 级 × 状态矩阵（§5 族谱分布统计的补全项）

| P 级 | 总数 | FIXED | OPEN | CLOSED | WONTFIX | 闭合率 |
|---|---:|---:|---:|---:|---:|---:|
| **P0** | 5 | 5 | 0 | 0 | 0 | 100% |
| **P1** | 28 | 27 | 1 | 0 | 0 | 96.4% |
| **P2** | 98 | 83 | 13 | 1 | 1 | 85.7% |
| **P3** | 156 | 110 | 44 | 2 | 0 | 71.8% |
| **P4** | 64 | 51 | 13 | 0 | 0 | 79.7% |
| 合计 | **351** | **276** | **71** | **3** | **1** | 79.8% |

- 严重度呈**底重金字塔**：P3 占 44.4%、P2 占 27.9%——V3 的缺陷主体是长尾低危面，高危面（P0×5、P1×28）处置纪律严格（P0 全闭，P1 仅剩 FIX-53 一条 OPEN）。
- **唯一 OPEN P1 = V3-FIX-53**（值得 V4 交接关注的第一顺位）。

### 4.3 按模块热点 top10（显式代码路径引用口径）

方法论：统计每条 FIX 行中显式出现的 `app/<包>/` 前缀、`*.py` 文件名（经 backend/app 文件名→包反查）、`*.go`、`*.dart` 引用，按行去重计数。351 行中 248 行（70.7%）有显式引用，103 行为纯描述性登记。

| 排名 | 模块 | 被引用行数 | | 排名 | 模块 | 被引用行数 |
|---:|---|---:|---|---:|---|---:|
| 1 | app/services | 90 | | 6 | app/core | 32 |
| 2 | mobile（.dart） | 68 | | 7 | gateway（.go） | 31 |
| 3 | app/models | 45 | | 8 | app/agents | 18 |
| 4 | app/orchestration | 45 | | 9 | app/aurora | 15 |
| 5 | app/api | 36 | | 10 | app/config | 14 |

热点与 §2 依赖重心高度吻合：`services` 既是最大包也是缺陷最密面（其 546 文件承载 90 行 FIX 引用，密度并不异常），`models`/`orchestration`/`api` 次之；跨端缺陷（mobile 68 + gateway 31 = 99 行）接近 backend 单包最大值，印证三层链路的联合修复是 V3 常态成本。

### 4.4 台账数据质量注记（V4 沿用台账前必读）

- 行尾状态格存在四例**替代闭合形态**（`CLOSED@E05X+LIVE`、`CLOSED@d98a70c1`、`CLOSED@f9df4a5a` + WONTFIX），统计脚本须一并识别，否则 OPEN 被高估 4 行。
- 台账自曝过三类行损毁：FIX-258 行重建回退、FIX-491/492/493 跨批合并丢闭账（FIX-508 实锤）、FIX-504 同族——**台账行会腐烂，以主干 SHA 为准**的纪律（§5 零假账）必须延续。
- `OPEN [wt474分诊:备忘型/可派发/待拍板]` 三态标注已在行内，V4 消化 71 条 OPEN 时可直接按分诊字段分桶（备忘型占比高，真待办少于表面数字）。

---

## 5. 回填交接文档的建议文本

**§9 末行（替换 `⏳ v0.2 补：代码规模统计、模块依赖图、测试覆盖分布`）**：

```
- 代码规模（wt780 实测@9a4ea3d4）：手写生产 ~113.5 万行——backend/app 1,356 文件/53.3 万行、gateway 生产 105 文件/3.8 万行、mobile/lib 1,187 文件/56.4 万行；测试资产 backend 1,443+gateway 141+mobile 518 文件（详 v3-output/WT780-METRICS/metrics.md）
- 模块依赖（AST import 扫描）：35 顶层包/192 边/34 对双向；地基=in-degree core 523、models 505、config 195；汇聚层 services out-degree 954（与 core 成最重双向对 14/314）——V4 分层治理首批解环对象
- 测试分布（collect-only，sqlite 内存口径，0 收集错误）：backend/tests 13,799（unit 占 70.8%）+tests_e2e 36+scripts/v3 34；gateway 746 Test 函数（静态）；flutter 2,628 调用（静态）；tests_e2e/test_galaxy_e2e.py 存在死 import（app.services.rag_service）收集即红——V4 待修
```

**§5 第 7 条（替换 `⏳ v0.2 将补：完整族谱分布统计…`）**：

```
7. 族谱分布统计（wt780 实测）：351 行台账（ID 1→511）——FIXED 276（78.6%）/OPEN 71（20.2%）/CLOSED 3/WONTFIX 1；P0 5/5 全闭、P1 27/28（唯一 OPEN=P1 FIX-53）、P2 83/98、P3 110/156、P4 51/64——底重金字塔（P3 占 44%），高危处置纪律严格。模块热点 top10：services 90、mobile 68、models/orchestration 各 45、api 36、core 32、gateway 31（详 v3-output/WT780-METRICS/metrics.md §4）
```

---

## 6. 本测量的诚实边界

1. **collect-only ≠ 通过**：第 3 节全部数字是静态收集数，无任何运行/通过断言；运行态证据仍以 CI 与各卡 receipt 为准。
2. **gen 依赖**：backend 收集依赖从主仓复制的未入库 `backend/app/gen/`（台账先例同款操作，只读主仓）；gateway 因同因未做 `go test -list`，用静态 grep 口径并已标注。
3. **测试环境变量**：使用 ci.yml 内已提交的 workflow 默认 `SECRET_KEY`/`JWT_SECRET`（公开非密）；worktree 无 .env，无任何真实凭据参与。
4. **静态计数的口径差**：Go「746 Test 函数」与 Dart「2,628 调用」与运行数（子测试/参数化展开后）必然有差，已标注口径；不可与「12.3k/692/2636 用例」类运行口径直接混比——backend 13,799 是收集口径，交接文档 §6 的 12.3k 是 CI 裁决口径，方向一致（13,799 收集 ≥ 12,340 通过+修复轮变动），差值主要是 e2e 标记跳过与历史修复轮增删。
5. **依赖图局限**见 §2.3；台账解析的状态分类规则与四例替代闭合注记见 §4.1/§4.4。
6. 本文所有数字可在同基线复算：脚本内联于本 worktree 会话（未入库，符合一次性脚本治理），复算命令与口径已在上文完整给出。
