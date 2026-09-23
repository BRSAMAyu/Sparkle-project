# MINIMAX-QUOTA — MiniMax M3 真实并发配额核实与进程分摊方案（研究卡收工报告）

- 卡号：MINIMAX-QUOTA（北极星全旅程战役 · B 纵队 · 配额核实线）
- worktree：`wt213`（基线 `ab4f99e7`，**零代码改动**，交付物 = 本报告）
- 背景卡：主仓 `v3-output/BATCH-CAP/REPORT.md` §⑤ 压测步骤第 3 步（容量对齐确认）
- 日期：2026-09-22｜纯研究 + WebSearch/WebFetch 官方文档核实

---

## 0. 结论速览（主会话照单执行清单）

1. **「token plan 并发硬上限 = 8」无官方出处**——MiniMax 官方对 LLM API **不设文档化并发数**，限的是**按账户（主+子账号共享）的 RPM/TPM**。代码里的「8」溯源到 `95941960` 提交时的工程假设，非官方数字。
2. **权威口径（中文平台 platform.minimaxi.com，代码实际域名 api.minimaxi.com，2026-09-22 抓取）**：M3 免费 = **20 RPM / 1M TPM**，充值 = **200 RPM / 10M TPM**，无其他档。
3. **主会话先做零成本动作**：登录 MiniMax 控制台看充值状态定档 → 免费档必须下调 env（推荐 `MINIMAX_MAX_CONCURRENCY=2`），充值档维持现状（8 不动）。
4. 控制台查不了/要复核时，跑本报告 §3 的**梯级探测脚本**（约 5 分钟、~200 次小请求，判据可同时区分 RPM 档与并发天花板）。
5. **不合并双池**（维持 BATCH-CAP 裁决 7）；分摊靠**每进程 env 覆盖**（pydantic 真实 env > .env，已核实可行），回滚 = 还原 env + 重启。
6. 坑位预警：`test_settings_expose_minimax_lane_config` 把默认值 8 **钉死在单测里**——改代码默认会红，改 env 不受影响（详见 §4.3）。

---

## 1. 配额证据（核实结果）

### 1.1 权威来源与数字

| 平台 | 端点 | M3 速率限制 | 来源与时效 |
|---|---|---|---|
| **中文平台（本项目实际使用）** | `api.minimaxi.com`（`MINIMAX_BASE_URL` 代码默认值，主仓 .env 同值） | **免费用户：20 RPM / 1,000,000 TPM；充值用户：200 RPM / 10,000,000 TPM** | `platform.minimaxi.com/docs/guides/rate-limits.md`（经 `platform.minimax.cn/docs/llms.txt` 索引定位的静态镜像），**2026-09-22 抓取**，页面无发布日期标注 |
| 国际版（对照） | `api.minimax.io` | M3 = 200 RPM / 10,000,000 TPM（未区分免费/充值；M2.x 系 = 500 RPM / 20M TPM） | `platform.minimax.io/docs/guides/rate-limits`，**2026-09-22 抓取** |

关键口径细节（中文平台速率限制页逐字要点）：

- **按账户计**：「对您的账号（包括主账号+子账号）实施相应的速率限制策略」——**多 key 不分摊**，全舰队三进程 + 任何同账户新 key 共享同一份 RPM/TPM。
- **超限行为**：「您将收到速率限制的返回报错」，API 拒绝后续请求直到时间窗经过；页面未载明 HTTP 状态码。错误码页（国际版 `errorcode.md`）给出：**1002 = rate limit**（retry later）、**1041 = conn limit**、**2045 = rate growth limit**（「避免请求量突增突降」）、**2056 = usage limit exceeded**（等 5 小时窗口）。
- **提额通道**：邮件申请，「有时可能需要 3-5 个工作日」。
- **Token Plan 订阅档**（Plus $22/Max $55/Ultra $132）面向编码 agent 场景，配额按 5 小时滚动 + 周窗口计，**页面不提供 LLM 并发数**；峰时（工作日 15:00-17:30）有动态限速。

