# V4-G02 · limitations（诚实登记）

1. **golden 基线 macOS 签发**：25 张 golden 由本机（darwin arm64，Flutter 3.41.3）签发；Linux runner 字体渲染（CJK 回退/抗锯齿）存在整族环境签名差（wt296 判例）——像素断言在 Linux 跳过、语义钉全平台照跑。基线再生仅限签发机 `--update-goldens`；判例守卫（golden_family_drift_guard）语义适用于旧族，新族带内漂移处置沿用同一裁决面。

2. **对话流 golden 用安静 harness 播种**：ChatScreen 四态由 provider 覆写 + notifier 直播 state（`seedMessages/seedStreaming/seedRetryableFailure`，f566 同款）驱动，非真实 send 流（本机环境真实事件流等待问题，FIX-566 run_manifest 已登记同源处置）。流式态为「部分内容直接在场」的结构真实，非逐 token 增量过程回放。

3. **core 共享面出家族 diff**：`LoadingIndicator.linear`（Material 无限进度条）自身动画不随 disableAnimations 降级——属 core/design 共享组件（全 app 消费面），本卡只停了家族侧控制器（regeneration_prompt 的 AnimatedBuilder churn）；Material 指示器本体的 reduce-motion 支持建议立 core 批次（不属本卡家族模块边界，未顺手改）。

4. **卡住 sheet 行为面不重做**：三段层级（先原因/单问 → 决策问题+提案 → 取消回原任务）的行为验收属 J-05 / V4-U02 / V4-FIX-569 已交付卡面；本卡只做风格呈现核验（TaskStuckCard 语义钉 + stuck_journey_sheet 源码级令牌核对），未重建其行为测试。

5. **格式器代差**：本地 dart format 2.3.2+（tall-style）与入库风格（旧 short-style）不同——本卡未对产品代码全量跑格式器；96f8d1bb 中 aurora_core_session_sheet / status_awareness_bar 两文件曾误跑格式器产生整文件 reflow 噪声（675/530 行），已手工对齐 lint 冲突 3 处并保持语义 diff 有限（该两文件 reflow 行内无值变化，`git show 96f8d1bb` 可核）。后续会话勿对 lib 全量 dart format（FIX-566 同款登记）。

6. **全量守卫以单规则 PASS 为准**：全量 runner 首跑时 SPACING-RHYTHM 携本卡两处 +1 FAIL（即 G02-D5 回环来源），闭环后 SPACING-RHYTHM / DL-SPEC / UI-TOKENS 单跑 PASS；其余规则族输出与基线同源（ENUM-PARITY 77 条 FAIL=0 WARN=7 等），未在本卡重复全量绿灯记录。

7. **批跑时序 flake 一例**：`websocket_chat_service_v2_a2_offline_queue_test`（data 层，本卡零改动）在 329 批首跑红 1 例，单跑×3 + 同批复跑全绿——判定批跑时序 flake 非回归，如实登记不掩盖。

8. **物理设备/三端截图矩阵不在本卡**：真机截图、HEAVY 三端矩阵归 Q05 重卡审查（no_duplicate_rule：G 卡返绿使 Q05 有据可过）；本卡 UI 证据 = 确定性 golden 25 张 + 语义钉（REPAINBoundary 渲染，非真机）。

9. **isLast 连接线**：collaboration_timeline 时间轴连接线因外层 `isLast` getter 恒 false 而不渲染——既有行为语义疑点，超风格面未顺手修，留行为卡裁决。

## Errata (leader, 2026-09-30, R1 info 收口 + 跨卡冲突注记)
- 跨卡冲突：aurora_core_session_sheet 与 G03 已合并重构（单路径 _dots+相位透明度）重叠——冲突区取 G03 版（其 R1 已验），G02 非冲突增量（令牌/着色扫描）自动保留；合并态补修 G02 分支带回的 pattern_list 旧闭合与 aurora 静态 0.2 覆盖（恢复相位 opacity）。
- R1-1：守卫浅档流式码面模型（ink@6