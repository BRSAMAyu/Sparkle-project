# WT352-WVPL-ENDPOINT — G7 WVPL 北极星只读暴露端点 报告

- **base SHA**: `178a6c6e`（main @ 开工时）
- **final SHA**: 分支 `wt352-wvpl-endpoint`
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt352-wvpl-endpoint`
- **差距依据**: `v3-output/WT347-VISION-GAP/REPORT.md` G7——WVPL（Weekly Valuable Progress Loops，METRIC_TREE North Star）有 frozen schema（`backend/app/core/north_star_wvpl.py`，`north_star.wvpl.fact.v1` + 口径 `wvpl.caliber.v1`）+ golden sha256 冻结（`backend/tests/golden/`）+ 每日 worker（`backend/app/workers/cost_wvpl_worker.py`），但 **api/v1 全目录 grep wvpl=0 命中**，评审无法查询分母/loops/分工分布。

## 交付物

| 文件 | 内容 |
|---|---|
| `backend/app/api/v1/north_star_wvpl.py`（新增） | `GET /api/v1/admin/north-star/wvpl-fact`：handler 只做参数解析，直接返回 `NorthStarWvplService.build_fact` 的事实 JSON dict——响应形状 = frozen schema，零后处理、不发明第二套 schema；认证/权限沿同族 admin 端点惯例（router 级 `dependencies=[Depends(get_current_active_superuser)]`，`memory_admin`/`admin_dashboard` 同款）；可选 `as_of` 查询参数透传为幂等锚点（同 as_of + 同库态 → 逐字节相同 JSON）；每条路由带 `# route-tier: internal`（Rule AX）。 |
| `backend/app/api/v1/router.py` | import + `api_router.include_router(north_star_wvpl.router)`（前缀在 router 自带，`memory_admin` 之后的 admin 区段）。 |
| `backend/tests/unit/test_north_star_wvpl_api.py`（新增） | 3 测试：①非 superuser 403（权限链生效）；②空库/未初始化态诚实返回——零计数 + None 比率 + 空 samples + frozen schema/caliber 标识在位（不造假数据，分母 0 不伪造比率是 frozen 口径的一部分）；③happy path——固定 fixture（与 golden 共享单份事实源）下端点响应与 frozen 口径服务产出逐字段一致，且 seed cohort 不混入生产数字（loops_total=2 非 3，excluded_users>0）。 |

## 关键设计事实

- **网关侧零改动**（卡面"最小注册"上限的更优解）：`backend/gateway/internal/handler/proxy_routes.go` 已有 `/api/v1/admin` catch-all 代理组（`authMiddleware + RequireAdmin` → Python 引擎，引擎侧 superuser 二次校验保留，分层边界不破），新路径自动透传，未碰任何 Go 文件。
- **分层**：handler → `NorthStarWvplService`（既有 frozen 服务，未改一行）；只读，无写路径，无 schema 变更，无迁移。
- **空态语义来自服务本身**：`wvpl_ratio`/`loops_per_wvpl_user` 分母 0 → None（frozen 口径 "no fabricated ratio"），端点不加默认值。

## OpenAPI 快照——发现预存漂移，本卡不吞（需主会话拍板）

卡面要求同步刷新 `docs/contracts/openapi_snapshot.json`。实测发现：**main 上快照自 09-22（`39045ad6`）冻结后已落后 app 约 390 条路径**（含 action-proposals/admin dashboard/memory admin killswitch 等整族；另有 6 条已删路径仍在快照、components 漂移）。整体重导出 = 84,451 行 diff（62,658+/21,393−），会把全部在航/已合卡的端点漂移吞进本卡 patch，与 §5 合并管线（--3way）高风险冲突。

处置：本卡**还原快照至 main 原态，未提交重导出**。建议独立一张机械卡在合并窗口做全量 re-freeze：`SECRET_KEY=<占位> DATABASE_URL="sqlite+aiosqlite:///:memory:" backend/.venv/bin/python scripts/export_openapi_snapshot.py`（worktree 根执行，产物仅此一文件）。附带情报：CI `Backend Tests` job 含 `OpenAPI Contract Check` 步（ci.yml:290），**当前 main 该步注定红**（与 wt326/327 无关的预存阻塞）——run 36015155771 的 Backend Tests 两次中段被取消未跑到此步，故此前未暴露。

## 测试证据（全部 DATABASE_URL="sqlite+aiosqlite:///:memory:"，backend/.venv）

| 批次 | 文件 | 结果 |
|---|---|---|
| 本卡测试 | `tests/unit/test_north_star_wvpl_api.py` | **3 passed** |
| golden 回归 | `tests/golden/test_north_star_wvpl_golden.py` | **3 passed**（frozen sha256 未动） |

## 验收门

| 门 | 结果 |
|---|---|
| `bash scripts/run_all_rule_guards.sh` | **exit 0（83 条全过）**（需先 cp -RL 主仓 backend/gateway/mobile 三处 gen 进 worktree，BG 假失败消除） |
| 冷 mypy（`rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary \| grep -c 'error:'`） | **1278 = 基线 1278，零推高**；新文件 `north_star_wvpl.py` 零错误 |
| ruff + black(120) | touched 文件全过 |

## 战区回避确认

未碰 galaxy / chat_mode / growth dashboard / goal 链；未做 UI（mobile 消费面是后续卡）；未扩 schema（frozen 即权威）；无造假数据。/tmp 自产（guards 日志、snapshot 对照件）收工清理。

## 交接

- 评委可见路径：`GET /api/v1/admin/north-star/wvpl-fact`（superuser JWT；经网关 `/api/v1/admin` 代理组透传）。
- 后续消费卡可用 `as_of` 参数做逐字节可复现的评审取证；解释层（LLM 消费事实 JSON）不在本卡。
- OpenAPI re-freeze 卡建议尽快排（附情报：它同时是 Backend Tests job 的预存红灯）。