### 1.2 「并发 8」的溯源：工程假设，非官方口径

- `git log -S` 溯源：`MINIMAX_MAX_CONCURRENCY=8` 语义诞生于 `95941960`（"MiniMax M3 free async lane — semaphore(8) fast-reject"），commit 与 MM-M3 卡报告均只写「token plan 并发上限，可不填」，**无任何官方文档引用**；「8」是当时为免费异步车道选的保护值。
- 官方三处文档（速率限制页 / Token Plan intro·faq·pricing / 错误码页）**均无 LLM 按模型的并发数**；唯一类并发数字在视频（inflight 30）、ASR（CONN 2）、音乐（CONN 20）——与 chat completions 无关。
- **未获权威口径的项如实申报**：账号当前是免费档还是充值档（需登录控制台，本卡无凭据）；官方是否在文档之外对免费账号执行隐性并发/突发钳制（唯一 1041 conn limit 错误码暗示存在某种连接级限制，但无数值）。→ 由 §3 探测方案补齐。

### 1.3 口径转换：RPM 才是硬约束，并发只是自保护阀

设批任务占用时长 H（BATCH-CAP 规划值 30s，实测批任务 15–60s），总在途 C 的请求发起速率 ≈ C/H×60。对照 RPM 预算（安全系数 0.8）：

| 账号档 | RPM 预算 | 不触 RPM 的总在途上界（H=30s） | 现状（三进程最坏 32 在途）判定 |
|---|---|---|---|
| 免费（20 RPM） | 16/min（0.8×） | **8** | **超 4×**：H=30s 时 32 在途 ≈ 64 发起/min > 20 RPM；叠加 celery 重试放大 → 与 PROD-LOG2 实测「熔断 OPEN×5 + unhealthy×8」吻合（当时归因于超订级联，真实 1002 混在其中未单独计数） |
| 充值（200 RPM） | 160/min（0.8×） | 80 | **不触线**：32 在途 ≈ 64 发起/min < 160，无需动 |

- TPM 两档都不构成约束：批任务单调用 ≤10K tokens（含思维链）× 200/min = 2M ≪ 10M（充值）；免费档 20/min × 10K = 200K ≪ 1M。
- **推论**：若账号是充值档，BATCH-CAP 观测到的供给瓶颈（≈16 tasks/min）与 429/熔断**全部**可由进程内超订级联解释（该链路已修）；若账号是免费档，则当时还存在真实 RPM 超限，**下调并发是必须项**。两条岔路由 §2 一步定档。

---

## 2. 定档与探测方案（主会话执行，本卡未真跑）

### 2.1 第一步（零成本，优先）：控制台定档

登录 platform.minimaxi.com → 查主账号充值记录/余额 → 有充值 = 充值档（200 RPM），否则免费档（20 RPM）。**定档即裁决，可跳过探测**。

### 2.2 第二步（控制台不可查时）：梯级探测

设计原则：与生产同构（同域名/同路径/同模型名）、同时探测「RPM 档位」与「并发天花板」两个未知量、识别两种错误形状（HTTP 429 与 HTTP 200 + `base_resp.status_code!=0`——后者为 MM-M3 实测的 MiniMax 特有形状，坏 key 即 1004，探针必须解析 body）。

