# Stage 5 Regression Snapshot

更新时间：2026-03-23 14:58:00 CST  
目的：记录阶段 5 第一批真实模块回归证据，仅记录本轮已实际执行并拿到回执的链路

---

## 1. 已执行脚本与结果

### 1.1 AI 对话主链

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/ai_chat_multiturn_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - `reasoning_mode=balanced`
  - `history_count=6`
  - `omnibar_action_type=TASK`
  - `study_plan_has_tool_signal=true`
  - 标准、多轮、深度分析、学习计划、错误诊断均返回非空内容

### 1.2 社群主链

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/community_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - 好友请求、接受好友、私聊消息、群组创建、群成员加入均跑通
  - 无密码哈希泄漏

### 1.3 社群分享 / 采纳双账号闭环

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/community_share_adopt_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - `group_shared_types=["plan","task"]`
  - `plan_shared_resource_id=17e8d709-1d9c-4632-938a-c07fac53db5e`
  - `task_shared_resource_id=5d51eadd-0e42-407b-862d-6d7c109ad6d4`
  - `adopted_plan_id=09238b49-f0c7-46fd-9f35-23fcefa1c3f5`
  - `adopted_task_id=713661ac-a340-4e3a-ad92-67e5e182ae96`
  - 已验证“私聊分享 -> 对方采纳 -> 对方实体归属到本人”

### 1.4 专注主链

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/focus_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - `today_total_minutes=25`
  - `weekly_session_count=1`
  - `history_total_count=14`
  - `breakdown_count=4`

### 1.5 日历 / 天气 / 建议时间

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/calendar_weather_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - `linked_task_id=72a2956e-c1e9-4fb8-8899-9afa430bfa42`
  - `linked_plan_id=6d8894d1-ec11-46c4-a3d0-c2eda382fa63`
  - `restored_event_id=7a6dd319-7dde-4b1e-97d0-11785a0a0e0a`

### 1.6 长期计划 / 计划管理

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/long_term_plan_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - `quota_used=3`
  - `primary_plan_id=6d8894d1-ec11-46c4-a3d0-c2eda382fa63`
  - `archived_total=3`
  - `restored_plan_id=7eefefbf-ff3d-4bf6-933c-24c25e884644`

### 1.7 种子库

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_library_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - `subscription_count=1`
  - `group_shared_types=["seed_item","seed_library"]`
  - `task_resource_types=["seed_library","seed_item"]`
  - `few_shot_inputs=["A","什么是验收测试？"]`
  - 私有种子库外部访问被 `404` 正确阻断

### 1.8 责任伙伴

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/accountability_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - `timeline_count=2`
  - `achievement_total=8`
  - `owner_notifications` 含 `accountability_partner_checked_in`
  - `partner_notifications` 含 `accountability_manual_nudge`

### 1.9 Galaxy / 计划 / 分享联动

- 命令：`cd backend && PYTHONPATH=. .venv/bin/python scripts/galaxy_plan_acceptance.py`
- 结果：`ALL_OK`
- 关键证据：
  - `plan_id=4c1630ee-ae21-4931-9344-ce8680a5e7a8`
  - `task_id=98b76526-165a-4da5-a0a3-ec1c70565420`
  - `shared_types=["knowledge_node","plan","task"]`

### 1.10 本地全量 acceptance 闸门

- 命令：`make local-acceptance`
- 结果：`PASS`
- 关键证据：
  - 本地配置审计通过
  - `auth_smoke.py` 通过
  - `community_smoke.py` 通过
  - `worker_smoke.py` 通过
  - 文档上传/向量化 smoke 通过
  - gRPC smoke 通过
  - WebSocket integration test 通过
  - AI provider live probes 全绿
  - Flutter 本地 smoke 通过：
    - `test/app/router_smoke_test.dart`
    - `test/app/main_pages_load_smoke_test.dart`
    - `test/app/main_actions_smoke_test.dart`
    - `test/integration/full_stack_e2e_test.dart`

### 1.11 从零复建后的 analyze 闸门

- 命令：`make flutter-analyze-gate`
- 结果：`PASS`
- 关键证据：
  - `ERROR=0`
  - `WARNING=0`
  - `INFO=1062`
  - 预算闸门通过，当前无新的 analyzer 阻断

### 1.12 从零复建后的服务健康

- 命令：
  - `docker compose down -v`
  - `docker compose up -d`
  - `cd backend && .venv/bin/python -m alembic upgrade head`
  - `make init-rag`
  - `cd backend && PYTHONPATH=. .venv/bin/python scripts/init_shop.py init`
  - `docker compose ps`
- 结果：`PASS`
- 关键证据：
  - `sparkle_api` `healthy`
  - `sparkle_gateway` `healthy`
  - `sparkle_agent` `healthy`
  - `sparkle_db` `healthy`
  - `sparkle_redis` `healthy`
  - Celery worker / GLM batch worker 均 `healthy`

### 1.13 从零复建后的 Flutter fresh build

- 命令：
  - `cd mobile && flutter clean`
  - `cd mobile && flutter pub get`
  - `cd mobile && flutter build ios --simulator --debug`
  - `cd mobile && flutter build apk --debug`
  - `xcrun simctl install booted /Users/brsama/code/GitHub/Sparkle-project/mobile/build/ios/iphonesimulator/Runner.app`
  - `xcrun simctl launch booted com.example.sparkle`
- 结果：`PASS`
- 关键证据：
  - `✓ Built build/ios/iphonesimulator/Runner.app`
  - `✓ Built build/app/outputs/flutter-apk/app-debug.apk`
  - `com.example.sparkle: 73711`
  - [stage6_simulator_app_launched_2026-03-23.png](/Users/brsama/code/GitHub/Sparkle-project/tmp/acceptance/stage6_simulator_app_launched_2026-03-23.png)

---

## 2. 当前结论

- 后端 / API 层的 AI 对话、社群、双账号分享采纳、专注、日历、长期计划、种子库、责任伙伴、Galaxy 分享骨干链本轮均拿到 `ALL_OK`
- 从零复建、analyze 闸门、本地 acceptance 闸门本轮也已再次拿到 `PASS`
- 这批证据足以把若干 `FAIL` 项推进到“已修待前端/模拟器复验”的 `PARTIAL`
- 仍不能替代模拟器 UI 连续点击签收，也不能替代真机音频 / haptic / 视觉最终签收
