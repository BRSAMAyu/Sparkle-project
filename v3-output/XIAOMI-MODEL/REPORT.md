# XIAOMI-MODEL 收工报告 — 小米车道正确模型名考证与一行回挂

- 卡号：XIAOMI-MODEL（北极星全旅程战役 · B 纵队 · 车道修复线）
- worktree：wt217，基线 `a51b01e6`（含 PROD-FIX-4 全部改动，零漂移）
- 日期：2026-09-22
- 交付物：本报告 + `changes.patch`（6 文件：4 app/config 面 + 2 测试面；零凭据、零 commit、零 push）
- 背景：`v3-output/PROD-FIX-4/REPORT.md`（小米两层修段+回挂点注释）、`v3-output/MINIMAX-QUOTA/REPORT.md`（研究卡方法先例）
- 测试方法：定向不宽扫；pytest 全程 `--timeout` + `-p no:cacheprovider`；基线克隆对比法（禁 stash 合规）

---

## 0. 结论速览（主会话照单执行清单）

1. **404 根因坐实：`mimo-v2-flash` 是已下线的官方模型 id**——北京时间 **2026-06-30 00:00 正式下线**（官方 deprecate 公告白纸黑字，系统替换 06-18→mimo-v2.5），不是 key 问题、不是端点问题、更不是幻觉名——它曾经真实存在（2025-12-16 发布，2026-03-03 仍有更新），死在下线。
2. **回挂已执行（wt217 内）**：两车道模型名 → **`mimo-v2.6-flash`**（V2.6 系列 2026-09-22 今日发布；**不挂官方替代品 mimo-v2.5**——它 2026-10-21 10:00 下线，挂上三周后再炸一次）。FAST/STANDARD 默认链按摘除前原位次（第 3 位）回挂。
3. **回挂不是一行**：考证发现 PROD-FIX-4 的「无 key 无害」是 key-gate + 整链摘除的叠加效应，回挂后必须补**注册过滤闭环**（llm_router 4 处推导式 + force_tier 路径加 `k in self._available_models`），否则无 key 环境的 force_tier/降级路径会重新解析出未注册键。详见 §②.3。
4. **agent_profiles 三处（:243/:521/:612）零编辑即对齐**：它们引用的是注册键 `xiaomi_chat` 而非模型 id；消费面 `_append` 本就有注册过滤（无 key 优雅跳过），有 key 环境随回挂复活。已新增契约用例钉死。
5. **回挂顺带治愈一个基线既有红**：`test_mimo_flash_thinking_is_available_in_standard_tier`（钉 `xiaomi_standard_thinking ∈ STANDARD 链`）在基线克隆上是 failed——PROD-FIX-4 摘链的附带损伤（其 17 文件回归面未含 `test_mimo_integration.py`），本次回挂使其转绿。对比法：基线 164 passed + 1 failed → 改动树 168 passed + 0 failed。
6. **主会话唯一待办**：用已配 key 跑一次单发探针终验（§④ 探测方案，本卡按纪律未真调 API）。现成脚本 `backend/test_xiaomi_mimo_direct.py` 已对齐新名可直接复用。
7. **附带发现（卡外登记，主会话裁决）**：`mimo_pro` 的 `XIAOMI_PRO_MODEL="MiMo-V2.5"` 是**展示名而非模型 id**（官方 id 全小写 `mimo-v2.5`），且该模型 10-21 下线——mimo_pro 复活前必须切 `mimo-v2.6-pro`。

---

## ① 考证证据

### 1.1 来源与时效