```bash
#!/bin/bash
# minimax_quota_probe.sh —— 主会话执行；KEY 经环境变量注入，不落盘不回显
# 用量: MINIMAX_API_KEY=$(grep '^MINIMAX_API_KEY=' backend/.env | cut -d= -f2) bash minimax_quota_probe.sh
set -euo pipefail
KEY="${MINIMAX_API_KEY:?need key}"
URL="https://api.minimaxi.com/v1/chat/completions"   # 生产 glm_batch 执行面同路径（openai SDK 拼 /chat/completions）
OUT="/tmp/minimax-probe-$(date +%Y%m%d-%H%M%S).json"

probe_one() {  # 单发请求，输出 (http_code|base_resp_code|latency_ms) 到 stdout
  local start=$(date +%s%3N) body http
  http=$(curl -sS -o /tmp/_mm_body -w '%{http_code}' -m 120 "$URL" \
    -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
    -d '{"model":"MiniMax-M3","max_tokens":1024,"messages":[{"role":"user","content":"用一句话解释什么是光合作用"}]}' 2>/dev/null || echo "curl_err")
  # 判据注意：max_tokens 必须 >=1024——M3 思维链计入 max_tokens，太小会 empty-content(length) 污染判据（MM-M3 实测）
  local base=$(python3 -c "import json,sys;d=json.load(open('/tmp/_mm_body'));print(d.get('base_resp',{}).get('status_code',0))" 2>/dev/null || echo "parse_err")
  echo "$http|$base|$(($(date +%s%3N)-start))"
}

judge() {  # $1=http $2=base_resp_code → OK | RATE | CONN | OTHER
  case "$2" in 1002|2045) echo RATE;; 1041) echo CONN;; esac
  case "$1" in 429) echo RATE;; esac
  case "$1" in 200) [ "$2" = "0" ] && echo OK || { [ "$2" = "1002" -o "$2" = "2045" ] && echo RATE || echo OTHER; } ;;
  *) echo OTHER;; esac
}

# —— 探针 A：RPM 档位判别（定免费 20 vs 充值 200，判别度 10×，极易区分）——
# A1: 90s 内每 3.5s 一发（≈17 RPM，贴免费档线下）→ 免费档应全过
# A2: 90s 内每 1.5s 一发（=40 RPM）→ 免费档应很快 RATE；充值档应全过
# 判读：A1 有 RATE ⇒ 连 17 RPM 都吃不下（另有隐性钳制，停探针走邮件提额）；
#       A2 RATE ⇒ 免费档；A2 全过 ⇒ 充值档
# —— 探针 B：瞬时并发天花板（梯级波次，区分 RPM 型与连接型拒绝）——
# 每级 C ∈ {8, 16, 32}：一波单时刻并发 C 发 + 冷却 90s（官方「~1 分钟重置」）× 2 波
# 判读表：RATE（1002/2045/429）= RPM 型，不代表并发上限；CONN（1041）= 真并发/连接上限；
#         Q = 全 OK 最高档。若 C=8 即 CONN，则存在隐性并发钳制 <8（罕见，如实记录）
# 停机条件：任一级连续 3 次 RATE/CONN ⇒ 终止该级；总量 ≈ A 120 发 + B 112 发 ≈ 232 发，
#         tokens 成本 ≈ 232 × ≤5K ≈ ≤1.2M（免费档 1M TPM 内单分钟均摊无压力）
# 执行窗口：避开批车道高峰（建议暂停 glm_batch 消费或低峰执行）；工作日 15:00-17:30 峰时限速窗口勿跑
# 产物：$OUT（逐发 JSONL）——审阅后删除，不入库（磁盘纪律）
```

（伪码级脚本骨架，主会话按需补并发波次的 `xargs -P` 展开；判据与停机条件为规格，照单实现即可。）

---

## 3. 分摊方案（推荐 + 决策树）

### 3.1 架构事实（读码核实，对齐 BATCH-CAP §1.1）

```
MINIMAX_MAX_CONCURRENCY（单值，settings.py:506，默认 8）
  ├─ 引擎进程（make grpc-server，宿主机，读 backend/.env）
  │    ├─ llm_concurrency MINIMAX 池（concurrency.py:132，llm_service/batch 本地兜底消费）
  │    └─ minimax_provider 直连池（minimax_provider.py:87，仅 error_book 消费）   ← 双池同读一个 env → 引擎最坏 = 2×env
  └─ glm_batch worker 容器（单容器 sparkle_celery_glm_batch_worker，celery --concurrency=2
       → 2 个 prefork 子进程各持 1 份 llm_concurrency 池，直连车道不在 worker 用 → 容器最坏 = 2×env）

系统最坏在途 = 4 × env 值（引擎 2 池 + worker 2 子进程；BATCH-CAP 实测口径吻合：8→32）
```

