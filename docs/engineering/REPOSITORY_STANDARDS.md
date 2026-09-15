# 仓库设计规范与整洁标准（Repository Standards）

> **文档定位**：本仓库的"东西应该放在哪、长什么样"的单一标准。2026-09-08 仓库整理轮建立。
> **适用对象**：所有贡献者（人类与 coding agent）。
> **执行方式**：PR 评审参照；agent 在创建任何新文件/目录前必须先对照本文。

---

## 1. 根目录白名单（Root Allowlist）

仓库根目录**只允许**存在以下类别的文件。新增根目录文件 = 违反规范，需先证明不属于下列任何一类：

| 类别 | 允许的文件 |
|---|---|
| 入口 README | `README.md`（中文主 README）、`README_EN.md`、`README_CN.md`（别名指针，历史决定保留） |
| Agent 指令 | `AGENTS.md`（规范入口）、`CLAUDE.md`、`GEMINI.md`（两者为 AGENTS.md 的薄指针 + 工具专属规则）、`MEMORY.md`（运行记忆，倒序追加条目） |
| 项目元数据 | `CHANGELOG.md`、`LICENSE`、`.gitignore`、`.gitattributes` |
| 构建与编排 | `Makefile`、`Makefile.test`、`docker-compose*.yml`、`buf.yaml`、`buf.lock`、`buf.gen.yaml`、`buf.gen.dart.yaml`、`redis.conf`、`.env.example` |
| 基础设施目录 | `backend/`、`mobile/`、`proto/`、`docs/`、`scripts/`、`tool/`、`docker/`、`k8s/`、`monitoring/`、`nginx/`、`quality/`、`tests_e2e/`、`third_party/`、`data/dictionaries/`、`.github/`、`.claude/plans/` |
| 运行时数据（gitignore，不入库） | `data/`（词典除外，见 §5）、`postgres_data/`、`redis_data/`、`minio_data/`、`logs/`、`outputs/`、`artifacts/`（部分子目录除外） |

**禁止出现在根目录**：一次性脚本、调试脚本、会话转储、临时报告、带日期的过程文档、孤儿 lockfile、误生成的代码目录。

## 2. 各类产物的归位规则

| 产物类型 | 归属位置 | 说明 |
|---|---|---|
| 一次性/调试/演示脚本 | `scripts/devtools/` | 每个脚本需有一行用途注释；无人引用、无人维护是常态，使用前自行验证 |
| 可复用工程脚本 | `scripts/`（按主题分子目录） | 被 Makefile/CI/规则守卫引用的脚本属于此类，移动前必须全局 grep 引用 |
| 治理守卫脚本 | `scripts/check_rule_*.py`、`scripts/guards/` | 必须注册进 `scripts/rule_guard_manifest.tsv` 才会被 CI 执行 |
| 阶段演练脚本 | `scripts/stage{N}/` | 与 kill switch 演练配套 |
| 过程性文档（对齐稿/交接稿/审计报告/阶段总结） | **不入库**；确需保留的移至仓库外本地归档 | 2026-09 起新阶段政策；历史存档见 `~/code/GitHub/Sparkle-archive-20260915/` |
| 工作文档 | `docs/` 对应编号目录 | 必须是"当前状态 + 关键路径 + 已知边界"型，且登记进所在目录 README |
| Agent 会话产物/PPT 生成物 | `outputs/`（已 gitignore） | 永不入库 |
| 词典/资源数据 | `data/dictionaries/` | 被 docker-compose 挂载与 settings 引用，勿动 |
| 供应商插件 fork | `mobile/third_party_plugins/` | 必须在该目录 README 登记用途与上游版本 |

## 3. 历史内容处置（2026-09 新阶段政策）

1. 旧阶段过程稿、审计与路演材料**不再进仓库**；确需保留的移至仓库外本地归档（当前为 `~/code/GitHub/Sparkle-archive-20260915/`，含全量 git bundle 与文档存档）。
2. 2026-09 仓库重置：历史压扁为单个初始提交，协作者拉取即当前工作区。
3. **活动文档中的链接必须有效**；发现死链顺手修复或删除。

## 4. 文档区整洁标准

1. `docs/` 下每个内容目录必须有 `README.md` 索引（一行用途 + 文档清单）；新目录不带 README = 不合规。
2. `docs/README.md` 是导航总入口；新建目录必须同步登记进其快速导航或专题目录表。
3. 文件命名：工作文档不带日期；过程文档带日期 `YYYY-MM-DD`（这就是它将来归档的信号）。
4. 同一主题只保留一份 canonical 文档，摘要/镜像进归档，不得双活。
5. 与代码现状冲突的文档，以代码为准，并顺手修正文档。

## 5. 数据与生成物红线

1. 运行时数据目录（§1 末行）永不提交；发现入库立即 `git rm --cached` + gitignore。
2. 生成代码目录（`*/gen/`、SQLC 产物）永不手改（源头在 proto / Alembic / query.sql）。
3. 供应商 fork、数据快照等大体积内容入库前必须评估体积与必要性。

## 6. 代码设计标准（分层摘要，细则见各语言工具链）

### 6.1 分层与边界（硬约束）

```
Flutter：UI / 本地状态 / 离线缓存          —— 禁：业务逻辑、直连 Python
Go Gateway：鉴权 / WS / 限流 / 缓存 / 桥接 —— 禁：AI 推理、LLM 调用、handler 直连 DB
Python Engine：编排 / RAG / 工具 / 路由    —— 禁：用户鉴权
```

修改跨边界的接口 = L3 级任务，先出影响面分析（认知协议见 CLAUDE.md）。

### 6.2 语言规范

- **Python**：类型注解 + Google docstring；black（120 列）/ ruff；`snake_case` / `PascalCase`
- **Go**：gofmt + golangci-lint（CI 强制）；导出用 PascalCase；handler → service → db 分层
- **Dart**：Effective Dart + flutter_lints；屏幕文件以 `_screen.dart` 结尾；最大化 `const`；UI 必须消费 `lib/core/design/` 令牌而非硬编码颜色

### 6.3 治理内建（新增能力时）

- 新 Aurora 能力 ⇒ 三态 kill switch（off/shadow/live）+ manifest 注册 + 演练脚本
- 新对外契约 ⇒ proto 定义先行 + `make proto-gen` + 契约快照更新
- 新表 ⇒ Alembic 迁移 +（Go 需要时）query.sql 更新 + `make sync-db`
- 新守卫 ⇒ exit 0/1 语义 + 注册 `rule_guard_manifest.tsv`

## 7. 提交前检查单

```
□ 根目录/文档区未新增白名单外文件
□ 一次性脚本进了 scripts/devtools/ 并带用途注释
□ 新文档登记进所在目录 README + docs/README.md（如适用）
□ 生成代码由源头重新生成，未手改
□ bash scripts/run_all_rule_guards.sh 通过
□ 受影响语言测试通过（pytest / go test / flutter test）
□ 跨边界改动附影响面分析（L3+）
```

---

**变更记录**：2026-09-08 建立（仓库整理轮）。规范变更需同步更新 `docs/README.md` 与编码代理深度指南。
