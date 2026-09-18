# R28 修复报告：中文 commitment/考试类记忆抽取断点

- worktree：`Sparkle-sysrev/wt-r28`，基线 `e26af7a2`
- 验收现场：用户 1a50cf82-126f-40b4-a970-5f5265ba9307 说"我下周三有数据结构期中考试，帮我记住这个。"，助手回复"已记住"，但 `episodic_memories` 只有电影偏好条目（0.98 置信）入库，考试条目缺失。

## 一、根因定位

### 事实链（主仓 DB 只读取证）

该用户当天消息时间线：

| 时间 | 消息 | 结果 |
| --- | --- | --- |
| 20:01:22 | USER "我下周三有数据结构期中考试，帮我记住这个。" | **无 assistant 回复**（turn 未完整走完，lane 未触发——基础设施层偶发因素） |
| 20:02:05 | USER "我最喜欢的电影是《星际穿越》，帮我记住这个。" | assistant "已记住"；episodic 落库 0.98 |
| 20:02:21 | USER "根据你的记忆，我之前提到过什么考试？" | 助手无记忆可答 |

电影条目 `source_lane=inferred_extraction`、confidence=0.98、summary 被改写为"用户最喜欢的电影是《星际穿越》。"——证明电影句走的是 **显式口令 fallback → 工作记忆 → LLM 抽取候选（0.98）→ explicit 确认固化** 链路。考试句在代码层即使 lane 被触发也进不了 commitment 通道，根因如下。

### 根因 1：规则路分类漏判（`memory_inferred_write_lane._looks_like_commitment`）

future_markers 全是第一人称意图式（"我会/我要/我打算/我计划/我准备/我想/本周要/这周要/明天要/今天要"）。"我下周三有数据结构期中考试"无任何标记 → 判为 `self`：
- `parse_commitment_due_at` 永不执行，due_at 恒为 None；
- 固化链 `should_consolidate` 的自动通道（`subject_type=="commitment" and due_at is not None`）失活；
- decay 退化为 "7d"/"30d"，语义错误。

### 根因 2：due_at 解析无中文星期覆盖（`commitment_parser.parse_commitment_due_at`）

只支持 明天/今天/这周/本周/月底/N天内/M月D日，**不支持"下周三/这周五/周X/星期X/礼拜X/下下周X"**。而 `extract_candidate` 对 commitment 且 due_at None 的句子**整条放弃**（lane line 279-280）——单修根因 1 会让这些句子反而全军覆没，两处必须同步修。

### 根因 3：固化门槛卡住无"我"主语短句（confidence 启发式）

无"我"主语的事件短句（"明天上午有英语课"）在加性启发式下 confidence ≈ 0.84-0.87，低于 `MEMORY_INFERRED_MIN_CONFIDENCE=0.9`：L1 直写被 `below_threshold` 拒，固化链 `write_candidate_to_l1`（force_write 不豁免 min_confidence）同样被拒。

### 根因 4：LLM 路 prompt 缺陷（`llm_extractor_prompt.v1.md`）

无 commitment 中文示例、payload 无当前时钟（"下周三"无从解析）、无 due_at 格式约束。且 LLM 产出的 commitment 缺 due_at 时会滞留工作记忆永不固化（RuleYAdapter.validate 不校验 due_at）。

### 附注（现场偶发因素）

考试 turn 在主仓 DB 中没有 assistant 回复记录，`enqueue_from_chat_turn`/`enqueue_from_session` 均只在 assistant 消息持久化后触发——该 turn 的 lane 根本没被调度。这是本修复之外的基础设施偶发，本修复保证 lane 被触发后中文承诺句**可靠入库**。

## 二、修复内容

### `app/services/commitment_parser.py`
- 新增 `resolve_weekday_anchor()`：解析 `下下?个?(周|礼拜|星期)X`、`(这|本)(周|礼拜|星期)X`、裸 `周X/星期X/礼拜X`（含数字形式 周3），支持中文数字与 1-7；本周已过自动顺延下周；时段修饰（上午/早上→09、下午→15、晚上→20，默认 18:00）。
- `parse_commitment_due_at` 插入星期分支（位于"这周/本周"兜底之前，避免"这周五"被吞）；全部返回值经 `ensure_naive_utc` 归一为 naive UTC。