### 3.2 决策树与分摊表

```
控制台定档 / 探针 A 判档
  ├─ 免费档（20 RPM）→ 方案 F：全进程 env=2（必须，非可选）
  ├─ 充值档（200 RPM）→ 方案 P：env=8 维持默认，零改动
  └─ 暂时查不了 → 方案 T（过渡）：env=4（最坏 16 在途，两档都不越线：
       免费档 H=30s 时 16 在途≈32 发起/min 仍超 20——过渡 ≤48h 并加速定档；
       充值档毫无压力）
```

| 方案 | 引擎 env | worker 容器 env | 引擎最坏 | worker 最坏 | 系统最坏 | vs RPM 预算 |
|---|---|---|---|---|---|---|
| **F 免费档** | 2 | 2 | 4（2 池×2） | 4（2 子进程×2） | **8** | 8/30s≈16 发起/min ≤ 16/min ✔（H=60s 时 8/min 更安全） |
| **P 充值档** | 8（默认） | 8（默认） | 16 | 16 | 32 | 64 发起/min ≤ 160/min ✔ 余量 2.5× |
| T 过渡 | 4 | 4 | 8 | 8 | 16 | 见上，限期 48h |

说明：

- **直连池不合并**（维持 BATCH-CAP 裁决 7）：直连车道唯一消费者 error_book 量小（BATCH-CAP 遗留申报原文「实际风险窗口小」），合并需动 `minimax_provider` 或引入 Redis 信号量，改动面大于收益；方案 F 下引擎双池合计 4 已足够 error_book 用。若未来 error_book 上量，另开卡把直连池并入引擎主池（进程内 semaphore 复用，无跨进程问题）。
- **吞吐预期管理**：免费档方案 F 的供给 ≈ 8 在途/30s ≈ 16 tasks/min——与现状供给持平（现状瓶颈本来就在 20 RPM 附近），**不期望吞吐提升**；免费档要吞吐只能①邮件提额（3-5 工作日）②充值升 200 RPM。充值档方案 P 供给上限 ≈ 32-64 tasks/min，随需求放开。
- **en 名单外提醒**：同账户后续任何新 key（如 mobile 直调、脚本探测）都共享同一 RPM 预算（§1.1 按账户计），扩容前重算。

### 3.3 env 写法（每进程覆盖，已核实机制可行）

机制：`settings.py` 用 pydantic-settings，`env_file=[repo_env_path, service_env_path, backend_env_path]`，**真实环境变量优先于 .env 文件**——因此引擎与 worker 可分别覆盖，互不干扰。

```bash
# ① 引擎（宿主机 make grpc-server → run_grpc_with_env.sh → grpc_server.py）：
#    启动前 export（launch env 注入，优先于 .env）
export MINIMAX_MAX_CONCURRENCY=2          # 方案 F；P 方案不 export
make grpc-server

# ② glm_batch worker 容器：Makefile celery-up 目标（Makefile:385-393）docker run 追加一行 -e
docker run -d --name sparkle_celery_glm_batch_worker --network sparkle-project_default \
    -e DATABASE_URL=... -e REDIS_URL=... \
    -e CELERY_BROKER_URL=... -e CELERY_RESULT_BACKEND=... \
    -e GLM_BATCH_MAX_CONCURRENCY=2 \
    -e MINIMAX_MAX_CONCURRENCY=2 \        # ← 新增本行（方案 F/T；容器内两个 prefork 子进程同时继承）
    ... sparkle_backend celery -A app.core.celery_app worker -l info -Q glm_batch --concurrency=2 --hostname=glm-batch@%h
# 注：容器挂载 ./backend:/app，/app/.env 也会被读到——真实 -e 优先于它；两 prefork 子进程共享容器 env，对称分摊天然成立

# ③ 不要改 backend/.env 来做分摊（.env 是引擎与 worker 容器的共享源，改它=三进程同值，
#    无法差异化）；且见 §4.3 钉死单测的坑。主仓 backend/.env 里如已有该键，保持 8 不动，
#    由 ①② 的真实 env 压过它。
```

