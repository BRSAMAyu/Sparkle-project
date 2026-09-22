# GRAPH-GRPC-SHAPE 收工报告 — 网关 galaxy/graph gRPC 路径丢失 per-node user_status

> Worker 卡 GRAPH-GRPC-SHAPE ｜ worktree `wt149`（基线 aab18e84）｜ 2026-09-23
> 交付物：本报告 + `changes.patch`（对 aab18e84 干净克隆验证可应用）。零 commit / 零 push / 零凭据。

---

## ① 复现红证（基线 aab18e84 实测）

**机制链确认**：`GET :8080/api/v1/galaxy/graph` 走 gRPC-first（`galaxy_handler.go` `GetGraph` → `galaxyClient.GetUserGalaxy`，失败才回落 REST 双跳）。COLDSTART（dd2be807）修好引擎 servicer 缓存命中崩溃后，gRPC 分支被激活——但 proto `GalaxyNode` 只有 `node_id/label/node_type/mastery(int32)/tags`，**整个 per-user 状态结构在 proto 上没有承载位**。

**引擎 servicer 现状实测**：`galaxy_grpc_service.py` GetUserGalaxy **确实填了** proto 的 `mastery` 字段（P1-22 修复：`mastery=int(node.user_status.mastery_score)`），但 `user_status` 结构本身无处安放——int32 还截断了小数（25.5→25）。

红证双侧留证（修复前运行输出）：

- **Go 侧**（`backend/gateway/internal/handler/galaxy_handler_user_status_test.go`）：
  ```
  --- FAIL: TestGalaxyNodeRESTPayload_EmitsUserStatusContract
      node payload has no user_status object (keys=[id mastery_score name node_type tags])
      — gateway gRPC path drops per-node user_status
  ```
- **Python 侧**（`backend/tests/unit/test_galaxy_grpc_user_status.py`）：
  ```
  ValueError: Protocol message GalaxyNode has no "user_status" field.
  ```
  proto 形状缺失即根因的直接证据。

## ② 方案裁决：**A（proto 补齐）**

**mobile 真实消费字段证据**（`mobile/lib/shared/entities/galaxy_model.dart` `GalaxyNodeModel.fromJson`，`userStatus?[...]` 读取点逐条核对）——mobile 从 `user_status` 读 **10 个字段**：

| # | key | mobile 用途 | 丢失后果（基线网关路径） |
|---|-----|------------|------------------------|
| 1 | `is_unlocked` | 星图锁定态渲染 | **已解锁节点渲染成锁定** |
| 2 | `mastery_score` | mastery 显示（第三回退链） | 网关靠顶层 `mastery_score`（int32 截断）兜底，小数丢失 |
| 3 | `study_count` | 学习次数 | 归零 |
| 4 | `recent_error_count` | 错误簇染色（14 天） | 归零 |
| 5 | `review_urgency_score` | 复习紧迫度 | 归零 |
| 6 | `is_review_recommended` | 复习推荐标记 | 归 false |
| 7 | `review_urgency_reason` | 复习推荐理由 | null |
| 8 | `mastery_last_updated_at` | 衰减/复习 UI | null |
| 9 | `days_since_mastery_update` | 同上 | 归零 |
| 10 | `first_unlock_at` | 解锁时间展示 | null |

已排查其余 mobile `user_status` 引用：`growth_dashboard.dart:160` 把 `user_status` 当字符串读（growth 域独立端点）、`community_repository.dart` 无 galaxy graph 消费、`GalaxySearchResult.fromJson` 有独立扁平化逻辑、`status`/`brightness` 计算字段 mobile 不读——proto 最小集即上表 10 字段。

**B 否决（网关改 REST 优先）**：查证 gRPC-first 的来历——round2 metadata 审计（`docs/competition/2026-tmall-hackathon/系统审查/round2/grpc-metadata-audit.md`，基线 efb1567a）明确记载 galaxy 桥 12 个调用点修复 metadata 注入前 gRPC 是**永远 401 的死代码**、全靠 REST 回落；审计修复的意图就是**激活** gRPC 单跳路径。此后 GW-GRAPH-SHAPE / GW-SHAPE-BATCH2 两批修复确立的既定模式是"保留 gRPC-first，把出站形状重拼回 REST 契约"（galaxy_handler.go 注释原文 "Both branches now speak the same outbound contract"）。B 等于推翻既定方向、放弃单跳优化、且把 batch1/batch2 的形状对齐工作作废。

**C 否决（servicer 填 mastery + 网关映射，不扩 proto）**：P1-22 已经做了（mastery 已填）；剩余语义损失是 `is_unlocked` 等 8 个字段——其中 `is_unlocked` 直接驱动星图锁定渲染，**不可接受**。且 C 无法修复 int32 截断。