| # | 页面（官方） | 抓取时间 | 要点 |
|---|---|---|---|
| 1 | `mimo.mi.com/llms.txt`（文档索引，root `<link rel="llms">` 指向） | 2026-09-22 | 定位全部静态 md 镜像：`mimo.mi.com/static/docs/**.md` |
| 2 | `.../quick-start/summary/first-api-call.md` | 2026-09-22 | BASE_URL 三套形制 + 官方示例模型 id + 鉴权 |
| 3 | `.../quick-start/summary/model.md` | 2026-09-22 | **现行模型总表**（id/能力/限流） |
| 4 | `.../usage-guide/text-generation/deep-thinking.md` | 2026-09-22 | `thinking.type` 形制 + 默认值 + 参数限制 |
| 5 | `.../updates/deprecate.md` | 2026-09-22 | **下线时间表**（mimo-v2-flash 行） |
| 6 | `.../updates/model.md` | 2026-09-22 | 发布日志（V2.6 今日发布；v2-flash 历史存在证明） |

时效申报：全部 **2026-09-22 抓取**；页面上 V2.6 系列「2026-09-22 正式发布」= 抓取当日，数字/阵容最热；各页无独立"最后更新"标注，若隔月使用建议 30 秒复核 deprecate 页。WebSearch 与 web_reader 配额均耗尽（2026-09-24 重置），本卡全部证据来自官方文档直抓——无搜索引擎聚合，来源纯度高但缺第三方旁证（如实申报）。

域名变迁备注：`platform.xiaomimimo.com` 302 → `mimo.mi.com`（SPA 外壳）；文档真身在 `static/docs/**.md` 静态镜像（SPA 路由页 WebFetch 抓不到内容，`.md` 直拼 404——经 root llms.txt 索引解决，方法同 MINIMAX-QUOTA 卡先例）。

### 1.2 模型 id 定论

**现行文本生成模型表（来源 #3，2026-09-22）**：

| 模型 id | 能力 | 上下文/输出 | 限流（按账户按模型） |
|---|---|---|---|
| `mimo-v2.6-pro` | 全模态/深度思考/Function Call/联网搜索/结构化输出 | 1M / 128K | RPM 100 / TPM 10M |
| `mimo-v2.6-flash` | 同上 | 1M / 128K | RPM 100 / TPM 10M |
| `mimo-v2.6-pro-ultraspeed` | 同上（20x 提速） | 1M / 128K | 定制（联系销售） |
| `mimo-v2.5`、`mimo-v2.5-pro` | **2026-10-21 10:00 下线，无系统替换** | 1M / 128K | RPM 100 / TPM 10M |

**`mimo-v2-flash` 的时间线（来源 #5/#6 交叉印证）**：

- 2025-12-16 发布（MiMo-V2-Flash Release），2026-01-12 / 02-04 / 03-03 多次更新——**它曾是我们配置名的真实对应物**；
- 系统替换时间 **2026-06-18 00:00**：请求自动路由到 `mimo-v2.5`；
- **下线时间（Deprecated Time）2026-06-30 00:00（北京时间）**：「After this time, requests using the name of the old model version will receive an error message」——即此后 `mimo-v2-flash` 一律报错，**与 PROD-LOG2 于 2026-09 观测的 404 Unsupported model（生产 3 站×2 条）时间与形状完全吻合**。根因链闭合：不是 key 失效（活栈 key 已配置仍 404，PROD-FIX-4 已自证）、不是端点变更（base_url 核对一致，见 §1.3）、是 id 本身死了近三个月。

### 1.3 端点形制核对（来源 #2）

| 用途 | 官方 BASE_URL | 本仓 settings | 判定 |
|---|---|---|---|
| 实时推理（OpenAI 兼容） | `https://api.xiaomimimo.com/v1` | `XIAOMI_MIMO_BASE_URL` 同值 | **逐字一致** |
| 实时推理（Anthropic 兼容） | `https://api.xiaomimimo.com/anthropic` | （未使用） | — |
| 批量推理 | `https://batch-api-cn.xiaomimimo.com/v1` | （未使用） | — |
| Token Plan | `https://token-plan-cn.xiaomimimo.com/v1` | `XIAOMI_MIMO_TOKEN_PLAN_BASE_URL` 同值 | **逐字一致** |