### 3.4 回滚

- 方案 F/T → 回默认：删 ① 的 export、删 ② 的 `-e MINIMAX_MAX_CONCURRENCY` 行 → `make celery-down && make celery-up` + 重启引擎。默认 8 即 BATCH-CAP 合入时已验证的形态。
- 全程零代码/零迁移/零 proto 变更；回滚窗口 < 1 分钟（一次重启）。
- 若方案 F 下 batch 队列丢弃恶化：不要回调并发（免费档 RPM 硬顶在那），走 SATURATION episode 观测（BATCH-CAP 修复面）+ 邮件提额/充值决策。

---

## 4. 附带发现（主会话裁决，本卡不动）

### 4.1 代码注释与官方口径不符（P3 文案债，零行为）

- `settings.py:498`：「token plan 免费档…并发钳制 = token plan 并发上限」；`concurrency.py:121`：「token plan 并发硬上限 = MINIMAX_MAX_CONCURRENCY」；`minimax_provider.py:11` 同。官方实际是**按账户 RPM/TPM**，无并发数。建议随下次触碰这些文件的卡顺带改写（示例措辞：「MiniMax 官方按账户限 RPM/TPM（免费 20/1M，充值 200/10M，主+子账号共享），无文档化并发数；本值是进程内自保护阀，分摊依据见 v3-output/MINIMAX-QUOTA」）。
- `.env.example:117` 注释可同步补一行档位说明。

### 4.2 单测钉死默认值 8（改默认必红的坑）

`backend/tests/services/test_minimax_provider.py:303` `test_settings_expose_minimax_lane_config` 断言 `settings.MINIMAX_MAX_CONCURRENCY == 8`。**改代码默认值会红**；§3.3 的 env 覆盖路径不影响该测试（测试环境无此 env 导出）。`test_batch_capacity_fault_chain.py:82` 与 `test_minimax_batch_routing.py:261` 是相对断言（== settings 值），env 化安全。

### 4.3 MINIMAX 池无 429 自适应（可选后续卡，非本卡范围）

`concurrency.py` 的 ZHIPU_CODING 池有 `adaptive=True`（429 退避+逐级恢复），MINIMAX 池 `adaptive=False`。免费档账号若确有 RPM 摩擦，可考虑给 MINIMAX 池开自适应或加账户级 RPM 节流器——涉及 `_detect_fallback_reason` 对 1002/1041 的归类映射（目前按 HTTP 429 归 RATE_LIMIT），另开卡。

---

## 5. 诚实申报

1. **信息时效**：两平台速率限制页均 2026-09-22 抓取，页面无发布日期标注，数字可能随官方调整漂移；执行分摊前建议 30 秒复核页面仍在。
2. **未登录控制台**：账号档位（免费/充值）未获直接证据，「免费档」假设依据 `95941960` 的「free async lane」命名与主仓 .env 使用个人 key 的事实；§2.1 一步可定。
3. **未真跑探测**：§2.2 脚本为规格设计未执行（按卡面「不真跑，留主会话」）；判据表中的错误码映射来自官方错误码文档 + MM-M3 实测形状（HTTP 200 + base_resp），未在本次实测 1002/1041 的真实返回形状。
4. **抓取路径**：中文平台 SPA 首页抓不到，经由 `platform.minimax.cn/docs/llms.txt` 索引定位到静态 `.md` 镜像（重定向链 minimaxi.com→minimax.cn，内容仍标注 minimaxi.com 域名）；国际版直接抓取成功。
5. **主仓只读**：零改动零 commit；/tmp 零本卡产物（探测脚本仅为报告内文字）；未起任何进程/模拟器/浏览器；全程 LIGHT。
6. **WebSearch 工具配额耗尽**（至 2026-09-24 重置）：本卡全部证据来自直接抓取官方文档页，未使用搜索引擎聚合结果——反而提高了来源纯度。
