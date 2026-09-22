# NBP5-DRIVER · 北极星驱动器判定词表与判据口径加固（收工报告）

> Worker 卡 NBP-5，worktree `wt130`（基线 `7454f484`）。性质：**只修测量仪器**（`backend/tests/northstar_eval/` 驱动器判据），被测系统零 diff。修复对象 = LOOP3 `manual_overrides` 登记的三处自动判据与人工复核不一致 + LOOP2 NBP-5 同族词表债（LOOP3 报告 §3 点名收编）。
> 诚实声明：本轮未跑 8 相真实驱动（要活栈 + LLM 往返，主会话职责）；验证面 = 单测 42 全绿 + LOOP3 真实证据全文 sanity。本修复让仪器测准，**不是**让分数好看——升级窗判据把 LOOP3 的人工翻案规则固化成口径，双读皆 0 仍判 fail。

## 1. 三处判据缺陷：证据引用与修法对照表

| # | 缺陷 | LOOP3 原文证据 | 缺陷还原（哪一行/什么词/什么口径） | 修法（`real_drive.py`） |
|---|---|---|---|---|
| 1 | **V2-D 词表缺口（双层）** | `V2-D-rejudged.json` reason：「探针自动正则 `(为假\|不成立\|是错\|不对\|错误)` 漏『是假的』变体」；`run-summary.json` manual_overrides：「V2-D: fail→pass（判卷词表缺口）」 | ①词表缺「是假的」类措辞；②更深的仪器缺陷：真实回答正文是「该命题是**假**的」——markdown 星号夹在字中间，**即使补词，按原文子串匹配任何「是假的」类词表项都物理上命中不了**。旧判据据 noop 判 fail，人工翻案 pass | 新增 `strip_md_emphasis()`（剥 `*_\`~`）作判据前置归一化；新增 `PROPOSITION_REFUTED_MARKERS`（≥2 字、带主语/系词锚定，如「是假的/命题不成立/结论错误」；裸「错误/正确」**故意不收**——「正确的判定条件是…」是复述条件不是判定命题）；新增 `judge_proposition_stance()` + `judge_gp07_correction_step()`（V2-D 步级：refuted+主题在场→pass；affirmed→fail=LOOP2 污染模式；主题在场立场不明→**blocked 进人工**；主题不在场→fail） |
| 2 | **V2-E 单字判定词** | `V2-E-rejudged.json` original_heuristic：「inconclusive: 无明确对/错判定措辞」；步证据 `says_wrong:false, wrong_hits_head400:[]`；回答原文以裸「**错。**」开头 | 旧 ≥2 字词表（错的/错误/不对/…）漏掉句界单字判定形式「错。」。而朴素补单字「对/错」进子串词表会**反向误匹配**（对→面对/核对/绝对/正对/针对；错→错误/错题/交错）——即任务卡所指单字陷阱，两头都不能走 | 新增 `_stance_single_char_verdicts()`：单字「对/错」仅当**独立成句**（句首或句读后 + 句末标点/串尾）才算判定词——中文无词边界，句界即边界。「错。」开头命中；「面对/核对/错误/对吗/对不上」全部不命中。单测 `test_stance_single_char_requires_sentence_boundary` 双向钉死 |
| 3 | **V1 30s 计时口径** | `run-summary.json` manual_overrides：「V1-EPISODIC30: fail 维持（30s 判据口径）但 90s 补读 3 条全对」；步证据：30s 读 0 条（15:28:27.70），而条目 `written_at=15:28:29.22`——投影比读时刻晚 **1.5s**；90s 复读 3 条全对 | 30s 窗口的计时锚点口径不统一：WS 回合墙钟实测 **19–87s 高方差**（LOOP3 V1-B 19.4s vs V1-A 86.9s），从 **send** 起算会把「LLM 多快」混进「投影多快」，仪器测的不是被测量。写账入队（`enqueue_from_chat_turn`）发生在回合末 → 锚点必须是 **turn end**（WS 终止帧 meta 到达、`send_message` 返回） | 新增 `EPISODIC_PROJECTION_SETTLE_S=30.0` / `EPISODIC_PROJECTION_ESCALATE_S=90.0` + `episodic_projection_reads(turn_end_monotonic)`（锚点=turn end 写死在代码注释与函数签名）+ `judge_episodic_capture()`：首读达标 pass（NBP-6 后常态）；首读不足→+90s 复读后才许 fail；未做复读→blocked 不冒判。**不是放宽**：+30s 与 +90s 双读皆 0 才 fail。NBP-6（7454f484）已把投影实测压到 ~0.6s，30s 首读窗 ~50x 余量，无需放回 90s 常态 |

### 附：LOOP2 NBP-5 同族债收编（LOOP3 报告 §3 点名「复跑者应先扩充 _judge 词表」）

- LOOP2 NBP-5：D1a「当前会话中**未保留**具体记录」未被 `MEMORY_ANTI_RECALL_MARKERS` 命中，自动误判 pass（该翻的是 pass 被翻成 fail，方向与三处相反）。
- 修法：词表补「未保留」「没有保留」两变体。单测 `test_judge_memory_recall_anti_recall_unretained_variant` 用 LOOP2 原句钉死。

