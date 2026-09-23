# GRADE-AB · 判卷档 A/B 评测集与运行器（B-QWEN 假设 A 备弹）

- Worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt189` ｜ 代码基线: `5588ed0a`
- 日期: 2026-09-23 ｜ Worker: B×C 纵队 GRADE-AB 卡
- Patch: `v3-output/GRADE-AB/changes.patch`（2283 行，3 个新文件，全部在 `backend/tests/northstar_eval/` 下）
- 设计依据: `v3-output/B-QWEN/REPORT.md` §4 假设 A（判卷/诊断结构化面，PRO 档 $0.0012 → qwen3.8-flash 同价档 $0.00025，-79%；采纳门槛「≥100 题一致率差 ≤3pp」）
- 红线遵守: **不切流**（零 env 改动、零产品代码改动、零 LLM 调用、零 commit）；真实 key 冒烟留给主会话（见 §6 执行命令）

---

## 0. TL;DR

1. 把 B-QWEN 假设 A 的采纳门槛变成三个可执行资产：**100 题离散数学静态金标题包**（`grade_ab_pack.json`）+ **双档 A/B 运行器**（`grade_ab.py`，`--dry-run` 无 key 可跑通全链装配）+ **pytest 守卫**（`test_grade_ab.py`，8 项断言钉住题包分布/双档解析/守卫阈值）。
2. 双档经 `llm_router.select_model(force_tier=…)` 显式 tier 参数直调，env 不动：档 A=PRO→`dashscope_reason`（qwen3.7-plus 思考，$0.0012/1k），档 B=STANDARD→`dashscope_standard_thinking`（qwen3.8-flash，$0.00025/1k，wire 注入 `enable_thinking=false`）。成本锚点比 0.2083（-79.2%），与 B-QWEN 预期一致，已钉进 pytest。
3. dry-run 全链装配通过（卡面命令原样）：题包加载→校验→双档路由解析→100 题提示词装配→输出骨架落盘。60/60 northstar_eval 目录测试全绿（本卡新增 8 项）。

---

## 1. 判卷链路契约（任务 1 结论）

「一次判卷」在仓库里有确定性面与 LLM 面，本评测对齐两者的输入/输出契约：

| 面 | 位置 | 输入 | 输出 | 本评测的对齐 |
|---|---|---|---|---|
| 确定性判卷（exam-sprint 诊断） | `backend/app/services/exam_sprint_diagnostic_service.py:1115`（`grade`），`:1345-1387`（`_score_answer`：choice 精确匹配 / short_answer 关键词比分∈[0,1]） | 题目（grading_payload 服务端持有，P1-E4 会话制）+ 学生作答 + 置信度（certain/fuzzy/guess） | correctness∈[0,1] → 分数/掌握度更新/瓶颈/过考概率 | 题包字段 `student_confidence` 镜像其置信度口径；`score` 字段对齐其 [0,1] 分值语义 |
| LLM 错题诊断（假设 A 真正的面） | `backend/app/core/agent_profiles.py:399-427`（ERROR_ANALYST，PRO 档，温度 0.3，四段结构①错误类型②根因③正确解法④变式） | 错题+作答 | 错误类型（知识性/理解性/计算性/粗心）+根因 | 判卷提示词消费其错误类型枚举（加 none/blank 两态），温度取 profile 同款 0.3 |

诚实修正沿用 B-QWEN：exam-sprint 判卷本身确定性无 LLM；假设 A 适用的是「若引入 LLM 判卷/聊天内错题诊断」这一面（ERROR_ANALYST + deep 链 PRO→PLUS→STANDARD，`llm_router.py:522`）。本评测=该面在**未来的判卷形态**下的备弹，不触碰现网。

## 2. 题包构成表（Worker 五要素①）

文件: `backend/tests/northstar_eval/grade_ab_pack.json`（schema `sparkle.northstar_eval.grade_ab.pack.v1`，pack_sha256 `fc979182…33e` 由运行证据携带）

| 维度 | 分布 |
|---|---|
| 题量 | **100**（门槛下限，pytest 钉死 ≥100） |
| verdict（金标） | correct **50** ｜ wrong **44** ｜ partial **6**（对错各半达成） |
| error_type（金标） | none 50 ｜ understanding 18 ｜ calculation 10 ｜ knowledge 12 ｜ careless 6 ｜ blank 4 |
| 边界例（卡面要求三类） | partial=部分正确 **6**（R11/F09/G21/C06/C09/A09）｜ slip=笔误滑笔 **6**（S06/G05/G15/G18/C04/C12）｜ blank=空白 **4**（S10/R13/G10/C07） |
| qtype | single_choice 42 ｜ judge 19 ｜ short_answer 39（partial 只出现在简答，与产品判卷语义一致） |
| 学科点（离散数学七大域） | 图论 **22**（欧拉/哈密顿/连通度/生成树/二部图/最短路，与 JOURNEY NS-001 同科同弱点）｜ 数理逻辑 16 ｜ 二元关系 14 ｜ 组合数学 14 ｜ 集合论 12 ｜ 代数系统 12 ｜ 函数与基数 10 |
| 学生置信度（判卷输入上下文） | certain 64 ｜ fuzzy 26 ｜ guess 10 |
| author_confidence（自拟学科置信度） | high 100（见 §5 诚实申报） |

校验：`load_pack` 结构+语义互锁（correct↔none、blank↔空作答、choice 答案必须在选项内、id 唯一），坏包拒绝进评测；pytest 逐题断言。

## 3. 运行器设计与双档路由解析证据（Worker 五要素②）

文件: `backend/tests/northstar_eval/grade_ab.py`（照 real_drive.py 风格：schema 常量、诚实 verdict 语义、证据 JSON 落盘、/tmp 无关、凭据不落盘）

**双档解析**（不依赖 env 切换；dry-run 实测输出）：

```
档 A: force_tier=PRO      → dashscope_reason               (qwen3.7-plus, $0.0012 /1k, thinking_wire=not-injected(provider-default-thinking-on))
档 B: force_tier=STANDARD → dashscope_standard_thinking    (qwen3.8-flash, $0.00025/1k, thinking_wire=False, extra_body={"enable_thinking": false})
成本锚点比 B/A = 0.2083（-79.2%，B-QWEN §4 预期 -79%）
```

- 入口与生产同一：`llm_router.select_model(AgentRole.ERROR_ANALYST, task_type=TaskType.ERROR_DIAGNOSIS, force_tier=…)`（`llm_router.py:1056`，force_tier 优先于 profile/task 路由，`reasoning_mode` 在 force 下不介入 `:1121`）。
- **档 B wire 形态的诚实说明**：`dashscope_enable_thinking_param`（`llm_router.py:196-207`）键于 `config.tier`，STANDARD 层注入 `enable_thinking=false`——这与假设 A 的切换方案（`LLM_TIER_PRO=dashscope_standard_thinking`）上线后的实际 wire 行为**一致**（env 换 PRO 池首位后，该条目的 config.tier 仍是 standard）。即本评测量测的就是假设 A 的真实上线形态，而非理想化的「flash 开思考」形态。
- **纯净性红线**：live 路径绕过 `llm_fallback_manager`/熔断器，router 解析后经 `get_openai_client_kwargs` 直调 `OpenAICompatibleProvider.chat`——降级链若介入会把 B 臂污染成其他模型，A/B 即失效。单题失败按题记 error，不重试换模型。
- JSON 解析消费 `LLMService._parse_json_payload` 同口径（`llm_service.py:1146`，`<think>` 剥离+块提取；三形态自测通过：思维链前缀/围栏/非 JSON→parse_fail 计数）。
- 判卷协议两臂同参：system 提示词逐字节相同（单变量=模型档位，pytest 钉住）、温度 0.3、串行、单题超时默认 120s（PRO 思考档量级）。
- 输出：控制台逐题对照表（两臂 verdict/error_type/解析 ok/互判 eq）+ 汇总（两臂 vs 金标 verdict_acc/etype_match/parse_rate/score_MAE/成本估算/P50/P95 时延）+ gate 判定 + 分歧/错判清单（题号级）；JSON 落盘 `grade_ab_run_<ts>.json`（meta 携带 pack_sha256/prompt_sha256/双档解析证据/key 只以布尔在场）。
- gate 冻结（B-QWEN §4，防事后合理化）：①错误类型分类一致率差 ≤3pp；②JSON 解析成功率差 ≤2pp；两条全过 → `adoption_signal=pass`。成本比另报不参与判定。

## 4. 冲突面声明（Worker 五要素③）

本卡改动 = 3 个**全新**文件，全部在 `backend/tests/northstar_eval/` 下：

| 文件 | 性质 |
|---|---|
| `backend/tests/northstar_eval/grade_ab.py` | 新增运行器 |
| `backend/tests/northstar_eval/grade_ab_pack.json` | 新增题包 |
| `backend/tests/northstar_eval/test_grade_ab.py` | 新增 pytest 守卫 |

零产品代码改动、零 env/配置改动、零 proto/迁移改动。与其他在跑卡（wt178=mobile、wt180=event_bus+网关、wt186=部署面、wt187=loguru 批量、wt188=orchestration 测试）**零重叠自明**；对 `tests/northstar_eval/` 既有文件（real_drive/runner/grading/journey_schema/metrics/simulator/feature_tour 及其测试）零改动，目录内测试 60/60 全绿可证。

## 5. 诚实申报（Worker 五要素④）

- **学科置信度**：100 题全部为组卡 agent 自拟并**逐题验算**（题包每题带 `author_confidence`，全部 high——存疑题未入包）。验算覆盖：组合数/排列/容斥/抽屉/隔板数值、欧拉/哈密顿/握手/连通度定义与实例、群/环/格/布尔代数判定、逻辑等值式与量词否定。`author_confidence:medium` 字段位保留但当前为空——若主会话复核发现任何题干或金标可疑，按题号剔改即可（题包静态、id 稳定）。
- **判卷边界例的固有噪声**：partial 题（6 题）的 error_type 金标是组卡 agent 的判读（如"漏答说明部分"记 understanding），LLM 在这类题上与金标分歧属预期——这正是边界例要压测的面；若 gate ① 恰在阈值边缘，建议先看分歧清单里 partial 题占比再下结论。
- **careless 判定的可观测性**：6 道笔误题的金标判据是"实质思路正确+表面滑笔"（如 `C(8,2)=26`、`9×8/2=72`），LLM 只见最终作答文本；其中 5 题滑笔在作答文本内可见（式与结果矛盾），G05/S06 型（列表对但计数错）相对难判——已按"计数笔误"写进 gold.brief 供人工复核分歧。
- **成本与时延为估算面**：单价取 router 注册锚点（$0.0012/$0.00025，B-QWEN 2026-09-22 快照，落地前以 dashscope 现价复核）；token 数为 CJK*0.6+other*0.25 的启发式（两臂同提示词，相对比较公平，绝对值不可当账单）。
- **无 live 实测数据**：worktree 无 .env、纪律禁止试调 LLM。所有质量结论（一致率差是否 ≤3pp）**尚不存在**，本卡只交付弹药；adoption_signal 只有主会话真实运行后才产生。

## 6. 主会话执行命令申报（真实 key 冒烟与全量）

worktree 无 .env（预期），key 由主会话注入；先 5 题冒烟再全量：

```bash
# ① 冒烟（5 题 ×2 臂，预计 ~1 分钟、成本 <$0.01）
cd <worktree>/backend && SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
  DASHSCOPE_API_KEY=sk-*** python3.11 tests/northstar_eval/grade_ab.py --limit 5

