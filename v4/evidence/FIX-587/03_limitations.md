# FIX-587 limitations

1. **触发源未在本卡定谳到具体请求**：本卡证据全部为客户端单测/组件测试（真实 TaskNotifier 流水线 + 仓库打桩）。integration 环境里「网关 /tasks* 三接口全 200 但客户端置 error」的具体失败读法（today 还是 recommended）与失败原因（首包超时/鉴权时序/其他）不可在单测观测，未定谳。修后该失败即使持续，也不再阻断创建路径（SnackBar 非阻断 + 空态引导）。
2. **修前红跑日志的文件版本差**：`repro_prefix_red.txt` 产生于测试文件最终版之前（当时断言「重试 findsNothing」，后发现 SnackBar 合法携带重试动作钮，改为 `CustomErrorWidget findsNothing`）。日志中 T2/T3 的失败形态（全页错误态顶掉空态标题）即缺陷本体，行为结论不受影响；与最终测试文件严格对应的红由 `mutation_gate_reverted_red.txt` 提供。
3. **Q01 driver v3.2 绕行未回正**（本卡只评估）：见 04_summary §绕行回正评估。回正动作归 Q01 遗产面，需 driver owner 全栈三轮定稳。
4. **真实设备/全栈验证未跑**：本机无 Intel AI PC/真机约束在案；widget test 不等于全栈 E2E。Q01 driver 回正重跑即全栈验收路径。
5. 与 U06 零交集纪律遵守：本卡变更 = task_list_screen.dart + task_provider.dart + 两个 task 屏测试 + 证据；未触 guest_upgrade_screen.dart / routes.dart。工作区内他线文件（scripts/devtools/disk_swap_guard.sh 改动、pg_env_drift_probe.sh 未跟踪）非本卡产物，未纳入提交。
