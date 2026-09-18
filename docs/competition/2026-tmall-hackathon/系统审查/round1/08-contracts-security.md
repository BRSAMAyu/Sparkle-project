# 08 跨层契约·安全横切·治理工具链 审查报告（round1）

- 审查员：8 号切片（层间接缝：proto↔三方生成物、DB 契约链、WS 协议双端、安全横切、治理工具链）
- 基线：`main@90daac8a`，工作树 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt8`（只读，未改任何业务代码）
- 日期：2026-09-18

---

## 1. 总评

**契约层整体健康度高于预期：proto → Python/Go/Dart 三方生成物在冻结基线上零语义漂移**（Python 15 个 pb2 模块 descriptor 级全等、Dart 36/36 文件归一化全等、Go 网关实际消费的 5 组契约字段 tag 全等）；WS 消息协议核心链路（delta/status/tool_call/tool_result/citations/usage/error/done/ack/nack）双端字段逐一吻合且客户端解析全部判空防御，无 null 崩溃面；鉴权链三层独立校验（网关 alg 白名单 JWT → 引擎 HTTP 自行 decode_token → 引擎 gRPC AuthInterceptor 含 user-id 冒用校验），不存在头信息盲信任。SQL 注入、secrets、路径穿越、上传校验扫描全部干净。

**真正的缺陷集中在 DB 契约链**：Alembic 迁移图存在一个 **4 节点循环依赖**（P1，当前被 alembic DFS 顺序+空操作合并节点侥幸掩盖）、**全新数据库无法直接 upgrade 到 head**（P1，`sparkle_galaxy` schema 由 c17 授权却无任何迁移创建）、以及网关 `schema.sql` 快照对 Alembic 终态的 **5 处实质漂移**（P2，且无守卫校验快照新鲜度）。另发现网关代理路由与引擎路由的一处命名漂移（`/release-approvals` vs `/release_approvals`，全 404 死路由）与引擎侧一个仅靠"注释标记+网络隔离"保护的 internal 端点。

---

## 2. 发现表

| ID | 严重度 | file:line | 触发场景 | 证据摘录 | 建议修复 |
|----|--------|-----------|----------|----------|----------|
| C-01 | **P1** | `backend/alembic/versions/comp_idx_20260508_add_composite_indexes.py:9-10`、`ac07dc579128_merge_pii_and_goal_id_heads.py:23-24`、`p001_20260507_add_goal_id_to_plans.py:17-18`、`7f807dcd4e5f_add_post_comments_table.py:23-24` | 任何工具对迁移图做拓扑排序/降级/重放：`alembic downgrade` 跨环、未来向这 4 个 revision 补真实 DDL、或第三方迁移校验工具 | 四文件构成环：`comp_idx_20260508.down='ac07dc579128'` ← `ac07dc579128.down=('02a063d173ec','p001_20260507')` ← `p001_20260507.down='7f807dcd4e5f'` ← `7f807dcd4e5f.down='comp_idx_20260508'`。alembic `get_revision()` 复核一致。当前侥幸可用：ac07 是 `pass` 空操作合并，alembic DFS 恰好产出 134 步可执行序 | 断环：新建 merge revision 不可行（环本身非法）；应将 `comp_idx_20260508.down_revision` 改指向环外祖先（如 `02a063d173ec`）并核实生产 alembic_version 落点后以 `alembic stamp` 修正分支归属 |
| C-02 | **P1** | `backend/alembic/versions/c17_20260502_create_service_roles.py:276-286`（及 `Makefile` `db-dump` 之外的引导链） | 全新环境（CI、新同事、灾备重建）执行 `alembic upgrade head` → 在 c17 处炸掉 | `GRANT USAGE ON SCHEMA sparkle_galaxy TO sparkle_engine` 对**从未被任何迁移创建的 schema** 授权；全仓（versions/、env.py、Makefile、docker/、compose initdb）均无 `CREATE SCHEMA sparkle_galaxy`。实测 fresh DB：先失败于 `schema "sparkle_galaxy" does not exist`，手工预建后 134 个迁移全部通过 | 在 c17 之前（或 c17 内部授权前）补 `CREATE SCHEMA IF NOT EXISTS sparkle_galaxy`；顺带审计 `ag_catalog`（AGE 扩展）等其它 out-of-band 对象的创建责任归属 |
| C-03 | **P2** | `backend/gateway/internal/db/schema.sql`（导出快照）vs `backend/alembic/versions/wp19_20260507_add_chat_messages_metadata_jsonb.py`、`02a063d173ec_add_pii_hash_columns_for_encryption.py`、`7f807dcd4e5f_add_post_comments_table.py`、`c1b2c3d4e5f6`（community_strategy_outcomes） | 以 schema.sql 为 sqlc 输入生成的网关代码，跑在"严格按 Alembic 建的库"上：新列（`chat_messages.metadata`、`user_devices.push_token_hash`）永不被网关读到；反向漂移列（`shared_resources.adoption_count/quality_score/quality_hidden/negative_feedback_count`）一旦被 sqlc 查询引用即 runtime SQL error | 实测三方比对（快照 vs fresh-迁移库 pg_dump）：快照独有 `saga_instances` 表 + shared_resources 4 列 + AGE 内表；迁移库独有 `post_comments`、`community_strategy_outcomes` 表 + `chat_messages.metadata` + `user_devices.push_token_hash`。快照是从盖戳 `t32_community_rooms`（基线中不存在）的 dev 库导出的——**快照源头已被污染且无新鲜度守卫**（`check_migration_contracts.py` 只校验迁移头注释） | 在 dev 库修复迁移链后重新 `make sync-db` 导出；新增守卫：CI 中 fresh-DB `alembic upgrade head` → `pg_dump` → 与 schema.sql 归一化比对 |
| C-04 | **P2** | `backend/app/api/v1/release_approvals.py:135-137` | 引擎端口被误暴露（内网横移、误配 nginx/端口映射）时，未认证读取待发布审批明细 | `# route-tier: internal` 仅为注释标记，运行时**无任何鉴权依赖**（对比同文件 summary 路由）；该标记的强制点是 CI 的 AX guard 而非运行时。当前外部不可达（nginx 仅暴露网关；网关显式代理表不含该路径；NoRoute 只转发公开 auth 前缀）——纯靠网络隔离 | 引擎侧给 `/admin-tab`（及同类 internal 路由）加 `Depends(get_current_active_superuser)` 或内部 API Key 校验，使"网络隔离"只是第二道防线 |
| C-05 | **P2** | `backend/gateway/internal/handler/proxy_routes.go:987` vs `backend/app/api/v1/release_approvals.py:22-23` | 网关按 "Missing Proxy Routes" 清单注册 `/release-approvals/*path`（连字符），引擎实际挂载 `/api/v1/release_approvals`（下划线）→ 该代理组**每个请求都在引擎侧 404** | 网关：`{"/release-approvals", "release-approvals"}`；引擎：`APIRouter(prefix="/release_approvals")` 且 router.py 234 行原样 include。同清单其余 10 项均匹配（已逐项脚本核对） | 统一命名（建议网关改 `/release_approvals` 或引擎改连字符），并在 BA 守卫中扩展"网关代理前缀 ↔ 引擎挂载前缀"自动比对（当前 BA 仅覆盖 ChatHistoryDTO） |
| C-06 | **P3** | `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:183、988` | 无运行时故障；纯死代码/不可达分支 | `case 'aurora_state_band'`、`case 'plan_review_widget'` 在 engine(grep=0) 与 gateway(grep=0) 均无产生者；另 `achievement_unlock`/`milestone_proposal` 依赖引擎 `app/core/websocket.py` manager 直发，但生产拓扑客户端连的是网关 `/ws/chat`，引擎直连 WS（`/ws/connect`）未在网关链路内——建议核实这两个类型是否存在真实到达路径 | 删除死 case 或补齐产生端；为每个 WS case 建立三端（engine/gateway/mobile）归属表进治理守卫 |
| C-07 | **P3** | `buf.gen.yaml:9、14` vs 现存 `backend/gateway/gen/**/*.pb.go` 头部 | `make proto-gen` 复现性：钉死的 remote plugin 版本与实际产物不一致 | 配置钉 `protocolbuffers/go:v1.36.5`、`grpc/go:v1.5.1`；现存产物头 `protoc-gen-go v1.36.11`、`protoc-gen-go-grpc v1.6.1`（docker 镜像内本地 plugin）→ `proto_toolchain.sh check-generated` 的 diff 在 Go 侧会因工具链版本噪声误报/漏报 | 统一生成器版本：要么 buf.gen.yaml 改用与镜像一致的版本，要么镜像内安装钉死版本；把"版本头不计入 diff"写进 check-generated |
| C-08 | **P3** | `backend/sparkle/signals/v1/signals_pb2*.py`、`backend/sparkle/rag/v1/evidence_pb2*.py`（git 提交的生成物） | 违反"生成物不入库、永不手改"精神的例外路径：这 4 个文件被 git 跟踪，但游离于 `proto_toolchain.sh check-generated` 守卫（只覆盖 backend/app/gen、backend/gateway/gen、mobile/lib/gen）之外 | 已实测当前与 `proto/sparkle/*` descriptor 级一致（无漂移），属"无守卫的已同步状态" | 要么纳入 check-generated 比对范围，要么改造 signals/rag 管线改为运行时从 app/gen 导入并删除该目录 |
| C-09 | **P3** | `backend/app/core/celery_tasks.py:1497` | 密码重置发送失败日志泄露收件人邮箱（PII 入日志） | `logger.error(f"Failed to send password reset email to {to_email}: {e}")` | 改用 `logsafe` 哈希/掩码（同仓 `token_revocation.py` 已是正确范式） |
| C-10 | **P3** | `scripts/guards/check_rule_bi_hardcoded_secrets.py:201-219`、`scripts/check_proto_contract.py` | 守卫覆盖缺口 | BI 仅扫 `backend/`、`gateway/`、`mobile/`，不含 `scripts/`、`k8s/`、`docker/`、`charts`（本次全仓 grep 未命中真凭据，属加固项）；`check_proto_contract.py` 依赖 gitignored 的 `backend/app/gen` 存在，干净环境直接 `ModuleNotFoundError: app.gen`（本 worktree 复现） | BI 扩大扫描根；proto contract 检查前置 `make proto-gen` 或在缺 gen 时显式 skip+警告 |

