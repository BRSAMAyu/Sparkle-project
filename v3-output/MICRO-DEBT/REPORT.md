# MICRO-DEBT 施工报告：两件微债

- Worker: wt106 ｜ 基线: main@db9e9fd8 ｜ 日期: 2026-09-22 ｜ 禁止 commit/push，未违反
- 产物: `v3-output/MICRO-DEBT/changes.patch`（3 文件，+150/−19）+ 本报告

---

## 件 1：e2e-tests.yml pytest 路径缺陷

### 红证（对照仓库布局证明路径错）

- `.github/workflows/e2e-tests.yml` 两处 `cd backend && pytest tests_e2e/`（原 L87、L308）。
- 仓库布局：`tests_e2e/`（含自己的 `pytest.ini` + `conftest.py`）在**仓库根**；`backend/tests_e2e` 不存在（`ls: tests_e2e: No such file or directory`）。
- 佐证：`Makefile.test:21` 的正确用法是仓库根直接 `pytest tests_e2e/`；conftest 自带 `sys.path` 注入 backend，任何 cwd 均可收集。

### 修法（一句）

两处改为 `cd backend && pytest ../tests_e2e/`——保持 cwd=backend，使同 workflow 内三个下游路径引用**零改动保持有效**：`--cov=app`（测 backend/app）、`--cov-report=xml` → `backend/coverage.xml`（codecov L97）、`--junitxml=test-results/python-e2e.xml` → `backend/test-results/`（artifact L107）。

### 该 workflow 其余路径引用核对（全部通过）

`./.github/actions/age-postgres`、`backend/requirements.lock`（×2）、`backend/scripts/init_age_extension.py`（×2）、`backend/gateway/go.mod`+`cmd/server/main.go`+`./internal/handler/...`、`mobile/integration_test/`、`backend/grpc_server.py`、alembic 调用——均存在且正确。

### 回归

- PyYAML `safe_load` 解析通过，5 jobs 完整；grep 确认两处 pytest 均已 `../tests_e2e/`，无残留直连。

---

## 件 2：S22 守卫读时重写反模式

### 红证（跑守卫前后 git diff 证明污染）

按 manifest 原样命令（`check_prompt_render_coverage.py --write`）跑一遍：
sha `79a1a959` → `77db20a5`，`git status` 出现 ` M docs/product/stage22_prompt_coverage_baseline.md`，diff 仅 `audited_at` 时间戳行（`1789894106.06...` → `1790081331.21...`）。根因双重：① `scripts/rule_guard_manifest.tsv:23` 给 S22-PROMPT 无条件挂 `--write`；② 脚本把 `audited_at` 记为文件自身 mtime，写入即变 mtime，故每次全量守卫必产生内容 diff。

### 修法（一句）

`scripts/check_prompt_render_coverage.py` 重构为 DL-SPEC 守卫同款纪律（参照 `scripts/guards/check_dl_spec_ratchet.py`）：默认**只读校验**——实时计算 13 字段状态与基线逐行比对（忽略 `audited_at` 行）、基线缺失/漂移/低于 `--min-ratio` 均 FAIL 并提示显式刷新命令、全程零写盘；仅 `--write` 显式落盘，且落盘前执行拒绝抬升检查（coverage 只许升：covered/ratio 将下降即 REFUSED exit 1，除非 `--allow-drop` 显式放行）；`audited_at` 改记写入时刻墙钟，只读跑不再触碰。配套 `rule_guard_manifest.tsv` 去除该条目的 `--write`。

### 验证证据（R1–R4）

| # | 验证 | 结果 |
|---|------|------|
| R1 | 默认只读连跑 2 遍 | 双 PASS（12/13, ratio=0.923），`git status` 基线文件零变更，sha 稳定 |
| R2 | `--write` 显式 | 才落盘（仅 `audited_at` 行更新 + `baseline updated: 12 -> covered=12/13`），随后已 `git checkout --` 还原 |
| R3a | 变异 prompts.py 去掉 `_mark_rendered("focus_stats")`（单文件粒度，已还原） | 默认只读 FAIL exit 1，逐项报 `focus_stats: baseline=covered live=missing` + `ratio 0.846 < min-ratio 0.85`，基线未被改动 |
| R3b | 同变异下 `--write` | `REFUSED — would LOWER coverage (covered 12 -> 11, ratio 0.923 -> 0.846)` exit 1，落盘被拒（docs/product 零变更） |
| R3c | `--write --allow-drop` | 才放行落盘；随后基线与 prompts.py 均已还原，`git status` 回到仅 3 个预期变更 |
| R4 | 风格 | `ruff check` 0 违例；`black --check --line-length 120` 通过；py_compile 通过 |

---

## 全量守卫绿证明（74 规则）

- `bash scripts/run_all_rule_guards.sh --jobs 4`：74 规则中 **72 绿**；失败集 = `{AQ, BG}`。
- **等价性铁证**：以 `git clone` 在 `/tmp/wt106-microdebt-baseline` 建干净 HEAD（db9e9fd8）基线克隆并全量跑——失败集同为 `{AQ, BG}`，逐条错误一致。即本卡改动**零回归**，「仍绿」成立。
- AQ/BG 失败原因：本 worktree 无 proto-gen 生成产物（`app.gen` python 模块、`websocket.pb.go`/`websocket_pb2.py`/Dart `websocket.pb.*.dart` 缺失）——**既有环境债，非本卡引入**，修法是 worktree 内 `make proto-gen`（超出本卡范围，未动）。关键验收点：全量守卫整轮跑完，`git status` 始终只有 3 个预期变更，基线文件零污染（旧版下每轮必脏）。

---

## 收工核查

- [x] 进程：未起任何服务/模拟器/长驻进程
- [x] 构建产物：无（未跑 flutter/gradle/构建）
- [x] `/tmp` 自清：`/tmp/wt106-microdebt-baseline` 已删除
- [x] 主仓只读：全程未写主仓（守卫对照一律在 worktree/克隆内进行）
- [x] 变异实验：仅单文件粒度（prompts.py、基线 md），逐一 `git checkout --` 还原并核验
- [x] 最终 `git status --short`：仅 `.github/workflows/e2e-tests.yml`、`scripts/check_prompt_render_coverage.py`、`scripts/rule_guard_manifest.tsv` 三个预期变更

## 顺带发现（未修，超出本卡范围，供 Leader 立卡）

1. **Makefile.test 同款路径缺陷**：L96/L142/L174/L184 四处 `cd backend && pytest tests_e2e/`（`tests_e2e` 不在 backend 下）；L21/L33 的根目录用法正确。
2. **AQ/BG 生成产物债**：`*/gen/` 产物不入库，worktree 类本地环境需先 `make proto-gen` 才能本地 74/74 全绿；CI 无此问题（`ci-pr.yml:67`、`ci.yml:46` 等均先跑 `make proto-tools-build && make proto-gen` 再执行检查）。
