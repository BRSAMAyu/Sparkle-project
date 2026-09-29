# FIX-584 limitations

1. **未真端复测**：修复以真实组件树 widget test（真向导屏 + 真 TaskNotifier/TaskRepository + 传输 mock）钉死，未在真设备/真栈重放 Q01 G5 旅程。真端复核归 Q01 复测轨（其栈保持运行）；本卡证据不含「真机上点出回执」帧。
2. **unawaited 填充的时序语义**：填充在途不阻成功弹窗/CTA（裁决依据见 run_manifest `fix.design_rationale`）。极端情形（用户在刷新完成前极快打开卡住 sheet）锚点晚一拍出现——sheet 对投影是 watch 型自愈（args 变化重建控制器），不会假缺席，但存在一拍延迟窗口。测试②以确定性 pump 收敛断言，非时序赌运气。
3. **todayTasks 分支未触**：向导任务 due_date=null 永不入今日面；锚点解析主路径是全量 `tasks` 列表（后端 GET /tasks 无 today 过滤，r5 console 实证）。今日面口径是另一卡的事，本卡不扩。
4. **r5 绕道失效归因是读证推断**：「拖拽未触发 onRefresh → 零 GET /tasks」来自 console 时间线（6470→6485 间无该请求）；driver 步骤 PASS 判据（列表文案在场）不能证明刷新发生。未在 driver 层重放验证该推断。
5. **后端/网关零改动**：本卡只触 mobile 两个文件；FIX-583 的 hybrid_journey_service 未触碰（零文件交集纪律）。
6. **worktree 环境一次性成本**：`flutter pub get --offline` + `make mobile-proto`（gen/ gitignored）；`mobile-proto` 走 host buf（1.66.0），未跑全量 `make proto-gen`（python/gateway 生成物与本卡无关且不触 proto 契约——proto 文件零改动）。
7. **测试文件锚定现状口径**：锚点钉断言消费 `recoveryCalibrationThisTimeCta`（「调整这次行动」）zh 文案与 scopeChoice 相结构——若 U02 面后续改版（文案/结构），本测试需随卡面演进同步（与既有 recovery 校准测试同一维护口径）。
