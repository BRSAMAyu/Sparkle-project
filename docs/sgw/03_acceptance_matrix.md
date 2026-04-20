# SGW v2 验收矩阵

> 版本: 1.1 | 日期: 2026-04-21 | 状态: FROZEN (审查修订版)
> 每个 Phase 的通过标准。未全部通过前不可进入下一 Phase。

---

## Phase 0: 范围冻结与抽象确立

| # | 验收项 | 标准 | 验证方法 |
|---|--------|------|----------|
| 0.1 | 设计文档完备 | 4份文档全部完成（scope/abstractions/data_contracts/acceptance） | 文件存在 + 内容非空 |
| 0.2 | 抽象无矛盾 | 01_abstractions.md 中所有抽象互相一致，无循环依赖 | 人工审读关系图 |
| 0.3 | Schema 可执行 | 02_data_contracts.md 的 SQL 可直接执行创建数据库 | `sqlite3 test.db < schema.sql` 成功 |
| 0.4 | 当前代码可映射 | 每个抽象都标注了"当前映射"到 sgw_orchestrator.py 的具体位置 | 行号引用正确 |
| 0.5 | 后续 Phase 可引用 | Phase 1-6 的代码都能引用 Phase 0 的抽象定义，不需要二次改动 | 文审确认 |

---

## Phase 1: 数据底座与可复现性

| # | 验收项 | 标准 | 验证方法 |
|---|--------|------|----------|
| 1.1 | SQLite 数据库创建 | `.sgw_state/sgw_runs.db` 存在且 schema 正确 | `sqlite3` 查询表结构 |
| 1.2 | run_id 机制 | 每次运行有唯一 run_id | 两次运行 run_id 不同 |
| 1.3 | config_hash 可复现 | 同一配置产生同一 hash | 两次相同配置 hash 一致 |
| 1.4 | 历史数据回填 | 现有 sgw_checkpoint.json 数据成功导入 SQLite | 数据库记录数 > 0 |
| 1.5 | 双写兼容 | checkpoint 同时写 JSON + SQLite | 两种格式都存在 |
| 1.6 | 差分查询 | 能对比两次 run 的所有指标差分 | `sgw-export --compare` 有输出 |
| 1.7 | 可复现性验证 | 确定性指标（session/turn计数）偏差 < 1%，统计性指标（violation rate）偏差 < 15% | 需要两次完整运行 |
| 1.8 | 现有功能不退化 | SGW v1 全部功能正常（WebSocket、违规检测、断点续跑） | 运行 30 分钟无错误 |

---

## Phase 2: 对话生成层重构

| # | 验收项 | 标准 | 验证方法 |
|---|--------|------|----------|
| 2.1 | turn_requirements 替换 | 不再有 `turn_index % N` 逻辑 | grep 代码无 `turn_index %` |
| 2.2 | 三轴采样生效 | 每个 session 的 persona_sample 包含三轴连续值 | DB 查询：axis 值呈连续分布 |
| 2.3 | ConversationArc 生成 | 每个 session 有 3-5 个 beat | DB 查询：beats 数在 3-5 范围 |
| 2.4 | State machine 运行 | 每轮 turn 有 TurnDecision 记录 | DB 查询：turn_decision 非空 |
| 2.5 | AI 行为分类 | 每轮 AI 回复有 behavior_class 标签 | DB 查询：ai_behavior_class 非空 |
| 2.6 | 反应性硬约束 | 模拟用户引用 AI 回复内容比例 > 60% | 抽检 50 session |
| 2.7 | Soft violation 下降 | 从当前 36% 降到 < 25%（注：完整达标需 Phase 3 audit 拆分后） | 200+ turns 后统计 |
| 2.8 | 吞吐量提升 | 至少 3x 当前水平（表达层换模型） | turns/hour 对比 |
| 2.9 | 对话真实性 | 抽检 50 session，conversational_responsiveness 维度均值 ≥ 0.70（rule-based 检测：引用率 > 50%） | 自动检测 + 人工抽检 |
| 2.10 | 表达层模型分离 | 表达层用独立模型/提供商，不抢审计额度 | 配置检查 |
| 2.11 | 向后兼容 | hard violation 检测不变，revoke 探测不变 | 功能测试 |

---

## Phase 3: 评估层解耦

