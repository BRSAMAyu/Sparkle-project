# FIX-563 summary — compose 容器名单侧分化收口

**一句话**：本仓（Sparkle-project）全部 compose `container_name` 单侧分化 `sparkle_*`→`sparkle_proj_*`（44 个，4 文件），跨仓 ops 误击（FIX-557 实战事故形态）自结构上根除；依赖面（预检门/脚本/Makefile/监控/17 件 live 文档）全量同步，grep 可执行容器操作旧名归零。

## 交付判定（对派单五项）

| 派单项 | 结果 |
|---|---|
| 1. compose 容器名分化 | 4 文件 44 名全分化（`sparkle_db→sparkle_proj_db`、`sparkle_redis→sparkle_proj_redis`、`sparkle_minio→sparkle_proj_minio` 及全部同名族）；服务名/DNS/volume 未动 |
| 2. 依赖面 grep 同步 | 脚本 18+Makefile+监控 9+文档 17 件同步；「改/豁免」三分类清单 `grep_exemptions.md`；可执行容器操作旧名残留 **0** |
| 3. 预检门扩展 | up.sh FIX-557 db 门扩为 db/redis/minio 三数据面同一套门（无第二套）；supervisor FIX-557 预检同批适配并扩语义（absent=绿/误挂=红），17+14 测试全绿 |
| 4. RUNBOOK 跨仓注记 | `scripts/RESTACK_RUNBOOK.md` 重写：两仓对照表（权威）+「永远先 `-p` 显式 project 名」纪律 + 容器名变更下次（重）创建生效注记 + 端口冲突预期 + 事故史录保留 |
| 5. smoke.sh/logs.sh 同族错名 | 两件 dash 形旧债（`sparkle-db`/`sparkle-redis`，初始 commit 既有债、P03-R2 登记）一并收口；logs.sh 服务名/容器名分轨重构 |

## 验证与红线

- `docker compose config` 四场景 exit 0，渲染容器名 100% `sparkle_proj_*`；volume 节逐字节未动（数据面零迁移）。
- 真机三容器（sparkle-cosmos 侧）全程 `Up 19h (healthy)` 零触碰；对 Docker 仅只读命令与 config 渲染。
- 不 push；sparkle-cosmos 仓零写入。

## 回退

单 commit revert 即全量回退（纯文本/配置变更，无数据面接触）；回退后两仓恢复同名碰撞态，FIX-557 门语义仍按旧逻辑工作（up.sh 旧门在 git 历史可考）。

## 后续接力（非本卡）

- prod 下次部署前：服务器侧核对 backup/restore 默认容器名（可用 env 覆盖过渡）；部署后 Q07 可把「错仓重建无碰撞」纳入混沌负例（P03-R2 §5 建议的消费关系）。
- sparkle-cosmos 仓侧的对称动作（其容器名仍与本仓新名零碰撞，非必需）。
