# 🎯 Sparkle 完整验收指南 - chat_test账户

## ✅ 你的原始账户

**账户名**: `chat_test`
**创建时间**: 2026-03-16 13:35:11
**密码**: `Chat123456`

这是数据最完整的账户，拥有：
- ✅ 3个知识星图节点（全部已解锁）
- ✅ 3个计划（计算机科学基础、Python强化、数据结构冲刺）
- ✅ 16个任务（11个今日任务）
- ✅ 10个成就（4个已解锁，40%）
- ✅ 7天连续学习，最长30天
- ✅ 3个群组（算法冲刺小队、前端学习互助组、晨跑打卡群）
- ✅ 5个好友

---

## 🚀 在Flutter App中使用

### 方法1：演示账号登录（推荐）

1. 打开Flutter app
2. 在登录页面点击**"演示账号登录"**按钮
3. 系统会自动用 `chat_test` / `Chat123456` 登录
4. 进入后即可看到所有完整数据

### 方法2：手动登录

1. 打开Flutter app
2. 输入用户名: `chat_test`
3. 输入密码: `Chat123456`
4. 点击登录

---

## 📊 API验收测试

### 测试Token

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODEzZmI5Yy1hMzY3LTRlYmUtYjE1Ny1lYTBkZDFhZjcxYjUiLCJzaWQiOiJtYW51YWwtdGVzdC1zZXNzaW9uIiwiaXNfZ3Vlc3QiOmZhbHNlLCJleHAiOjE3NzM3NzMzMjksImlhdCI6MTc3Mzc3MTUyOSwianRpIjoiZDJhZTJhNmQtNGRkYy00YmZkLThhYTgtMWJmN2M1MDlmYjg5IiwidHlwZSI6ImFjY2VzcyIsImlzcyI6InNwYXJrbGUtZ2F0ZXdheSIsImF1ZCI6InNwYXJrbGUtYXBwIn0.uxiVM-t0mxcxaOd19sDt30UPmqUTV3A7SqSgW2C7f48
```

### cURL测试命令

```bash
# 设置Token
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODEzZmI5Yy1hMzY3LTRlYmUtYjE1Ny1lYTBkZDFhZjcxYjUiLCJzaWQiOiJtYW51YWwtdGVzdC1zZXNzaW9uIiwiaXNfZ3Vlc3QiOmZhbHNlLCJleHAiOjE3NzM3NzMzMjksImlhdCI6MTc3Mzc3MTUyOSwianRpIjoiZDJhZTJhNmQtNGRkYy00YmZkLThhYTgtMWJmN2M1MDlmYjg5IiwidHlwZSI6ImFjY2VzcyIsImlzcyI6InNwYXJrbGUtZ2F0ZXdheSIsImF1ZCI6InNwYXJrbGUtYXBwIn0.uxiVM-t0mxcxaOd19sDt30UPmqUTV3A7SqSgW2C7f48"

# 测试Galaxy
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8080/api/v1/galaxy/graph" | python3 -m json.tool

# 测试Plans
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8080/api/v1/plans" | python3 -m json.tool

# 测试Tasks
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8080/api/v1/tasks/today" | python3 -m json.tool

# 测试Achievements
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8080/api/v1/achievements" | python3 -m json.tool

# 测试Community
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8080/api/v1/community/groups" | python3 -m json.tool
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8080/api/v1/community/friends" | python3 -m json.tool
```

---

## 🔧 已修复的问题

1. ✅ Gateway Authorization Header转发
2. ✅ Galaxy Graph字段兼容性（添加edges和user_flame_intensity）
3. ✅ Galaxy Stats方法调用
4. ✅ DateTime Timezone问题
5. ✅ Community Feed优雅降级
6. ✅ **chat_test账户Galaxy数据补充**

---

## 📝 注意事项

1. **演示账号登录** = `chat_test` 账户（3月16日创建，数据最完整）
2. **访客登录** = 创建新的临时guest账户（数据较少）
3. 所有后端服务必须运行中：
   - Go Gateway: 8080
   - Python REST: 8000
   - Python gRPC: 50051
   - PostgreSQL: 5433
   - Redis: 6379

---

**现在你可以在Flutter app中点击"演示账号登录"，立即体验所有功能！**
