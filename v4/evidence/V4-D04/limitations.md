# V4-D04 · limitations

1. **「有效 outcome」的账本扫描有界（3×100，I01 同款）**：task 完成通道判定依赖 `OutcomeLedgerService.query` 公共读面有界扫描匹配 outcome_id。完成行刚发生时首页必中；若该用户 task 流在扫描窗外堆积 >300 条且目标 outcome 极旧（事件重放场景），未命中 → fail-closed PRACTICED（解锁可见、零融合）。方向选择：参与可见优先于零痕迹；更保守（TRACE_ONLY）或按 id 直查（需账本加 get-by-id 面，归 D-02 锁 owner）都在单点可改。

2. **「独立检验」的边界裁决（预登记挑战①）**：focus 覆盖支撑的 ACTUAL 完成归 PRACTICED 而非 VERIFIED——本卡把「独立检验」收紧到「quiz 物化 / 已解析 verifiable 产物」。`classify_task_completion` 的 focus 覆盖率规则（账本 ACTUAL 语义）不受影响——分歧只在星图消费面。若裁决要放宽，`_HUMAN_VERIFICATION_EVIDENCE_SOURCES` 加 `focus_session` 即可，但会重新打开「时长点亮掌握」通道，与卡面验收①直接冲突，需显式裁决留痕。

3. **展示封顶只盖 authoritative 面（verified 显式传入）**：`_calculate_status` 封顶只在 `verified=False`（图列表/节点详情/测试面，均装配 verified 计数）生效；`verified=None`（未装配证据查询的兼容路径：`predict_next_node` 返回卡、`get_galaxy_graph` 之外的 `from_models` 直呼点）不封顶——D04 前行为逐字节一致（有测试钉住）。全量收口需要给所有 `from_models` 调用点装配计数，属展示面扫尾（注册为 F 线可接项）。`node_capability_channel(None)` 保守标 practiced，数据面不谎称检验。

4. **存量 mastery 的亮度保留**：旧时间累计的存量 mastery 不清洗（卡面「旧时间累计亮度可作为参与足迹」+「迁移不得丢用户数据」）；视觉上未检验节点亮度仍按存量分数渲染（封顶只作用于 BRILLIANT/MASTERED **标签**）。存量 80+ 未检验节点显示 SHINING+0.86 亮度+practiced 通道——「亮但不叫精通」是刻意的组合。

5. **spark 审计行方言修复的范围**：spark 写点的 mastery_audit_log INSERT 此前在 sqlite 纪律方言恒失败（UUID 裸绑 ProgrammingError，生产 asyncpg 正常），本卡顺手补 GUID bindparams（与 G-02 吸收器同款）——这使时长活动痕迹行在测试方言真实落库（行为面回归测试因此可见）。生产语义不变（该行在 PG 本就写入）。

6. **用户级读门是撤回域粗粒度**：`capability_user_read_state` 比「任意未重算撤回 ⇒ pending」，不细分到 outcome/节点级（per-node 精细门 `capability_node_read_state` 保留）。pending 期间全图建议面（predict-next）禁用——保守方向；细粒度按需在消费卡接（事件 payload 已带节点关联）。

7. **sprint 面为差量举证非新面**：「sprint奖励不读AI掌握分」当前仓库已满足（sprint_task_ledger 只读任务账本；奖励路径无 mastery 读点，grep 证据在 run_manifest），本卡零改动仅举证。成就引擎 config 型 `mastery_threshold` 查询读存量 mastery——存量中的 legacy 时间成分（V3 遗留）仍可影响成就判定；D04 后新增 mastery 只能由 VERIFIED 证据产生，存量清洗归数据治理（本卡不动，迁移红线）。

8. **读门/图面缓存的一致性窗口**：`get_galaxy_graph` 是 ttl=600 视图缓存；登记/重算后即时 DEL（本卡新增），但 DEL 失败（Redis 不可达）时最长 10 分钟内响应整体是旧快照（值+读门状态一致地旧——单响应内无自相矛盾）。epoch/账本门是保证层，DEL 只是加速（M-07 同款口径）。

9. **无 UI 截图面**：视觉/数据双区分落在类型化字段（`capability_channel`/`projection_version`/状态封顶判定+测试），Flutter 消费与呈现文案归 F 线卡；本卡无模型调用（零 LLM），无费用面。

10. **main 前进与集成复验**：执行期间 main 前进至 8458d3c7（F03/F04/I07 销账+FIX-560），`git diff --name-only 7fd77b6d..main -- backend/app` 与本卡变更文件零交集；合并时按流程做集成 SHA 复验+全批重跑。

## 一审补充披露（F-1/F-2）

- **F-1（潜在，无生产消费点）**：节点级读门世代源当前用全局记忆 epoch 计数器——纯记忆域 bump（零撤回）会误判节点 stale=True（用户级门正确 fresh）。消费卡接线节点级读门前必须切 `_last_retraction_epoch`（撤回域专用世代）。
- **F-2（V3 既有，非本卡回归）**：`POST /nodes/{node_id}/spark` 接受客户端自报 outcome（quiz/value/confidence）绕过通道分类直接融合并可达成就光子。按 D04 词表客户端自报=SELF_REPORTED 不应融合——独立小卡收口（FIX-562），本卡不越权代改 V3 既有路由。
