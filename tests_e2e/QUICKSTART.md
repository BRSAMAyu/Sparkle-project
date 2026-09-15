# E2E测试快速入门

## 5分钟快速开始

### 1. 确保服务运行
```bash
# 启动基础设施 (PostgreSQL, Redis)
make dev-all

# 或使用Docker Compose
docker compose up -d postgres redis
```

### 2. 运行测试

#### 方式A: 运行所有E2E测试
```bash
make test-e2e-all
```

#### 方式B: 只运行Python E2E测试
```bash
cd backend
pytest tests_e2e/ -v
```

#### 方式C: 快速冒烟测试 (30秒)
```bash
make test-smoke
```

## 按功能运行

### 聊天系统测试
```bash
cd backend && pytest tests_e2e/test_chat_e2e.py -v
```

### 计划系统测试
```bash
cd backend && pytest tests_e2e/test_plan_lifecycle_e2e.py -v
```

### 知识星图测试
```bash
cd backend && pytest tests_e2e/test_galaxy_e2e.py -v
```

### 离线同步测试
```bash
cd backend && pytest tests_e2e/test_offline_sync_e2e.py -v
```

## 常见问题

### Q: 测试失败,提示数据库连接错误?
```bash
# 检查PostgreSQL是否运行
docker ps | grep postgres

# 重启PostgreSQL
docker compose restart postgres
```

### Q: 测试超时?
```bash
# 增加超时时间
cd backend && pytest tests_e2e/ -v --timeout=300
```

### Q: 如何只运行一个测试?
```bash
cd backend && pytest tests_e2e/test_chat_e2e.py::test_e2e_simple_chat_message_flow -v
```

### Q: 如何调试测试?
```bash
# 查看详细输出
cd backend && pytest tests_e2e/test_chat_e2e.py -vv -s

# 使用pdb调试器
cd backend && pytest tests_e2e/test_chat_e2e.py --pdb
```

## 测试覆盖率

### 生成覆盖率报告
```bash
cd backend && pytest tests_e2e/ --cov=app --cov-report=html
open htmlcov/index.html
```

### 查看覆盖率摘要
```bash
cd backend && pytest tests_e2e/ --cov=app --cov-report=term-missing
```

## CI/CD集成

### 本地运行CI测试
```bash
make test-e2e-ci
```

### 查看GitHub Actions状态
访问: `https://github.com/YOUR_REPO/actions/workflows/e2e-tests.yml`

## 下一步

- 📖 阅读完整文档: `tests_e2e/README.md`
- 📊 查看实施总结: `tests_e2e/IMPLEMENTATION_SUMMARY.md`
- 🔧 添加新测试: 参考现有测试文件结构
- 📈 提高覆盖率: 运行覆盖率报告并补充测试
