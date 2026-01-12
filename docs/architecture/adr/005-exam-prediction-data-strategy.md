# ADR-005: 考点预测数据粒度与评估协议 (Month 19+)

| 属性 | 内容 |
| :--- | :--- |
| **状态** | Accepted (已决策) |
| **日期** | 2026-01-04 |
| **范围** | Exam Prediction (Month 19-24), 数据埋点 (Month 1-18) |
| **驱动目标** | 确保 Month 19 启动模型训练时“数据可训练、可评估、可迭代” |
| **Owner** | AI Lead |
| **Reviewers** | Data Scientist, Product Manager |
| **Next Review** | Month 18 (Pre-Training Check) |

## 背景

考点预测目标是输出 Top-K 知识点及解释。已规划 GNN+LLM，但模型上限主要取决于数据质量与评估科学性。

## 决策

1.  **引入“题目 (Question/Item)”为一等实体 (Required)**
    *   数据体系必须支持 `exam` → `questions` → `knowledge_points` 的映射。
2.  **所有训练特征必须具备事件时间 (event_time) 并支持“考试日前截断”**
    *   训练集构建以 `exam_date - T` 为特征截止点（T=7天），防止时间泄漏。
3.  **评估必须采用时间切分 (Time-based split)**
    *   按学科/学校/学期分桶，严禁随机切分。

## Label 口径 (必须冻结)

*   **Ground Truth 源头**: 以“题目级标注”为准：`question_id` -> `{node_id...}`。
*   **多对多映射**: 若一个题对应多个 node，均计入真值集合；可选记录 `relation_strength`。
*   **评估命中判定**: 以 `node` 粒度进行。预测的 Top-K nodes 与真值 nodes 集合取交集。

## Non-goals (非目标)

*   本阶段 **不引入**：基于题目内容的语义理解（Content-based Embedding），仅使用 ID 和图结构。
*   本 ADR **不覆盖**：主观题的自动评分逻辑。

## Rollout (渐进上线策略)

1.  **Data Collection**: 上线埋点，收集 6 个月以上的用户行为与考试数据 (Month 1-18)。
2.  **Baseline Validation**: 使用简单统计基线 (Frequency) 验证评估流程畅通 (Month 19)。
3.  **Model Training**: 启动 GNN 训练，对比基线 (Month 20-22)。
4.  **Shadow Deployment**: 影子模式运行，记录预测结果但不推送 (Month 23)。
5.  **Full Release**: 对 HitRate 达标的学科/学校开启推送 (Month 24)。

## Verification (验收与证据)

*   **必须产出证据**: 离线评估报告，显示 GNN 在 Test Set (时间切分) 上显著优于 Frequency 基线。
*   **必须通过检查**: 每一条训练样本的特征时间戳必须早于 Label 对应的考试时间。
*   **必须具备回滚**: 一键降级回统计基线 (Baseline) 的开关。