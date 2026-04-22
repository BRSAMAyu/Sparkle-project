# Sparkle Aurora Stage 36 Handoff

日期: 2026-04-22
范围: WS-36-01.5 / 02 / 03 / 04 / 05 收口 + Stage 36 终局验收

## 1. WS 提交清单

- WS-36-01 基底合并: `40855516` `[Stage36][WS-36-01] 基底合并:Stage 33 正式化 + Stage 34/35 回主干`
- WS-36-01.5 基底稳定: `5a58a354` `[Stage36][WS-36-01.5] 基底稳定:migrate + 测试漂移修复 + 0 条 quarantine`
- WS-36-02 Token Bucket 量纲修复: `00d50779` `[Stage36][WS-36-02] 修复 Token Bucket 量纲错配(elapsed ms × rate per-s)`
- WS-36-03 Theater IDOR 修复: `be8f299b` `[Stage36][WS-36-03] Theater IDOR 修复:加 user_id 作用域`
- WS-36-04 OpenClaw SSRF 修复: `78f55182` `[Stage36][WS-36-04] OpenClaw SSRF 防护:URL 白名单 + 大小上限 + 超时`
- WS-36-05 审计文档补入: `d9637fea` `[Stage36][WS-36-05] 审计文档补入:DEEP_AUDIT_SUMMARY + context_pruner`

Stage 36 WS 完成后的主干 HEAD:
- `d9637fea0ebc3d7c85b485908bf746160395fe71`

Stage 34/35 原始 9 条 commit 仍完整可见:
- `da28fdde`
- `19e27f0d`
- `947c1b49`
- `685dcdd2`
- `5476e896`
- `a9b94a1b`
- `0d051e2e`
- `631de7aa`
- `85eba758`

## 2. 基底稳定动作

WS-36-01.5 已完成的基底稳定动作:
- `alembic current` / `alembic heads` 已对齐到 `s31a1b2c3d4 (head)`
- 修补 7 个历史 migration，解决 UUID/索引/幂等升级兼容性问题
- 修补 `session_feedback.py` 的向后兼容输入与策略文案渲染
- 修补 `jitai_trigger_service.py` 的本地状态过期判定时间引用，消除日期漂移
- 修补 13 组测试漂移或桩实现断言不匹配问题，覆盖 orchestrator / theater / task / strategy prompt / migration 线

本阶段未使用 quarantine:
- `docs/aurora/stage36_quarantine.md` 未创建
- `xfail` 条目: 0

## 3. 安全修复摘要

WS-36-02 Token Bucket:
- 修正 Lua/Go 两侧量纲: `tokens_added = (elapsed_ms / 1000.0) * rate_per_s`
- 新增 `rate_limiter_tokens_current` gauge
- 新增 `rate_limiter_rejections_total` counter
- 新增 3 个 Go 回归测试
- 新增 Rule AW 文档与 guard

WS-36-03 Theater IDOR:
- Theater 关键读写路径切换为 `user_id` 作用域查询
- 拒绝访问统一返回 `403 resource access denied`
- 新增 `theater.access_denied` 审计事件
- 新增 3 个 Python 回归测试
- 新增 Rule Z-Theater guard

WS-36-04 OpenClaw SSRF:
- 新增 `backend/app/services/openclaw/url_guard.py`
- 仅允许 `http/https`
- 拦截私网/回环/链路本地/metadata 地址和危险 scheme
- 下载改为 streaming + `OPENCLAW_MAX_DOWNLOAD_BYTES=10MB`
- 超时统一为 connect/read/write/pool 受控配置
- 新增 4 个 Python 回归测试

## 4. Guard 与 Manifest

新增 guard:
- `scripts/guards/check_rule_aw_rate_limiter_sanity.py`
- `scripts/guards/check_rule_z_theater_user_scope.py`

Manifest 行号:
- `Z-THEATER`: `scripts/rule_guard_manifest.tsv:6`
- `AW`: `scripts/rule_guard_manifest.tsv:8`

## 5. 验收结果

最终一次性验收结果:
- `cd backend && pytest -q` → `3214 passed, 179 skipped`
- `cd backend/gateway && go test ./...` → 全绿
- `bash scripts/journey_smoke.sh all` → 全绿
- `bash scripts/run_all_rule_guards.sh` → 全绿（含 AW / Z-THEATER）

CLAUDE.md 矛盾声明核对结果:
- Fail-Closed 声明已改成与 `REDIS_FAIL_CLOSED` 实际默认行为一致
- Timing-Attack 声明已补充为“gateway secret checks 在 secret 已配置时使用 constant-time compare；backend internal 端点仍依赖非空 `INTERNAL_API_KEY` 才会真正执行校验”

## 6. Stash 与遗留工作树状态

保留未动的 stash:
- `stash@{2026-04-22 20:09:29 +0800}: On codex/stage20-execution: codex-stage36-ws36-01-premerge-unrelated-dirty-state`

本次未纳入 Stage 36 提交的工作树残留:
- `.claude/worktrees/friendly-swirles-8f551c/`
- `.claude/worktrees/jolly-sutherland-3fb20d/`
- `docs/audit/deep_audit_2026-04-22_1045_routing_engine.md`
- `docs/audit/deep_audit_2026-04-22_1100_ux_envelope.md`
- `docs/audit/deep_audit_2026-04-22_1115_response_builder.md`
- `docs/audit/deep_audit_2026-04-22_1130_prompts_assembly.md`
- `docs/sgw/08_rl_scaffolding_deep_dive.md`

## 7. 留给 Stage 37 的 TODO

工作流 A 剩余:
- wildcard 路由盘点
- admin 端点限流
- internal/admin 端点鉴权补齐
- `INTERNAL_API_KEY` 空值跳过修复（fail-open → fail-closed）

工作流 B 全量:
- LLM 安全层 47 调用方接入
- API Key 明文驻留最小化
- 工具异常原文回送清洗
- Prompt 注入分隔符接线

## 8. Memory 索引

仓库中未发现 `MEMORY.md` / `memory.md`，本次未追加记忆索引条目。

## 9. 最近 15 条 Git Log

```text
d9637fea [Stage36][WS-36-05] 审计文档补入:DEEP_AUDIT_SUMMARY + context_pruner
78f55182 [Stage36][WS-36-04] OpenClaw SSRF 防护:URL 白名单 + 大小上限 + 超时
be8f299b [Stage36][WS-36-03] Theater IDOR 修复:加 user_id 作用域
00d50779 [Stage36][WS-36-02] 修复 Token Bucket 量纲错配(elapsed ms × rate per-s)
5a58a354 [Stage36][WS-36-01.5] 基底稳定:migrate + 测试漂移修复 + 0 条 quarantine
40855516 [Stage36][WS-36-01] 基底合并:Stage 33 正式化 + Stage 34/35 回主干
85eba758 [Stage35][WS-35-04] Add journey smoke coverage
631de7aa [Stage35][WS-35-03] Close the metacognition router loop
0d051e2e [Stage35][WS-35-02] Declare backend-only mobile parity fields
a9b94a1b [Stage35][WS-35-01] Render UserStateV1 profile cards
5476e896 [Stage34][WS-34-05] Wire capsule preferences into inline snapshot
685dcdd2 [Stage34][WS-34-04] Archive orphan services and add Rule AT
947c1b49 [Stage34][WS-34-03] Recalibrate error replan bridge
19e27f0d [Stage34][WS-34-02] Wire journey event subscribers
da28fdde [Stage34][WS-34-01] Fill context builder memory lanes
```