**实施内容**：
1. `proto/galaxy_service.proto`：新增 `GalaxyNodeUserStatus` 消息（10 字段：mastery_score **double**、is_unlocked、study_count、recent_error_count、review_urgency_score、is_review_recommended、review_urgency_reason、days_since_mastery_update、两个 `google.protobuf.Timestamp`），`GalaxyNode` 追加 `user_status = 6`（纯追加，wire 兼容）。
2. `make proto-gen`（host 工具链，docker 镜像本机不存在、脚本自动回落）→ Go/Python/Dart 三侧 gen 重生成，**gen 未手改**。
3. 引擎 `galaxy_grpc_service.py`：`_node_user_status_pb()` 辅助 + GetUserGalaxy 节点映射填 `user_status`；`None → 不设置`（proto3 message presence，镜像 REST 的 `user_status=null`，绝不发全零块——全零会被解读为"存在信号但锁定"）。缓存命中路径先 `model_validate` rehydrate（COLDSTART 既有逻辑）保证字段齐全。
4. 网关 `galaxy_handler.go`：`galaxyUserStatusRESTPayload()` 把 proto 映射回 REST `user_status` dict（10 个 mobile 消费键一一对齐；空 reason → null、Timestamp → RFC3339Nano UTC 字符串、nil → null）；`galaxyNodeRESTPayload` 追加 `"user_status"` 键。共享 mapper 的三个调用方（graph/search/recommended）统一受益：search/recommended 的 servicer 暂未填 → 输出 null，与 REST 可空语义一致、mobile 解析中性。

## ③ 冲突面声明

- 在途卡 wt144（events）/ wt146（词库）/ wt147（sector）/ wt148（tests）：本卡改动文件为 `proto/galaxy_service.proto`、`backend/app/services/galaxy_grpc_service.py`、`backend/gateway/internal/handler/galaxy_handler.go` + 两个新测试文件，**与四张在途卡的文件面零交集**。
- 但 **proto 改动是全局性**的：`GalaxyNode` 增字段会重生成三侧 gen（gitignored，见下）。任何在途卡若同时重跑 `make proto-gen`，得到的是包含本字段的同一确定性输出（幂等已验证），无合并冲突；若在途卡手头有旧 gen 快照，重跑 proto-gen 即对齐。
- **gen 入库与 .gitignore 的冲突**：任务卡要求"两侧 gen 产物入库"，但仓库 `.gitignore:240-242` 明确忽略 `mobile/lib/gen/`、`backend/gateway/gen/`、`backend/app/gen/`（"Generated Proto Code (use make proto-gen)"）。本卡遵守仓库现行 .gitignore 策略：**changes.patch 只含源码改动（proto + engine + gateway + 测试），gen 由合入方执行 `make proto-gen` 确定性重生成**（幂等校验见回归矩阵；本机 docker 工具链镜像缺失时脚本自动回落 host buf，已实测可用）。**合入后必须先 `make proto-gen` 再编译 Go/启动引擎/Go 测试**，否则 `GalaxyNode` 无 `user_status` 字段会编译/运行失败。

## 回归矩阵

| 验证项 | 结果 |
|--------|------|
| 新增 Go 测试（5 个：mapper 契约/值保真/nil→null/空 reason→null/端到端等价性） | 全绿 |
| 新增 Python 测试（2 个：user_status 逐字段映射含 25.5 double 保真、无状态节点不设零块） | 全绿 |
| 端到端等价性（`TestGetGraph_GRPCBranch_EquivalentToRESTUserStatus`）：经 `:8080` 网关 gRPC 分支，解锁节点 user_status 10 键齐全 + mastery_score=25.5，无状态节点=null，`via:"grpc"` 证明走的 gRPC 分支，REST 回落未被触碰 | 绿 |
| 既有网关测试族（`CGO_ENABLED=0 go test ./internal/handler/ -run 'Galaxy|...'` + handler 包全量 + `./internal/service/`） | 零新增失败 |
| 网关全仓 `go test ./...`（补 `JWT_SECRET` 环境变量后） | 全绿（config 包初始失败纯系缺 JWT_SECRET 环境变量） |
| 引擎 galaxy 域定向（unit 6 文件 + api shield_invalidation + tests/services/galaxy）：113 passed | 3 failed + 3 error 全部为 `test_galaxy_concurrency.py` 的 **asyncpg "password authentication failed for user postgres"**——环境性 DB 依赖（本沙箱无可用 PostgreSQL 凭据，演示 DB 只读不予 provisioning），失败点在 DB 连接层、与 servicer 改动无关；COLDSTART 契约测试（`test_galaxy_grpc_cached_graph.py`）全绿 |
| COLDSTART 既有测试族 | 3 passed |
| `buf breaking --against main` | 干净（纯追加） |
| `buf lint` | 仅基线既有的目录布局投诉（扁平 proto/ 目录 vs package 路径，全部 proto 文件共有），非本卡引入 |
| `make proto-gen` 幂等：连跑两次 galaxy gen 校验和 | `20ee0820…` == `20ee0820…` 一致 |
| gofmt（本卡文件）/ ruff + black（本卡 Python 文件） | 干净（`ws_e2e_roundtrip_test.go` 的 gofmt 投诉为基线既有、非本卡文件，未触碰） |
| patch 可应用性：对 aab18e84 干净克隆 `git apply --check` | 通过 |
| 生成 python pb2 导入 / servicer 实际运行（pytest 全链路） | 通过 |

