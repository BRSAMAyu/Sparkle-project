# V4-B06｜limitations

1. **样本量**：全链探针 n=3（t3 还因上游 400 走了 rescue 链），只能作基线种子，**不能下 p50/p95 结论**，更不能外推 S05/S06 的 L2/L3 长尾。卡定的 ≤5 次预算优先于统计功效。
2. **单供应商单层**：3 轮全部落在 dashscope_fast（qwen3.7-flash）。GLM「保留待用」各层、MiniMax batch 车道、OCR/翻译/语音专家层均**未做真实 probe**（不在预算内）。tier 映射中各模型的 `cost_per_1k_tokens` 为代码内写死估值，其价格来源未在本次核验——V4 不引用其作商业单价（LATENCY_COST_RUNTIME 口径）。
3. **rescue 链污染 t3 语义**：t3 本意测 L0 问候零生成路径，实际触发上游 400 → rescue 二次调用。「问候语走 L0 零生成」在当前代码**未成立**（仍进 generation_node）；400 根因（消息角色 `USER` 大写被 dashscope 拒绝）在哪个上下文组装环节注入未深挖——记为待修线索，非本卡范围。
4. **回执 cost_micro_usd=0 的根因未改**：本卡只定位到 Usage proto 帧恒 0 而内部账本有估算值的**两账不一致**事实；0 来自哪一层（引擎未填/网关透传）未逐层追踪。
5. **reasoning_mode=fast 请求未生效的观察未定案**：t2 传 `extra_context.reasoning_mode=fast`，回执 metadata 仍 balanced，但该轮本就走 rule_fast_path/fast lane，无法区分「参数未生效」与「metadata 回显口径」——需 I10/路由卡用带日志的对照轮定案。
6. **探针对活栈的写副作用**：guest 登录在 sparkle_db 创建了 1 个访客用户（username 前缀 v4b06_probe_）及其演示种子数据；3 轮对话入会话历史。属产品正常路径写入，未触碰迁移/修数；如需清理走既有 GDPR 清理路径，不在本卡做。
7. **LLM_TIER_PRO 残留钉死未处理**：属用户配置决策面（该 .env 不入库），本卡只记录运行时证据（覆盖生效日志），修复需用户裁决。
8. **价格来源冻结不完整**：MINIMAX 充值档 200 RPM/10M TPM 来自 .env 注释（2026-09-24 实证注记），本轮未独立向供应商核验。
9. **网关整链指标只有 chat_mode 单标签**：整链首 token 无法按模型/tier 分层观测，属观测面增量项（已记 metering_point_map §2）。
10. **独立审查未发生**：review_receipt.json 如实标 PENDING；按舰队模型由未参与会话在集成 SHA 复验。