## 2. manual_overrides 机制支持

- 三类 override 的判定逻辑已修进驱动器本体（`judge_proposition_stance` / `judge_gp07_correction_step` / `judge_episodic_capture` / 反记忆词表），LOOP4 探针直接 import，这三类**不再需要人工翻案**。
- 溯源：新增 `JUDGE_LEXICON_VERSION = "lexicon-v3-nbp5"`（仪器序列号），gp-04/gp-07 增益证据与 `phase_rejudge` 产物统一落 `judge_version` 字段（原硬编码 `"anti-recall-v2"` 收编进常量）；`judge_proposition_stance` 返回值携带命中词与归一化头部 200 字，人工复核可直接看机器看到了什么。
- 已知局限（诚实）：立场判据仍是启发式——inconclusive 的下游语义是 blocked（人工复核队列），不是 pass；「先驳后夹杂肯定语气」类长文仍可能 inconclusive，属漏报给人工，不属冒判。

## 3. 回归验证

- `cd backend && SECRET_KEY=test /opt/homebrew/bin/pytest tests/northstar_eval/ -q` → **42 passed**（gate 12 + real_drive 单测 30；其中新增 12 个 NBP-5 回归钉）。
- 新增测试均以 **LOOP3/LOOP2 真实证据原文**为样例（V2-D full_text 节选含 `**假**` 原样、V2-E「错。」开头、LOOP2 污染句「这条结论是正确的」、LOOP2 D1a「未保留」句），不是自造样例。
- LOOP3 证据**全文**（非节选）sanity：V2-D → pass（refuted 命中「是假的」）、V2-E → pass（refuted 命中句界「错」），双向 affirmed 命中均为空——无误报。
- 未跑 8 相真实驱动（活栈 + LLM 往返，主会话职责）；驱动器自测 `--check` 亦未跑（无活栈保证，避免对演示栈产生探针流量）。

## 4. 下轮 LOOP4 使用注意

1. **import 面变了**：命题立场判据用 `from tests.northstar_eval.real_drive import judge_gp07_correction_step, judge_proposition_stance`；episodic 排程用 `episodic_projection_reads(time.monotonic())`（在 `send_message` **返回后**取锚点）+ `judge_episodic_capture(first_count, escalated_count, expected_min)`。
2. **证据必须落锚点元数据**：V1 步证据 request 里写 `anchor: "turn_end"` + `turn_end_iso`，可审计防口径再漂移。
3. **判据输入必须先过 `strip_md_emphasis`**（`judge_proposition_stance` 内部已做；探针里其他裸子串匹配一律照此办理）。
4. **V1 判据语义**：首读（turn end+30s）0 条不许直接 fail，必须走 +90s 复读；双读皆 0 才 fail。NBP-6 后预期首读即达标。
5. gp-04/gp-07 证据新增 `judge_version` 字段；出分歧先报代次再对词表。
6. 裸「正确/错误」「为真」「有误」等词**保持不收**（解释性用法误报），扩充词表时维持「≥2 字 + 主语/系词锚定」纪律。

## 5. Worker 五要素

① **三处对照表**：见 §1（每处含 LOOP3 原文引用 + 旧判据为何错 + 新判据为何测得准）；同族债 LOOP2 NBP-5 一并收编。
② **红线面**：`git status` 仅 `backend/tests/northstar_eval/real_drive.py` + `test_real_drive_unit.py` 两文件（+292/-2），被测系统（backend/app、gateway、mobile、proto）**零 diff**；worktree 缺 gitignored 的 `app/gen/`，按卡从主仓拷贝（900K，不入 git，两树 proto 一致——环境预存状况申报）。
③ **冲突面**：在途卡 wt123（mobile chat UI）/wt125（plans API）/wt126（orchestration）/wt129（error 吸收）——本轮只动 `tests/northstar_eval/`，与其改动面**零交集**；不碰 `plans/`、`orchestration/`、`errors` 相关产品代码（NBP-3b 的 goal_type 一行修属产品侧，不在本卡范围，未动）。
④ **诚实申报**：未跑真实 8 相与 `--check`（无活栈）；立场判据对「先驳后夹杂」长文可能 inconclusive→blocked（进人工），修复目标是消灭已知的漏报/误报类，不宣称全自判；单测样例中 V2-D 为节选（全文另做 sanity 验证）；`changes.patch` 由 `git add -N` 生成后已 `git reset -q` 还原 index；**未 commit / 未 push**。
⑤ **收工核查**：见 §6。

## 6. 收工核查

- [x] 改动全部在 worktree `wt130` 内；主仓只读未触碰
- [x] 零 commit / 零 push；交付物 = 本 REPORT.md + changes.patch
- [x] /tmp 无本轮产物（未产生）；无新起进程/模拟器/浏览器；未触活栈
- [x] pytest 仅定向跑 `tests/northstar_eval/`（42 passed，0.1s，内存纪律 LIGHT）
- [x] `app/gen/` 拷贝为环境预存状况，git untracked，随 worktree 生命周期回收
- [x] 本报告已登记于 `v3-output/NBP5-DRIVER/`
