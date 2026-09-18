# 系统审查（全系统审查体系）

按轮次组织的全系统审查与修复记录。每轮 8 个并行审查员（切片互不重叠）+ 修复波（多修复员并行）。

- `round1/` — 第一轮（基线 90daac8a，2026-09-18）：8 份审查报告（01 引擎编排/02 规划执行/03 关键服务/04 引擎基建/05 网关/06 移动核心/07 移动长尾/08 契约安全），`0N-fixes.md` 为对应修复波记录。
- `round2/` — 第二轮复审（基线 ca86bda8，R1 修复已集成）：修复验证 + 运行时/集成视角复审 + 移交专项；`0N-r2-fixes.md`/`0N-r2-fixes.patch` 为对应修复波记录与 diff 快照；`m6-09-interrupt-preserve.md`/`.patch` 为 M6-09「流式取消=中断保留」产品决策的移动端落地记录；`schema-consistency-audit.md`/`.patch` 为 ORM ↔ 迁移链 ↔ 网关快照三方一致性专项（gfix02 + 单头守卫 + 快照重放）；`engine-restore-storm.md`/`.patch` 为会话恢复风暴专项（同步 send_task 冻结事件循环根因 + single-flight/并发钳制/异步投递修复 + 20 并发红绿压测）；`llm-semantics-f1f2.md`/`.patch`（基线 b97a0674）为 AI 功能评测 F-1/F-2 修复（deep_analysis 档真实路由 v4-pro + `DEEP_ANALYSIS_FORCE_FAST_TIER` 逃生阀、推送文案 JSON 稳健解析 + 重试 + 降级遥测、LLMMonitor 属性漂移修复）；`statechart-iterfix.md`/`.patch`（基线 6e9abd97）为 F-1 附带的 execution_review 别名 dict 迭删崩溃修复（`_merge_context_data` 迭代快照 + TestAliasMergeSafety 回归）；`memory-revival.md`/`.patch`（基线 32d2ebe3）为多端实测 MR-1..MR-4 记忆链复活专项（显式记忆口令 fallback 候选、slim 路径记忆窗口 top-3/500 token、grounding 段与实际检索对账、MinIO 凭证对齐 + Celery worker runbook，附 5 次聊天 LLM 预算的端到端验收脚本 `scripts/devtools/acceptance_memory_revival.py`）。 `exam-p1-fixes.md`/`.patch`（基线 6b0c02db）为考试系统 P1×5 修复（网关错题本 gRPC 桥 user-id 注入、诊断掌握度落 canonical sprint 节点、判分服务端化去答案泄漏 + 选项文本兼容、数据结构模板集、移动端诊断入口 + sprint-summary 天数修复）。
- `漏洞台账.md` — 两轮全量发现的清零追踪表（唯一权威状态源）。

切片边界：splash/onboarding/auth/home/chat/task/settings 归 06，其余 35 个 features 归 07；`gen/` 生成物只对照不审。
