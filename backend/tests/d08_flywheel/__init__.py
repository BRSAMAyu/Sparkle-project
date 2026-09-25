"""D-08 · 数据飞轮纵向证明 harness（Day0/Day3/Day7 配对 + 双臂因果差分）。

评估对象 = 生产数据飞轮服务面（零重建、零语义 mock；A-08 harness 同源复用）：

- **决策面**：真实 ``StuckJourneyService`` + ``FrictionChatWiringService``
  （与 A-08 同款调用协议）；
- **记忆面**：真实 ``ContextPackBuilder``（召回→surfaced 全漏斗 + 真实
  ``ContextPackRun`` telemetry）+ 真实 ``MemoryService``（reference outcome /
  retract——M-01/M-08 治理动作真源）；
- **理解面**：真实 D-03 ``UnderstandingDimensionsService`` 取数 + ``core``
  五维纯函数（缺数据 = unknown，永不默认 0/1）+ 真实 Stage20 确定性
  ``SufficiencyJudgeService`` 落行（coverage 数据源）；
- **outcome 面**：真实 D-05 ``InterventionLifecycleService`` exposure/accept/
  outcome 关联（A-08 同款契约载荷）；
- **个性化面**：真实 A-05 ``PolicyPatchService``（propose → admit 证据门 →
  confirm）+ 真实 ``StuckJourneyCorrection`` 纠正环。

协议（``d08_flywheel_spec.v1``，冻结）：

- 人口 = A-08 的 10 persona（复用 ``tests.aurora_ablation.persona``，探针组成 =
  该 persona 首个 episode 的摩擦真值/停滞天数/失败痕迹数/词牌——零新建模）；
- **双臂**：``flywheel``（反馈事件全开）vs ``no_feedback``（同一世界、同探针、
  零反馈事件——PERSONALIZATION_EVAL 的 paired design 的确定性操作化）；
- **三探针**：Day0 / Day3 / Day7 同构（同词牌、同 S/F、同 session 语义）——
  探针间行为差异只可能来自飞轮自身累积的反馈状态；
- **adaptation 因果链**：事件（纠正/patch/记忆反馈）→ 服务读侧证据
  （applied ids / demotion 码 / surfaced 差异）→ 与 no_feedback 臂同日探针的
  行为差分，三段齐备才成立；无效力/有害个性化进台账不筛除。

模型 judge 0 次：全部指标为确定性程序计算（``d08_flywheel_metrics.v1``）。
"""