chat completions 路径 = `{base}/chat/completions`（OpenAI SDK 自动拼接，官方 curl 示例同路径）。**端点无病，纯模型名错**——PROD-FIX-4「模型名被小米端点本身拒绝」的判断准确。

鉴权：官方 curl 示例用 `api-key: $KEY` 头；但官方同页给出 OpenAI Python SDK 示例（`OpenAI(api_key=...)` → Bearer 头），故 Bearer 兼容性由官方自身示例背书（本仓 llm_client 走 OpenAI SDK，无需改动；未实测，如实申报）。

### 1.4 思考控制形制核对（来源 #4）

- 控制参数：`thinking.type = "enabled" | "disabled"`（非标准 OpenAI 参数，OpenAI SDK **必须**经 `extra_body` 传递）——本仓 `llm_service.py:887` `extra_body["thinking"] = {"type": ...}` 与官方形制**逐字一致**，零改动。
- 默认值：v2.6 全系（pro/flash/pro-ultraspeed）**默认 enabled** → FAST 车道（`xiaomi_chat`）显式 `thinking_mode="disabled"` 是必要项，既有配置正确。
- 参数限制（已知悉）：思考模式下 `temperature`/`top_p` 被忽略（强制 1.0/0.95）→ `xiaomi_standard_thinking` 的 `XIAOMI_TEMPERATURE=0.3` 在思考时被小米端覆盖，行为差异官方文档明示，无需代码改动。
- 官方请求参数用 `max_completion_tokens`（非 `max_tokens`）：本仓发的是 `max_tokens`（GLM 有效预算装配点统一注入）——OpenAI 兼容层是否接受 `max_tokens` **未经实测**，探测方案覆盖（§④.3）；若 400 则 llm_service 装配点一行小改（另开微卡）。
- 能力注记：两车道模型均支持 Web Search / Function Call（`enable_web_search` 的 `{"type":"web_search"}` 工具形制在 Web Search 文档同一体系内，本卡两车道未开启，不展开）。

### 1.5 配额口径（附带核实，MINIMAX-QUOTA 式登记）

- **按账户按模型**：RPM 100 / TPM 10M（单一账户下所有 API Key 对同一模型的请求合计——多 key 不分摊，与 MiniMax 同款口径）；
- 平台另设**账户级模型并发上限**（「The platform sets a model concurrency limit for each account」，数值未公开，超载返回 429/延迟）——与 MINIMAX-QUOTA 卡「官方无文档化并发数」的结论不同，**小米是明示有并发限制但无数字**，探针/压测时注意 429 形状；
- 官方建议：高并发场景实现重试与退避（E-07 熔断已在位）。

---

## ② 回挂裁决与改动

### 2.1 裁决

考证明确（官方模型表 + 发布日志 + 下线公告三重一致）→ **执行回挂**。选 `mimo-v2.6-flash` 而非官方替代链给出的 `mimo-v2.5`：

- `mimo-v2.5` 2026-10-21 10:00 下线（无系统替换）——挂它等于三周后再炸一次、再修一次；
- `mimo-v2.6-flash` 今日刚发布（生命周期最长位），官方快速选型指南定位「频繁调用与大规模任务」= 恰是 FAST/STANDARD 车道定位；
- 与原设计一致：两车道同 id，靠 `thinking.type` enabled/disabled 区分（原 `XIAOMI_CHAT_MODEL == XIAOMI_STANDARD_MODEL == mimo-v2-flash` 的双车道结构保留）。

