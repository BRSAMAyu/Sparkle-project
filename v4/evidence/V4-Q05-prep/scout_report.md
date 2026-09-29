# V4-Q05 预备侦察报告（scout, 2026-09-30, main@0d182493, 纯只读零写入）

> 用途：Q05（HEAVY, qa-visual 锁, deps 含 U06）派单直接引用。侦察产物非验收证据，Q05 实现时逐条亲验。

## 一、审查矩阵（7 家族×15 态，检查点取自 SCREEN_FAMILIES.md 原文行号）
1. 首页/目标/任务/日历：排序 L3-4/结果标准非大百分比/执行区中心+提交自报语义/日历普通排版/表单先目标成果；键盘替代拖动 L4；U08 改期判例。
2. 对话/卡住/Hybrid/运行台：平直纸面无双框 L7/按段流式增量不抢滚动 L7/工具阶段状态行/卡住 sheet 先原因再决策/Hybrid 三段/Run ID；流式不抢焦点。
3. 记忆/Aurora/理解：项目分组三分区无人格雷达 L10/「来自/仅用于/更改/忘记」L10/清空说明与进度；纠正≠本轮生效辨析 L10。
4. 星图/学习/错题/资料：证据路径可探索 L13/线性列表+缩放+键盘导航 L13/主操作续动作/来源 badge 跳原文；OCR 手输入替代 L13/示例测验隔离；F06 galaxy_edge_list_a11y 判例。
5. 洞察/复盘/报告：一句可核验→≤3 带来源→一调整 L16/无数据明说 L16/印章标类型不盖认证章 L16/图表颜色语义一致；不捏造趋势。
6. 小队/自我锚/光子/成就：先行动共享再装饰 L19/self-anchor 非排行 L19/兑换不暗示付费 L19/真实账本可关庆祝；Shop HIDDEN 禁令——S04 资产账本交叉核对。
7. 账号/设置/通知/异常/长尾：原生输入错误优先 L22/四开关默认不自动播放 L22/深链落对象失效有替代 L22/404 离线登录失效模型失败分流 L22/LABS 只记 fallback；U15 长尾守卫钉。
- 每家族统一 15 态（L25）：默认/空/加载/部分/模型失败/离线/恢复/取消/未知写入/过期/权限失效/200%字体/键盘遮挡/深链返回/减少动态；**截最上层实际画面**禁栈底复用（EVALUATION_PROTOCOL.md:7）。

## 机械执行作业（零新权威，全沿用既有工具）
- 截图规格：B04 GBNF 命名（scripts/devtools/visual_baseline/naming.py）+9 canonical 注册表（states.py:32-130）+U09 三端 viewport 派生（matrix.py）+visual_baseline.py plan/manifest/verify/coverage/diff/report-template。
- 主题轴：F05 成对纪律（4 profile×采集面+*_semantics.txt+同 build 同冻结 seed）；Q05 从 5 面扩 7 家族不另造采集器。
- 弹层顶层抽查：B04 可失败对照模式（折叠 0px 必 FAIL/展开内容可见）；产品 sheet 目标=卡住/dashboard_edit/focus_session_outcome。
- 对比度字体：ACCESSIBILITY_ASSETS.md 阈值（正文≥4.5:1/大字≥3:1/48dp/最终计算色）；F06 判例复算（15 对最低 5.24）；pixel_a11y_f06_test 11 测复用；浏览器 200% 与文本缩放分开 L13。
- 低端等价：Q06 六态抽样不全家重放；reduce-motion=S01 判例（落定终态 vs 静态分支 RGBA 逐字节+label 相等）；oracle=V4_DONE 问 7/8/9。
- golden 纪律：EVALUATION_PROTOCOL.md:24 独立签理由；分母如实（Q06「2 格独立+7 格登记」计数规则）。
- HEAVY/锁：单槽纪律+qa-visual 经 fleet.py（远端未配置 diff 自证口径，F05 判例）。

## 二、B04 残量（deferred 面 → 落点）
| # | 残量 | 现状 | 落点 |
|---|------|------|------|
| 1 | 产品 UI 顶层截图 NOT_RUN | **FIX-558 已解封**（isar 补丁三构建 exit 0） | Q05 直接承接 |
| 2 | dialog/sheet 顶层可失败验证 NOT_RUN | 可采 | Q05 显式作业 |
| 3 | 应用内字号缩放未触及 | F06 组件族面已落，全家族矩阵未跑 | Q05 字体轴承接 |
| 4 | build 维度 FAIL 证据 | 558 后可记真实 build ID | Q05 run_manifest 常规面 |
| 5 | viewer hash 对照缺 | /docs 渠道专属 | 债务台账转登，非 Q05 |
| 6 | 多模式构建独立日志 | — | Q05 纪律注意项 |
| 7 | Android adb 无 | 无证据已装 | 执行风险预登记（web/macOS 先行，U09 matrix 允许差异表） |
- 参考图隔离已闭合：Q05 顺手复核无 jpg 入产品（REFERENCE_ONLY.jpg 仅 02_design）。

## 三-a、FIX-565 typing_text 两案（证据全表见侦察原文/台账）
- 事实：lib 零 import 零调用；初始提交即零接线；F06 迁移 58 行零覆盖；产品现状=ChatRunPhaseIndicator 三阶段+正文直渲染+Aurora 自有 dots；repeat 棘轮占 49 席之一。
- **leader 裁决（2026-09-30）：摘**——按段流式是 SCREEN_FAMILIES L7 明令，打字机逐字相抵触无强语义空位，留案=为保留找装饰位=造活；摘=删文件零连锁+棘轮 49→48 合法（guard 只允许清理出集）+与 U15 孤儿删除同类并案；F06 迁移沉没如实记档。
## 三-b、FIX-569 三 implicit 组件两案
- 事实：三 widgets 零产品调用；预算表本体已接线（press/haptics）；S01 移交令"V4 收口前不得无主"；F03 R1 低成本样本=intervention 卡 mark_seen 上报处单点接线。
- **leader 裁决（2026-09-30）：接线（F03 链低成本样本先行），载体=F03 后续接线小卡即派**——删除会使乐谱 proposalEnter/receiptReplace/evidenceStamp 三行永久无实现、Q06 C4 缺口永久化，与 S01 已验收价值冲突；新小卡避开 F03/Q05 卡面边界；Q08 前置清单登记。

## 四、RF-06 冲突预报
- 分支只在远端（tip 92203d5c，178 commits，mobile/lib 110 文件）；Q05 写入面=evidence+mobile/test（RF-06 该目录 0 命中）+零 mobile/lib——**零写入零文件冲突成立**。
- 事实漂移防火墙：Q05 审查对象绑定 Sparkle-project main SHA（source_sha）；结论不外推 RF-06 lineage。
- 资源竞争实为 Q01/U06 重轨；Q05 起跑以 U06 集成为门。