| # | 验收项 | 标准 | 验证方法 |
|---|--------|------|----------|
| 3.1 | Audit 拆分 | compliance 和 authenticity 独立评分、独立记录 | DB 查询：两种 audit_type |
| 3.2 | Compliance soft violation | < 5%（audit 拆分后，剔除对话质量问题应显著改善） | 500+ audits 后统计 |
| 3.3 | Authenticity 均值 | ≥ 0.80 | 统计 |
| 3.4 | Audit 输入包含上下文 | audit prompt 包含对话上下文 | prompt 检查 |
| 3.5 | Audit 模型异构 | compliance 和 authenticity 用不同模型/提供商 | 配置检查 |
| 3.6 | 真实性报表 | 能输出"某 persona 轴组合下 authenticity 偏低" | SQL 查询有结果 |
| 3.7 | 人工校准（预留） | 设计了校准流程（Cohen's kappa），但不要求立即执行 | 文档检查 |

---

## Phase 4: 元编排与归因闭环

| # | 验收项 | 标准 | 验证方法 |
|---|--------|------|----------|
| 4.1 | Diagnostic Agent 可运行 | 输入一批失败 session，输出 1-3 个结构化假设 | 运行一次 |
| 4.2 | 假设有证据支撑 | 每个 hypothesis 有 evidence_refs | DB 查询 |
| 4.3 | 实验设计 | 能生成 ExperimentPlan（control vs treatment） | 自动产出 |
| 4.4 | 实验执行 | 能同时跑 control 和 treatment 两组配置 | 运行验证 |
| 4.5 | 统计检验 | 自动计算 p-value 和 effect size | 输出检查 |
| 4.6 | Meta loop 自主运行 | 能自主跑 ≥ 10 轮不需要人介入，且至少 3 轮产生可操作的参数变更 | 运行验证 + 检查 config_changes 非空 |
| 4.7 | 迭代日志 | 每轮产出 1 份可读的 IterationReport | docs/sgw/iterations/ 有文件 |
| 4.8 | 假设验证 | 至少 3 个假设被验证并采纳到主配置 | DB 查询：status="verified" |
| 4.9 | 防局部最优 | random exploration batch 注入正常 | 日志检查 |
| 4.10 | 多样性不坍缩 | persona 轴覆盖率、AI 行为分布保持分散 | 统计检查 |

---

## Phase 5: 通用化脚手架

| # | 验收项 | 标准 | 验证方法 |
|---|--------|------|----------|
| 5.1 | ScenarioSpec 可配置 | 能用一份配置文件切换测试场景 | 创建新 scenario 文件 |
| 5.2 | Stage 17 scenario | 至少一份 Stage 17 的 ScenarioSpec 可运行 | 运行验证 |
| 5.3 | 多场景并行 | 两个 scenario 可同时运行互不污染 | 并行运行 |
| 5.4 | 不改核心代码 | 新 scenario 只需配置文件 + 规则文件 | 代码 diff 检查 |
| 5.5 | Adversarial 反馈 | 攻击成功率作为反馈信号 | 数据流检查 |

---

## Phase 6: 观测与长期运行

| # | 验收项 | 标准 | 验证方法 |
|---|--------|------|----------|
| 6.1 | 仪表板 | 实时展示关键指标 | 访问仪表板 |
| 6.2 | 告警 | 指标连续劣化触发通知 | 模拟劣化测试 |
| 6.3 | 知识检索 | 能检索历史 iteration 报告 | 搜索测试 |
| 6.4 | 7天无人运行 | 平台连续运行 7 天不人工介入 | 运行日志 |
| 6.5 | 健康度查询 | 任意时刻 10 秒内回答"当前健康度" | 实际操作 |
| 6.6 | 操作手册 | 新开发者看手册半天内能上手 | 文档检查 |

---

## 最终验收（六阶段全部完成时）

| # | 全局验收项 | 标准 |
|---|-----------|------|
| F.1 | 可复现 | 任意 run_id 可完整复现指标 |
| F.2 | 可归因 | 任何失败都能切片到具体维度和 hypothesis |
| F.3 | 可迭代 | Meta loop 能自主跑 ≥ 100 轮，累积 ≥ 30 条已验证假设 |
| F.4 | 可复用 | 至少 2 个 ScenarioSpec 并行运行 |
| F.5 | 对话真实 | 人工盲测分辨准确率 < 70%（混入真人对话） |
| F.6 | 合规 | Compliance soft violation < 3%、hard violation = 0 |
| F.7 | 长期可运维 | 连续 7 天无人介入运行 |
| F.8 | 知识沉淀 | iteration 报告可被后续开发者检索和复用 |

---

## Phase 间门控规则

```
Phase 0 PASS → 可进入 Phase 1
Phase 1 PASS → 可进入 Phase 2
Phase 2 PASS + Phase 1 PASS → 可进入 Phase 3
Phase 2 PASS + Phase 3 PASS → 可进入 Phase 4
Phase 4 PASS → 可进入 Phase 5
Phase 5 PASS → 可进入 Phase 6
```

每个 Phase 的验收由审查角色独立执行，不符合标准则打回修改，不可带病进入下一 Phase。
