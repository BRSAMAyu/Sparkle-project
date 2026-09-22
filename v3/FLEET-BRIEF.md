# Sparkle 舰队使命简报（FLEET-BRIEF v1）

> 主会话维护，每轮唤醒更新。所有任务卡的共同上下文源——派卡时相关节直接嵌入，卡内写明「本卡在战役中的位置」。

## 一、产品愿景（一句话）

**期末只剩一周的大学生，用 Sparkle 备考效果最好、能拿的分最高**——比裸用 GPT/Claude/豆包/DeepSeek 好得多。一切工作以这个北极星排序。

## 二、当前战役（2026-09-23 凌晨起）：「北极星全旅程」

C 线 API 级压缩轮已 **fail=0** 收官（CP-01/CP-03 稳定 pass，TTFT 1-2s、投影 0.6s、星图经网关全链可见）。战役目标：把验证从「单日 API 闭环」推进到**「7 天完整旅程 + 新功能协同成体」**，让北极星从工程指标绿变成用户旅程真。

战役三纵队：
1. **JOURNEY（旅程纵深）**：驱动器补 Day2-Day7 相位——CP-04~08（次日计划适应/复习命中率/覆盖度/后测增益/遗忘率）全部 blocked 的唯一原因是压缩轮无多天数据。制高点卡。
2. **TOUR（功能成体）**：今晚落地的 6 个新面（计划确认/冲刺小队/自习室/小队榜/自我锚/光子兑换）**作为一条用户旅程串测**——单独绿 ≠ 协同可用。
3. **MOBILE（用户可见）**：新后端面在 mobile 的入口盘点与补齐——功能没入口等于不存在。

## 三、四线现状图（2026-09-23 04:5x）

| 线 | 状态 | 下一步 |
|---|---|---|
| A 设计语言 | SPEC v1.0 定稿；B3-CHAT/批3 落地（面积 71.8%/76.3%）；批4 收件箱桥在跑（wt160） | 批4 余项、H2 真人访谈（待用户/组员） |
| B 模型 | Qwen 主力+MiniMax batch+GLM 保留，全链验证完 | 观察期，无卡 |
| C 北极星 | 压缩轮 fail=0；TTFT/投影/星图/幂等全链闭合 | **本战役主战场** |
| D 商业化 | D-COMMUNITY 六卡落地五卡（学出会员/小队/自习室/小队榜/自我锚） | D-COMM-5/6 待价值评估；云端部署已备 |

## 四、共同约束（每卡必守，违反=返工）

1. **口径单一事实源**：任务/完成度=`sprint_task_ledger`（BP-4）；今日视图=`goal_today_view`；galaxy 写路径失效必须走 `invalidate_galaxy_graph_view_cache`+shield 回调（SHIELD-INVAL 模式）。新聚合**禁止**自算一套。
2. **反刷分红线**：任何榜/队内比较只准用 sprint-completion 口径，XP/光子/photon_balance/flame_level 禁入（AST+行为双钉模式照 D-COMM-3/4）。
3. **价值增量红线**：免费闭环行为零变化；光子只经「学出会员」出口变现（D-COMM-2 有界兑换）。
4. **诚实性**：空数据返回诚实空态（`has_ledger_data:false` 式），不造默认值；仪表数字必须有真源。
5. **SPEC（A 线）**：必达项≤2/surface；唯一交互色 accent；语义槽 5；DL-SPEC ratchet 只降不升。
6. **工程红线**：proto→make proto-gen；迁移挂唯一 head+合入验单头；分层（网关禁业务/引擎禁鉴权/handler 走 service）；改动必带回归验证（对比法）；交付物零凭据；遮蔽法处理安全词库。
7. **资源纪律**：定向测试绝不宽扫描（今晚两次熔断）；收工清 pytest-tmp/build/.dart_tool；HEAVY（模拟器/gradle/浏览器）等 swap 闲≥1.2G。

## 五、口径词典（跨卡一致性）

- 「冲刺完成度」= sprint 周期内 ledger 记录的完成任务/计划任务的比率（D-COMM-3 定义，唯一定义点）
- 「自我锚」= 本人近 7 日每日完成度/掌握度增量（D-COMM-1，UTC 窗口）
- 「在场」= study_room_sessions 的进出记录（D-COMM-4，时长仅展示）
- 「可兑换基数」= 审计流水重放（四收入类型+首胜/combo，transfer_in 排除）
- 「星图可见」= 经网关 gRPC 路径 user_status 等价直连（GRAPH-GRPC-SHAPE 契约）

## 六、合入管线（主会话职责，卡不碰）

备份→apply --3way→定向测试（对比法）→commit→push（带重试）→删 worktree→活库迁移→重启探针。Worker 交付 = worktree 改动 + v3-output/<卡>/REPORT.md + changes.patch。
