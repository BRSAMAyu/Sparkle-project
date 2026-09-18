# 引擎 LLM 功能路径全量真实调用评测（ai-functions-real-eval）

- 日期：2026-09-18 23:08–23:22（本机真服务，未重启任何进程）
- 仓库 HEAD：aabc7f1e
- 评测员：AI 功能全量真机评测（重派轻量轮，串行命令，实际消耗 LLM 请求 ≈10 次，预算 40 内）
- 凭据：游客 token（`guest_id=aifull02`）经 `POST /api/v1/auth/guest` 获取；WS 经 `/api/v1/ws/ticket` → `ws://…/ws/chat?ticket=…`
- 引擎配置实证（backend/.env + LLMRouter 启动日志）：`DEEPSEEK_CHAT_MODEL=deepseek-flash`、`LLM_REASON_MODEL_NAME=deepseek-v4-pro`（v4-pro 对应 **max/reasoning 层** 的 `deepseek_reason`，不是 pro 层）

## 路径 × 结果矩阵

| # | 路径 | 触发方式 | 结果 | 延迟 | 质量一句话 | 降级优雅度 |
|---|---|---|---|---|---|---|
| 1 | WS 聊天·reason 复杂消息（"帮我制定考研40天冲刺计划"，standard 模式） | WS 全链路真调 | ✅ 通（但未达 v4-pro，见问题 F-1） | total 4.7–7.8s，TTFB ≈4.7s | 澄清式追问（问时长/薄弱科），合理但浅 | 无降级，正常回答 |
| 1b | WS 聊天·`chat_mode=deep_analysis` 同消息 | WS 真调 | ✅ 通（仍未达 v4-pro，F-1） | total 8.9s，TTFB 8.7s | 同上，与 standard 档差异不明显 | 无降级 |
| 2 | 建模聊天开场白（A-3 根因） | WS 发 `_onboarding_start_` + extra_context `mode=onboarding_modeling` | ✅ 通 | total 16.0s，**TTFB 13.9s** | 开场白完整、语气合规、给出两问引导 | 客户端首事件超时 45s > 13.9s，余量够 |
| 3 | 推送内容生成 | 直调 `llm_service.generate_push_content`（Celery 路径，绕过后台） | ⚠️ 半通：LLM 真调但 **JSON 解析失败**，静默落固定文案（F-2） | 2.5s | 降级文案「学习提醒/该复习了」完全丢上下文 | 静默降级：调用方无感知，质量塌陷 |
| 4a | goal 创建 | `POST /api/v1/goals` | ✅ 通（纯 CRUD，无 LLM） | 0.43s | 落库正确、milestones 归档 | — |
| 4b | goal 意图分析 | `POST /api/v1/goals/analyze-intent` | ⛔ 被 `goal_first_minute` kill-switch 关闭，恒返 `mode=disabled`（0.04s，无 LLM；代码注释明示"no LLM"） | 0.04s | — | 优雅（200+disabled，客户端走旧向导） |
| 4c | plan 创建 | `POST /api/v1/plans` | ❌ **500**：`pg_advisory_xact_lock(hashtextextended(:user_id::text,0))` SQL 语法错误（`plan_service.py:91`，C2 配额锁修复引入）→ **下游 LLM 生成任务/阶段计划全部不可达**（F-3） | 0.05s | — | **不优雅**：裸 500，无兜底 |
| 5 | insights/反思摘要 | `GET /insights/recent-directives`、`GET /reflections/summary`、`GET /reviews/nightly/latest` | ✅ 端点全通；但**全部为规则/模板，无任何 LLM 调用**（F-4） | 0.03–0.25s | 夜间回顾文案为固定句式「没有新错题，保持节奏。」 | — |
| 6a | 翻译 | `POST /api/v1/translation/translate`（en→zh） | ✅ 通，真 LLM（provider=siliconflow，`cache_hit=false`） | 0.65s（meta latency 612ms） | 「线粒体是细胞的"动力工厂"」准确流畅 | 好，含配额剩余/建卡建议 |
| 6b | STT | `POST /api/v1/stt/transcribe`（1s 静音 wav） | ⚠️ 200 + `{"text":"Transcription failed. Please try again later.","error":true}`（无可用 provider 配置） | 0.39s | — | 较优雅：有 error 标记+文案，但语义上 200 承载失败欠妥 |
| 6c | OCR | 直调 `ocr_service.ocr_for_math(无效URL)`（真调 vision provider） | ⚠️ 失败形态优雅：provider 真调→400→全部 provider 遍历后返回**空串**，不抛异常（fire-and-forget 调用方不更新记录） | 2.5s | — | 优雅：无裸 500、不脏数据 |
| 7 | 免费层钳制（引擎未重载新代码，改单测式直调 llm_router） | python3.11 + .env 直调 `select_model` | ✅ 三例全符合：`free`+PRO → **fast** 且 `free_tier_downgrade=true`、reason 含 `free_tier_downgrade(pro->fast)`；非 free+PRO → glm_4_7_pro 不钳制；free+FAST → 不钳制（ceiling=fast） | 离线（无网络调用） | 降级链为 deepseek_fast（deepseek-flash） | 精确：标记+原因+日志三件套齐 |

