# Sparkle 社群功能详解

## 概述

Sparkle 社群功能为用户提供了一个社交学习环境，包括好友系统、学习小队、冲刺群等功能。通过社群互动，用户可以与他人共同学习、互相激励、分享进度，增强学习的社交性和持续性。

## 功能模块

### 1. 好友系统

#### 功能概述
好友系统允许用户添加和管理学习伙伴，基于共同课程/考试/作息等因素进行智能匹配，促进学习交流。

#### 核心功能
- **好友搜索**: 基于共同课程、考试等条件搜索潜在好友
- **好友请求**: 发送和响应好友请求
- **好友推荐**: 智能推荐可能认识的人或有共同兴趣的学习伙伴
- **好友互动**: 查看好友学习进度、分享学习成果

#### 数据模型
- **friendships**: 好友关系表
  - `user_id`: 用户ID
  - `friend_id`: 好友ID
  - `status`: 状态（待确认、已接受、已拒绝、已屏蔽）
  - `initiated_by`: 发起者
  - `match_reason`: 匹配原因（共同课程、相同考试等）
  - `created_at`: 创建时间

#### API端点
- `POST /api/v1/community/friends/request` - 发送好友请求
- `POST /api/v1/community/friends/respond` - 响应好友请求
- `GET /api/v1/community/friends` - 获取好友列表
- `GET /api/v1/community/friends/pending` - 获取待处理请求
- `GET /api/v1/community/friends/recommendations` - 获取好友推荐

### 2. 学习小队 (Squad)

#### 功能概述
学习小队是面向长期目标的社群组织，用户可以创建或加入针对特定学习目标的小组，如"每日算法一题小队"、"考研数学基础夯实组"等。

#### 核心功能
- **创建小队**: 用户可以创建具有特定学习目标的小队
- **加入小队**: 通过邀请码或公开搜索加入小队
- **小队管理**: 小队长可以管理成员、设置小队规则
- **进度共享**: 小队成员可以分享学习进度和成果
- **任务协作**: 在小队内分配和协作完成学习任务

#### 小队类型
- **主题型**: 围绕特定学科或主题（如"数据结构学习组"）
- **目标型**: 针对特定目标（如"考研数学冲刺组"）
- **习惯型**: 培养学习习惯（如"每日背单词组"）

#### 数据模型
- **groups**: 群组表
  - `id`: 群组唯一标识
  - `name`: 群组名称
  - `type`: 群组类型（squad/sprint）
  - `description`: 群组描述
  - `focus_tags`: 关注标签（JSON数组）
  - `visibility`: 可见性（公开/私有）
  - `max_members`: 最大成员数
  - `created_by`: 创建者ID
  - `created_at`: 创建时间

- **group_members**: 群成员表
  - `group_id`: 群组ID
  - `user_id`: 用户ID
  - `role`: 角色（owner/admin/member）
  - `joined_at`: 加入时间
  - `flame_contribution`: 火苗贡献值
  - `last_active`: 最后活跃时间

#### API端点
- `POST /api/v1/community/groups` - 创建群组
- `GET /api/v1/community/groups` - 获取我的群组
- `GET /api/v1/community/groups/search` - 搜索公开群组
- `GET /api/v1/community/groups/{id}` - 群组详情
- `POST /api/v1/community/groups/{id}/join` - 加入群组
- `POST /api/v1/community/groups/{id}/leave` - 退出群组

### 3. 冲刺群 (Sprint)

#### 功能概述
冲刺群是短期临时群组，通常围绕特定的截止日期（如期末考试、项目DDL）创建，带有倒计时功能，帮助用户在紧张的时间内共同冲刺目标。

#### 核心功能
- **创建冲刺群**: 基于特定截止日期创建群组
- **倒计时功能**: 显示距离目标日期的倒计时
- **群任务池**: 共享任务列表，成员可以认领
- **进度追踪**: 跟踪群组整体和成员个人进度
- **激励机制**: 基于进度的奖励和激励

#### 冲刺类型
- **考试冲刺**: 针对期末考试、资格考试等
- **项目冲刺**: 针对作业DDL、项目截止日期
- **竞赛冲刺**: 针对比赛准备

