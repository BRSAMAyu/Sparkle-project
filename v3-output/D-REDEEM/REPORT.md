# D-REDEEM · 兑换码付费闭环（参赛演示级）REPORT

> Worktree: `wt108`（基于 `main@4d0ec81c`）｜ 2026-09-22 ｜ Worker 交付
> 产物：`v3-output/D-REDEEM/changes.patch`（31 files）+ 本报告

---

## 0. 一句话方案（回执①）

**表结构**：新表 `redeem_codes`（`code_hash` 唯一键存归一化明文的域分隔
SHA-256（`sparkle_redeem.v1:<CODE>`），明文/可逆形态永不落库；`tier /
duration_days / max_uses / used_count / used_by / used_at / created_by /
batch_id / expires_at`）+ `users.entitlement_expires_at`（TIMESTAMP NULL，
NULL=永久）。
**核销原子性**：条件 UPDATE（`UPDATE redeem_codes SET used_count =
used_count+1 ... WHERE id=:id AND used_count < max_uses`）在行锁下串行化，
`rowcount==1` 即核销成功——并发同码恰成功 `max_uses` 次，先读后写不存在；
8 并发同码测试实测 1 成功 7 exhausted。

## 1. 交付面（触达 31 文件，回执②）

### 引擎（backend/app）
| 文件 | 变更 |
|---|---|
| `alembic/versions/rd01_20260922_redeem_codes.py` | 新迁移（挂当前唯一头 `x07_20260921`；建表 + users 新列，可逆，sqlite 可隔离重放） |
| `models/redeem_code.py`（新） | RedeemCode 模型（SoftDeleteMixin，BaseModel 标准列） |
| `models/user.py` | `entitlement_expires_at` 列（NULL=永久） |
| `models/__init__.py` | RedeemCode 登记 |
| `core/entitlement.py` | `entitlement_effective` / `entitlement_effective_grants_pro`：到期降级判级（降级方向恒 pro→free，与「宁降不升」同向）；存量语义零变化 |
| `schemas/redeem.py`（新） | RedeemRequest/Response、BatchCreate（tier 封闭为 pro、count≤200、max_uses≤500、duration≤3650d 防呆） |
| `services/redeem_service.py`（新） | 生成批次（CSPRNG、码面 `SPARK-XXXX-XXXX-XXXX`、哈希冲突自动重生成）+ 原子核销 + 叠加授予 + 批次摘要 |
| `api/v1/redeem.py`（新） | `POST /api/v1/billing/redeem`（user 面，404/409/410 业务映射）+ `POST /api/v1/billing/redeem-codes`（admin 面：`get_current_active_superuser` + `@audit_admin_action(billing/high)`；同 batch_id 幂等 409） |
| `api/v1/router.py` | billing 路由登记 |
| `services/user_service.py` / `services/agent_run_service.py` | 既有两处 entitlement 读点改走 effective 判级（is_pro 派生、O-07 run 预算派生）——到期后自动落 free 档 |

### 网关（backend/gateway）
| 文件 | 变更 |
|---|---|
| `internal/db/schema.sql` + `query.sql.go` + `models.go` | `make db-dump`（throwaway fresh-migration 库，未触碰共享 dev 库版本表）+ `sqlc generate` 重生 |
| `internal/service/user_context.go` | 新 `IsProEntitlementEffective(entitlement, expiresAt)`（与引擎同语义，双侧同步义务已注释）；`GetChatUserProfileSnapshot` 改走 effective |
| `internal/handler/chat_orchestrator_chatflow.go` | fallback 判级改走 effective（到期降级即时生效于 chat 链路） |
| `internal/handler/proxy_routes.go` | `/billing` 组（authMiddleware）+ `POST /redeem` 代理，`route-tier: authed`（AX 守卫合规） |
| `scripts/guards/check_rule_ba_routes_parity.py` | ENGINE_ONLY 挂账 1 条：`/api/v1/billing/redeem-codes`（admin face engine-side only，marketplace/seed-libraries 先例）；**守卫绿：350 proxy ↔ 961 engine，0 drift** |