### 2.2 改动清单（`changes.patch`，6 文件，+151/-49）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `backend/app/config/settings.py` | `XIAOMI_CHAT_MODEL`/`XIAOMI_STANDARD_MODEL`：`mimo-v2-flash` → **`mimo-v2.6-flash`**；考证来源+下线时间线注释；`XIAOMI_PRO_MODEL` **不动值**仅加注释（官方 id 全小写 + 10-21 下线提示，卡外登记） |
| 2 | `backend/app/core/llm_router.py` | ① `fast_models` 第 3 位回挂 `xiaomi_chat`、`standard_models` 第 3 位回挂 `xiaomi_standard_thinking`（PROD-FIX-4 摘除前原位次，git diff 实证）；② 注册处注释块改写为考证结论；③ **注册过滤闭环**（见 2.3）；④ STANDARD 兜底默认参数 `["xiaomi_standard_thinking"]` 摘除（该死键残留在这行 `.get()` 默认值里，一并清理） |
| 3 | `backend/.env.example` | 两模型名对齐 + 考证注释 + mimo_pro 提示 |
| 4 | `backend/test_xiaomi_mimo_direct.py` | 手动探针脚本默认名 `mimo-v2-flash` → `mimo-v2.6-flash`（主会话终验直接复用） |
| 5 | `backend/tests/core/test_llm_router_xiaomi_lane_gate.py` | 5 用例 → **8 用例**，适配新真值（见 2.4） |
| 6 | `backend/tests/unit/test_llm_router_free_tier.py` | 1 用例断言适配：`candidates == 原始静态链` → `candidates == 已注册静态链`（不变量演进所致，用例意图=钉「钳制后候选仍是 FAST 链」不变） |

### 2.3 关键伴生修改：注册过滤闭环（为什么不止一行）

PROD-FIX-4 的「无 key 无害」是**两件叠加**：key-gate 注册 + 整链摘除。回挂让静态链重新含 xiaomi 键后，「静态链键 ⊆ 已注册键」这条隐含不变量在无 key 环境被打破。消费面审计结果：

| 路径 | 原过滤 | 判定 |
|---|---|---|
| `_select_by_policy`/`resolve_candidate_models` 的 `_append`（:1257/:1383） | `model_key not in _available_models → skip` | 本就有注册过滤 |
| `fallback.py` 同层降级候选（:288） | `model_key in llm_router._available_models` | 本就有 |
| `LLM_TIER_*` env override（:1067） | `item in self._available_models` | 本就有 |
| GLM_BATCH 链内联（:1031） | `if key in self._available_models` | 本就有 |
| **`select_model` 主链推导（:1192）** | 只按 `_is_model_healthy` | **缺口** |
| **`select_model` STANDARD 兜底推导（:1199）** | 只按健康 | **缺口** |
| **降级 `_fallback_to_next_tier`（:1772）** | 只按健康 | **缺口** |
| **`resolve_candidate_models` force_tier 路径（:1244）** | 无过滤（返回原始静态链） | **缺口** |

最坏情形（修补前，无 key 环境）：FAST 链前两位（dashscope/deepseek）被 E-07 熔断后，候选落到未注册的 `xiaomi_chat`，`.get(key, default)` 兜到 default 的 ModelConfig——**model_key 标签与实际发出请求的配置失真**（观测面假数据 + 绕过注册语义）。修补 = 4 处推导式统一加 `k in self._available_models`，与 `_append`/override/GLM_BATCH 既有过滤同一语义。**有 key 活栈行为零变化**（xiaomi 已注册，过滤为恒真条件；全量回归亦证）。

注：`_is_model_healthy` 对未注册键返回 True（「unknown 默认健康」）——这是缺口此前不可见的另一原因，本卡不动其语义。

### 2.4 lane-gate 测试新真值（8 用例）

保留（PROD-FIX-4 原契约）：无 key 不注册 / 有 key 注册 / 显式选择干净回退（带「未注册」原因）/ 其余链位次零变化。
改约+新增：**模型名钉死**（注册条目 model_name 必须 = `mimo-v2.6-flash`，且 ∉ {mimo-v2-flash, mimo-v2.5, mimo-v2.5-pro} 三个已下线/将下线 id——防再漂移）；**回挂位次**（FAST/STANDARD 第 3 位 = xiaomi hop）；**无 key 解析候选过滤**（force_tier 路径不含未注册 xiaomi）；**policy 对齐**（keyed 时 RETRIEVAL 候选含 xiaomi_chat、unkeyed 不含——钉 agent_profiles 三处对齐面）；位次守护收严为全链逐位断言。

