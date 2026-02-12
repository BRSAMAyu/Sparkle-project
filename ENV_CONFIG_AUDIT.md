# .env 文件配置审查报告

**审查时间**: 2026-01-29
**审查范围**: 根目录 .env 和 backend/.env

---

## 📋 文件概览

| 文件 | 行数 | 用途 | 优先级 |
|------|------|------|--------|
| `/Users/a/code/sparkle-flutter/.env` | 36 行 | 项目根目录配置 | 低 (Docker环境) |
| `/Users/a/code/sparkle-flutter/backend/.env` | 103 行 | 后端服务配置 | 高 (本地开发) |

---

## ⚠️ 重要发现

### 1. 配置重复且包含敏感信息

**问题**: 两个 `.env` 文件都包含**真实的 API Keys**，存在安全风险。

```bash
# 根目录 .env
XIAOMI_MIMO_API_KEY=sk-cmwqykkej4amo184uyqf700glf5xcqiuahremcrg2j2kb8o6
DEEPSEEK_API_KEY=sk-29c29c1c5a9447949b09762140a210ef
ZHIPU_API_KEY=e78e70c5f139453c9d0df15b848fa084.W31a9cNerGcSYDTt

# backend/.env (相同的 keys)
XIAOMI_MIMO_API_KEY=sk-cmwqykkej4amo184uyqf700glf5xcqiuahremcrg2j2kb8o6
DEEPSEEK_API_KEY=sk-29c29c1c5a9447949b09762140a210ef
ZHIPU_API_KEY=e78e70c5f139453c9d0df15b848fa084.W31a9cNerGcSYDTt
```

### 2. 配置不一致

| 配置项 | 根目录 .env | backend/.env | 差异 |
|--------|-------------|--------------|------|
| **Redis Host** | `sparkle_redis` | `localhost` | ⚠️ 环境不同 |
| **数据库密码** | `change-me` | `change-me` | ✅ 一致 |
| **LLM_PROVIDER** | `zhipu` | `dashscope` | ⚠️ 默认值不同 |
| **SECRET_KEY** | 相同 | 相同 | ✅ 一致 |

### 3. 缺失的配置

#### 根目录 .env 缺少:
- ❌ DashScope API Keys (通义千问)
- ❌ SiliconFlow API Keys (OCR/翻译)
- ❌ XunFei STT 配置 (语音识别)
- ❌ Embedding/Rerank 配置
- ❌ GLM-4.7-Flash 配置

#### backend/.env 完整度:
- ✅ 包含所有 API Keys
- ✅ 包含 Embedding/Rerank 配置
- ✅ 包含 STT 配置
- ✅ XiaoMi MIMO 已禁用 (API Key 失效)

---

## 🔍 详细对比

### 数据库配置

```bash
# 根目录 .env (Docker 环境)
POSTGRES_HOST=sparkle_db
REDIS_HOST=sparkle_redis

# backend/.env (本地开发)
POSTGRES_HOST=sparkle_db  # 会映射到 localhost
REDIS_HOST=localhost
```

**建议**: 根目录 `.env` 用于 Docker Compose，backend/.env 用于本地开发。

### LLM Provider 配置

```bash
# 根目录 .env
LLM_PROVIDER=zhipu  # ❌ 缺少其他 provider 配置

# backend/.env
LLM_PROVIDER=dashscope  # ✅ 完整配置
DASHSCOPE_API_KEY=sk-cd9af6e3b7da44c9b67de53c69f2fae8
ZHIPU_API_KEY=e78e70c5f139453c9d0df15b848fa084.W31a9cNerGcSYDTt
DEEPSEEK_API_KEY=sk-29c29c1c5a9447949b09762140a210ef
SILICONFLOW_API_KEY=sk-wregwpyfxrafholmzwrrbucyyvtfgepffgqfysmljdutoqpx
```

---

## 🎯 推荐方案

### 方案 1: 统一使用 backend/.env (推荐)

**优点**:
- ✅ 配置完整，包含所有 API Keys
- ✅ 后端服务直接读取，无需映射
- ✅ 本地开发开箱即用

**操作**:
1. 删除或清空根目录 `.env` 中的敏感信息
2. 仅保留 Docker 相关配置 (数据库、Redis)
3. 后端配置独立管理

### 方案 2: 环境分层

**结构**:
```
根目录 .env          → Docker 环境 (仅基础配置)
backend/.env         → 本地开发 (完整配置 + API Keys)
gateway/.env         → Gateway 配置
mobile/.env          → 移动端配置
```