### 移动（mobile）
| 文件 | 变更 |
|---|---|
| `features/user/data/models/redeem_code_result.dart`（新） | 有界结果词表 success/invalid/expired/exhausted/error + HTTP 映射 |
| `features/user/data/repositories/user_repository.dart` | `redeemCode(code)`：POST `/billing/redeem`（gateway authed 代理） |
| `features/user/presentation/widgets/redeem_code_dialog.dart`（新） | 兑换对话框：输入→核销→toast 显示档位与到期；只消费 DS.* 令牌与 SparkleButton（SPEC 合规，analyze 0 新 issue）；网络面经 `onRedeem` 注入可测 |
| `features/user/presentation/screens/unified_settings_screen.dart` | 设置页「兑换码」入口卡（无障碍卡之后） |
| `lib/l10n/app_zh.arb` / `app_en.arb` + 3 个生成文件 | 9 个新 key（`flutter gen-l10n` 重生） |
| `test/widget/redeem_code_dialog_test.dart`（新） | 4 个 widget 测试 |

### 工具
| 文件 | 变更 |
|---|---|
| `scripts/devtools/generate_demo_redeem_codes.py`（新） | 展会引导脚本：目标库上直接铸码（明码仅 stdout 一次） |
| `backend/tests/unit/test_rd01_redeem_loop.py`（新） | 19 个引擎测试 |
| `backend/gateway/internal/service/user_context_entitlement_effective_test.go`（新） | 2 个 Go 测试 |

## 2. 核销语义细节

- **码面**：`SPARK-XXXX-XXXX-XXXX`，字母表 31 字符（剔除 0/O/1/I/L），
  CSPRNG（`secrets`）；归一化 = 去连字符 + 大写 → 域分隔 SHA-256。
- **幂等/防双花**：同码并发只成功一次（条件 UPDATE 判定，非先读后写）；
  同一用户重复提交已用码 → `exhausted`，权益不被二次叠加。
- **叠加**：有效期内 pro 从现到期日顺延（+10d 再兑 30d → 40d）；过期
  pro/free 从当前时刻起算；**既有永久 pro（expires NULL）保持 NULL**——
  绝不把永久权益降为有期。
- **码有效期**：批次可带 `expires_in_days`（演示建议 90 天），过期码
  `410 GONE`。
- **到期降级**：判级真源 `entitlement_effective`；引擎两读点（user context
  is_pro、run budget 派生）+ 网关两读点（chat profile snapshot、chatflow
  fallback）全部接入——到期后模型路由/预算/权益自动落 free，无需定时 job。

## 3. 红线自查（任务四）

| 红线 | 结论 | 证据 |
|---|---|---|
| entitlement/budget 既有语义零破坏 | ✅ | `entitlement_expires_at=NULL` 时 effective 判级与原函数逐值等价（含 unknown 宁降不升）；`test_o04`（12）、`test_o07`、`test_user_service`、`test_agent_run_service`（136）全绿 |
| fail-safe 降级路径回归 | ✅ | `test_budget_derivation_degrades_to_free_after_expiry`：过期 pro 预算派生 == free 派生 |
| admin 鉴权面不弱化 | ✅ | admin 路由挂 `get_current_active_superuser`（静态依赖断言测试）+ `audit_admin_action(category=billing, risk=high)`；gateway 不代理 admin 面 |
| 明文不落库不进日志 | ✅ | 表内仅 SHA-256；`test_plaintext_never_enters_logs_or_hash_column`（caplog DEBUG 全量断言 + hash 列比对）；生成/核销日志仅 batch_id/prefix |
| 幂等：同码并发只成功一次 | ✅ | `test_redeem_concurrent_same_code_exactly_one_success`（8 并发 → 1 ok / 7 exhausted / used_count==1） |

## 4. 测试与回归统计（回执③）

**红→绿**：基线 `main@4d0ec81c` 干净克隆（/tmp，已清理）上运行新测试套件
→ collection 即红（`app.services.redeem_service` / `redeem_codes` 表 /
billing 路由 / `IsProEntitlementEffective` 均不存在）；落补丁后：