# ② 全量（100 题 ×2 臂，串行；A 臂思考档预计 ~8min，成本估算 <$0.5）
cd <worktree>/backend && SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \
  DASHSCOPE_API_KEY=sk-*** python3.11 tests/northstar_eval/grade_ab.py
# 证据默认落 <worktree>/v3-output/GRADE-AB/runs/（GRADE_AB_OUT_DIR 可覆盖）
```

判定读法：汇总里 `gate ①/②` 双 PASS → `adoption_signal=pass`（省 79% 成本的判卷面切换可立项）；任一 FAIL → 分歧清单按题号人工复核（partial/slip 边界题优先）。

## 7. 验收记录（本卡）

- 卡面 dry-run 命令原样通过：`SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 tests/northstar_eval/grade_ab.py --dry-run` → 题包加载 100/100、双档路由解析（dashscope_reason / dashscope_standard_thinking）、提示词装配 100 题（prompt_sha256=c344e7b8a146d990…）、输出骨架落盘。`-m` 模块式调用与文件式调用均验证。
- live 无 key 路径：诚实拒绝（"DASHSCOPE_API_KEY 为空……或先 --dry-run"），不半跑。
- pytest：`tests/northstar_eval/` 全目录 60/60（本卡 test_grade_ab.py 8 项：题包下限/分布/互锁、双档解析与 -79% 锚点、两臂同提示词、gate 数学 pass/reject 双向、阈值冻结、CLI dry-run 端到端）。
- ruff + black(--line-length 120) 干净。
- 零 LLM 调用（纪律红线；live 路径存在但本卡未执行过）。

## 收工申报（Worker 五要素⑤）

- [x] 题包构成表（§2）
- [x] 运行器设计与双档路由解析证据（§3）
- [x] 冲突面声明（§4，3 新文件零重叠）
- [x] 诚实申报（§5，含主会话执行命令）
- [x] 收工核查：未 commit/push；`git status` 仅 3 个 untracked 新文件 + v3-output/GRADE-AB/（REPORT.md+changes.patch）；/tmp 干燥产物（grade_ab_dryrun*、grade_ab_live、构建脚本）已删；无进程/模拟器/浏览器残留；无凭据入任何交付物
