# Sparkle 六个断点完整对齐文档

> 日期: 2026-04-03  
> 参与者: 创始人 + 多位产品/技术专家 + Codex 持续实施与汇总  
> 状态: 当前阶段总对齐文档  
> 版本: 1.0  
> 用途: 统一记录从产品共识形成到六个断点推进过程中的目标、实现、验收、当前状态与未完成事项

---

## 1. 这份文档的定位

这份文档不是新的产品总纲，也不是某一轮开发日报。

它的作用是把以下内容统一收口:

1. 我们为什么提出“六个断点”。
2. 这些断点分别解决什么核心问题。
3. 从最开始的产品共识，到今天为止，我们已经真实完成了什么。
4. 哪些工作已经达到“主链成立”。
5. 哪些工作还没有完成，或者只完成了 MVP 版本。
6. 后续继续推进时，团队应该以什么状态判断为准。

这份文档是当前阶段 Sparkle 从“方向共识”走向“系统闭环”的总进度索引。

---

## 2. 与现有文档的关系

本文件建立在以下文档之上:

- `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md`
- `docs/product/SPARKLE_INTERVENTION_LANGUAGE_SYSTEM_2026-04-02.md`
- `docs/product/implementation/ADAPTIVE_REPLANNER_PLAN_EXECUTION_IMPLEMENTATION_2026-04-02.md`
- `docs/product/implementation/ERROR_BOOK_TO_KNOWLEDGE_MASTERY_IMPLEMENTATION_2026-04-02.md`

关系如下:

- `SPARKLE_PRODUCT_CONSENSUS` 定义“为什么做、做成什么”。
- `SPARKLE_INTERVENTION_LANGUAGE_SYSTEM` 定义“系统如何以用户可接受的方式交付”。
- 两份 implementation 文档定义断点 1 和断点 2 的最小实施方案。
- 本文档定义“六个断点当前走到了哪里”。

如果后续需要快速对齐，推荐阅读顺序:

1. 产品共识总纲
2. 干预语言体系
3. 本文档
4. 具体实现文档或代码

---

## 3. 从共识到断点：我们是如何收敛到这条主线的

### 3.1 最早的核心问题

这轮讨论最开始要回答的，不是“还能加什么功能”，而是:

- Sparkle 到底为什么存在。
- 它为什么不是另一个 AI 助手或聊天机器人。
- 它真正为用户创造的核心价值是什么。

在多轮专家讨论中，团队逐步形成了以下共识:

1. Sparkle 不应该被定义为“AI 学习助手”。
2. Sparkle 也不应该停留在“AI 学习教练”。
3. Sparkle 的统一定义是:

`AI 学习成长系统`

### 3.2 核心价值判断

最终一致认为，Sparkle 的价值不在于“回答问题更聪明”，而在于:

`比用户更早发现他为什么走不动，并帮助他重新走起来。`

所以 Sparkle 要成立，不能只做到:

- 会看
- 会说
- 会提醒

而必须做到:

- 会发现问题
- 会以低防御方式交付问题
- 会让用户愿意采纳
- 会真实改变下一步计划或路径
- 会验证这次干预是否有效
- 会把结果回流到系统里

### 3.3 最终主闭环

在这一过程中，团队最终把闭环定义为:

`发现问题 -> 以用户可接受的方式交付 -> 用户愿意采纳 -> 产生行动 -> 验证有效 -> 更新系统`

六个断点，正是围绕这条主闭环拆出来的系统性工程分段。

---

## 4. 六个断点总览

| 断点 | 名称 | 原始问题 | 当前状态 |
|------|------|----------|----------|
| 断点 1 | `adaptive_replanner -> 计划执行` | 系统会算调整，但不会真的改计划 | 已完成并验证 |
| 断点 2 | `错题分析 -> 知识节点掌握度` | 系统知道错题，但不知道用户哪里真正没懂 | 已完成并验证 |
| 断点 3 | `plan health -> 事件化` | 系统会判断风险，但没有稳定可消费的事件源 | 已完成并验证 |
| 断点 4 | `行为/计划信号 -> 干预真实交付` | 记录被创建了，但没有真正送达用户 | 已完成并验证 |
| 断点 5 | `参数级调整 -> 主链写回` | intervention 触发了，但没有把参数级策略真正落到计划层 | 已完成并验证 |
| 断点 6 | `干预后效果验证与回流` | 系统不知道这次干预后来到底有没有用 | MVP 已闭环，仍有增强项 |

当前判断:

`六个断点的主链已经全部接通。`