### 2.5 agent_profiles 三处的对齐裁决（零编辑）

`agent_profiles.py:243/:521/:612` 的 `preferred_models` 列的是**注册键** `xiaomi_chat` 而非模型 id 字面量；消费路径 `_append` 的注册过滤使无 key 环境优雅跳过（PROD-FIX-4 已核实显式选择路径，本卡核实 policy 路径同理）。回挂+改名后，有 key 活栈上这三处重新成为合法候选——**对齐由 settings 模型名修正达成，profiles 本体零编辑**。已新增 lane-gate 用例把该对齐钉进契约。`predictive_service:1504`/`multi_intent_service:382` 的 `preferred_order` 同为键引用，一并随回挂自愈（PROD-FIX-4 遗留申报收窄）。

---

## ③ 验证（红绿证据 + 对比法）

- **lane-gate**：改动树 8/8 passed；基线克隆上旧 5 用例 passed（契约随真值演进，非回归）。
- **定向回归电池**（15 文件，改动树）：**168 passed, 0 failed**，含 B-MODEL-SWITCH 守卫 `test_batch_llm_provider_switch.py` **24/24 绿**（其断言面=GLM_BATCH 链+batch 条目不进能力层，与小米回挂正交，实测证之）、Qwen 路由契约、LLM policy、credential routing、E-07 双文件、free tier、same-tier/tier-order/timeout fallback、mimo_integration、predictive_realtime_degrade。
- **补充面**（5 文件）：capability_lane / batch_capacity_fault_chain / o04 / glm_batch_adaptive / explicit_temperature = **96 passed**。
- **对比法**（基线 a51b01e6 克隆至 /tmp，同面同序）：**164 passed + 1 failed**。唯一红 = `test_mimo_integration.py::test_mimo_flash_thinking_is_available_in_standard_tier`（断言 `xiaomi_standard_thinking ∈ STANDARD 链`）——**PROD-FIX-4 摘链的附带红**（其 17 文件回归面未含 mimo_integration），本次回挂治愈：改动树同文件绿。即本卡净效果 = 全部面零新增失败 + 治愈一红。
- **注册数自证**：无 key 环境 `LLMRouter initialized with 27 model configs`、有 key 29（恰差 xiaomi 两键，与 PROD-FIX-4 记账吻合，pytest 日志实证）。
- **环境注记**：worktree 缺 gitignore 产物 `app/gen/` 时 free_tier 两个 streamchat 用例 import 红——从主仓只读拷贝 gen 后绿（PROD-FIX-4 同先例，产物不进 patch）。

---

## ④ 主会话探测方案（本卡未真调 API，按纪律留主会话）

1. **现成脚本（首选）**：`backend/test_xiaomi_mimo_direct.py`（已对齐新名；key 仅从环境读、不回显）：
   `cd backend && XIAOMI_MIMO_API_KEY=$(真实注入) python test_xiaomi_mimo_direct.py`（worktree 合入后在主仓跑同款即可）。
2. **/models 列表端点**：官方文档未记载该端点。可先试 `GET https://api.xiaomimimo.com/v1/models`（Bearer）——200 则顺带拿全量 id 清单复核本报告；404/405 则直接进 3。
3. **单发 chat 探针判据**：`model="mimo-v2.6-flash"` + `thinking disabled`（extra_body）+ `max_completion_tokens=64`；HTTP 200 且 content 非空 = 回挂成立。若 400 提参数问题→改用 `max_tokens` 重发一次（顺带验证本仓参数形制，见 §1.4）；若仍 404→本卡考证链失效（可能性极低，如实回报主会话）；401→key 问题（与模型名无关）。
4. **活栈观测**：合入重启后 llm_router 日志应显示 29 configs；首日盯 E-07 面板 xiaomi 两 hop（若小米端仍拒，熔断会自动摘除，不伤主链）。
5. 成本：单发 ≤ 数百 tokens，可忽略；避开批车道高峰（惯例）。