## 通过率

- 12 个测试点：**8 通 / 2 半通（带质量或形态问题）/ 2 断**（4b 功能性关闭属设计开关、4c 属真 bug）。
- 真 LLM 触达路径：WS 聊天（flash）、建模开场白（flash）、翻译（siliconflow）、推送内容（flash，解析失败）、OCR vision（失败遍历）= 5 条；reasoning/v4-pro 档 **0 条触达**。

## 问题清单

### P1
- **F-3 plan 创建 500 阻断 LLM 计划链**：`POST /api/v1/plans` 必现 `asyncpg.PostgresSyntaxError: syntax error at or near ":"`。位置 `backend/app/services/plan_service.py:91`（`text("SELECT pg_advisory_xact_lock(hashtextextended(:user_id::text, 0))")`，C2 TOCTOU 修复）。参数绑定未生效直达 PG；配额检查在其之前执行不到，**所有用户 plan 创建全量失败**，进而 `phase-sketch/generate`、`generate-tasks` 等下游 LLM 生成不可达。复现：任一鉴权用户 POST name/type 即 500（0.05s，trace_id d25310d5…）。

### P2
- **F-1 reason/复杂档从未路由 v4-pro**：standard 与 `deep_analysis` 两档实测主回答均由 generation 走 `deepseek_chat`（standard 层，deepseek-flash），orchestrator 另被 `强制tier=fast`。根因链：`STANDARD_CHAT_FORCE_FAST_TIER=True`（`app/config/settings.py:605`，首答强制 FAST）+ `_should_force_fast_first_touch`（`reasoning_mode=fast` 且 standard 模式即触发）+ generation Agent 策略偏好 deepseek_chat。v4-pro（=deepseek_reason，**max 层**）在全部观测窗口 0 次出现。另有首个请求（23:08:13，reasoning_mode 未达 deep 时）整条链强制 fast——**「reason 档」在现网配置下实际不存在**。
- **F-2 推送文案 JSON 解析失败静默塌陷**：`llm_service.generate_push_content` 真调 LLM 后 `Expecting value: line 1 column 1` → 返回硬编码 `{"title":"学习提醒","body":"…该复习了。"}`，丢 streak/任务等全部上下文且无遥测标记。附带小 bug：`LLMMonitor object has no attribute 'LLM_CALLS_TOTAL'`（监控埋点属性名漂移）。

### P3
- **F-4 反思/夜间回顾为纯模板**：`nightly_review_service._build_summary` 等无 LLM 参与；对参赛叙事「AI 反思摘要」需修正口径或补 LLM 路径。
- **F-5 STT 200 承载失败**：`error:true` 藏在 200 体内，建议改 503+结构化错误或至少前端按 error 分支提示。
- **F-6 建模开场白 TTFB 13.9s**：A-3 现状=服务端可出开场白但偏慢；客户端 45s 守卫（`modeling_chat_screen.dart:43`）当前兜得住，建议压缩 aurora onboarding 链路。

## A-3 定性

A-3（建模聊天开场白静默断流）**服务端链路现版本已可复现成功**：`_onboarding_start_` + `mode=onboarding_modeling` 经 WS 正常返回完整开场白（16.0s，392 帧文含 delta 流+full_text+meta+done 全帧序）。客户端已加 45s 首事件超时守卫（注释明示 A-3），13.9s TTFB 在容忍内。**定性：已修复（工程上可达），残留风险为 TTFB 长尾**——若 aurora onboarding 链路偶发 >45s，守卫会把静默断流转为可见可重试错误，不再无声。

## 附：本次未测/受控项

- `learning-paths/{node}/plan`（LLM 生成学习计划）未测：需真实 KG 节点 UUID，且受 F-3 阻断预期同源链路。
- 推送/夜间回顾 Celery 触发路径未跑（不重启服务纪律）；改直调服务函数，行为等价于 worker 内调用体。
- 引擎日志 `/tmp/engine_server.log` 在评测中段发生轮转（9251→125 行），关键路由证据（强制tier=fast / Agent策略路由）已于轮转前捕获并写入本报告。