## ④ 诚实申报

1. **范围截留**：`SearchNodes` / `GetRecommendedNodes` 两个 servicer 也构造 `GalaxyNode`，本卡**未**给它们填 `user_status`（SearchNodes 的 servicer 只查了 mastery 一列，填半截 user_status 会造出 `is_unlocked=false` 的语义谎言；RecommendedNodes 的 `predicted.user_status` 可以填，属同模式后续）。它们的网关出站现在是 `user_status: null`——解析中性，但 REST 面的 search `results[].user_status` 与 gRPC 分支存在同型（轻于 graph）的形状差。**建议登记同模式 follow-up**（与 GW-SHAPE-BATCH2 已登记的 search similarity proto 扩展同一批做掉最经济）。
2. **时间戳表示偏差**：REST/pydantic 输出 naive ISO 字符串（无 Z），网关现在输出 `RFC3339Nano UTC`（带 Z）。同一时刻、不同拼写，`DateTime.tryParse` 两者皆收；逐一字节对齐需要网关剥掉时区后缀，收益为零，未做。
3. **REST `user_status` 的其余字段**（`total_study_minutes/is_collapsed/is_favorite/last_study_at/next_review_at/decay_paused/status/brightness/mastery_evidence`）未进 proto——mobile 从不读取（已逐一核对），minimal set 裁决如上表。若未来 mobile 消费面扩大，proto 需再扩。
4. **测试环境**：本机无 worktree 独立 venv，Python 测试复用主仓 venv 解释器（cwd 恒在 worktree、`PYTHONDONTWRITEBYTECODE=1`，主仓零写入）；`test_galaxy_concurrency.py` 的 DB 失败未做基线复跑（失败模式是 asyncpg 连接认证、与代码路径无关），已如实标注为环境性。
5. proto-gen 走 host 工具链（buf 远端插件 + 本地 grpc_tools），因 `sparkle/proto-toolchain:latest` 镜像本机不存在；生成结果经幂等校验，与工具链容器路径理论同源（同一 buf 模板 + 远端插件版本钉死在 buf.gen.yaml）。

## ⑤ 收工核查

- [x] 改动全部在 `wt149` 内；主仓只读（仅只读借用 venv 解释器与只读查看 gen 基线）
- [x] 零 commit / 零 push（交付前 `git status`：3 modified + 2 untracked，全部在 patch 内）
- [x] proto 硬规则：只改 `proto/*.proto`，gen 全部由 `make proto-gen` 生成、未手改；Go 侧全程 `CGO_ENABLED=0`
- [x] 演示 DB 只读、活栈未动、无模拟器/无 HEAVY 任务启动（swap 914M 低于 HEAVY 启动门，本卡全程 LIGHT）
- [x] `/tmp` 自清（`ggs-verify` 克隆、`base_servicer.py` 已删）
- [x] 无 `.env` 副本、无凭据入 patch（`SECRET_KEY=test`/`JWT_SECRET=test-secret` 仅命令行环境变量）
- [x] 交付物：`v3-output/GRAPH-GRPC-SHAPE/REPORT.md`（本文件）+ `changes.patch`

## 合入方操作指引（重要）

1. 应用 patch 后**必须先 `make proto-gen`**（gen 是 gitignored 产物，patch 不含也无法含），再编译网关/启动引擎——顺序错了 `GalaxyNode.UserStatus` 字段不存在会编译失败。
2. 网关验证：`cd backend/gateway && JWT_SECRET=<...> CGO_ENABLED=0 go test ./internal/handler/ -run Galaxy -count=1`；引擎验证：`cd backend && pytest tests/unit/test_galaxy_grpc_user_status.py tests/unit/test_galaxy_grpc_cached_graph.py`。
3. 活栈终验探针（留主会话）：修后 `:8080/api/v1/galaxy/graph` 与 `:8000/api/v1/galaxy/graph` 同账号同刻对比，节点应同现 `user_status.mastery_score`（含小数）与 `is_unlocked=true`。
