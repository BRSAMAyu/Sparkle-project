# FIX-563 limitations（诚实边界，8 条）

1. **up.sh 新门未真跑**：真跑会执行 `docker compose up`（踩"不动运行中容器"红线）。门逻辑以同构的 supervisor `check_data_plane_owner`（真机真 inspect，absent 分支实测）+ 17 项单测佐证；真跑验证自然发生在本仓下次 up 时。
2. **共享栈搭车模式（piggyback）随分化终止**：分化前本仓 up.sh 检测到 cosmos 栈在跑会 SKIP_DB_UP 搭车；分化后两栈容器名/卷彻底分家，本仓 up 只能起自己的栈。若 cosmos 栈仍占 127.0.0.1 的 5432/6379/9000，本仓 up 将 port-binding 失败（fail-loud，门有 NOTE 预警）。**两栈并存需显式错端口**（`SPARKLE_DB_PORT` 等已存在）或先停另一栈——端口面分化不在本卡授权内，未做。
3. **prod 容器名变更在下次 prod 部署生效**：`docker-compose.prod.yml` 22 个 container_name 已分化，但 Aliyun 服务器上现役 prod 容器仍是旧名，`backup/restore_prod_data.sh` 默认值已指向新名——**下次部署前用旧默认值跑备份会打不中容器**（脚本支持 `POSTGRES_CONTAINER=` env 覆盖过渡）。RUNBOOK 已注记"自然（重）创建生效"；prod 部署属 HUMAN_INBOX 面，本卡不触发部署。
4. **分化前旧名监控兼容窗**：`sparkle-data-services.json` 的 job 正则并列新旧名（`postgres|sparkle_db|sparkle_proj_db|db`），泛型分支（db/redis/minio）本就匹配新旧容器，未重建窗口面板不空洞。
5. **既有陈旧配置零触碰**：`monitoring/prometheus-celery.yml` 的 `sparkle_backend:8000` target 在分化前后都不存在于任何形制（主栈后端容器名 dev=sparkle_api→sparkle_proj_api、prod=backend→sparkle_proj_backend），系本卡之前既有断靶，未顺手修（超授权面）；k8s 形制的 `sparkle-gateway` 资源名同理不动。
6. **测试重写系语义反转所需**：`test_fix557_owner_precheck_real_and_negative` 原断言「sparkle-project_ 前缀=红」恰是分化前的误挂形态；FIX-563 后本仓前缀=正属主（绿），测试按新真值表重写（本仓卷绿/他仓卷红/absent 绿带注记四象限），非删断言凑绿——原负例（他仓卷→红+RUNBOOK 指引）保留并加强。
7. **black 仓库级漂移零新增但未清零**：改动 py 文件 black 26.3.1 would-reformat 与基线同判（P03-R2 已登记的工具链工件），本卡循仓库既有 canon 未重排。
8. **本仓首个数据面将是空库**：现役真 dev 数据卷在 sparkle-cosmos 项目下。分化后本仓首次 `up` 创建全新 `sparkle-project_*` 空数据面并跑迁移（门有 WARNING 防误读为数据丢失）；两仓数据面如何各自播种/导入属产品决策，不在本卡。