---

## 3. 执行结果记录（脚本输出摘要）

### 3.1 三方生成物比对（任务 A）

方法：用本机 buf/grpc_tools/protoc-gen-dart 从 wt8 的 proto/ **全新重生成**三语言产物到 `/tmp/sr8/gen/`，与 main 检出（同一 commit 90daac8a）的 gitignored 生成物做归一化/语义比对（生成物不入库，wt8 内不存在）。

- **Dart**：`fresh=36 checked=36 diff=0 → IDENTICAL (normalized)` —— 移动端与基线 proto 零漂移。
- **Python**（AST 提取 `AddSerializedFile` 的 FileDescriptorProto，免导入比对 message/field/number/type/label/oneof/enum 全量语义）：
  ```
  [MATCH] app/gen/agent/v1/agent_service_pb2.py (proto=agent_service.proto, msgs=53)
  [MATCH] app/gen/agent_service_pb2.py / error_book_pb2.py (20) / galaxy/v1 (23)
  [MATCH] app/gen/sparkle/{inference(10),rag(2),signals(15)} / stt/v1 (10)
  [MATCH] app/gen/user_state_pb2.py (51) / websocket_pb2.py (10) / ws/websocket_pb2.py
  [MATCH] backend/sparkle/{signals,rag}（git 提交副本）
  SUMMARY: match=14 drift=0 skip=1(re-export stub)
  ```
