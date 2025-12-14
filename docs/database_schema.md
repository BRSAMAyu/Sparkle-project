# Sparkle 数据库设计文档

## 概述

本文档描述了 Sparkle 应用的数据库模型设计。

## 技术栈

- **主数据库**: PostgreSQL 14+ (生产环境)
- **开发数据库**: SQLite 3 (可选)
- **ORM**: SQLAlchemy 2.0
- **迁移工具**: Alembic

## 数据模型

### 1. 用户表 (users)

用户基本信息和个性化设置。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 用户唯一标识 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 邮箱 |
| hashed_password | VARCHAR(255) | NOT NULL | 加密密码 |
| nickname | VARCHAR(100) | NOT NULL | 昵称 |
| avatar_url | TEXT | NULL | 头像 URL |
| flame_level | INTEGER | DEFAULT 1 | 火花等级 (1-10) |
| flame_brightness | FLOAT | DEFAULT 0.5 | 火花亮度 (0-1) |
| depth_preference | FLOAT | DEFAULT 0.5 | 深度偏好 (0-1) |
| curiosity_preference | FLOAT | DEFAULT 0.5 | 好奇心偏好 (0-1) |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

### 2. 任务表 (tasks)

学习任务卡片。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 任务 ID |
| user_id | UUID | FK(users.id), NOT NULL | 所属用户 |
| plan_id | UUID | FK(plans.id), NULL | 关联计划 |
| title | VARCHAR(255) | NOT NULL | 任务标题 |
| type | ENUM | NOT NULL | 任务类型 |
| tags | JSON | DEFAULT [] | 标签数组 |
| estimated_minutes | INTEGER | NOT NULL | 预计耗时(分钟) |
| difficulty | INTEGER | DEFAULT 1 | 难度等级 (1-5) |
| energy_cost | INTEGER | DEFAULT 1 | 能量消耗 (1-5) |
| guide_content | TEXT | NULL | 执行指南(AI生成) |
| status | ENUM | DEFAULT 'pending' | 任务状态 |
| started_at | TIMESTAMP | NULL | 开始时间 |
| completed_at | TIMESTAMP | NULL | 完成时间 |
| actual_minutes | INTEGER | NULL | 实际耗时 |
| user_note | TEXT | NULL | 用户备注 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**任务类型 (type)**:
- `learning`: 学习型
- `training`: 训练型
- `error_fix`: 纠错型
- `reflection`: 反思型
- `social`: 社群型
- `planning`: 规划型

**任务状态 (status)**:
- `pending`: 待开始
- `in_progress`: 进行中
- `completed`: 已完成
- `abandoned`: 已放弃

### 3. 计划表 (plans)

冲刺计划和成长计划。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 计划 ID |
| user_id | UUID | FK(users.id), NOT NULL | 所属用户 |
| name | VARCHAR(255) | NOT NULL | 计划名称 |
| type | ENUM | NOT NULL | 计划类型 |
| target_date | DATE | NULL | 目标日期(冲刺计划) |
| description | TEXT | NULL | 计划描述 |
| daily_available_minutes | INTEGER | DEFAULT 60 | 每日可用时间 |
| mastery_level | FLOAT | DEFAULT 0.0 | 当前掌握度 (0-1) |
| is_active | BOOLEAN | DEFAULT true | 是否激活 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**计划类型 (type)**:
- `sprint`: 冲刺计划
- `growth`: 成长计划

### 4. 对话消息表 (chat_messages)

用户与 AI 的对话记录。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 消息 ID |
| user_id | UUID | FK(users.id), NOT NULL | 所属用户 |
| session_id | UUID | NOT NULL | 会话 ID |
| task_id | UUID | FK(tasks.id), NULL | 关联任务 |
| role | ENUM | NOT NULL | 消息角色 |
| content | TEXT | NOT NULL | 消息内容 |
| actions | JSON | NULL | 结构化动作 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

**消息角色 (role)**:
- `user`: 用户
- `assistant`: AI 助手
- `system`: 系统

### 5. 错误档案表 (error_records)

用户的错题和错误记录。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 记录 ID |
| user_id | UUID | FK(users.id), NOT NULL | 所属用户 |
| task_id | UUID | FK(tasks.id), NULL | 关联任务 |
| subject | VARCHAR(100) | NOT NULL | 学科/课程 |
| topic | VARCHAR(255) | NOT NULL | 知识点 |
| error_type | VARCHAR(100) | NOT NULL | 错误类型 |
| description | TEXT | NOT NULL | 错误描述 |
| correct_approach | TEXT | NULL | 正确解法 |
| frequency | INTEGER | DEFAULT 1 | 出现频次 |
| last_occurred_at | TIMESTAMP | NOT NULL | 最近出现时间 |
| is_resolved | BOOLEAN | DEFAULT false | 是否已解决 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

## 索引设计

### users 表
- `idx_users_username` ON (username)
- `idx_users_email` ON (email)

### tasks 表
- `idx_tasks_user_id` ON (user_id)
- `idx_tasks_plan_id` ON (plan_id)
- `idx_tasks_status` ON (status)
- `idx_tasks_created_at` ON (created_at)

### plans 表
- `idx_plans_user_id` ON (user_id)
- `idx_plans_is_active` ON (is_active)

### chat_messages 表
- `idx_chat_user_id` ON (user_id)
- `idx_chat_session_id` ON (session_id)
- `idx_chat_created_at` ON (created_at)

### error_records 表
- `idx_error_user_id` ON (user_id)
- `idx_error_subject_topic` ON (subject, topic)
- `idx_error_is_resolved` ON (is_resolved)

## 关系图

```
users (1) ----< (N) tasks
users (1) ----< (N) plans
users (1) ----< (N) chat_messages
users (1) ----< (N) error_records

plans (1) ----< (N) tasks
tasks (1) ----< (N) chat_messages
tasks (1) ----< (N) error_records
```

## 数据迁移

使用 Alembic 管理数据库版本：

```bash
# 创建新的迁移
alembic revision --autogenerate -m "描述"

# 升级到最新版本
alembic upgrade head

# 回滚一个版本
alembic downgrade -1
```

## 后续优化

- [ ] 添加全文搜索索引（PostgreSQL FTS）
- [ ] 实现向量数据库集成（pgvector）用于知识检索
- [ ] 添加数据归档策略
- [ ] 实现读写分离