#### 数据模型
- **groups** 表中包含额外字段：
  - `deadline`: 截止日期
  - `sprint_goal`: 冲刺目标
  - `daily_target`: 每日目标

#### API端点
- `POST /api/v1/community/groups` - 创建冲刺群（指定deadline）
- `GET /api/v1/community/groups/{id}/progress` - 获取群组进度
- `GET /api/v1/community/groups/{id}/countdown` - 获取倒计时信息

### 4. 群聊功能

#### 功能概述
群聊功能支持群组内的实时交流，包括文本消息、任务分享、进度更新等，营造积极的学习氛围。

#### 核心功能
- **文本消息**: 支持富文本消息发送
- **任务分享**: 分享个人任务到群聊
- **进度分享**: 分享学习进度和成果
- **成就分享**: 分享学习成就和里程碑
- **系统消息**: 系统自动发送的提醒和通知

#### 消息类型
- `text`: 普通文本消息
- `taskShare`: 任务分享
- `progress`: 进度分享
- `achievement`: 成就分享
- `checkin`: 打卡消息
- `system`: 系统消息

#### 数据模型
- **group_messages**: 群消息表
  - `id`: 消息唯一标识
  - `group_id`: 群组ID
  - `sender_id`: 发送者ID
  - `message_type`: 消息类型
  - `content`: 消息内容
  - `content_data`: 附加数据（JSON）
  - `created_at`: 发送时间

#### API端点
- `GET /api/v1/community/groups/{id}/messages` - 获取群消息
- `POST /api/v1/community/groups/{id}/messages` - 发送群消息

### 5. 打卡功能

#### 功能概述
打卡功能允许用户在群组中记录每日学习情况，形成学习习惯，同时群组成员可以互相监督和鼓励。

#### 核心功能
- **每日打卡**: 记录当日学习时长和内容
- **打卡统计**: 统计个人和群组打卡情况
- **连续打卡奖励**: 鼓励连续打卡
- **火苗贡献**: 打卡行为对群组火堆的贡献

#### 打卡计算
- **基础火苗**: 每次打卡获得10点基础火苗
- **连续奖励**: 连续打卡奖励（最多20点）
- **时长奖励**: 根据学习时长奖励（最多30点）
- **群组贡献**: 个人打卡对群组火堆的贡献

#### 数据模型
- **checkins**: 打卡记录表
  - `id`: 打卡记录唯一标识
  - `user_id`: 用户ID
  - `group_id`: 群组ID
  - `date`: 打卡日期
  - `duration_minutes`: 学习时长（分钟）
  - `message`: 打卡留言
  - `flame_gained`: 获得火苗数
  - `created_at`: 打卡时间

#### API端点
- `POST /api/v1/community/checkin` - 群组打卡
- `GET /api/v1/community/checkin/history` - 获取打卡历史
- `GET /api/v1/community/checkin/streak` - 获取连续打卡记录

### 6. 火堆系统

#### 功能概述
火堆系统是Sparkle社群功能的视觉核心，将个人和群组的学习成果以"火堆"的形式可视化展现，体现社群的集体学习氛围。

#### 核心功能
- **个人火苗**: 体现个人学习活跃度
- **群组火堆**: 体现群组整体学习氛围
- **动态效果**: 实时更新的火焰动画效果
- **贡献排名**: 显示成员对火堆的贡献排名

#### 火堆计算
- **个人火苗等级**: 基于学习活跃度的等级系统（1-10级）
- **火苗亮度**: 基于近期活跃度的亮度值（0-1）
- **群组火堆强度**: 基于全体成员贡献的火堆强度

#### 数据模型
- **flame_stats**: 火苗统计表
  - `user_id`: 用户ID
  - `group_id`: 群组ID（NULL为个人）
  - `flame_level`: 火苗等级
  - `flame_brightness`: 火苗亮度
  - `total_contributions`: 总贡献值
  - `last_updated`: 最后更新时间