### `app/services/memory_inferred_write_lane.py`
- `_looks_like_commitment`：保留原 future_markers 短路；新增事件标记分支（考试/期中/期末/小测/测验/要交/得交/要考/有课/上课/deadline/截止/截稿/面试 + 正则 `有[^，。！？]{0,4}课` 兜住"有英语课"），**且必须 `parse_commitment_due_at` 可解析才判 commitment**——分类与解析联动，杜绝"判成 commitment 又因缺 due_at 整条丢弃"。
- `extract_candidate`：候选句先剥离显式口令（新增 `_strip_memory_command_phrases`，按短语长度降序替换，修复"帮我记住这个"被拆成"帮我"+"这个"残留），candidate_text/semantic_key 不再被口令污染；occurred_at/due_at 过 `ensure_naive_utc`。
- `_resolve_occurred_at`：插入星期锚分支，"下周三"的 occurred_at 对齐真实事件日（此前落进"下周"兜底的周一）。
- confidence：commitment 且 due_at 可解析时 `min(0.95, max(confidence+0.03, 0.9))` 托底到直写门槛（修复根因 3）。
- `_build_explicit_command_candidate`：口令 fallback 产出的事实若含可解析时间锚，升级为 `commitment` + `due_at+7d`（覆盖"帮我记住，下周三有考试"这类无主语句）。

### `app/services/llm_extractor_service.py` + `llm_extractor_prompt.v1.md`
- payload 增加 `now_utc`，LLM 解析相对时间有时钟参照。
- prompt 增补规则 8-10：commitment 的中文事件式定义与示例、commitment 必须resolve due_at（否则降级 self）、时间戳一律 naive UTC ISO8601。
- `_build_candidate` 校验加固：LLM commitment 缺 due_at → 降级 `self`（decay `due_at+7d`→`30d`），避免滞留工作记忆永不固化。

## 三、红绿测试

新增 `backend/tests/unit/test_memory_inferred_chinese_commitment.py`（冻结时钟 2026-09-21 周一）：

- 覆盖中文承诺句 5+：验收原句"我下周三有数据结构期中考试，帮我记住这个。"、"这周五要交实验报告"、"明天上午有英语课"、"下周四有一场高数小测"、"我下周一要考概率论"，以及口令前缀句、真 fallback 句、无时间锚提问负向守卫、naive UTC 断言。
- **修复前：13 红 / 2 绿**（红：self 误判、due_at None、口令残留、occurred_at 偏周一）；**修复后：全绿**。
- 定向回归 `test_commitment_parser` + `test_memory_inferred_write_lane` + `test_llm_extractor_service` + `test_memory_naive_utc_write` + 精度夹具：39 passed，零回归。

## 四、E2E 实测（worktree 独立引擎 :8004）

环境：worktree 代码 + 主仓 Postgres/Redis（进程独立、端口 8004），OpenAI 兼容 mock LLM（:8090，stdlib http.server；`DEEPSEEK_BASE_URL`/`XIAOMI_MIMO_BASE_URL` 指向 mock；**未触碰主仓 backend/.env，未动主仓任何进程**）。REST `POST /api/v1/chat` 全链路：

| 输入 | 入库结果 |
| --- | --- |
| "我下周三有数据结构期中考试，帮我记住这个。" | summary="我下周三有数据结构期中考试"，`commitment`，conf 0.93，**due_at=2026-09-23 18:00（下周三，naive UTC）**，occurred_at 对齐事件日，decay=due_at+7d |
| "明天上午有英语课，别忘了提醒我。" | `commitment`，conf 0.90，**due_at=2026-09-19 09:00（明天上午，naive UTC）** |

测试数据（3 个 E2E guest 用户及关联行）已全部清理，:8004/:8090 进程已杀净，`app/gen` 软链已移除。

## 五、遗留与建议（未在本 patch 范围）

1. **lane 触发依赖 assistant 回复持久化**：assistant 流中断的 turn（如验收现场的考试句）lane 完全不跑。建议后续增加 session 级补偿扫描（对"有用户消息但无 assistant 配对"的 turn 补触发一次 lane）。
2. LLM 路真机（qwen）效果未验证——本环境无真实 key，prompt 已给出 resolve 规则与降级路径，建议接入真实 key 后做一轮 dry-run 抽查。
3. `_pick_candidate_sentence` 的学习词表（learning_tokens）偏 English-CS 语料，"考会计/考公"等人文类事件句依赖事件标记兜底，词表可按误报数据持续扩充。
