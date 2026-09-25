"""P-05 · Proactive Longitudinal Evaluation 引擎（多天 persona 时间线驱动）.

纵向评估 P-03（cooldown/mute 反馈回路）+ P-04（auto-execute 授权模型）+
comeback 主动面在多天时间线里的交互行为与恢复/负担两轴量化。

设计纪律（卡面红线）：
- **真源不重建**：生成路径 = 真实 ``comeback_nudge_task``（celery 任务函数直调，
  仅把 ``AsyncSessionLocal`` 重定向到本世界 sqlite 引擎——基建绑定，非语义
  mock）；行动路径 = 真实 ``ActionCommandService`` 统一 command path；反馈路径
  = 真实 ``ProactiveSuggestionFeedbackService``；授权路径 = 真实
  ``ActionPermissionService``。
- **可控测试时钟**：不等待真实时间——``engine.SimClock`` 把模拟时刻（第 d 天 +
  当日钟点）换算成真实时间戳回写活动痕迹/计划窗口/建议投递时间/cooldown 窗口
  尾（与 ``tests/aurora/test_comeback_context.py``、
  ``dbfixture.backdate_proposal_expiry`` 的 backdate 口径同源），随后调用真实
  服务（其内部 ``datetime.now`` 即感知为模拟时刻）。
- **persona 决策是显式模型**：seeded、参数全部落 raw——结论口径里 persona 模型
  是被声明的实验装置，不是被冒充的真实用户。
"""

from __future__ import annotations