| 套件 | 结果 |
|---|---|
| 引擎新增 `test_rd01_redeem_loop.py`（判级/迁移重放/生成/核销/并发/过期/上限/叠加/永久 pro/红线/API） | **19 passed** |
| 引擎回归（o04 + o07 + user_service + llm_router_qwen + agent_run_service + run_state_machine） | **225 passed** |
| 引擎 `-k "entitlement or budget or redeem"` 全选 | **204 passed, 1 skipped** |
| 网关新增（`TestIsProEntitlementEffective` 8 子用例 + legacy 回归） | **2 passed** |
| 网关回归（handler / service / db 三包，`CGO_ENABLED=0`） | **all ok** |
| 移动新增兑换对话框 widget 测试（成功/用完/过期/取消） | **4 passed** |
| 移动回归（unified_settings 两套件 + router smoke） | **15 passed** |
| 治理守卫 `run_all_rule_guards.sh` | **74 规则全绿**（含 AX route-tier、BA-ROUTES parity、DB-HEAD 单头=rd01_20260922） |

新增合计：**25 个测试文件级用例（19 engine + 2 go + 4 widget）全绿**；回归面 0 破坏。

## 5. 演示 Playbook（参展用，回执④）

### 生成命令（演示部署库迁移到 rd01 之后执行其一）

```bash
# A. 引导脚本（推荐，无需 admin 账号；在 backend 环境执行）
cd backend && python ../scripts/devtools/generate_demo_redeem_codes.py \
    --count 5 --tier pro --duration-days 30 --batch-id demo-sparkle-2026

# B. admin API 面（等价；展示 admin 治理面用）
curl -X POST http://<engine>:8000/api/v1/billing/redeem-codes \
  -H "Authorization: Bearer <SUPERUSER_JWT>" -H "Content-Type: application/json" \
  -d '{"tier":"pro","duration_days":30,"count":5,"batch_id":"demo-sparkle-2026"}'
```

### 样例码（pro/30 天，batch `demo-sparkle-2026`，本机经真实服务路径生成）

```
SPARK-S6BH-PRZV-K674
SPARK-WESG-MH8X-9NJV
SPARK-RRZ8-W8WK-QPQK
SPARK-A4QD-GEKK-43B7
SPARK-CJEC-JY5S-QHM8
```

> 注意：码的哈希必须存在于**演示库**才可核销。上列 5 枚生成于本地 scratch
> 库（用于展示码面形态）；参展前请在演示库上执行上述命令现铸一批（幂等
> batch_id 冲突时换一个即可），打印结果即录入参展物料。

### 演示动线

1. App「我的 → 设置 → 兑换码」→ 输入码 → toast「兑换成功！已开通 pro，
   有效期至 <日期>」；聊天/深度档立享 pro 预算（4 倍 run 预算 + 模型放开）。
2. 同码二次输入 → 「兑换码已被使用」（409，防双花现场演示）。
3. （可选）演示到期：库里把 `entitlement_expires_at` 改到过去 → 判级/预算
   立即回 free，无需重启。

## 6. 收工核查（回执⑤）

- [x] 零 commit / 零 push：交付物为 patch + 报告（`git log` 仍指向 4d0ec81c）
- [x] 树变更最小：`git status` 与交付清单逐一比对一致（20 modified + 11 new，无杂散）
- [x] 未触碰共享 dev 库版本表（schema 导出走 throwaway fresh 库；未跑 `make db-migrate`）
- [x] 未创建 .env / 未落主仓；venv 与 proto 产物均为 worktree 内 gitignore 产物
- [x] /tmp 产物已清（`/tmp/wt108-baseline`、lock 过滤文件已删）；零模拟器；无遗留进程
- [x] 并发纪律：过程仅做过单文件粒度 stash push/pop 对照实验并立即 pop 还原（settings 屏 issue 数 73→73 无新增）
- [x] 蓝图回填：MONETIZATION §5 第 0 期（兑换码）落地；第 1 期（微信支付+订单）不在本卡范围

## 7. 已知边界（诚实挂账）

1. `max_uses>1` 时 `used_by/used_at` 记录**最后一次**核销者（used_count 才是
   剩余判定真源）；逐人明细需第 1 期订单表时再补 redemption 子表。
2. mobile 端权益状态刷新依赖既有 profile 拉取节奏，兑换 toast 的到期时间为
   端内展示真源（服务端判级不受影响）。
3. `entitlement_expires_at` 的主动降级依赖读时判级（惰性）；无定时 job 也无
   推送提醒——第 1 期接 celery beat 到期 job（beat 拓扑现成）。