- **Go**（结构体 protobuf tag 语义比对，剥离工具链版本头）：网关实际 import 的 `agent/v1`、`galaxy/v1`、`proto/error_book`、`ws`、`sparkle/{signals,rag,inference}` 全部字段级一致；`MISSING-CHECKED` 仅命中 community_service 与 user_state 两个**网关零 import**（grep 证实无 `gen/community`、`gen/userstate` 引用）的 proto，不构成编译/运行时风险。
- **proto 卫生**：`buf build` 成功（无编号冲突/无循环 import，protoc 级保证）；`buf lint` 输出均为命名风格类（RPC 后缀、enum 零值 `_UNSPECIFIED` 等，STANDARD 集），非契约缺陷。

### 3.2 Alembic 迁移链（任务 B）

静态构图脚本（134 个版本文件，支持注解赋值与多行 tuple down_revision）：

```
total files=134 revisions=134 roots=2 heads=1
HEADS: ['0150e391736a']   ROOTS: ['cc9383c4c29f', 'cs001']
merge revisions (24)：多父 tuple 全部静态解析成功、父引用齐全
[CYCLES] [['comp_idx_20260508','ac07dc579128','p001_20260507','7f807dcd4e5f','comp_idx_20260508']]
```

Alembic 官方 ScriptDirectory 复核：`get_revision()` 逐环确认 4 节点 down_revision 闭合；`_upgrade_revs('heads', None)` 仍产出 134 步（DFS 顺序，非合法拓扑序，环被空操作合并节点掩盖）。单 head 达成（唯一的好消息）。

