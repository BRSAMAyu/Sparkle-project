# V4-B06｜diff_or_evidence_only

**结论：EVIDENCE_ONLY（验证卡，行为已存在，做差量举证；未改任何产品代码路径）**

## 做了什么

1. **模型配置盘点（冻结）**：读活栈 `backend/.env`（Sparkle-project，密钥仅记长度零回显）+ 加载 `app/core/llm_router` 实际注册表冻结为 `model_routing_frozen_snapshot.json`：31 个注册模型、30 个带 key、12 层 tier 映射。主力=qwen（dashscope 置首），GLM 全层「保留待用」，MiniMax M3 仅 glm_batch 车道（RPM 200 预算）。
2. **配置漂移发现**：活栈 .env 末尾残留 `LLM_TIER_PRO=dashscope_standard_thinking,glm_4_7_pro`，运行日志证实覆盖生效（PRO 层首位被降档为 standard_thinking），与该文件「已移除全部 tier 钉死」注释矛盾。本卡不改配置，如实记录待裁决。
3. **全链限额探针（3 次真实轮次 ≤ 卡定 5 次预算）**：`POST :8080/api/v1/auth/guest`（零模型）→ WS `:8080/ws/chat?token=` → 网关 → gRPC → 引擎 → DashScope。测得整链 ack/首可见内容/完成三时点 + usage 回执形态。种子数据见 `probe/probe_raw.json` 与 `metering_point_map.md §5`。
4. **FIX545 与隐藏调用定位**：FIX545 在当前仓库 = V3-FIX-80 已把 default 桶拆为 `no_generation_model`/`unattributed_model`（response_builder.py L44-68），但「带 token 的 no_generation_model」**无检出器**（自测 A3 NOT_FOUND）且产生机制仍在（合成估算时序，L1652-1661）。探针 T3 实捕一例现行产生路径（rescue 链）。
5. **计量面地图（I10 依赖）**：8 个计量写入点 M1-M8 + 缺口清单，见 `metering_point_map.md`。

## 探针关键实证（全链口径，与 S05/S06 gRPC-only 口径分开）

| 样本 | 整链首可见内容 | 整链完成 | 真实模型/链 | 计量实证 |
|---|---|---|---|---|
| t1 生成 | 2.818s | 17.213s | qwen3.7-flash (fast) | 实账 1369+72 tok；回执 cost_micro_usd=0 |
| t2 生成 | 1.093s | 20.969s | qwen3.7-flash (fast) | 实账 1245+76 tok；回执 cost=0 |
| t3 问候 | 1.858s | 1.990s | 流式 400 失败→rescue 非流式成功 | 回执无 usage 帧；内部仅记估算 44 tok（FIX545 现行形状） |

## 验收逐条

1. **任何 Key 不入输出；未授权不发大批请求**：满足。21 项敏感键仅 `<REDACTED len=N>`；probe_raw.json 经模式扫描（eyJ/access_token/token= = 0 命中）。真实调用 3 轮（含失败轮共 ≥4 次上游调用），未超 5 次授权，未重试。
2. **带 token 的 no_generation_model 可检出；未知价格不填 0**：**当前不满足**（如实 FAIL 记录）：检出器不存在（A3）；`estimate_cost` 对未知键/`no_generation_model` 静默按 gpt-4 定价填错价（A4：42tok→$0.00126；unknown 150tok→$0.006）。该缺口即 I10 的工作面，本卡产出为检出台账与复现路径。
3. **gRPC 测量与整链指标标签分开**：满足。引擎 `sparkle_request_latency_seconds{module,method}`/`AI_RESPONSE_TOTAL_DURATION{chat_mode,reasoning_mode,model_tier}` 与网关 `sparkle_ai_chat_*_{duration}{chat_mode}` 序列名与标签集互不重叠（metering_point_map.md §2）。

## 与既有事实的关系

- 不重建 V3：复用既有 guest 登录、WS 协议、`latency_probe`、`token_tracker`、网关指标；S05/S06 的 104 条 gRPC 数据与结论未重置。
- 本卡无 DB 迁移、无 proto 变更、无生成代码改动。

## 交付物索引

`run_manifest.json`（命令/exit/环境/预算）、`test_results.json`（自测+探针）、`probe/probe_raw.json`（原始帧）、`env_redacted_snapshot.txt`、`model_routing_frozen_snapshot.json`、`hidden_llm_consumer_files.txt`（67+23 文件）、`metering_point_map.md`（M1-M8 + 缺口）、`review_receipt.json`（待独立审查）、`limitations.md`。
