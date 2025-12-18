# Sparkle（星火） - AI 学习助手

> 🎯 一个面向大学生的智能学习 App，核心概念是「AI 时间导师」

## 📖 项目简介

Sparkle 是一款帮助大学生提升学习效率的 AI 助手应用，通过「对话 → 任务卡 → 执行 → 反馈 → 冲刺计划」的完整闭环，为用户提供个性化的学习指导和时间管理。

**目标**：2025年2月2日前完成 MVP 版本，参加大学软件创新大赛

## ✨ 核心功能

### 已完成功能 ✅

#### 🎓 学习核心功能
- 💬 **AI 微导师对话**：与 AI 导师实时对话，获取个性化学习建议和任务推荐
- 📋 **智能任务卡系统**：
  - 支持 6 种任务类型：学习、训练、纠错、反思、社交、规划
  - 任务状态管理：待办、进行中、已完成、已放弃
  - AI 智能生成任务建议
- ⏱️ **专注执行模式**：番茄钟式任务执行，配合计时器提升专注力
- 🎯 **冲刺 & 成长计划**：
  - 考试冲刺计划（Sprint Plan）
  - 长期成长计划（Growth Plan）
  - AI 辅助计划制定和任务分解

#### 📊 学习数据分析
- 📝 **错题档案系统**：智能记录错题，支持遗忘曲线复习
- 📈 **学习统计分析**：任务完成率、学习时长、知识点掌握度追踪
- 🔥 **火花成长体系**：
  - 火花等级（Flame Level）：反映学习阶段
  - 火花亮度（Flame Brightness）：反映近期活跃度
  - 可视化学习进度和成长轨迹

#### 🌌 知识管理
- 🗺️ **知识星图（Knowledge Map）**：
  - 可视化知识图谱，构建个人知识网络
  - LLM 驱动的知识点智能拓展和推荐
  - 向量语义搜索，智能关联相关知识点
  - 知识掌握度追踪（Mastery Level）
  - 基于遗忘曲线的自动复习提醒
- 📚 **科目管理**：支持多科目分类和课程管理

#### 🔔 智能推送系统
- 📱 **基于 Persona 的个性化推送**：
  - 冲刺提醒：考试前智能推送学习计划和复习建议
  - 记忆唤醒：根据遗忘曲线推送知识点复习
  - 沉睡唤醒：长时间未活跃用户的个性化激励消息
  - 可配置推送偏好（频率、时段、内容类型）
  - 通知权限智能引导

#### 👤 用户体验
- 🚀 **游客模式**：支持游客快速体验核心功能，无需注册
- 🔐 **完整的用户认证系统**：注册、登录、JWT Token 自动刷新
- 🎨 **主题定制**：支持亮色/暗色主题切换

## 🛠️ 技术架构

### 前端（Mobile）
- **框架**：Flutter 3.x
- **语言**：Dart
- **状态管理**：Riverpod
- **本地存储**：shared_preferences + Hive
- **网络请求**：Dio
- **目标平台**：Android / iOS

### 后端（Backend）
- **框架**：FastAPI (Python 3.11+ (tested with 3.14))
- **ORM**：SQLAlchemy 2.0
- **数据库**：PostgreSQL (开发环境可用 SQLite)
- **任务调度**：APScheduler
- **数据库迁移**：Alembic
- **API 文档**：Swagger UI / ReDoc

### AI 服务
- **模型**：通义千问（Qwen）/ DeepSeek
- **接口**：统一 LLM Service 抽象层
- **开发测试**：兼容 OpenAI API 格式

## 📁 项目结构

```
sparkle/
├── backend/          # Python FastAPI 后端
├── mobile/           # Flutter 移动端
└── docs/             # 项目文档
```

## 🚀 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 配置数据库和 API 密钥
alembic upgrade head
uvicorn app.main:app --reload
```

### 移动端启动

```bash
cd mobile
flutter pub get
flutter run
```

## 📚 文档

- [API 设计文档](docs/api_design.md)
- [数据库设计文档](docs/database_schema.md)
- [开发指南](docs/development_guide.md)

## 👥 团队

4名大二/大三计算机专业学生

- 擅长：Python、AI 开发工具（Cursor、Claude）
- 学习中：Dart、Flutter、Go、Java

## 📄 License

本项目用于大学软件创新大赛

## 🔗 相关链接

- [项目看板](#)
- [设计稿](#)
- [API 文档](#) (启动后端后访问 `/docs`)

---

**Version**: MVP v0.2.0
**Last Updated**: 2025-12-18

## 🆕 最近更新

- ✅ 知识星图功能上线（遗忘曲线、知识点拓展、向量搜索）
- ✅ 智能推送系统完成（基于 Persona 的个性化推送）
- ✅ LLM 宽容模式解析增强至 v2.2
- ✅ 游客模式支持
- ✅ 推送偏好设置和通知权限配置