Fresh-DB 实测（运行中的 sparkle_db 内临时库 `sr8_mig_audit`，用后即删）：

```
alembic upgrade head
→ FAILED: ProgrammingError: schema "sparkle_galaxy" does not exist  (at c17)
→ CREATE SCHEMA sparkle_galaxy 后重跑：
   Running upgrade ... -> 0150e391736a, merge_final_heads_20260516
   全链 134 迁移通过，alembic_version=0150e391736a
```

### 3.3 schema.sql 快照漂移比对（任务 B）

`pg_dump --schema-only`（fresh 迁移库） vs `backend/gateway/internal/db/schema.sql`（表/列归一化比对，234/235 表）：

```
tables ONLY in fresh migrations (2): community_strategy_outcomes, post_comments
tables ONLY in snapshot (3):        saga_instances, _ag_label_edge, _ag_label_vertex
column drift (3):
  chat_messages:    snapshot 缺 metadata
  shared_resources: snapshot 多 adoption_count/quality_score/quality_hidden/negative_feedback_count
  user_devices:     snapshot 缺 push_token_hash
```

影响面核实：sqlc 生成的是**显式列名** SQL（`SELECT *` 在生成期展开），多余 DB 列不炸扫描；多余列均未被 query.sql 引用（grep 证实）；`saga_instances` 有 `cmd/server/setup.go:319 EnsureSchema` 自愈建表。故评级 P2（契约撕裂+无守卫+源头库盖戳 `t32_community_rooms` 不在基线），非 P0。

### 3.4 WS 协议双端比对（任务 C）

- 网关侧枚举（chat_orchestrator_protocol.go 等全部 handler）：`delta, tool_call, status_update, full_text, error, usage, citations, tool_result, intervention, done, metadata, message_ack/ack, message_nack, meta, pong, plan_review_status, action_status, intervention_feedback_ack, response_feedback_ack, widget, ack/error_update_node_mastery`。
- 移动端 switch（websocket_chat_service_v2.dart，38 个 case）**全覆盖**网关集合，且 error/usage/citations/delta 的字段逐一对照吻合（`error_code/message/retryable`、`prompt/completion/total_tokens/cost_micro_usd`、citations 10 字段、metadata.event_type 解包 transparency/run_ledger/orchestration_trace）。
- 反向差集：`aurora_state_band`、`plan_review_widget` 仅 mobile 存在（engine=0，gateway=0，grep 三端核实）→ C-06。
- 客户端解析全部 `as String?`/`??` 判空兜底，**无缺字段 null 崩溃面**。

### 3.5 安全横切扫描（任务 D）

- 真凭据模式（sk-/AKIA/ghp_/github_pat_/xox/私钥块，全仓含 yaml/json/env）：0 命中（仅 BI 守卫自身的正则定义）。
- Python f-string SQL：唯一命中 `app/db/extensions.py:79` 为白名单校验后的 `CREATE EXTENSION`（安全）；Go `fmt.Sprintf` SQL：0 命中。
- CORS：网关 `middleware/cors.go` 反射白名单内 origin + `Vary: Origin` 防缓存投毒；引擎默认空 origin 列表 + 生产禁 `*`/非 HTTPS（settings.py:1060-1068）。
- 上传链：`documents.py` 尺寸上限 + mime 白名单 + 文件名清洗 + confirm 期 magic bytes 校验（PDF/PK/PNG/JPEG/GIF/WebP/UTF-8 文本逐一比对）+ 对象键服务端构造 `{user_id}/{uuid}/original{ext}`，无用户输入入路径。
- 鉴权链：网关 JWT alg 白名单（RS256 优先，HS256 迁移期兜底，其余拒绝）；引擎 `get_current_user` 自行 `decode_token` + jti 黑名单，**不信任网关头**；gRPC `AuthInterceptor` JWT 校验 + `user-id` 元数据与 token sub 一致性校验（防冒用）+ 常数时间 INTERNAL_API_KEY 比对。
- PII 日志：token 撤销链全用 `user_id_hash`；唯一漏点 `celery_tasks.py:1497` 邮箱明文（C-09）。
- admin 面：admin_dashboard/dlq/feedback/memory/executions 全部 `Depends(get_current_active_superuser)` + audit 装饰器；`/release_approvals/admin-tab` 例外见 C-04。

