# Sparkle 文档重组方案

> 创建日期: 2026-03-30
> 目标: 清理根目录，建立层次化文档体系

## 当前问题诊断

### 根目录污染 (62个.md文件)
- 大量临时性报告: `*_FIX_REPORT.md`, `*_TEST_REPORT.md`, `*_ACCEPTANCE_REPORT.md`
- 重复的README: `README.md`, `README_CN.md`, `README_EN.md`, `README_PHASE0.md`
- 散落的配置指南: `ENV_CONFIG_*.md`, `*_SETUP_GUIDE.md`
- 过时的演示文档: `DEMO_*.md`
- 技术债追踪文件混杂在根目录

### docs/目录结构混乱
- 存在重复的编号目录: `03_功能实现指南` 和 `04_功能实现指南`
- 存在重复的编号目录: `06_重构与优化` 和 `03_重构与优化报告`
- 根目录散落大量未分类文件: `A3_*.md`, `A4_*.md`, `A5_*.md`, `A7_*.md`
- 中英文混合命名不一致
- 存在大量过时验证报告

## 新文档结构设计

```
docs/
├── README.md                          # 文档导航首页
├── 00_overview/                       # 项目概览
│   ├── vision.md                      # 项目愿景
│   ├── architecture.md                # 技术架构
│   └── quickstart.md                  # 快速开始
├── 01_modules/                        # 核心模块文档
│   ├── agent/                         # AI智能体
│   ├── galaxy/                        # 知识星图
│   ├── task/                          # 任务管理
│   ├── plan/                          # 计划管理
│   ├── chat/                          # 对话系统
│   ├── theater/                       # 仿真剧场
│   └── achievement/                   # 成就体系
├── 02_design/                         # 技术设计
│   ├── api/                           # API设计
│   ├── database/                      # 数据库设计
│   ├── proto/                         # gRPC协议
│   └── ux/                            # 用户体验设计
├── 03_implementation/                 # 实现指南
│   ├── backend/                       # 后端开发
│   ├── gateway/                       # 网关开发
│   ├── mobile/                        # 移动端开发
│   └── testing/                       # 测试指南
├── 04_operations/                     # 运维部署
│   ├── deployment/                    # 部署指南
│   ├── monitoring/                    # 监控告警
│   └── runbook/                       # 运维手册
├── 05_reference/                      # 参考资料
│   ├── adr/                           # 架构决策记录
│   ├── glossary/                      # 术语表
│   └── external/                      # 外部参考
└── archive/                           # 历史归档
    ├── reports/2025-q4/               # 2025年Q4报告
    ├── reports/2026-q1/               # 2026年Q1报告
    └── deprecated/                    # 已废弃文档
```

## 文件迁移计划

### 阶段1: 根目录清理 (高优先级)

| 文件 | 目标位置 | 说明 |
|------|----------|------|
| `README.md` | 保留 | 作为项目主入口 |
| `README_CN.md` | 合并至 `README.md` | 通过目录切换语言 |
| `README_EN.md` | 删除 | 内容已在主README |
| `README_PHASE0.md` | `archive/deprecated/` | 历史文档 |
| `CLAUDE.md` | 保留 | AI协作指南 |
| `CHANGELOG.md` | 保留 | 变更日志 |
| `AGENTS.md` | `docs/01_modules/agent/README.md` | 智能体文档 |
| `DEPLOY.md` | `docs/04_operations/deployment/` | 部署指南 |
| `*_FIX_REPORT.md` | `archive/reports/` | 历史修复报告 |
| `*_TEST_REPORT.md` | `archive/reports/` | 历史测试报告 |
| `*_ACCEPTANCE_REPORT.md` | `archive/reports/` | 历史验收报告 |
| `ENV_CONFIG_*.md` | `docs/04_operations/deployment/env.md` | 合并环境配置 |
| `DEMO_*.md` | `archive/deprecated/` | 演示相关已过时 |
| `FULL_STACK_*.md` | `docs/02_design/` | 技术参考文档 |
| `LOCAL_DEVELOPMENT_GUIDE.md` | `docs/00_overview/quickstart.md` | 本地开发指南 |

### 阶段2: docs/目录重组 (中优先级)

| 操作 | 说明 |
|------|------|
| 删除重复编号目录 | 合并 `03_功能实现指南` 和 `04_功能实现指南` |
| 删除重复编号目录 | 合并 `06_重构与优化` 和 `03_重构与优化报告` |
| 归档根目录散落文件 | 将 `A3_*.md`, `A4_*.md` 等移至 `archive/` |
| 标准化命名 | 统一使用小写下划线命名 |
| 创建索引 | 在每个子目录创建 README.md 作为导航 |

### 阶段3: 文档内容更新 (低优先级)

| 任务 | 说明 |
|------|------|
| 更新过期链接 | 确保所有文档间引用正确 |
| 标记过时内容 | 在过期文档顶部添加警告 |
| 合并重复内容 | 消除不同文档间的重复描述 |
| 创建导航图 | 在 `docs/README.md` 创建可视化导航 |

## 执行命令参考

### 根目录清理
```bash
# 创建归档目录
mkdir -p docs/archive/reports/2025-q4
mkdir -p docs/archive/reports/2026-q1
mkdir -p docs/archive/deprecated

# 移动报告文件
find . -maxdepth 1 -name "*_REPORT.md" -exec mv {} docs/archive/reports/2026-q1/ \;
find . -maxdepth 1 -name "*_SUMMARY.md" -exec mv {} docs/archive/reports/2026-q1/ \;

# 移动演示相关
find . -maxdepth 1 -name "DEMO_*.md" -exec mv {} docs/archive/deprecated/ \;
```

### docs/目录重组
```bash
# 移动散落文件到归档
find ./docs -maxdepth 1 -name "A*.md" -exec mv {} docs/archive/deprecated/ \;
find ./docs -maxdepth 1 -name "*_对齐*.md" -exec mv {} docs/archive/reports/ \;

# 合并重复目录 (需要手动处理)
# rmdir docs/04_功能实现指南  # 在合并内容后
```

## 验收标准

1. 根目录仅保留必要文件: `README.md`, `CLAUDE.md`, `CHANGELOG.md`
2. 所有报告类文件归档至 `docs/archive/reports/`
3. `docs/` 目录下无散落的 `.md` 文件
4. 每个子目录都有 `README.md` 导航
5. `docs/README.md` 提供完整文档地图
6. 所有文档间的内部链接正确更新

## 注意事项

- 执行前建议创建备份分支
- 某些文件可能需要内容合并而非简单移动
- 检查是否有外部链接指向这些文档
- 更新 CI/CD 中可能引用这些路径的配置
