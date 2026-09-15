# 计划管理模块 (Plan Management) - 功能描述文档

## 模块概述

计划管理模块是Sparkle应用中负责学习计划管理的核心模块。该模块支持两种类型的计划：短期冲刺计划（Sprint Plan）和长期成长计划（Growth Plan），帮助用户设定学习目标、跟踪进度并生成相关任务。

## 后端实现 (PlanService)

### 当前实现状态

根据代码分析，后端的PlanService存在以下情况：
- API路由已定义：`/api/v1/plans`
- API端点已注册到路由器
- 但`plan_service.py`文件为空，实际业务逻辑未实现
- API端点`list_plans`仅返回空数据

### API接口现状

#### 已定义的API端点
- `GET /api/v1/plans`: 列出计划（当前返回空数据）
- 通过路由文件注册到系统中

### 数据模型

#### 计划类型 (PlanType)
- `sprint`: 冲刺计划 - 短期目标导向
- `growth`: 成长计划 - 长期发展导向

#### 计划状态 (PlanStatus)
- `active`: 激活状态
- `inactive`: 未激活状态

### 核心表结构
1. **plans**: 计划表
   - id: 计划唯一标识
   - user_id: 所属用户ID
   - name: 计划名称
   - type: 计划类型
   - description: 计划描述
   - target_date: 目标日期（冲刺计划使用）
   - daily_available_minutes: 每日可用分钟数
   - total_estimated_hours: 预估总小时数
   - mastery_level: 掌握等级
   - progress: 进度百分比
   - is_active: 是否激活

## 前端实现

### 主要组件
- **SprintScreen**: 冲刺计划界面
  - 显示当前激活的冲刺计划
  - 展示计划进度和剩余天数
  - 显示计划相关任务列表
  - 提供计划创建入口

- **GrowthScreen**: 成长计划界面
  - 显示用户的成长计划列表
  - 展示计划的掌握等级和进度
  - 提供计划管理功能

### 功能特性
- 计划进度可视化
- 目标日期跟踪
- 任务关联展示
- 计划创建和管理

## API 接口

### 当前API端点
- `GET /api/v1/plans`: 获取计划列表（返回空数据）
- `POST /api/v1/plans`: 创建计划（未实现）
- `GET /api/v1/plans/{id}`: 获取计划详情（未实现）
- `PUT /api/v1/plans/{id}`: 更新计划（未实现）
- `DELETE /api/v1/plans/{id}`: 删除计划（未实现）

## 前端数据模型

### PlanModel
- id: 计划唯一标识
- userId: 用户ID
- name: 计划名称
- type: 计划类型 (sprint/growth)
- description: 计划描述
- targetDate: 目标日期
- dailyAvailableMinutes: 每日可用分钟数
- totalEstimatedHours: 预估总小时数
- masteryLevel: 掌握等级
- progress: 进度百分比
- isActive: 是否激活
- createdAt: 创建时间
- updatedAt: 更新时间
- tasks: 相关任务列表

### PlanCreate
- name: 计划名称
- type: 计划类型
- dailyAvailableMinutes: 每日可用分钟数
- description: 计划描述
- targetDate: 目标日期
- subject: 关联科目

### PlanUpdate
- name: 计划名称（可选）
- description: 计划描述（可选）
- dailyAvailableMinutes: 每日可用分钟数（可选）
- isActive: 激活状态（可选）

## 关键业务流程

### 冲刺计划流程
1. 用户创建冲刺计划
2. 设置目标日期和每日时间
3. 计划自动关联相关任务
4. 跟踪进度直到目标日期
5. 提供完成反馈

### 成长计划流程
1. 用户创建长期成长计划
2. 设定掌握目标
3. 持续跟踪学习进度
4. 根据学习情况调整计划

## 模块关系

### 与任务模块的集成
- 计划可包含多个任务
- 任务完成影响计划进度
- 支持计划内任务生成

### 与知识星图模块的集成
- 计划目标与知识点关联
- 学习进度影响计划状态
- 知识掌握度影响计划评估

### 与推送模块的集成
- 接近截止日期的冲刺计划触发推送
- 计划进度提醒推送

### 与LLM模块的集成
- AI辅助计划创建和调整
- 智能任务生成

## 当前实现状态总结

### 已完成部分
- 前端界面实现（SprintScreen、GrowthScreen）
- 前端数据模型定义
- 前端状态管理（Riverpod providers）
- 前端API调用层（Repository）
- API路由定义

### 待实现部分
- 后端PlanService业务逻辑
- 完整的CRUD操作
- 计划与任务的关联逻辑
- 进度计算和更新逻辑

## 技术亮点（前端）

### 1. 状态管理
- 使用Riverpod进行状态管理
- 完整的PlanProvider实现
- 异步数据加载和错误处理

### 2. 用户体验
- 进度可视化展示
- 目标日期提醒
- 任务关联展示

### 3. 响应式设计
- 刷新和加载状态管理
- 错误处理和重试机制

## 扩展性考虑

### 1. 模块化设计
- 前端组件模块化
- 服务层与UI层分离

### 2. 可配置参数
- 计划类型可扩展
- 进度计算规则可调整

### 3. API兼容性
- 为后端实现预留接口
- 前后端分离架构

## 待完善建议

### 1. 后端实现
- 完成PlanService业务逻辑
- 实现完整的CRUD操作
- 添加进度计算逻辑

### 2. 数据验证
- 计划创建参数验证
- 业务规则验证

### 3. 性能优化
- 计划数据缓存
- 分页查询支持
