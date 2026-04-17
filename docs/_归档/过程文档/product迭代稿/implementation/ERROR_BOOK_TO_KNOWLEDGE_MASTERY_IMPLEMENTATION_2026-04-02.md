# 错题分析 -> 知识节点掌握度实施方案

> 日期: 2026-04-02  
> 适用对象: 后端研发、产品、测试、数据  
> 关联文档:  
> - `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md`  
> - `docs/product/implementation/ADAPTIVE_REPLANNER_PLAN_EXECUTION_IMPLEMENTATION_2026-04-02.md`  
> 状态: 第一版最小可实施方案

---

## 1. 这项工作要解决什么问题

当前 Sparkle 的错题链路已经能做到:

- 创建错题记录
- OCR 提取题目内容
- 检索并关联知识节点
- 输出 `error_type / root_cause / recommended_knowledge`
- 维护错题自身的 `mastery_level`

但当前最大的断裂是:

`错题证据没有正式写回知识节点掌握度。`

结果就是:

- 错题系统知道用户错了什么
- 知识星图系统知道用户学过什么
- 但两者之间没有形成“理解状态更新”的主干

这意味着知识星图很容易变成:

`任务完成地图`

而不是:

`理解质量地图`

本方案的目标是把错题链路正式接入 `UserNodeStatus.mastery_score` 主干。

---

## 2. 当前代码现状

### 2.1 错题链路现状

`backend/app/services/error_book_service.py` 当前会:

1. 创建 `ErrorRecord`
2. 做 OCR 和知识点检索
3. 写入 `latest_analysis`
4. 写入 `linked_knowledge_node_ids`
5. 在复习时更新错题自身的 `mastery_level`

但不会:

- 更新 `UserNodeStatus.mastery_score`
- 写入 `StudyRecord`
- 发布 `node_mastery_updated` 事件

### 2.2 知识掌握度主干现状

系统中已经存在一条成熟主干:

- `UserNodeStatus.mastery_score`
- `StudyRecord`
- `node_mastery_updated` 事件

例如 `backend/app/services/galaxy/stats_service.py` 已经在任务完成时:

1. 更新节点掌握度
2. 写入 `StudyRecord(record_type='task_complete')`
3. 发布掌握度更新事件

说明:

`节点掌握度更新机制并不是没有，而是错题系统没有接进来。`

### 2.3 当前可利用的辅助能力

系统还已有:

- `BKTService.update_mastery(user_id, node_id, correct)`  
  可更新 `bkt_mastery_prob`

- `ErrorRecord.linked_knowledge_node_ids`  
  已经提供错题到节点的关联

- `ErrorRecord.latest_analysis.error_type`  
  已经提供错误类型

这意味着本次实现不需要从零造概念，只要:

`让错题成为节点掌握度的证据源之一`

---

## 3. 目标定义

本阶段目标不是建立完美的认知诊断系统，而是打通最小闭环:

`错题发生 -> 节点掌握度下降 / 标记风险 -> 针对节点复习 -> 节点掌握度恢复`

成功后，系统将第一次具备这样的能力:

- 知识节点掌握度不再只由“学了多久”决定
- 而会被“在哪里持续犯错”真实影响

---

## 4. 设计原则

### 4.1 先保守，不做激进扣分

掌握度是长期状态，不应该因为一道题瞬间崩掉。

所以第一阶段原则:

- 错题只做“有限降权”
- 不做激进清零
- 优先反映风险，不优先惩罚用户

### 4.2 先处理已关联节点

第一阶段只处理:

- `linked_knowledge_node_ids` 已存在的错题

暂不处理:

- 仅靠 `recommended_knowledge` 推断的新节点
- 多节点复杂归因
- 冷启动下的弱关联推断

### 4.3 先让“概念混淆”最有权重

不同错误类型对节点掌握度的影响不应一样。

第一阶段建议权重从高到低:

1. `concept_confusion`
2. `knowledge_gap`
3. `method_wrong`
4. `logic_error`
5. `calculation_error`
6. `reading_careless`
7. `other`