但这不等于“系统已经完全完成”。  
更准确的说法是:

`Sparkle 已经从“会诊断和提示”进入到“会改变路径、接收反馈、验证效果”的阶段。`

---

## 5. 断点 1：adaptive_replanner -> 计划执行

### 5.1 原始问题

在最初状态下，`AdaptiveReplanner` 已经能:

- 判断计划健康度
- 输出 `adaptive_adjustments`
- 区分 `adjust` 和 `replan`

但最大问题是:

`这些调整写进了 PlanState，却没有真正改写用户眼前的计划任务。`

也就是说，系统“知道要变”，但用户“看不到变”。

### 5.2 目标

把下面这条链接通:

`PlanHealthReport -> adaptive_adjustments -> 未来任务 patch -> 用户看到接下来真的变了`

### 5.3 已完成实现

本断点当前已完成的核心实现包括:

1. 新建 `backend/app/services/plan_adjustment_applier.py`
2. 在 `backend/app/orchestration/adaptive_replanner.py` 中完成集成
3. 支持四类增量 patch:
   - 时长放大
   - 难度调整
   - 插入前置复习
   - 收缩并发 / 隐藏远期任务
4. 完成 snapshot、回滚和 user-facing summary 主干
5. 修复了三类关键一致性问题:
   - 回滚不仅回滚 PlanState，也回滚 Task 实体
   - `adaptive_meta` 改为合并写回，不再被覆盖
   - `hidden_task_ids` 也进入 snapshot / notify 主干

### 5.4 当前验收结论

本断点已达到:

`会改计划，并且回滚链成立。`

对应测试:

- `backend/tests/unit/test_plan_adjustment_applier.py`
- 当前与其他断点联跑的一组后端重点回归中，包含在 88 个后端测试通过范围内

### 5.5 对产品的意义

断点 1 完成后，Sparkle 不再只是“建议用户调整”，而是第一次具备了:

`真实改写路径`

这让系统从“成长仪表盘”开始变成“成长系统”。

### 5.6 当前剩余增强项

虽然主链已完成，但后续仍可增强:

1. 更丰富的 patch 类型
2. 更细粒度的任务拆分策略
3. 更强的集成测试覆盖真实计划实体和前端呈现

---

## 6. 断点 2：错题分析 -> 知识节点掌握度

### 6.1 原始问题

最初系统已经能:

- 创建错题
- OCR
- 关联知识节点
- 输出 `error_type`

但核心断裂是:

`错题没有正式写回知识节点掌握度。`

这会导致知识星图更像“任务完成地图”，而不是“理解质量地图”。

### 6.2 目标

把这条链接通:

`错题发生 -> 节点掌握度下降 / 标记风险 -> 错题复习 -> 节点掌握度恢复`

### 6.3 已完成实现

当前已完成:

1. 新建 `backend/app/services/error_book_mastery_sync_service.py`
2. 在 `backend/app/services/error_book_service.py` 两处接入:
   - `analyze_and_link()` 后执行 diagnosis 同步
   - `submit_review()` 后执行 review feedback 同步
3. 引入基于 `error_type` 的权重更新
4. 写入 `StudyRecord`
5. 发布 `node_mastery_updated`
6. 修复了两类关键一致性问题:
   - 事件发布改成提交后一致，不再先发事件再 commit
   - 避免零证据节点污染与双重扣分冲突
7. 补齐节点主干字段同步:
   - `mastery_score`
   - `bkt_mastery_prob`
   - `bkt_last_updated_at`
   - `next_review_at`
   - 首次解锁状态

### 6.4 当前验收结论

本断点已达到:

`错题证据正式进入知识掌握度主干。`

对应测试:

- `backend/tests/unit/test_error_book_mastery_sync_service.py`
- 当前与其他断点联跑的一组后端重点回归中，包含在 88 个后端测试通过范围内

### 6.5 对产品的意义

断点 2 完成后，Sparkle 第一次具备了:

`用户哪里没懂，会影响系统对其知识状态的判断`

这是 Sparkle 与普通任务型学习工具真正拉开差距的一步。

### 6.6 当前剩余增强项

仍未做完的增强工作包括:

1. 多节点复杂传播和高阶知识依赖传播
2. 更精细的错题根因与节点影响映射
3. 与更高层学习报告和首页摘要的联动展示

---

## 7. 断点 3：plan health -> 事件化

### 7.1 原始问题

最初系统已经能通过 `evaluate_progress()` 产出:

- `warning`
- `critical`
- `adjust`
- `replan`

但问题在于:

`这些判断只是内部计算结果，不是一个稳定的、受控的、不会误触发的事件源。`

### 7.2 目标

把下面这条链接通:

`任务反馈 / 计划进度 -> PlanHealthReport -> 受控事件 -> 下游干预与交付`

### 7.3 已完成实现

当前已完成:

1. 新增事件类型 `PLAN_HEALTH_ALERTED`
2. 新建 `backend/app/services/plan_health_signal_service.py`
3. 在 `backend/app/orchestration/adaptive_replanner.py` 的 `_handle_report()` 中发事件
4. 新建 `backend/app/services/plan_health_event_consumer.py`
5. 完成 consumer 启动 / shutdown 注册
6. 建立了关键控制规则:
   - 事件从 `_handle_report()` 发，不从读模型 `evaluate_progress()` 发
   - 事件必须带 `action_taken`
   - 同签名 + 冷却期抑制
   - 严重度升级立即重发
   - 已完成可见交付时，避免二次打扰

### 7.4 当前验收结论

本断点已达到:

`计划风险判断已经从内部读模型变成稳定的干预触发源。`

对应测试:

- `backend/tests/unit/test_plan_health_signal_service.py`
- 当前与其他断点联跑的一组后端重点回归中，包含在 88 个后端测试通过范围内

### 7.5 对产品的意义

断点 3 是“主动纠偏能力”的结构前提。

没有这一层，Sparkle 永远只能:

- 等用户来问
- 等用户来抱怨
- 等用户失败后才调整

有了这一层，系统才第一次真正具备:

`先于用户感知问题`

### 7.6 当前剩余增强项

后续可继续增强:

1. 更完整的恢复事件，例如 `PLAN_HEALTH_RECOVERED`
2. 更细的信号分层和置信度体系
3. 更丰富的行为触发策略与节流规则

---

## 8. 断点 4：行为/计划信号 -> 干预真实交付

### 8.1 原始问题

在断点 4 之前，系统已经会创建 intervention record，但主要问题是:

`记录被创建了，不等于用户真的收到了。`

桥接层曾经存在“预先标记 delivered”的风险，导致系统以为已经交付，但实际没有完成真实送达。

### 8.2 目标

把下面这条链接通:

`行为信号 / 计划健康信号 -> InterventionRecord -> 模板渲染 -> 通知/推送 -> DELIVERED`

### 8.3 已完成实现

当前已完成:

1. 新建 `backend/app/services/intervention_event_consumer.py`
2. 把 `intervention_record.created` 接成真实交付链
3. 在行为桥和计划健康桥中取消“预先 delivered”
4. 引入真实模板渲染和低防御文案交付
5. 完成:
   - 通知投递
   - push history 记录
   - action payload 回写
   - 只有真实交付成功后才转入 `DELIVERED`
6. 统一通知中心对 `intervention` / `intervention_push` 的识别和分类
7. Flutter 端通知中心可正确承接 intervention 通知

### 8.4 当前验收结论

本断点已达到:

`intervention 不再停留在记录层，而是真正进入用户可见交付。`

对应测试:

- `backend/tests/unit/test_phase2_intervention_pipeline.py`
- Flutter 通知中心相关测试

### 8.5 对产品的意义

断点 4 让 Sparkle 从“内部有主意”变成“真的能把主意送达给用户”。

这是干预系统是否成立的最基本门槛。

### 8.6 当前剩余增强项

仍可增强:

1. 更多交付通道，例如 Focus Mode / Chat 内嵌卡片
2. 更细粒度的用户偏好与免打扰策略
3. 更丰富的模板版本与 A/B 实验体系

---

## 9. 断点 5：参数级调整 -> 主链写回

### 9.1 原始问题

断点 4 解决了“交付”，但仍有一个更深的问题:

`系统把 intervention 发出去了，不等于参数级策略真的改写进了计划。`

也就是说，交付和执行层仍可能分离。

### 9.2 目标

把下面这条链接通:

`plan-backed intervention -> ParameterCompiler -> adaptive_adjustments -> PlanAdjustmentApplier -> 任务层 patch`

### 9.3 已完成实现

当前已完成:

1. 在 `backend/app/services/intervention_event_consumer.py` 中接入:
   - `ParameterCompiler`
   - `PlanAdjustmentApplier`
2. 将 `parameter_compilation` 结果写回 `record.action_payload`
3. 记录:
   - `result`
   - `affected_task_count`
   - `inserted_task_count`
   - `hidden_task_count`
   - `decision_log_entry_id`
