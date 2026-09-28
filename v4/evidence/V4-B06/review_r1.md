# V4-B06 一审 receipt（独立审查）

- 审查会话：wtB06R（未参与 B06 实现）
- 审查对象：分支 `agent/v4/b06` @ `c0261f1e0b63a458cc605d95ebd74fd95c55e5f8`
- 审查日期：2026-09-28 ｜ 方式：只读审查 + 活栈日志/只读 .env 交叉核验（未复跑探针，未烧预算）
- **总裁决：PASS_WITH_CHALLENGES（有保留通过）**——证据实质真实、三条计量缺陷断言全部代码级核实、配置漂移发现成立；但存在 1 项安全门整改（C1）与 3 项记录性勘误（C2-C4），C1 必须在集成/合并前整改。

## 1. 安全门（脱敏复核）

- 全 commit 树扫 `sk-[A-Za-z0-9]{10,}` / `AKID` / `LTAI`：命中均为既有仓库内容（文档假键、测试样例、go.sum 哈希巧合），非 B06 引入。B06 新增文件无 JWT（`eyJ`）、无 `access_token=`/`token=` 实值。
- **C1（CHALLENGED·必须整改）**：`env_redacted_snapshot.txt` L13/L20 以 URL 内嵌形式泄漏真实口令——`DATABASE_URL=postgresql+asyncpg://<REDACTED_URLCREDS>@@127.0.0.1:5432/sparkle`、`REDIS_URL=redis://:<口令明文>@127.0.0.1:6379/0`。REDIS_URL 口令长度 22 与同文件被脱敏的 `REDIS_PASSWORD len=22` 一致，即同一秘密在一处脱敏、另一处明文。同时 `XUNFEI_APP_ID=4e9a500e` 未遮蔽。自检用的模式（eyJ/access_token/token=）覆盖不到 `://user:pass@` 形态，故自测 A6 PASS 结论对该两行不成立，违反卡验收「任何 Key 不入输出」。定性：本机回环 dev 栈口令，风险有限；但口令已进分支 git 历史。整改要求：① 追加提交重脱敏该两行（保留 host/port/库名）；② 后续脱敏脚本模式加入 URL 内嵌凭据；③ 合并裁决时知悉历史已含该口令（本地 dev，轮换可选）。**C1 整改前本卡不得进入集成。**
- 其余敏感键 21 项 `<REDACTED len=N>` 抽验无误；`model_routing_frozen_snapshot.json` 中 `llm_tier_pro_env` 记录的是模型键列表非凭据，放行。

## 2. 探针数据真实性（核验通过）

在只读活栈引擎日志 `logs/grpc_server_2026-09-28_09-55-32_333353.log` 中逐条比对 probe_raw.json / test_results.json：

- 三条 `[LATENCY]` 行逐字吻合：t1 total=16506ms/first_stream_content=2113ms/execute_graph=14632ms；t2 20903/1039/20186；t3 1941/1811/1355（L36121/36237/36333，17:18:23-47 本地，与 probe_raw 09:18Z 窗口一致）。
- 三条 `Token usage recorded` 吻合：1441 tok/$0.000144、1321/$0.000132、44/$0.000004，user_id 与 probe_raw guest 一致。
- 时序单调自洽：ack 0.6-16.9ms → 首可见 1.09-2.82s → 完成 1.99-21.0s；整链口径均晚于引擎口径且方向一致。t3 帧形态（单 delta + full_text、无 usage 帧）与非流式 rescue 一致；`usage_frames:[]` 与「客户端零 usage」一致。
- **t3 400+rescue 时间线实锤**：17:18:46.510 `Generation streaming failed...Error code: 400 - USER is not one of ['system','assistant','user','tool','function']` → 46.524 rescue `Attempt 1/3: model=qwen3.7-flash, reason=强制tier=fast`。成本数学自洽：44×$0.0001/1k=$0.000004（内部账 dashscope_fast 价），支持「rescue 真实用量无实账、仅合成估算 44tok 记账」结论。t1 的 $0.000144=1441×0.0001/1k 同时实证「内部账有估算、回执 cost_micro_usd=0」两账不一致。
- 预算合规：3 模型轮 + t3 失败/rescue 共 ≥4 次上游调用 ≤ 卡定 5，无重试。
- C4（记录性）：probe 脚本 L204 以 `python3 --version`（shell PATH=3.14.3）记录解释器版本，与实际运行的 venv 3.11.15 不符；仅元数据字段误导，帧数据不受影响。

