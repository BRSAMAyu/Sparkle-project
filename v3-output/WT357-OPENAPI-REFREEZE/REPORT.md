# WT357-OPENAPI-REFREEZE — OpenAPI 契约快照重冻结（机械卡）报告

- **base SHA**: `0484727b`（main @ 开工，已含 wt352 wvpl-fact 端点）
- **final SHA**: 分支 `wt357-openapi-refreeze`
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt357-openapi-refreeze`
- **唯一产品改动**: `docs/contracts/openapi_snapshot.json`（纯生成器产出，无任何手编）。零产品代码、零 API 形状、零 CI workflow 改动。

## 1. 导出口径考古（与 CI 完全一致，未自造）

| 事实 | 出处 |
|---|---|
| CI 校验命令 = `python3 scripts/check_openapi_contract.py` | `.github/workflows/ci.yml` `Backend Tests` job → `OpenAPI Contract Check` 步（ci.yml:290 附近） |
| CI 依赖的 workflow 级 env：`SECRET_KEY` / `JWT_SECRET` | ci.yml:19-22（该步自身无 env 块，靠全局兜底；本地预演按同值注入） |
| 校验机制：子进程重导出到 `quality/openapi_snapshot.generated.json`，与 `docs/contracts/openapi_snapshot.json` 做 **JSON 语义比对**（非文本比对，键序无关） | `scripts/check_openapi_contract.py` |
| 正规重冻结路径 = `python3 scripts/check_openapi_contract.py --update`（校验失败信息原话指引）≡ `python3 scripts/export_openapi_snapshot.py`（默认输出即快照路径） | `scripts/check_openapi_contract.py:39-45`、`scripts/export_openapi_snapshot.py` |
| 导出器口径：`app.main.app.openapi()` → 去 `servers`、schema 名去模块路径抖动、`$ref` 同步归一、全键排序 | `scripts/export_openapi_snapshot.py:_canonicalize` |
| 等价 Makefile 入口：`make openapi-contract-check` | `Makefile:218` |
| 解释器：worktree 无 `backend/.venv`，校验脚本回退 `sys.executable`；实际用主仓 `backend/.venv` Python 3.11.15（依赖齐备；CI 为系统 python3+装依赖，脚本逻辑完全一致） | `scripts/check_openapi_contract.py:_preferred_python` |

## 2. 红基线复现（"注定红"坐实）

main 上快照最后冻结于 `39045ad6`（2026-09-22 23:51 +0800），与 wt352 情报一致。在 worktree 以 CI 同款 env+命令预演：

```
SECRET_KEY=ci-workflow-default-secret-0123456789abcdef \
JWT_SECRET=ci-workflow-default-jwt-0123456789abcdef \
python3 scripts/check_openapi_contract.py
→ EXIT=1  "❌ OpenAPI contract drift detected."（12000 字符截断 diff，"Run: --update" 提示）
```

导入 app 未连接任何 PG/Redis（仅内存构造：LLM router 27 配置、circuit breaker、并发管理器；缺 api key 的 provider 打 INFO/ERROR 日志后跳过——与 CI 该步无 services 的运行形态一致）。

## 3. 重冻结与 diff 统计

执行 `python3 scripts/check_openapi_contract.py --update`（CI 指引的原生命令）。

| 指标 | 旧（39045ad6） | 新 | 变化 |
|---|---|---|---|
| paths | 500 | **884** | 净 +384（新增 390 / 移除 6） |
| components.schemas | 435 | 787 | +352 |
| git 行级 diff | — | — | **1 file changed, 62,658 insertions(+), 21,393 deletions(-)**（84,051 行级变化，8 万行级生成物刷新正常形态） |

新增 390 条与 wt352 情报 "~390 条路径漂移" 精确吻合。

## 4. 自检：diff 全是真实 API 面变化，非生成器噪声/排序漂移

抽样 5 处逐项核对（新旧两侧同用未改动的导出器 canonicalize——排序确定性由代码保证，且 CI 比对是 JSON 语义级，键序本就不影响判定）：

1. **`/api/v1/admin/north-star/wvpl-fact` 在新快照在列**：`GET`，summary="WVPL 北极星事实 JSON（frozen schema north_star.wvpl.fact.v1）"，responses 200/422，可选 query 参数 `as_of`——与 wt352 卡逐项一致。
2. **移除的 6 条全是双重前缀修复**（`/api/v1/audit/audit/avatars*` ×3、`/api/v1/chat/chat*` ×3），其单前缀去向（`/api/v1/audit/avatars`、`/api/v1/chat`、`/api/v1/chat/confirm`、`/api/v1/chat/stream` 等）全部在新快照在列。
3. **同路径方法集变化 2 处**：`/api/v1/community/groups/{group_id}/files` 增 `POST`；`.../moderation` 增 `GET`——真实 API 演进。
4. **新增整族端点**：`/api/v1/action-proposals`（GET+POST）及 `{proposal_id}/approve|reject|cancel|receipt|transitions` 等约 13 条——09-22 后合入的新 API 族。
5. **同路径同方法内容 diff 28 处**，抽查 2 处（achievements/contracts 的 POST/DELETE）均为 "R2-8 契约复审" 幂等头（`Idempotency-Key` header 参数）+描述补注——真实契约演进。

未发现任何导出器版本导致的无意义重排。

## 5. 本地预演：从注定红转绿

```
# 重冻结后，同一 env、同一命令：
SECRET_KEY=... JWT_SECRET=... python3 scripts/check_openapi_contract.py
→ EXIT=0  "✅ OpenAPI contract check passed"
```

证据链：ci.yml:290 步命令 + ci.yml:19-22 env → 本地同口径 EXIT=1（红基线，见 §2）→ `--update`（生成器产出唯一改动）→ 同口径 EXIT=0。main 后续前移 `22f99776`（wt353，已核对 `backend/`+`proto/` 零改动，纯 mobile 令牌），本快照对 main@22f99776 依然精确有效。

## 6. 验收门

| 门 | 结果 |
|---|---|
| `bash scripts/run_all_rule_guards.sh` | **exit 0，84 rules 全过**（worktree 需先 `cp -RL` 主仓三处 gen：`backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen`——首跑 BG 项因缺 Dart 生成物 FAIL，补齐后全绿，与 wt352 情报一致） |
| 冷 mypy（`cd backend && rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary \| grep -c 'error:'`） | **1278 = 基线 1278，零推高**（唯一改动为 JSON 快照，不动代码） |
| pytest | 未跑广域套件：本卡唯一改动是快照 JSON，无 DB-free 单测覆盖该产物；其权威验证即 §5 的 CI 同款脚本比对 + §6 守卫。LIGHT 约束（禁连本地 PG/Redis）全程遵守，两次导出/校验运行均未建 DB/Redis 连接 |

## 7. Forbidden 核对

- 未改任何产品代码/API 形状：`git diff main...HEAD` 仅含快照 JSON 与本交付目录。
- 未手编快照内容：唯一写入路径是 `check_openapi_contract.py --update`（生成器）。
- 未动 CI workflow：`.github/workflows/ci.yml` 零改动。
