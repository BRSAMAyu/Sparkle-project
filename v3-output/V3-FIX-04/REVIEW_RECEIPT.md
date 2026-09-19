# V3-FIX-04 REVIEW_RECEIPT — 独立复核（Reviewer）

> 复核人：V3 Fleet Independent Reviewer｜日期：2026-09-19｜对象：wt4 v3-output/V3-FIX-04（REPORT.md + changes.patch + worktree 未提交改动）
> 方法：全部结论独立重验（自跑测试、自写 stash 对照、自写探针直连 API），不采信 worker 自报数据。

## 结论

**ACCEPT**。改动逻辑正确、接线唯一、零回归、机制经真实 API 双向验证成立。

## 逐项复核结果

### 1. 三个纯函数逻辑（读 diff 独立核对）— 通过
- `is_zhipu_coding_endpoint`：子串 `/api/coding/`（lowercase）判定，与 `providers.py::_get_provider_name` 既有判据一致。
- `glm_thinking_disabled_on_wire`：`ZHIPU and truthy(clear_thinking) and coding端点` — 标准端点不发（否则 400/1210，见 §4）；`clear_thinking=False` 车道不发。
- `glm_effective_max_tokens`：`ceil(requested × 0.15 / 0.12) = ceil(1.25×requested)`，1024→1280 已由单测断言；`None`/≤0/非 zhipu/思考已关车道均原样返回。
- 接线：`get_openai_client_kwargs` 为唯一 `thinking` 构造点（grep 全 app 无第二处）；`clear_thinking` 字段保留 → `llm_service.is_thinking_mode()`(L1620) 与 `custom_expert_service.py:284` 不受影响；`llm_service.py` 两处装配点对 caller 显式 max_tokens 应用留量（`setdefault` 后覆写，显式传参只放大一次，1024→1280 有单测断言）。
- 无冲突确认：无任何 ZHIPU lane 配置 `thinking_mode`（仅 XIAOMI/DEEPSEEK/DASHSCOPE），`_create_raw_completion` 里 MIMO thinking_mode 覆写不会撞上 disabled。

### 2. 测试独立复跑 — 通过
- 新套件：`tests/core/test_llm_router_glm_thinking.py` **6/6 passed**（mock 传输，捕获线上 JSON，零真实请求）。
- 抽查回归：`test_llm_same_tier_fallback.py`(6) + `test_llm_service_streaming.py`(6) + `test_llm_router_policy.py`(7) + `test_llm_router_health_tracking.py`(11) = **30/30 passed**，零回归。

### 3. 基线失败 stash 对照 — 材料性通过（计数小出入，见"非阻塞备注"）
- 对报告点名的 3 个失败套件做真实 `git stash push/pop` 对照：改动前后失败清单**逐字节一致**（10 个 FAILED，free_tier 2F + stage37 2F + deep_analysis 6F），证明与本改动零因果。
- 基线行为探针（stash 后直调 `get_openai_client_kwargs`）：`extra_body={'clear_thinking': True}`、无 `thinking` 键 — 与报告 RED 前提一致。
- 注意：最终版测试文件在基线**连 import 都不过**（helper 不存在），报告的 "3 failed KeyError" 系 TDD 中间态，不可从最终产物复现；但 RED 实质（基线无 thinking 键）已由上述探针独立证实。

### 4. 机制独立验证（自写探针，真实调用恰 2 次，≤2 上限内）— 通过
- CALL1 `glm_4_7_no_thinking`（coding，引擎路径 `select_specific_model → get_openai_client_kwargs → AsyncOpenAI`）：线上 extra_body `{"clear_thinking": true, "thinking": {"type": "disabled"}}` → finish=stop、reasoning_content 空、**reasoning_tokens=0**、1.231s（与 worker 自报 1.262s 一致）。
- CALL2 `glm_4_7_flash_no_thinking`（标准端点）：引擎确实**不发** thinking（extra_body 仅 `{"clear_thinking": true}`）；人工强行附 `thinking:{"type":"disabled"}` → **HTTP 400 code 1210**「该模型始终思考，不支持关闭思考」— 直接证明"标准端点不发该参数"的设计必要性。

### 5. patch 完整性与安全 — 通过
- patch 恰好 4 文件（llm_router.py、llm_service.py、新测试、REPORT.md），`git apply --reverse --check` 证明 patch 与 worktree 状态完全一致。
- 无 `.env`、无密钥：唯一密钥样式命中是测试 dummy `api_key="test-key"`；新旧 key 前缀 `006afe`/`f3835e` 在 patch、diff、REPORT、新测试中 **零命中**。
- base 说明：worktree HEAD 51f5acd7 早于报告所写 fleet base 1083f4f5，但两 commit 间两个被改源文件 **diff 为空** → patch 可直接干净落在 1083f4f5。

## 非阻塞备注（供主会话/后续任务参考）

1. **留量双重放大潜伏边角**：若未来某 zhipu lane 配置 `config.max_tokens` 且 caller 不传 max_tokens，`get_openai_client_kwargs` 已放大一次、`_create_raw_completion` 的 setdefault 放入放大值后再被留量函数放大第二次（1024→1280→1600）。当前不可达（registry 全部 zhipu lane `max_tokens=None`，已逐条核实），且方向安全（多给预算），不阻塞；建议后续在装配点改为"对原始 config 值判定、caller 值单次放大"。
2. 报告 §2.3 失败计数与我的复现有小出入（报告称 free_tier 4F/共 12F；我复现 free_tier 2F/点名 3 套件共 10F，套件组合不同所致）——材料性结论（基线一致、零回归）不受影响。
3. 报告 §4 范围外观察（`core/llm_client.py` 直连路径、标准端点 flash 车道、registry 元数据失真）复核属实，维持"不阻塞、另派单"。

## 收工清理确认

- [x] wt4 `backend/.env` 临时副本已删（gitignored，从未入 status/patch/输出）
- [x] `/tmp/review_fix04_probe.py`、`/tmp/review_fix04_with_changes.txt`、`/tmp/review_fix04_baseline.txt` 已删
- [x] 无模拟器/浏览器/flutter 进程（LIGHT）；未重启主仓引擎；未 commit/push；stash 已 pop、工作区还原无损
- [x] 真实 API 调用共 2 次，未超上限；输出中无任何密钥内容