4. 增加最小观测指标:
   - delivery success / suppressed
   - push history count
   - parameter compilation result

### 9.4 当前验收结论

本断点已达到:

`intervention 可以直接驱动参数级策略写回计划主链。`

这意味着 Sparkle 不再是“发一个建议”，而是已经开始:

`发建议的同时，直接把系统状态和计划参数改掉。`

### 9.5 对产品的意义

断点 5 是从“交付层成长系统”进入“执行层成长系统”的关键一步。

它让系统开始具备:

`干预不是嘴上说，而是同步重写路径`

### 9.6 当前剩余增强项

可继续增强:

1. 更多 trigger 到参数策略的映射
2. 更细的 patch 解释和前端可视化
3. 更强的参数效果追踪和策略版本管理

---

## 10. 断点 6：干预后效果验证与回流

### 10.1 原始问题

这是最关键也最晚接的一条链。

在断点 6 之前，系统最大的问题是:

`系统不知道某次干预后来到底有没有用。`

也就是:

- 发出干预了
- 用户可能也看到了
- 甚至计划也改了

但系统并不清楚:

- 用户是不是接受了
- 是不是开始执行了
- 后来有没有真的改善
- 这个策略以后还应不应该继续用

### 10.2 目标

把下面这条链接通:

`DELIVERED -> SEEN / ACCEPTED / ACTED -> outcome verification -> evidence -> strategy feedback`

### 10.3 已完成实现

当前已完成的 MVP 包括两个部分。

#### A. 真实交互状态回传

后端:

1. 新增 `POST /notification-center/notifications/{notification_id}/intervention-action`
2. 将通知中心操作同步到 `InterventionRecord` 状态机
3. 支持:
   - `seen`
   - `accepted`
   - `acted`
   - `dismissed`
   - `snoozed`
4. `mark_notification_read`、删除、全部已读等链路也会同步 intervention 状态

移动端:

1. intervention 通知卡片新增:
   - 接受建议
   - 开始这步
   - 稍后
2. `SEEN / ACCEPTED / ACTED` 从通知中心真实上报回后端
3. 本地状态会同步更新，避免只靠后端回拉

#### B. outcome verification 与回流

当前已完成:

1. `backend/app/services/card_protocol/outcome_verifier.py` 读取:
   - `parameter_compilation`
   - patched task count
   - post-intervention `feedback_log`
   - `plan_health_recovered`
   - `mastery_improved`
2. outcome 评估不再只看 acted/no acted，而是看:
   - 是否有真实参数落地
   - 干预后是否出现积极反馈
   - 干预后是否仍连续负反馈
3. outcome 会反向影响 strategy learning feedback

#### C. 前端可见化

当前已完成:

1. 通知详情视图会展示:
   - 当前交互状态
   - 验证结果
   - 参数调整摘要
   - 验证证据摘要
2. 通知分析页会展示:
   - total accepted
   - total acted
   - intervention acceptance rate
   - intervention action rate
3. 统一通知返回会 enrich intervention 的:
   - `acceptance_status`
   - `outcome_status`
   - `outcome_evidence`
   - `parameter_compilation`

### 10.4 当前验收结论

本断点当前可评价为:

`MVP 主闭环已成立。`

更准确的说:

`系统已经能记录、接收、验证并展示干预后结果，但距离“完美验证系统”仍有增强空间。`

### 10.5 对产品的意义

断点 6 的完成，意味着 Sparkle 第一次真正具备了:

`因果证据闭环`

也就是:

1. 发现问题
2. 做出干预
3. 用户是否采纳
4. 后来是否变好
5. 系统下次如何学得更准

这正是 Sparkle 长期壁垒的起点。

### 10.6 当前剩余增强项

这是六个断点里未完成事项最多的一段，主要包括:

1. outcome verifier 的定时任务 / 调度化运行仍需正式落地
2. 目前移动端真实上报主要接在通知中心，尚未覆盖 Chat / Focus Mode / 其他 intervention 表面
3. intervention 详情目前是增强弹窗，不是独立详情页
4. analytics 目前已支持 accepted / acted，但还没有按 trigger / intent / cohort 的深度漏斗
5. 缺少一条完整的端到端自动化测试:
   `信号产生 -> intervention 交付 -> 用户操作 -> outcome verifier -> analytics / detail view`

---

## 11. 当前可验证状态

截至 2026-04-03，当前至少有以下重点验证基线:

### 11.1 后端重点回归

已通过:

```bash
cd backend && pytest \
  tests/unit/test_plan_adjustment_applier.py \
  tests/unit/test_error_book_mastery_sync_service.py \
  tests/unit/test_plan_health_signal_service.py \
  tests/unit/test_phase2_intervention_pipeline.py -q
```

结果:

- `88 passed`

这组测试覆盖了:

- 断点 1 的计划 patch / rollback
- 断点 2 的错题掌握度同步
- 断点 3 的 plan health signal
- 断点 4/5/6 的 intervention pipeline、状态迁移、analytics enrich 与 outcome evidence

### 11.2 Flutter 通知中心相关回归

已通过:

```bash
cd mobile && flutter test \
  test/widget/intervention_notification_model_test.dart \
  test/widget/overflow_regression_test.dart
```

结果:

- `14 passed`

这组测试覆盖了:

- intervention 通知模型
- interaction state 显示规则
- 通知卡片 CTA
- 通知中心与分析页相关 UI 回归稳定性

### 11.3 语法与基础校验

本轮相关 Python 文件已通过 `py_compile`。  
本轮相关 Dart 文件已完成 `dart format`。

---

## 12. 当前系统所处阶段

如果把当前阶段放在整个成长系统建设路径里看，Sparkle 已经跨过了最关键的一道坎:

`从“模块很多但闭环不成立”进入“六条主断点已接通，系统开始形成证据闭环”。`

当前更准确的阶段判断是:

### 12.1 已经完成的跨越

Sparkle 已经不再只是:

- 会生成计划
- 会记录错题
- 会发提示

而是已经开始做到:

- 改写真实计划
- 更新真实掌握度
- 事件化风险
- 真实交付干预
- 参数级写回
- 验证并展示干预结果

### 12.2 还没有完成的跨越

Sparkle 还没有完全进入“成熟成长系统”阶段。

当前仍未完成的更高层工作包括:

1. 全渠道 intervention 状态回传
2. 更完整的效果验证调度与运维可观测性
3. 更深的 analytics / funnel / cohort 视图
4. 更成熟的前端详情体验和运营视图
5. 更长链路的 E2E 自动化验证
6. 与首页、报告、周摘要、策略面板的系统级联动

---

## 13. 未完成事项清单

下面列的是“当前阶段仍应明确记账”的未完成事项。

### 13.1 产品与体验层

1. intervention 详情仍是增强弹窗，不是完整详情页
2. 目前真实状态上报主要发生在通知中心，其他交互表面尚未统一
3. accepted / acted 虽已进入分析页，但未形成更完整的干预漏斗和 intent 分析
4. 还未把断点 6 结果系统性外显到首页、报告、周报、成长摘要

### 13.2 系统与调度层

1. outcome verifier 需要正式定时任务化，而不是只依赖手动或局部调用
2. intervention 结果回流尚未形成全局策略面板或运营监控
3. 更多 trigger / channel / parameter 组合还未完全覆盖

### 13.3 测试与工程层

1. 缺少完整 E2E 自动化测试
2. 当前 warning 中仍有既有 Pydantic/SQLAlchemy 历史警告，未纳入本轮处理范围
3. 断点 4/5/6 尚未各自沉淀成独立 implementation 文档，当前主要由代码和本对齐文档承接

---

## 14. 后续建议

如果以“继续把成长系统做深”为目标，建议后续按下面顺序推进。

### 14.1 第一优先

把断点 6 从 MVP 做成稳定机制:

1. outcome verifier 定时化
2. intervention 结果回流的监控与运营看板
3. 多表面状态回传统一

### 14.2 第二优先

把“系统知道结果”升级成“用户也真正感受到成长证据”:

1. 首页成长摘要
2. 周报 / 报告整合
3. intervention 详情页

### 14.3 第三优先

继续提升策略学习深度:

1. 更多 parameter strategy 的效果验证
2. 更细 trigger / intent 漏斗
3. 更长期的因果证据积累

---

## 15. 最终总结

从产品共识形成到今天，Sparkle 已经完成了一个非常关键的转变。

最开始，我们面对的问题是:

`系统有很多模块，但没有一条真正成立的成长主链。`

而现在，至少在六个关键断点上，我们已经把主链接成了:

`诊断 -> 交付 -> 采纳 -> 改写路径 -> 验证 -> 回流`

这不意味着 Sparkle 已经完成。  
但它意味着 Sparkle 已经不再只是“关于成长的产品叙事”。

它开始成为:

`一个真的能在用户成长过程中发现问题、改变路径、记录证据并从中学习的 AI 学习成长系统。`

这就是当前阶段最重要的里程碑。
