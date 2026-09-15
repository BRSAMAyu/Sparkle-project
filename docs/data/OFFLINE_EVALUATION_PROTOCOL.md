# 离线评估协议 (Offline Evaluation Protocol)

> **目标**: 确保考点预测模型在上线前具备可信的衡量标准，避免“离线高分、上线扑街”。
> **Version**: v1.0.0

## 1. 数据划分 (Data Splitting)

**原则**: 必须按 **时间** 和 **场景** 切分，严禁随机 Shuffle。

*   **切分方式**: Time-based split
    *   **Training Set**: 历史学期数据 (e.g., 2024-Fall 及以前)
    *   **Validation Set**: 上一个完整学期 (e.g., 2025-Spring)
    *   **Test Set**: 最近一个完整学期 (e.g., 2025-Fall)
*   **分桶报告**: 不看全局平均值，必须按 `school_id` × `subject_id` × `semester` 输出分桶指标。

## 2. 特征工程约束 (Feature Constraints)

*   **时间截断 (Time Cutoff)**:
    *   对于目标考试日期 `E_date`，所有特征构建只能使用 `E_date - T` (例如 T=7天) 之前的数据。
    *   严禁使用 `E_date` 之后的行为（如考后复盘、成绩录入）作为特征。

## 3. 核心指标 (Metrics)

*   **命中率 (Ranking Quality)**: `HitRate@5`, `HitRate@10`, `NDCG@10`。
*   **校准度 (Calibration)**: `Brier Score` 或 `ECE`。

## 4. 不确定性与显著性 (必须)

*   所有核心指标必须报告 **95% 置信区间 (95% CI)** (通过 Bootstrap 或分桶均值计算)。
*   任何“优于基线”的结论必须满足：在主要分桶中同时成立，且置信区间不重叠。

## 5. 基线对照 (Baselines)

只有当 GNN 模型在 Test Set 上显著优于以下基线时，才允许进入 AB 测试阶段：
1.  **Baseline-1 (Frequency)**
2.  **Baseline-2 (Recency)**
3.  **Baseline-3 (User Weakness)**

## 6. 评估报告模板 (输出格式)

每次实验必须产出如下报告：

```markdown
### Experiment ID: EXP-2026-001
- **数据范围**: 2024-Fall (Train) / 2025-Spring (Test)
- **样本数**: 50 Exams, 2000 Questions
- **核心指标**:
  - HitRate@10: 72.5% (95% CI: [70.1%, 74.9%])
  - vs Baseline-1: +5.2% (Significant)
- **分桶分析**:
  - Best Bucket (Math-CS-101): 85%
  - Worst Bucket (History-Art-202): 45% (Fail)
- **结论**: 
  - [ ] 允许上线 A/B
  - [x] 需优化长尾学科 (History)
```

## 7. 验收标准 (Acceptance Criteria)

*   **MVP 阶段**: `HitRate@10` > 70% (在数据充足的学校/学科分桶中)。
*   **推理性能**: 单次预测耗时 < 2s。