原因:

- 前三类更接近“理解没建立”
- 后几类更像“执行或注意偏差”

---

## 5. 第一阶段最小规则

### 5.1 错题创建后

当错题完成分析并已关联知识节点后:

- 如果存在 `linked_knowledge_node_ids`
- 则对这些节点做轻度掌握度下调
- 并写入一条 `StudyRecord(record_type='error_diagnosis')`
- 同步更新 BKT

### 5.2 下调幅度建议

建议第一阶段采用固定基础值 + 错误类型权重。

示例:

| error_type | mastery_delta |
|------------|---------------|
| concept_confusion | -8 |
| knowledge_gap | -10 |
| method_wrong | -6 |
| logic_error | -5 |
| calculation_error | -3 |
| reading_careless | -2 |
| other | -3 |

约束:

- 单次错题最多对单节点下调 10
- 节点最低不低于 0
- 若关联多个节点，按衰减权重分配

### 5.3 多节点分配规则

如果 `linked_knowledge_node_ids` 有多个:

- 第一个节点: 100% 权重
- 第二个节点: 60%
- 第三个节点: 30%

例如:

- 基础降幅为 -10
- 三个节点分别变成 -10 / -6 / -3

这是为了避免“一个错题把整个相关知识树一起打崩”。

### 5.4 复习后的回升规则

当用户对错题执行 `submit_review()`:

- 不只更新错题自身 `mastery_level`
- 同时回写关联节点掌握度

建议映射:

| performance | node mastery delta |
|-------------|--------------------|
| remembered | +4 |
| fuzzy | +1 |
| forgotten | -2 |

这能形成最小的“错题 -> 节点 -> 复习 -> 节点恢复”闭环。

---

## 6. 技术实现建议

### 6.1 新增服务

建议新增:

`backend/app/services/error_book_mastery_sync_service.py`

职责:

1. 从 `ErrorRecord` 中读取已关联节点
2. 基于 `error_type` 计算节点掌握度变动
3. 更新 `UserNodeStatus`
4. 写入 `StudyRecord`
5. 调用 `BKTService`
6. 发布 `node_mastery_updated` 事件

建议接口:

```python
class ErrorBookMasterySyncService:
    async def apply_error_diagnosis(self, user_id: UUID, error: ErrorRecord) -> list[dict]:
        ...

    async def apply_review_feedback(self, user_id: UUID, error: ErrorRecord, performance: str) -> list[dict]:
        ...
```

### 6.2 接入点

建议接入两个位置。

#### 接入点 A: `analyze_and_link()` 成功落库后

在 `error.latest_analysis` 与 `error.linked_knowledge_node_ids` 成功写入之后:

- 调用 `apply_error_diagnosis()`

这样系统第一次拿到完整错因和关联节点时，就能更新节点掌握度。

#### 接入点 B: `submit_review()` 成功更新错题后

在错题复习状态更新后:

- 调用 `apply_review_feedback()`

这样错题复习行为就能真正影响知识节点状态，而不只是影响错题本自己。

---

## 7. UserNodeStatus 更新规则

### 7.1 获取或创建状态

对每个关联节点:

- 先查 `UserNodeStatus(user_id, node_id)`
- 不存在则创建

创建时默认:

- `mastery_score = 0`
- `is_unlocked = True`
- `study_count = 0`

注意:

错题导致的首次出现，不代表用户掌握它，但代表这个节点应进入用户视野。

### 7.2 更新字段

第一阶段建议更新:

- `mastery_score`
- `last_study_at`
- `updated_at`
- `is_unlocked`
- `study_count`
- `next_review_at`

其中:

- `study_count` 可视为“被证据触达次数”，第一阶段可 +1
- `next_review_at` 可简单设置为更近时间，便于后续复习建议

### 7.3 是否更新 `total_study_minutes`

第一阶段建议:

- 错题分析阶段不增加 `total_study_minutes`
- 错题复习阶段如果有 `time_spent_seconds`，可以折算增加

