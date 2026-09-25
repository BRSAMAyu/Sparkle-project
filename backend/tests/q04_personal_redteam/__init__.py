"""Q-04 · Personalization / Overpersonalization 独立红队 harness 包.

纪律（卡面 + PERSONALIZATION_EVAL.md）：
- 世界 = 模拟对象（A-08 PersonaWorld 同源基建零重建）；个性化语义零直写——
  全部经真实服务面（MemoryService 写/删/撤回、ContextPackBuilder 全漏斗、
  StuckJourneyService / FrictionChatWiringService 决策、PolicyPatchService、
  SquadService / SeedLibraryService 跨用户面）；
- paired design：同一 current context，个性化开/关双臂（或新旧偏好双臂），
  臂标识抹除后交程序化 rubric 盲评（模型 judge 0 次）；
- 统计口径四量：precision / invalid / overpersonalization / uplift；
  invalid=0 硬门；失败案例原样保留。
"""
