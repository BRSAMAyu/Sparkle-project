# Sparkle（星火） - AI 学习助手

> 🎯 一个面向大学生的智能学习 App，核心概念是「AI 时间导师」

## 📖 项目简介

Sparkle 是一款帮助大学生提升学习效率的 AI 助手应用，通过「对话 → 任务卡 → 执行 → 反馈 → 冲刺计划」的完整闭环，为用户提供个性化的学习指导和时间管理。

**目标**：2025年2月2日前完成 MVP 版本，参加大学软件创新大赛

## ✨ 核心功能

- 💬 **智能对话**：与 AI 导师对话，获取学习建议
- 📋 **任务卡系统**：将学习目标拆解为可执行的任务卡
- ⏱️ **专注执行**：番茄钟式任务执行，提升专注力
- 📊 **学习分析**：错题档案、知识图谱、学习统计
- 🔥 **火花成长**：通过火花等级和亮度可视化学习进度
- 🎯 **冲刺计划**：AI 辅助制定考试冲刺和成长计划

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

**Version**: MVP v0.1.0
**Last Updated**: 2025-12-15
