"""A-08 · Aurora 纵向/消融评估 harness（四臂对照：no-memory / no-experience / fixed-policy / full）。

评估对象 = 生产 Aurora 决策服务面（零重建、零语义 mock）：

- **恢复旅程面**：``app.services.stuck_journey_service.StuckJourneyService``
  （J-05 旗舰恢复入口；真源读侧 Goal/Task/stuck-signal → A-03 诊断 → 单问
  闭环 → 纠正反馈环）——DB = sqlite 隔离，时间戳 = 可控时钟 backdate；
- **chat 决策面**：``app.services.friction_chat_wiring.FrictionChatWiringService``
  （WIRING-1 生产接线：spine 状态 + A-05 patch 重排 + A-02 规则评估 + ask
  闭环）——Redis 用 fakeredis（与单测同款基建绑定）+ 真实 spine
  ``StateRegister`` 累积经验状态；
- **经验回路**：真实 D-05 ``InterventionLifecycleService``（exposure/accept/
  outcome 关联）+ 真实 A-05 ``PolicyPatchService``（propose → admit 证据门 →
  confirm/自动激活 → patched_decision_inputs 重排）。

四臂在同一 persona 时间线（同 seed、同 ground truth、同世界事件）上只差异
Aurora 的能力面（输入投影面消融，不改产品代码）：

- ``full``：全部能力（记忆事实 + 纠正记忆 + spine 经验 + A-05 适应）；
- ``no-memory``：记忆面消融——失败痕迹/纠正不落库（旅程面读不到历史），
  spine 与 patch 仍在；
- ``no-experience``：经验面消融——spine 不写、patch 不提议（chat 面无适应），
  记忆事实仍在；
- ``fixed-policy``：固定模板基线——无诊断/无澄清/无适应，任何卡点会话恒回
  固定干预（``explain``）；零引擎调用。

指标全部为确定性程序计算（raw → summary 纯函数复算），模型 judge 零使用。
"""