## 3. 计量缺陷三断言代码锚点抽验（全部属实）

1. **cost_micro_usd=0 两账不一致**：`response_builder.py` `_cleanup`（L1619-1701）确认归因判定在前（`resolve_metering_model_key(has_real_usage=tokens>0)`）、合成估算在后（L1652-1661 块：tokens≤0 时按最新 user/assistant 文本估 token）——「no_generation_model + tokens>0」产生机制（FIX545 形状）属实；回执 0 与内部账非 0 已由第 2 节日志实证。
2. **estimate_cost 未知键静默 gpt-4 错价**：`token_tracker.py` L518-519 `if model not in pricing: model = "gpt-4"` 属实；A4 数学复核成立（42×$0.03/1k=$0.00126；100+50 tok 按 gpt-4 in/out=$0.006；dashscope_fast 1441→$0.000144 正确走 router 价）。
3. **no_generation 检出器缺失**：独立复跑 `grep -rn -i no_generation app/ --include=*.py` = 仅 `response_builder.py` 3 处定义/调用，无任何下游检出/告警。A3 FAIL 结论成立（如实 FAIL，不改标签，符合验收精神）。
4. 附带核实：`app/core/metrics.py` L33/L45/L61 与 `gateway/internal/metrics/ws_metrics.go` L140-165 序列名不重叠；**C3（勘误）**：标签集并非"互不重叠"——`chat_mode` 同时出现在引擎 AI_RESPONSE_TOTAL_DURATION 与网关四个序列上，严格表述应为「序列名不重叠、网关标签集为引擎子集（仅 chat_mode）」；卡验收「分开」实质仍满足。
5. `standard_workflow.py` L845 `_build_mode_rescue_response` 存在，rescue 真实二次烧上游属实（M3/缺口清单成立）。

## 4. 配置漂移声明（成立）

- 只读 grep 活栈 `backend/.env`：`^LLM_TIER_PRO=` 存在（L172，1 处活跃行，值未回显），与同文件 L93-97「已移除全部 tier 钉死」注释矛盾——漂移发现属实。
- **C2（证据定位勘误）**：所引日志行 `LLM tier override applied for pro` 不在探针当时引擎进程日志（09-55-32）中；实测位于 `llm_router.py:1116`（`_override_tier_mapping_from_env`）且出现在同日更早引擎进程日志 `grpc_server_2026-09-28_03-05-52` L7490：`...for pro: ['dashscope_standard_thinking', 'glm_4_7_pro']`，与冻结快照 `tier_mapping_effective.pro` 首位降档一致。声明实质为真，证据位置应改指（或补冻结脚本 stdout 存档）。
- 快照核验：31 注册模型/30 带 key/12 tier 与声明一致；hidden_llm_consumer_files.txt 90 行=67+23 与声明一致。

## 5. 裁决与后续

- **tasks.json B06 `evidence_verdict=PASS` 维持有效**（验证卡、FAIL 如实记录且缺口已路由 V4-I10，`I10 depends_on=[B06]` 核实），以本 receipt 为一审依据；**前置条件：C1 整改提交后本 receipt 方随集成生效**。
- C1：必须整改（重脱敏 + 脱敏模式修正）；C2/C3/C4：随 C1 同一或后续提交勘误，不需重跑探针。
- review_receipt.json 维持 PENDING→由协调者以本 receipt 落 VERDICT；本审查未复跑探针（遵守预算红线），真实性以活栈日志交叉核验替代。

—— wtB06R，2026-09-28
