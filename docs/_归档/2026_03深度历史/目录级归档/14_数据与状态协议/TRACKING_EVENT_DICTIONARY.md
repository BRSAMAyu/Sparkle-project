# 埋点事件字典 (Data Tracking Dictionary)

> **目标**: Month 1-18 “埋点优先”，让任何模型（规则/回归/GNN）都有干净的训练材料。
> **Owner**: Data Team
> **Last Updated**: 2026-01-04

## 数据契约 (Contract)

*   **版本**: v1.0.0 (任何字段新增/枚举变更必须 bump minor)
*   **兼容性**: 新增字段只允许“可选”；删除字段或修改语义属于 breaking change。
*   **事件幂等**: 同一 `event_id` 必须可安全重复写入（去重规则由后端数据管道定义）。

## PII / 合规 (必须遵守)

*   **Payload 禁止包含**: 姓名、手机号、邮箱、真实试卷原文、聊天原文（除非已脱敏）。
*   **题干内容处理**: 仅存储 Hash 值或引用 `object_id`，原始内容进入受控存储（S3/Blob）。
*   **数据保留策略**: Raw Event 保留 365 天，聚合特征保留 3 年。

## 通用结构 (Schema)

每条事件必须包含以下字段：

| 字段名 | 类型 | 说明 | 约束 |
| :--- | :--- | :--- | :--- |
| `event_id` | UUID | 唯一标识符 | 必填 |
| `user_id` | UUID | 用户 ID | 必填 |
| `tenant_id` | UUID | 租户 ID | 必填 (默认租户需填默认 UUID) |
| `subject_id` | Int | 学科 ID | **业务事件必填** (全局事件如 app_launch 可空) |
| `node_id` | UUID | 知识点 ID | 可空 (题目事件后续关联) |
| `question_id` | UUID | 题目 ID | 可空 |
| `event_name` | String | 事件名称 (枚举) | 必填 |
| `event_time` | Timestamp | 事件发生时间 (UTC) | 必填 (用于时间截断) |
| `payload` | JSONB | 扩展数据 | 视事件而定 |
| `client_ts` | Timestamp | 客户端时间 | 可选 (用于校准) |
| `source` | String | 来源 | 枚举: `mobile`, `web`, `api` |

## 事件枚举 (Events)

### 1. 学习行为 (Learning)
*(subject_id 必填)*

| event_name | 说明 | payload 示例 |
| :--- | :--- | :--- |
| `node_view` | 浏览知识点 | `{"duration_ms": 5000}` |
| `node_mark_important` | 标记重点 | `{"level": "high"}` |
| `node_review_start` | 开始复习 | `{"mode": "flashcard"}` |
| `node_review_finish` | 结束复习 | `{"cards_count": 20, "duration_s": 120}` |

### 2. 做题行为 (Practice)
*(subject_id 必填)*

| event_name | 说明 | payload 示例 |
| :--- | :--- | :--- |
| `question_start` | 开始做题 | `{"type": "choice"}` |
| `question_submit` | 提交答案 | `{"correct": true, "time_spent_ms": 3000, "answer_type": "text", "difficulty_estimate": 3}` |
| `quiz_session_finish` | 练习结束 | `{"total": 10, "correct_count": 8, "duration_s": 300}` |

### 3. 考试数据 (Exam)
*(subject_id 必填)*

| event_name | 说明 | payload 示例 |
| :--- | :--- | :--- |
| `exam_upload` | 上传试卷/回忆版 | `{"image_count": 3, "ocr_status": "pending"}` |
| `exam_label_submit` | 标注题目对应知识点 | `{"relation_type": "strong", "weight": 1.0}` |

### 4. 反馈闭环 (Feedback)
*(subject_id 必填)*

| event_name | 说明 | payload 示例 |
| :--- | :--- | :--- |
| `prediction_view` | 用户查看预测报告 | `{"stay_duration_ms": 15000}` |
| `prediction_feedback` | 预测准确性反馈 | `{"helpful_score": 4, "missed_points": ["uuid-1", "uuid-2"]}` |