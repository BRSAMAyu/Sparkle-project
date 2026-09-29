# V4-U12｜limitations（已知限制与边界，如实登记）

1. **「一致像素语法」按家族判例落在令牌统一，不做 PixelFrame 换装。** self-anchor 与
   photon/redeem-pro 活路由已消费 DS 令牌与 DS 组件（U11 同家族判例：已是 DS 令牌呈现
   即零重写）；F02 PixelFrame 换装会在 classic 档（发布默认）引入视觉差量（圆角
   24→22、面槽/描边槽变化、失去 EmotionResponsive 阴影简化联动），与「参考图=提案非
   批准（发布默认主题不换）」红线冲突，故不做。像素 preview 档下这些屏不出现切角
   轮廓——若后续裁决要像素档全家族覆盖，属独立视觉批次（需先过参考图批准门）。

2. **幂等双闸的分工边界。** 客户端重入守卫只保证「同一 UI 逻辑动作不产生第二次
   POST」；同账号跨设备/直接打 API 的重复兑换由服务端月顶屏障裁决（原子扣减+月顶
   复查回滚，`test_monthly_cap_blocks_second_redeem_and_converges` +
   `test_concurrent_redeem_exactly_one_success` 回归绿）。`X-Idempotency-Key` 头在该
   端点被引擎忽略（IdempotencyMiddleware PROTECTED_PATHS 不含 /photons/redeem-pro），
   移动端拦截器仍随请求带键（未来引擎侧接入时零客户端改动）；本卡不扩引擎保护面
   （契约归单一 owner，path_policy）。

3. **无真机截图/录屏。** 本机无接入设备（U11 同状）；UI 语义以 widget 测试断言
   （中文文案/ValueKey 定位/类型在场缺席）代替截图语义 dump，真机视觉未采，
   DEVICE_UNVERIFIED。卡面 evidence_required 的 screenshots 项按 F06/U11 先例
   「语义文本口径」披露。

4. **arb 勘误为修改非纯新增。** `leaderboardSelfAnchorLoadFailed` zh/en 两键由
   「{error} 占位模板」改「固定人话模板」（U11「勘误」同口径）：键名保留、语义收敛、
   占位移除。理由=N9 泄漏通道关闭（守卫协议内 cleanup batch，棘轮 260→256/72/77 随
   基线 JSON 下调入库）；风险=无（唯一调用面同步更新，grep 自证；既有测试文案前缀
   断言不破坏，已回归绿）。

5. **庆祝关闭的覆盖口径。** 低刺激档抑制覆盖 SparkleConfetti 全部调用点（其内部
   短路=视觉+粒子预算+控制器整体停）与触觉/声效（U14 独立开关）；成就弹窗本体在
   低刺激档仍会出现（信息回执性质：成就名/奖励/叙事），可一键关闭
   （barrierDismissible+关闭钮）——「关闭庆祝」裁决为关效果而非拦截信息回执；
   milestone_celebration_screen 为用户主动深链进入的分享面，不在自动庆祝范畴，
   本卡未改其内部（其彩带同受 SparkleConfetti 抑制链覆盖）。

6. **模块 achievement 的实现差量为零。** 卡 modules 含 achievement，但 MODULE_MATRIX
   achievement 行处置（「只为真实成果或已定义行为展示轻庆祝；缺席不惩罚；不改原奖励
   账本」）经差量举证已满足：解锁弹窗 barrierDismissible+关闭钮、庆祝受低刺激档抑制
   （本卡正反钉）、奖励走既有账本（本卡零触碰）。D04 负责其语义面，本卡不重写。

7. **商店路由仍可深链直达（既有形态）。** `/shop` 路由在 routes.dart 挂载（深链兜底、
   errorBuilder 兜底语义），本卡按「维持 HIDDEN」只钉零入口零推广，不撤路由——撤路由
   属 shop 行处置变更（需裁决），非本卡差量。

8. **全量 flutter test 长尾环境性风险。** 主检出基线存在个别依赖 10.0.2.2:8080 网关
   live 调用的 goldens 测试在全量并发跑时网络抖动失败（U11 记录 q03 goldens
   tearDownAll 一例，单测复跑全绿）。本卡零触碰该域；如复现按同口径归因，不计回归。


## 一审勘误（C-2）：N9 基线下调归属分解（receipt 1a443b5f）
- 本卡净贡献：arb 258→256（leaderboardSelfAnchorLoadFailed zh/en 占位删除）+ bareCatchVar 73→72（self_anchor_screen getter 化）；catchVarToString 净降 0。
- 260→258 / 76→73 / 78→77 差额=开卡前已陈旧的基线导入（V3-FIX-490 删 learning-mode 孤儿屏+键；understanding_overview_view -3 为 U03 时代修复；U11 receipt §0 已实测记录 258/73/77 PASS）——update-baseline 导入陈旧差量为守卫工具固有行为，非本卡修复亦非掩盖。
- 守卫脚本零改动、三检测维度原样、无任何检测面弱化（一审逐处 diff 核+双探针实证）。