**操作**:
1. 根目录 `.env` 不包含 API Keys
2. backend/.env 用于本地开发
3. 生产环境使用环境变量或密钥管理服务

---

## 🚨 安全建议

### 1. 立即操作

```bash
# ⚠️ 检查 .gitignore 是否正确配置
cat .gitignore | grep -E "\.env$"

# 应该包含:
# .env
# .env.local
# .env.*.local
```

### 2. 移除敏感信息

**根目录 .env 应该只保留**:
```bash
SECRET_KEY=...
POSTGRES_HOST=sparkle_db
POSTGRES_PASSWORD=change-me
REDIS_HOST=sparkle_redis
REDIS_PASSWORD=change-me
# ❌ 不要包含 API Keys
```

### 3. 使用环境变量管理

**生产环境**:
```bash
# 使用环境变量
export ZHIPU_API_KEY="..."
export DASHSCOPE_API_KEY="..."

# 或使用密钥管理服务
# AWS Secrets Manager
# Azure Key Vault
# HashiCorp Vault
```

---

## 📊 配置优先级

### Python 读取顺序 (`settings.py`)

```python
# backend/app/config/settings.py 第 96-100 行
env_file=[
    repo_env_path,        # /Users/a/code/sparkle-flutter/.env
    service_env_path,      # /Users/a/code/sparkle-flutter/backend/.env
    backend_env_path,      # /Users/a/code/sparkle-flutter/backend/app/.env
]
```

**优先级**: `backend/app/.env` > `backend/.env` > `根目录/.env`

**实际效果**: backend/.env 优先级最高，会覆盖根目录 .env 的配置。

---

## ✅ 建议的配置结构

### 推荐方案: 最小化根目录配置

**根目录 `.env`** (仅 Docker 基础配置):
```bash
# 基础配置
SECRET_KEY=...
POSTGRES_HOST=sparkle_db
POSTGRES_PORT=5432
POSTGRES_DB=sparkle
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
REDIS_HOST=sparkle_redis
REDIS_PORT=6379
REDIS_PASSWORD=change-me

# ❌ 不包含 API Keys
# LLM_API_KEY=
# ZHIPU_API_KEY=
```

**backend/.env** (完整配置):
```bash
# 继承根目录基础配置
# 添加所有 API Keys 和服务配置
ZHIPU_API_KEY=e78e70c5f139453c9d0df15b848fa084.W31a9cNerGcSYDTt
DASHSCOPE_API_KEY=sk-cd9af6e3b7da44c9b67de53c69f2fae8
DEEPSEEK_API_KEY=sk-29c29c1c5a9447949b09762140a210ef
SILICONFLOW_API_KEY=sk-wregwpyfxrafholmzwrrbucyyvtfgepffgqfysmljdutoqpx
# ... 其他配置
```

---

## 🔧 需要修正的问题

### 1. XiaoMi MIMO API Key 已失效

**状态**: ❌ 401 Invalid API Key
**位置**: 根目录 .env 和 backend/.env
**操作**: 已在 backend/.env 中禁用，根目录也需要禁用

### 2. 清理根目录 .env 中的敏感信息

**当前问题**: 根目录 .env 包含真实 API Keys
**建议**: 移除所有 LLM API Keys，仅保留 Docker 基础配置

### 3. 统一 LLM_PROVIDER 默认值

**根目录**: `LLM_PROVIDER=zhipu`
**backend**: `LLM_PROVIDER=dashscope`
**建议**: 使用 backend/.env 的配置 (dashscope)

---

## 📋 行动清单

- [ ] 清理根目录 .env 中的 API Keys
- [ ] 禁用根目录 .env 中的 XiaoMi MIMO
- [ ] 更新根目录 .env 中的 LLM_PROVIDER 为 dashscope
- [ ] 验证 .gitignore 包含 `.env`
- [ ] 提交时确认不包含敏感信息

---

## 🎯 总结

| 检查项 | 状态 | 说明 |
|--------|------|------|
| **敏感信息泄露** | ⚠️ 风险 | 两个 .env 都包含真实 API Keys |
| **配置一致性** | ❌ 不一致 | Redis 主机、LLM Provider 不同 |
| **配置完整性** | ⚠️ 不完整 | 根目录缺少大量配置 |
| **XiaoMi MIMO** | ❌ 已失效 | 已在 backend/.env 禁用 |
| **API 测试** | ✅ 9/10 成功 | 除 XiaoMi MIMO 外都正常 |

**推荐**: 使用 backend/.env 作为主要配置文件，清理根目录 .env 的敏感信息。