### 3.6 治理工具链（任务 E）

- AX/AT 增量扫描：`git symbolic-ref origin/HEAD` → `merge-base HEAD` → `merge_base...HEAD` 逐行解析新增行（正确跳过删除行计数），基线不可用时回退全量——**merge-base 选取正确**。实跑：AX PASS(DIFF)、AT PASS。
- BI：全量 rglob 扫描（无增量选取问题），placeholder 白名单+排除目录在位；实跑 PASS。缺口：扫描根不含 scripts//k8s//docker/（C-10）。
- `check_migration_contracts.py`：实跑输出 "No changed migration files"（增量逻辑依赖 BASE_REF，worktree 内行为正常）。
- **serial_merger.py 不存在于基线**：全 wt8、全 sysrev 各 worktree、main 检出均无 `scripts/coordination/` 目录与该文件（git 未跟踪）。任务指定审的 gate binding/journal 幂等/disconnect reconcile 无从审起——已改为对迁移树本身做全量验证（3.2），24 个多父合并 revision 的 tuple 解析全部正确。建议把该工具入库或从任务清单移除。

---

## 4. 验证良好清单

1. proto ↔ 三方生成物：Python 14 模块 descriptor 全等、Dart 36/36 全等、Go 消费契约字段全等——基线契约零漂移（这是本切片最重要的好消息）。
2. 迁移链单 head（`0150e391736a`）、24 个 merge revision 多父 tuple 全部正确、134 个文件静态解析无重复 revision id、无缺失父引用（除环）。
3. Fresh-DB 全链 134 迁移在补建 schema 后可一次通过——链路本身（除 C-01/C-02）质量良好。
4. WS 核心协议双端字段级吻合 + 客户端全防御性解析 + 引擎→metadata→网关透传→移动端解包（transparency/run_ledger/orchestration_trace）三端链路完整。
5. 三层鉴权各自独立校验、互不盲信；gRPC 冒用校验（user-id vs token sub）是超出预期的纵深防御。
6. SQL 注入面、secrets、上传路径穿越/类型校验全部干净。
7. `CGO_ENABLED=0 go vet ./...` 全绿；Go proto 序列化契约测试通过（`go test ./internal/handler -run ProtoSerialization` ok）。
8. 网关 CORS（Vary: Origin 防缓存）、NoRoute 代理仅放行公开 auth 前缀 + `path.Clean` 防穿越、admin 代理 catch-all 有 RequireAdmin 双闸。

## 5. 测试执行记录

| 命令 | 结果 |
|---|---|
| `buf lint` / `buf build -o descset.pb`（wt8） | lint: 命名风格项（无契约缺陷）；build: OK |
| `python3 /tmp/sr8/{stale_check,go_dart_drift,py_drift2,go_tag_drift,mig_chain,schema_cmp}.py` | 见第 3 节各摘要 |
| alembic ScriptDirectory 校验（standalone venv，wt8/backend） | heads=[0150e391736a]；环 4 节点复核成立 |
| `alembic upgrade head`（fresh DB `sr8_mig_audit`） | 首跑失败于 c17 缺 schema（C-02）；预建后 134 步全部通过；库已删除 |
| `pytest tests/test_migrations.py tests/contract tests/security`（wt8 backend） | **未能执行**：`uv sync --frozen` 被 uv.lock 钉死的 aliyun 镜像 403 阻断（官方 PyPI 覆盖被 lockfile 源 URL 锁死）。已用等价/更强的手动验证替代（fresh-DB 全链升级 = test_migrations 的核心断言） |
| `CGO_ENABLED=0 go vet ./...`（wt8 gateway，gen 目录自 main 检出同 commit 恢复） | exit=0，无输出 |
| `CGO_ENABLED=0 go test ./internal/handler -run ProtoSerialization -count=1` | ok 0.904s |
| guards 实跑：AX / AT / BI / check_migration_contracts | 全 PASS（proto_contract 因缺 gitignored app.gen 环境性失败，见 C-10） |

---

**结论**：跨层契约（proto/WS）与安全横切基本面扎实；DB 契约链是当前系统性风险所在——C-01/C-02 两个 P1 建议进入下一轮修复排期的最前端（两者都影响"从零重建环境"这一参赛演示的关键路径）。
