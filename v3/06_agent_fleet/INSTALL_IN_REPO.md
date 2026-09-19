# 将 V3 包收编进当前仓库

推荐目标：`docs/product/v3/` 或当前黑客松目录下独立 `v3/`；以仓库根 AGENTS.md 规范为准。

必须：
- `tasks.json` + shared fleet state 是状态真源；Markdown cards 是规格，不手改状态造成分叉；
- V2/V2.5 历史卡保留，不迁移/重开；
- `PROJECT_SNAPSHOT_V3_20260919.md` 保存为输入证据，不当运行时配置；
- tools 的 state 文件加入适合团队的共享策略：若多机通过 git 协作，状态更新应小提交/专门控制分支；若已有任务协调服务，适配该服务；
- completion/review evidence 放在仓库定义的 outputs 目录并可关联 task id。

不要把整个 ZIP 本身作为唯一真源；解包收编后，仓库版本是后续真源。
