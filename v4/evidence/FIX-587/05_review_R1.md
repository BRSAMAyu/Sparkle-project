# FIX-587 R1 独立审查（首审，未参与实现）

> 审查基线：main@e9da058d（被审修复 94ad92fb）。全程只读产品/测试码；mutation 已还原，树净（git diff 空）。integration_test driver 他线在途，未触。

## 裁决：PASS

## 逐靶结论

1. **定谳复核（最重靶）— 属实**。亲读 94ad92fb diff：构造器 `Future.wait([loadTodayTasks(), loadRecommendedTasks(), loadTasks()])` 三读并行共享一个 `error` 位；修前 `loadTasks` 成功路径 copyWith 只写 isLoading/tasks/缓存域、不写不清 `error` → 兄弟失败一次即粘滞，结构上确认。T1/T2/T3 亲跑修后全绿（+3）；门回退 mutation（listError→共享 error）亲做：`+1 -2`，T2/T3 红的失败形态=空态标题「今天还没有待办事项」Found 0（被全页错误态顶掉），T3（列表先成功渲染空态、today 后失败）红即粘滞确定性实证；还原后树净。与自报 mutation 日志逐字一致。
2. **修法语义 — 成立，一处计数偏差**。`_runWithErrorHandling` 调用点实数 12（grep 亲查；自报「20+」系夸计），其中仅 loadTasks 传 `listScoped:true`（唯一出现点）；新增参数带默认值，其余 11 处结构上零漂移。交互核验：非 listScoped 失败传 `listError:null`（copyWith 保旧不清）→ 列表失败后兄弟再失败，listError 保留、全页门不撤（语义正确）；兄弟失败+空 → 共享 error 走 SnackBar 监听器（非阻断），横幅被 `tasks.isNotEmpty` 正确抑制，空态 CTA 可达；兄弟失败+有行 → 横幅（L289）不变。三态与自报一致。
3. **回归亲跑 — 全绿**。本人亲跑 `--concurrency=1`：gate 3 绿 + `test/features/task` 全目录+`router_smoke` 116 绿 + `test/features/home` 113 绿，合计 232 测零失败。证据三 tier 日志尾 `+136/+85/+40` 与自报一致。
4. **绕行回正评估 — 如实**。fix 提交文件清单不含 integration_test（driver 未动）；driver `v4_q01_vertical_journey_test.dart` L1322 起「兜底：列表空态 CTA 路径」分支亲读在案，回正后即自然主径的论证成立；回正条件（Q01 owner 全栈三轮定稳）与「本卡不代行」如实归 Q01 遗产面。
5. **证据完整性 — 完整且诚实**。四件 md + 8 日志齐；limitations 自认三条关键未决（触发源全栈定谳挂账/修前红跑日志版本差以 mutation 日志兜底/真机全栈未跑），无夸大。

## 偏差登记（不阻塞）

- 自报与 04_summary「20+ 处 `_runWithErrorHandling` 调用点」实为 12 处调用点（13 含定义）；「零漂移」主张本身成立。
- `repro_prefix_red.txt` 产生于测试文件定稿前（limitations §2 已自披）；与定稿严格对应的红由 `mutation_gate_reverted_red.txt` 提供，本轮审查员独立复现同形红，闭环。

## 最重残余风险

真实 integration 环境的触发源（today/recommended 哪个读、何种失败）未定谳挂账（limitations §1）——修后客户端对触发源已两域免疫，但共享 `error` 位粘滞机制本体仍在（其余消费面按设计保留），若触发源高频复现，SnackBar 播报的同类别去重（`error == previous?.error`）可能吞掉后续不同因的重复失败提示；driver 回正依赖 Q01 owner 三轮重跑，绕行移除前 CI 零任务路径仍走绕行锚点（已在台账挂账，条件明确）。
