# WT351-GUARD-GOFMT 报告

工号 wt351 ｜ 卡面：守卫网自愈——补 gateway gofmt/golangci 规则 ｜ 2026-09-25
分支 `wt351-guard-gofmt`（基于 main @ 178a6c6e）

## 交付物

| 文件 | 说明 |
| --- | --- |
| `scripts/guards/check_gateway_gofmt.py` | 新守卫：`gofmt -l` 全目录扫 `backend/gateway`，非空即败、逐文件列出、给 remediation（`gofmt -w backend/gateway`） |
| `scripts/rule_guard_manifest.tsv` | 注册新规则 `GOFMT-GW`（置于 gateway 相关的 BA-ROUTES 旁），83→84 |

无任何产品代码变更，无 CI workflow 变更，守卫脚本结构零重构（最小增量：1 脚本 + 1 清单行）。

## 规则设计（GOFMT-GW）

- **语义**：对 `backend/gateway` 整树跑 `gofmt -l`，输出非空即败。**无基线、全目录**——这是对 CI 的刻意加严，不是镜像。
- **事故闭环**：CI run 36080561418 死于 lint 首关（`s2_ticket_budget_repro_test.go` gofmt 不规范，d680a891 已修）。本地 83 条守卫当时零 Go 格式检查。本地守卫的职责是提前拦：CI golangci-lint 带 `new-from-rev: e6256a3` 基线（见 `backend/gateway/.golangci.yml`），旧文件/触碰旧代码的格式漂移 CI 根本不拦，本地全目录扫正好补位。
- **排除项与 CI 对齐**：`*.pb.go`、`vendor/`、`mocks/`（镜像 `.golangci.yml` 的 exclude 语义）。
- **fail-closed**：gofmt 不在 PATH 即败（明示装 Go），绝不静默绿。
- **命名**：沿 `DB-HEAD`/`GOV-DATA-MIN`/`N37-TIMEOUT` 的描述式惯例。
- docstring 完整记录事故、设计理由与已知局限（gofmt 不跳 testdata——当前 gateway 无 testdata 目录，如未来出现故意坏格式的 fixture 需显式豁免，可审）。

## golangci-lint 取舍（按卡面 fallback 执行：只 gofmt）

本地有 golangci-lint（`/Users/brsama/go/bin/golangci-lint`），但 **CI 等价性不可保证**，取证：

- CI 用 `golangci/golangci-lint-action@v6` + `version: latest`（floating，v2.x 系）；本地实测 **v1.64.8**。跨大版本，config schema 与 finding 集都不同。
- CI 结果依赖 git history（`new-from-rev` 基线），本地分支/worktree 跑出来的结果不可复现 CI。
- 结论：纳入本地守卫 = 制造版本漂移型假红/假绿。gofmt 是稳定确定性子集，本地拦格式；golangci 其余项由 CI 兜底。已在守卫 docstring 记录。

## 自验证据（红→绿→全量）

1. **启用前提**：当前 gateway 树 229 个 .go 文件 `gofmt -l` 零输出（全绿基线，启用不会立红）。
2. **单规则绿**：`run_all_rule_guards.sh --rule GOFMT-GW` → PASS exit 0。
3. **红**：向 `internal/middleware/` 投放未格式化探针文件（`wt351_gofmt_probe_test_helper.go`）→ 规则 FAIL exit 1，输出逐字列出该文件并给 `gofmt -w` remediation。
4. **绿**：删除探针（探针文件与 `/tmp` 伴生文件均已删，`git status` 干净）→ 复绿 exit 0。
5. **全量**：`bash scripts/run_all_rule_guards.sh` → **exit 0，`all rule guards passed (84 rules)`**（83→84 达成，守卫日志 `--list` 亦 84 行）。
6. **mypy**：未动 `backend/`（`git status` 仅 2 个守卫文件），冷 mypy 计数天然不变 ≤1278，按协议免跑。

## 排查报告（只报告，未扩卡）

1. **gateway 本地/CI 检查盲区清单**：守卫清单里 gateway 相关只有 Python 脚本型契约/路由 parity（BA、BA-ROUTES）+ 本卡的 GOFMT-GW。`go build` / `go vet` / `go test ./...` 均为 **CI-only，本地守卫零覆盖**——即 Go 侧"编译不过/测试红"只能等 CI。实测当前 `go vet ./...` 在 worktree 干净（exit 0），若后续想补本地 vet 守卫，今天补是零成本立绿的，收益是本地预检提前于 CI（建议开卡，不贪）。
2. **CI 侧 golangci 版本风险（非本卡）**：CI floating `latest`（v2.x）配 v1 schema 的 `.golangci.yml`，action 升级窗口存在 config 兼容风险；本地 v1.64.8 与之漂移。属 CI 治理议题，记录不处理。
3. **环境隐患（值得舰队周知）**：gitignored 的生成产物树（`backend/app/gen` 等）在主仓检出里含**绝对符号链接**（至少 `backend/app/gen/proto/error_book/*` 指回主仓路径）。任何新鲜 worktree/clone 直接 `cp -R` 复制产物后，`path.resolve()` 型守卫（本卡实测 K、Z 崩溃：ValueError 路径逃出仓库）会假红。worktree 跑全量守卫须用 `cp -RL` 解引用拷贝，或上游改为真生成。本次验证即用 `cp -RL` 修复后达成 84 全绿。另：新鲜 worktree 缺 proto 生成产物时 AQ、BG 天然红（生成物不入库所致，环境性既有失败，非回归）。

## 禁区确认

未改任何产品代码；未动 CI workflow；未重构守卫脚本结构。唯一改动 = 1 个新守卫脚本 + 1 行清单注册 + 本报告与 patch。
