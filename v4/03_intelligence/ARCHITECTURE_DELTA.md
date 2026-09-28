# AI 架构增量：在已有权威上增加一条可证明的闭环

## 已有结构不动
Flutter → Go Gateway（身份/WS/限流/桥）→ Python Engine（业务与推理）→ PostgreSQL/Redis/Celery。主聊天仍为自研StateGraph，LangGraph仅已有规划用途；不迁框架。权限上下文由网关可信传入，引擎对具体对象/调用能力仍必须做授权边界校验，不能把“网关认证”误当“任何对象都可访问”。

Aurora、memory_preferences、episodic_memories、working_memory、user_preferences、TaskService、sprint_task_ledger、goal_today_view、outcome、runtime和现有A05 policy patch均继续主权。名称是资料定位种子，V4开工由当前代码映射确认；本包不声称新增类已存在。

## 新增逻辑责任，不默认新增服务
```
当前目标/动作/资料/约束
     + 合法历史候选 (原Context Compiler)
     ↓
可用性过滤 + 记忆效用门  [增量 I02]
     ↓
规则快路 / 受限语义选择 / 一次决策性澄清 [增量 I03-I04]
     ↓
既有 AuroraDecision / A05 六字段策略 / Human-Agent-Hybrid
     ↓
既有 Proposal → Confirm → Command → Receipt
     ↓
呈现投影 ExperienceEvent → 文本/像素/声/触 [增量 F03/S01]
     ↓
既有生命周期 + rendered曝光 + outcome/censor/retract [增量 D01-D03]
     ↓
合规经验候选 → 影子验证/回退 [增量 I05]
```

## 新契约最小面
1. ContextSelectionReceipt：输入各权威版本、候选/选用ref、拒用原因、预算、作用于何处、选择器版本。正文仅显示用过的合法依据；debug侧可看摘要但不泄露被拒内容。
2. EpisodeResumeView：existing goal/task/run/last_valid_outcome引用，last_confirmed_step、pending_human_step、expires_at；它是读模型，绝非另一份主任务。原run状态始终优先。
3. ExperienceEvent：呈现事件，不可授予写权限或表示额外业务事实。
4. OutcomeObservation：现有schema按需扩展delivery_state、attribution_level、window_end、censored_reason、evidence_kind与policy_version。新字段向后兼容，老行unknown，禁止回填臆测。

## 同一轮的原子性和过期
读取context版本→生成提案→确认前再校验对象version/memory_epoch/policy_version。期间用户删除记忆，提案转expired并解释“你的设置已更新，需要重新生成”；不是拿旧上下文照样写任务。UI可以先保留用户编辑内容，不能复用过期授权。

在线必要状态更新（用户纠正/撤回）与版本提升沿已有原子事务；离线总结不影响当前确认的可用性。Celery派发/outbox失败不能丢已提交事实，重放幂等；若某读投影落后，UI显式“正在同步”，不以旧事实庆祝第二次。

## 变更策略
扩展字段先shadow读写，旧客户端忽略未知可选字段。数据库只有迁移单头；proto改动先contract-owner提交，再生成Go/Dart/Python，其他Agent只基于已合并契约。新视觉默认off，新的语义选择shadow；在既有kill-switch manifest中登记，不造另一组常量开关。

## 缓存
key绑定user、consent_scope、goal/task version、memory_epoch、policy_version、material_version、selector_version；矫正/删除立即使相关读失效。单纯LLM输出缓存不能代替写动作；匿名demo和真实账号完全隔离。当前State必须读权威或有明确watermark的快照，不能用旧摘要覆盖。