原因:

- 分析本身不等于真实学习投入

---

## 8. StudyRecord 记录规范

为保证后续分析和报告统一，建议错题链路也写 `StudyRecord`。

### 8.1 新增 record_type

建议增加两种记录类型:

- `error_diagnosis`
- `error_review`

### 8.2 写入时机

1. `analyze_and_link()` 成功后  
   写 `error_diagnosis`

2. `submit_review()` 后  
   写 `error_review`

### 8.3 字段建议

`error_diagnosis`:

- `study_minutes = 0`
- `mastery_delta = 负值`
- `initial_mastery = 更新前 mastery`

`error_review`:

- `study_minutes = time_spent_seconds / 60`
- `mastery_delta = 正或负值`
- `initial_mastery = 更新前 mastery`

这一步非常关键，因为之后:

- 报告系统
- 周报系统
- 进度系统
- 模拟系统

都可以直接吃 `StudyRecord` 主干，而不用为错题单独做旁路统计。

---

## 9. 事件发布

为了接入现有图演化和可视化系统，建议沿用现有事件:

- `node_mastery_updated`

每个受影响节点都发布一次。

原因:

- `galaxy_event_consumer` 已经接这类事件
- 可以减少新事件类型的引入
- 让知识星图、预测和洞察系统自然感知更新

建议 `reason` 字段值:

- `error_diagnosis`
- `error_review`

---

## 10. 风险与防护

### 10.1 风险: 节点误关联导致误扣分

防护:

- 第一阶段仅处理 top 1-3 个强关联节点
- 设置单次最大扣分
- 允许后续 review 回升

### 10.2 风险: 用户掌握度波动过大

防护:

- 错题扣分低于任务完成加分强度
- 单节点短时间内限制最大负向变化

### 10.3 风险: 错题太多导致图大面积变暗

防护:

- 增加冷却窗口
- 同类错误短时间内合并衰减

第一阶段先不做复杂聚合，但建议预留接口。

---

## 11. 第一阶段不做什么

1. 不做复杂根因到多节点链路传播
2. 不做前置节点递归扣分
3. 不做个性化权重学习
4. 不做跨错题聚类后统一更新
5. 不做“预测掌握度”替代真实掌握度

只做一件事:

`让错题正式成为知识掌握度的证据源。`

---

## 12. 测试建议

### 12.1 单元测试

建议覆盖:

1. 无关联节点 -> 不更新
2. 单节点 concept_confusion -> 掌握度下降
3. 多节点 knowledge_gap -> 按衰减权重分配
4. submit_review remembered -> 节点掌握度回升
5. submit_review forgotten -> 节点掌握度继续下降
6. 不会跌破 0
7. 会发布事件
8. 会写 `StudyRecord`

### 12.2 集成测试

建议跑通一个最小场景:

1. 用户已有一个节点 `mastery_score = 55`
2. 创建并分析一个关联到该节点的错题，类型为 `concept_confusion`
3. 节点掌握度下降到 47 左右
4. 用户执行一次 `remembered` review
5. 节点掌握度回升到 51 左右

这条链一旦跑通，就代表断点 2 已经成立。

---

## 13. 成功标准

这项工作的成功，不是“又多了一条同步逻辑”，而是以下四件事成立:

1. 错题证据会真实影响知识节点掌握度
2. 错题复习会真实修复节点掌握度
3. 更新进入 `StudyRecord` 主干
4. 知识星图开始从“任务完成地图”向“理解质量地图”转变

---

## 14. 一句话结论

这项工作的本质不是“让错题系统更复杂”，而是:

`让 Sparkle 第一次真正知道：用户在哪里没懂，并把这份证据写进成长系统的主干里。`

这一步完成后，后续的:

- 动态重规划
- 主动干预
- 学习报告
- 模拟诊断

才会开始拥有更真实的证据基础。

---

**文档状态**: 第一版最小可实施方案  
**建议下一步**: 直接按本方案进入代码实现，优先完成 diagnosis 写回，再补 review 回升链路