---

## ⑤ 冲突面声明

| 并行卡 | 其改动面 | 本卡触碰 | 判定 |
|---|---|---|---|
| wt216（只读实测） | 无代码交付面（只读实测线） | settings.py / llm_router.py / 2 测试 / .env.example / manual 探针 | **零重叠** |
| wt218（引擎心跳） | 引擎心跳面 | 本卡动 llm_router.py（注册/选择/回挂函数区） | **同文件不同函数区**：本卡不碰心跳代码路径；合入若同文件建议主会话按 hunk 核对，测试面无交集 |
| agent_profiles.py | — | **本卡零编辑**（新用例仅引用其 AgentRole/ModelTier 常量） | 无冲突 |

---

## ⑥ 诚实申报

1. **未真调小米 API**（卡面纪律）：`mimo-v2.6-flash` 在活栈可用的最终证据只能来自主会话单发探针（§④）。官方证据链=模型总表+发布日志（今日发布）+快速选型指南+官方示例代码，三重一致且 id 生命周期处于最起点。
2. `max_tokens` vs `max_completion_tokens` 兼容性未证实（官方示例全用后者）；探测方案已覆盖，若 400 需一行装配点小改。
3. 官方 curl 用 `api-key` 头、OpenAI SDK 走 Bearer——兼容性由官方 SDK 示例背书，未实测。
4. 信息时效：全部 2026-09-22 抓取；V2.6 系列发布日=抓取日，限流数字可能随后调整；隔月复用先复核 deprecate/model 两页。
5. **mimo_pro 卡外发现**：`XIAOMI_PRO_MODEL="MiMo-V2.5"` 是展示名非 id（官方 id 全小写），且 10-21 10:00 下线（无系统替换）——若 token-plan key 在用，**10-21 前必须切 `mimo-v2.6-pro`**；本卡按 PROD-FIX-4「不动项」边界未动其值，仅登记。
6. WebSearch/web_reader 配额耗尽（9-24 重置）：全部证据为官方文档直抓，无第三方旁证；SPA 页抓取方法（root llms.txt → static md 镜像）已记录可复用。
7. 思考车道 temperature=0.3 会被小米端强制 1.0/0.95（官方明示），行为差异已登记，无需改动。
8. 免费层钳制相关：小米限流口径为按账户按模型 RPM 100/TPM 10M + 明示存在未公开数值的账户级并发上限——若未来小米升主力需与 Qwen 配额统一规划。
9. 本卡改动超出一行回挂（6 文件）：超常部分=注册过滤闭环（§2.3，回挂的必要伴生，不做则把必炸 hop 变相引回无 key 环境）+ 测试契约适配；均已在 §② 逐条给证。

---

## ⑦ 收工核查

- **零 commit / 零 push**：`git status --short` = 6 个 modified + 1 个 untracked（`v3-output/XIAOMI-MODEL/`），与改动清单逐一对上；`changes.patch` 由 `git diff` 生成（332 行）。
- **主仓只读**：唯一接触 = ①只读借用 `.venv` 解释器跑 pytest（`PYTHONPATH` 钉死 wt217，`import app.__file__` 实证解析到本 worktree）；②只读拷贝 gitignore 产物 `app/gen/`（PROD-FIX-4 同先例，不进 patch、不写主仓）。
- **零凭据**：无 .env 读写；活栈 key 状态沿用 PROD-FIX-4 count-only 结论；pytest 用一次性进程内 `SECRET_KEY`（不落盘）。
- **纪律**：pytest 全程 `--timeout` + `-p no:cacheprovider`；定向共 21 个测试文件、约 264 用例，无宽扫；全程 LIGHT（文档抓取+定向单测），无模拟器/浏览器/长驻进程；磁盘 15Gi 可用（<6G 红线远）。
- **/tmp 清理**：基线克隆 `/tmp/wt217-baseline-xiaomimodel` 与 6 个 mimo 文档缓存已删。