#### API端点
- `GET /api/v1/community/groups/{id}/flame` - 获取群组火堆状态
- `GET /api/v1/community/flame/personal` - 获取个人火苗状态

## 用户体验设计

### 1. 界面设计
- **火苗视觉元素**: 统一的火苗视觉语言贯穿整个社群功能
- **群组卡片**: 直观展示群组信息、进度和活跃度
- **聊天界面**: 清晰的消息分类和丰富的互动元素
- **打卡界面**: 简洁的打卡流程和即时反馈

### 2. 交互设计
- **一键加入**: 简化群组加入流程
- **快速打卡**: 便捷的打卡入口和操作
- **消息模板**: 提供常用消息的快速发送选项
- **进度可视化**: 直观的进度条和图表展示

### 3. 激励机制
- **成就系统**: 完成特定社群活动获得成就
- **排行榜**: 基于学习贡献的排行榜
- **徽章系统**: 体现用户在社群中的贡献和地位
- **奖励机制**: 完成社群任务获得奖励

## 技术实现

### 1. 后端实现
- **社区服务层**: `CommunityService` 处理所有社群相关业务逻辑
- **消息服务**: 实时消息推送和历史消息管理
- **打卡服务**: 打卡逻辑和火苗计算
- **群组管理**: 群组CRUD和成员管理

### 2. 前端实现
- **社群模型**: `CommunityModel` 定义所有社群相关数据结构
- **社群仓库**: `CommunityRepository` 处理API调用和数据缓存
- **状态管理**: `CommunityProvider` 使用Riverpod管理社群状态
- **UI组件**: 丰富的社群功能UI组件

### 3. 实时通信
- **WebSocket/SSE**: 实时消息推送
- **事件系统**: 社群活动的实时通知

## API接口

### 好友相关
- `POST /api/v1/community/friends/request` - 发送好友请求
- `POST /api/v1/community/friends/respond` - 响应好友请求
- `GET /api/v1/community/friends` - 获取好友列表
- `GET /api/v1/community/friends/recommendations` - 好友推荐

### 群组相关
- `POST /api/v1/community/groups` - 创建群组
- `GET /api/v1/community/groups` - 获取我的群组
- `GET /api/v1/community/groups/search` - 搜索群组
- `GET /api/v1/community/groups/{id}` - 群组详情
- `POST /api/v1/community/groups/{id}/join` - 加入群组
- `POST /api/v1/community/groups/{id}/leave` - 退出群组

### 消息相关
- `GET /api/v1/community/groups/{id}/messages` - 获取消息
- `POST /api/v1/community/groups/{id}/messages` - 发送消息

### 打卡相关
- `POST /api/v1/community/checkin` - 打卡
- `GET /api/v1/community/checkin/leaderboard` - 打卡排行榜

### 火堆相关
- `GET /api/v1/community/groups/{id}/flame` - 火堆状态

## 扩展性考虑

### 1. 功能扩展
- **活动功能**: 群组内组织学习活动
- **知识分享**: 群组内的知识分享和讨论
- **视频通话**: 支持群组视频学习
- **文件共享**: 群组内学习资料共享

### 2. 社交功能
- **学习日记**: 个人学习日记分享
- **学习伙伴**: 一对一学习伙伴匹配
- **兴趣小组**: 基于兴趣的学习小组

### 3. 智能功能
- **智能匹配**: 基于学习习惯的智能匹配
- **AI助手**: 群组内的AI学习助手
- **内容推荐**: 基于群组兴趣的内容推荐

## 最佳实践

### 1. 社群管理
- **明确规则**: 为每个群组设定明确的学习规则
- **活跃度维护**: 定期组织活动保持群组活跃
- **质量控制**: 确保群组内的学习内容质量

### 2. 用户体验
- **隐私保护**: 保护用户隐私和学习数据
- **骚扰防范**: 防止群组内的骚扰行为
- **适度参与**: 避免过度社交影响学习

### 3. 技术优化
- **性能优化**: 优化群组消息和实时通信性能
- **数据安全**: 确保社群数据的安全性
- **可扩展性**: 设计可扩展的社群功能架构
