# B-05/B-05b 独立 Reviewer 复核回执（2026-09-19）

> Reviewer 独立重测了全部 5 项关键结论（直连 API + 引擎栈复跑），全部核心数字与机制复现。判定 **ACCEPT**，附 2 处非阻塞文档瑕疵（见 §6）。

- 复核人：独立 Reviewer agent（wt2 工作区）
- 复核时间：2026-09-19 12:08–12:15
- 方法：不复用 Worker 探针代码，自写脚本直连 API；引擎 lane 复跑直接执行 patch 内的 `scripts/devtools/probe_zhipu_lanes_b05b.py`（验证脚本本身可用）；API key 临时从主仓 `backend/.env` 读入内存，任何输出/回执不含 key 明文。

## 1. 机制重测（直连 API，与自报比对）

| # | 项目 | 自报 | Reviewer 实测 | 判定 |
|---|---|---|---|---|
| ① | 标准端点 + `thinking:{"type":"disabled"}` | 400 code 1210「该模型始终思考，不支持关闭思考；请使用 low、high 或 max。」 | **400 code 1210，报错文案逐字一致** | ✅ 复现 |
| ② | coding 端点 + 同参数 | 200、无 reasoning_content、~1.01s | **200、reasoning_content 缺失、content 正常（41 字）、总时延 1.342s** | ✅ 复现 |
| ③a | 标准端点默认 ×3 | total p50 1.661s / p95 2.997s | total 1.888 / 2.197 / 2.818s（中位 2.20s，TTFT 0.66–1.90s），全部落在自报 min–p95 区间内 | ✅ 量级吻合 |
| ③b | coding 端点默认 ×3 | total p50 4.760s / p95 7.828s | total 3.415 / 4.811 / 5.213s（中位 4.81s ≈ 自报 p50 4.76s），「coding 显著慢于标准」方向确认 | ✅ 量级+方向吻合 |

补充机制验证：自写用例 `max_tokens=96` + 思考型提问 → `finish_reason=length`、`reasoning_tokens=96/96`、**content 为空**——独立证实「思考可耗尽 completion 预算致空回复」（自报 84–88% 占比与 raw 中 1022/1024 案例一致）。

## 2. OCR / ASR 重测（各 1 次）

- **glm-ocr**（同截图 `主仓 .fieldtest-shots/round3/24_chat_reply1.png`，`/api/paas/v4/layout_parsing`）：**200、0.932s**，`md_results` 与 Worker raw 逐段一致（`AI currently remembers`、`0 current session memories`、`Aurora`、`最近2张任务中有1张超时·轻度关注`、`Current self-model 5 correctable claims`），usage 同为 **580+92 tokens**。✅
- **glm-asr-2512**（`/api/paas/v4/audio/transcriptions`，afconvert 生成 6.5s zh 语音 16kHz mono PCM16）：**200、0.446s**（自报 0.441s，几乎重合），转写「星火复合测试，今天是9月19日，请把这段话准确地转成文字。」——仅 TTS 同音字差异（复核→复合），其余逐字正确。✅（备注：Reviewer 首次用 macOS `say`Flo 声音生成出 0.016s 损坏音频，智谱返回 400 code 1210 参数错误——截断/极短音频硬编风险与自报观察一致。）

## 3. 引擎 lane 独立复跑

临时拷贝主仓 `.env` → wt2 `backend/.env`（复核后**已删除，未进任何输出**），原样执行 patch 内探针脚本：**9/9 lane OK，零 4xx/5xx**，全部正确应答「在线」。Reviewer 实测时延 1.14–3.40s（标准 lane 1.14–1.32s；coding lane 1.91–3.40s），与自报 1.57–6.18s 同量级。脚本本身可运行、行为与 `probe8_engine_lanes.json` 记录一致。✅

## 4. 安全审查

- 全部交付物（`SUPPLEMENT_KEY_ROTATED.md`、`capability_matrix_zhipu.csv`、`changes.patch`、`raw/` 全部 8 个文件）+ `scripts/devtools/probe_zhipu_lanes_b05b.py`：grep **新 key 前缀 `006afe` 0 命中、旧 key 前缀 `f3835e` 0 命中**；`[0-9a-f]{24,}\.[A-Za-z0-9]{10,}` key 形态字符串 0 命中。
- `changes.patch` 仅含声明的 6 个文件，无 `.env`、无任何 `ZHIPU_API_KEY=` 赋值行。
- Reviewer 自身输出（本回执）亦不含 key 明文；`.env` 副本与 `/tmp/b05-review/`、`/tmp/b05b-probe/` 已删除；未起进程/模拟器，未 commit。✅

## 5. 数据一致性

- **CSV ↔ raw 抽样 4 行**：`ocr_primary`（0.743s、580+92 tok）、`stt_backup_zhipu`（0.206s/0.441s、159+25 tok、逐字转写）、`glm_concurrency4`（标准 TTFT 0.447–0.502s、coding total 1.86–5.88s、8/8 无 429）、`glm_lane_engine_stack`（9 lane 时延区间）均与 raw 完全对得上。
- **SUPPLEMENT p50/p95 ↔ raw stats**：标准端点 TTFT p50 0.644/p95 0.727、total p50 1.661/p95 2.997；coding 端点 TTFT p50 0.699/p95 4.277、total p50 4.760/p95 7.828；思考占比 84.5%/87.5%；长上下文 8338 prompt_tokens、needle「萤火计划」、5570-token 案例 reasoning 1022/1024 空 content——逐项一致。✅

## 6. 非阻塞瑕疵（不改判定）

1. `SUPPLEMENT_KEY_ROTATED.md` §1.1 括号示例「如 run1：reasoning 926 字符 vs content 40 字符」与 raw `probe6` 标准 run1（310/42 字符）不符，疑似引自未归档的预跑；不影响其引用的 84.5% 均值与全部 p50/p95（均与 raw 吻合）。建议合入前顺手改为 raw 中的真实示例。
2. §1.4 称中文三重约束「全部满足」，而 raw `chinese_instruction[0]` 记录 `constraint2_pass=false`。人工复核答案「瑞利散射使蓝光如星火布满天空」（14 字、含"星火"、无标点）确认三条约束实质全部满足，属 raw 探针的检查器误报；建议在文档中加一句说明以免后人对照 raw 时困惑。

## 7. 清理声明

wt2 `backend/.env` 副本已删；`/tmp/b05-review/`、`/tmp/b05b-probe/` 已删；无残留进程/模拟器；未执行任何 git commit/push；主仓全程只读。
