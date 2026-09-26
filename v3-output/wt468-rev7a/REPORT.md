# wt468 独立审查报告 — 审查轮 7A（wt444..wt466 集成进 main 的 backend 产品码改动）

- 审查人：wt468（独立会话，未参与窗口内任何实现）
- 审查基座：worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt468-rev7a`，分支 `wt468-rev7a`，base `310d6b22`
- 审查窗口：`b5a59b1b..310d6b22`（wt450 轮6登记之后至 wt466 集成 + 台账卫生；窗口内产品码 diff 共 22 文件，+873/−107）
- 方法：逐文件读 diff + 读当前完整实现；每个疑点写探针测试跑真实代码（backend venv + sqlite/go test），只有探针红的记 finding；同时抽查窗口内新测试与被改测试的断言质量。
- 探针为临时文件（`backend/tests/unit/zz_probe_*.py`），结论留痕于本报告后已删除，未提交。

## 总 verdict

**fix-required（窄）**：4 个 finding——1×P2（FIX-77 恒真式正则误拒数学学习内容）+ 3×P3。窗口主线交付（V3-FIX-155 SSE EOF 哨兵、FIX-150/151/149、FIX-78/79/80/81、FIX-146/147/148、FIX-145 gateway 补挂）全部经探针验证成立、无回归；P2 一项是 FIX-77 修复引入的新误判族（同症状换形态），建议开修复卡，不阻塞集成。

## Finding 列表（已按 V3-FIX-164..167 登记 DYNAMIC_ISSUES.md 表尾）

### V3-FIX-164 · P2 · SQL 校验器恒真式正则误拒数学学习内容（FIX-77 新误判族）

- 位置：`backend/app/orchestration/validator.py:56`（`SQL_INJECTION_PATTERNS[0]`：`\b(?:or|and)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+\b`）
- 复现探针：`RequestValidator()._contains_malicious_content("Is 1 = 1 and 2 = 2 always true?")` → **True**；`"Which is true: 2 = 2 or 3 = 3?"` → **True**（探针实录红，两例均命中恒真式 pattern）
- 危害：`validate_message → _contains_malicious_content → "Message contains potentially malicious content"` 硬拒（non-retryable，error_code=INVALID_ARGUMENT）。该链在 `/ws/chat` 主链路 `orchestrator.process_stream` Step 1 无条件生效（orchestrator.py:2216 → validator.py:218）——数学真值问句是学习域合法核心内容，与 FIX-77 要治的「正常学习内容被拒答」同症状。与原病例差异：原为英文词序 4/400 实锤；本例为构造性探针（未做 bench 扫描），频谱更窄（需 `or|and`+数字=数字 相邻形态）。
- 建议修法：恒真式信号加载荷语境约束（前邻引号/右括号，如 `['\"`]\s*(?:or|and)\s+...`）或双侧限单数字并要求引号邻接；修卡需对 400 样本 bench 复扫双向收敛（既不再拒数学句，也不丢 `' OR '1'='1` 族）。附 NOTE：数学句被拒证据链已实测，注入判定语义改动需 reviewer 过（沿用 FIX-77 卡纪律）。

### V3-FIX-165 · P3 · V3-FIX-78 typed error 消息违反自身关键词约束（重试关键词泄入 str，当前 latent）

- 位置：`backend/app/services/llm/fallback.py:638-641`（chat 链 `No fallback candidates left after {n} attempts; last error type: {type(e).__name__}`）、`fallback.py:807-810`（stream 链同式）、`fallback.py:489-505` 预算/预检消息（干净）
- 复现探针：`_detect_fallback_reason(LLMProvidersExhaustedError("No fallback candidates left after 2 attempts; last error type: APITimeoutError"))` → **FallbackReason.TIMEOUT**；`... last error type: APIConnectionError` → **CONNECTION_ERROR**（探针实录红）
- 危害：`core/exceptions.py` 两个 typed error 的 docstring 明文约束「消息不得含 429/rate limit/timeout/connection/503/quota 等关键词，否则会被 _detect_fallback_reason 误判为可换道重试」——本窗口实现把上游异常**类名**拼进 str，超时/连接类类名（APITimeoutError/APIConnectionError/TimeoutError）逐字含 `timeout`/`connection`，约束在落地当天即被打破。当前**无活跃再喂入路径**（下游 standard_workflow `_should_fast_fail_generation`、`build_safe_chat_error` 均为 isinstance 判类，实测用户文案/错误码不受影响），故 P3；但任何未来外层字符串分类重试循环都会把「快速诚实失败」重新变回换道烧预算（FIX-78 立卡动机原样复活）。
- 建议修法：str 只附中性终结码（如 `last upstream error class: upstream_terminal`）或对类名做关键词消毒；同步把 docstring 约束补一条测试钉住（现有 test_q06_resilience_fastfail 只钉了健康路径消息，未钉末次异常类名拼接消息）。

### V3-FIX-166 · P3 · finish_reason='length'（provider 侧 token 上限截断）被当作完整收尾——FIX-155 契约未覆盖的截断同族形态

- 位置：`backend/app/services/llm_service.py:1669-1670`（finish_reason 只留布尔 `_saw_finish_reason`，值面丢弃）；`backend/app/api/v1/chat.py:857`（done `completed=True` 无 length 分支）
- 复现探针：provider 流末帧 `finish_reason="length"` → 无 `stream_truncated` 标记（探针实录：P6 断言「length 不标截断」成立）——即部分回答（被 max_tokens 掐断）在 REST /stream 面 `done.completed=true`、照常落库为完整轮
- 危害：与 FIX-155/160 同族的「部分内容冒充完整答案」，但形态是 provider 授权截断（用户侧症状相同：答案中途戛然而止且无任何标记）。窗口在 service 层手里**已有** finish_reason 值、且刚冻结了 done.completed 契约（天然挂点），却只消费了空/非空；/ws/chat 面 StreamChunk 无 finish_reason 字段，gRPC 轨道同样不可见。
- 建议修法：值面观测 `length` → 最小形态=落库/响应 metadata 加 `finish_reason=length` 标注（对齐 FIX-160 的 truncated 键消费卡一并裁决）；协议形态如需 done `reason=upstream_length_truncated` 走契约变更（六帧冻结纪律不破坏）。

### V3-FIX-167 · P3 · 六帧契约锁正则盲区：双引号风格发射的帧不被枚举捕获（断言质量）

- 位置：`backend/tests/unit/test_v3_fix155_stream_eof_sentinel.py:340`（`re.findall(r"\{'type': '(\w+)'", source)`）
- 复现探针：对 `chat_stream` 源码跑该正则 → 捕获集 `{text,tool_start,tool_result,widget,error,done}`（六帧齐）；但 stream_interrupted 分支的 done 帧是 `json.dumps({"type": "done", ...})` 双引号风格，`re.findall(r'\{"type": "(\w+)"')` 另捕获 `{'done'}`——**当前锁对双引号帧完全失明**（探针实录）
- 危害：未来新增帧型若采用双引号风格发射（本窗口已开此先例），契约锁零告警静默通过——「六帧枚举冻结」的门禁强度低于其声称语义。产品码无缺陷，纯断言质量。
- 建议修法：锁测试同时提取单引号与双引号两种字面量风格并入并集断言（一行改动，把本探针断言转正即可）。

## 逐对象 verdict

| 对象 | 窗口改动 | verdict | 证据 |
|---|---|---|---|
| `services/llm_service.py`（FIX-155 哨兵） | `_saw_finish_reason` 闭环判完成；缺哨兵 yield `stream_truncated`；截断轮抑制 tool_call_end；异常原样上抛 | **approve** | 探针 6 项：零帧 EOF 标截断/带 finish_reason 零误标（含 reasoning+annotation+usage 空 choices 尾帧）/截断工具桶零 tool_call_end/异常路径零截断标记混入/FIX-61 孤儿桶抑制在重排后仍生效（回归探针）/FIX-53 关联测试绿；length 形态见 V3-FIX-166 |
| `services/llm_service.py`（FIX-53/61 现状复核） | 窗口外落地，本轮复核 | **approve** | 关联测试 4/4 绿；`chat_stream_with_tools` 当前实现 index 归属/稳定 id/孤儿桶抑制逐条读实现确认 |
| `api/v1/chat.py`（SSE 帧契约） | error 帧错误路径、`\n\n` framing、done `completed` 字段、截断轮不落库 | **approve**（附 167 锁强度 finding） | 探针：落库异常→error+done(turn_failed)；tool_start 已宣布后截断→零执行零 tool_result+done(completed=false)+零落库；既有 FIX-53 SSE 路由测试 4/4 绿；六帧枚举源码锁绿；OpenAPI 快照重冻结恰一行（diff 实测 1 行） |
| `services/tool_history_service.py` + `orchestration/executor.py`（FIX-62 现状复核） | 窗口外落地，本轮复核 | **approve** | 两落点日志仅 `type(e).__name__+DBAPI 类名/pgcode`（tool_history_service.py:157-166、executor.py:1160-1168），零消息文本；专项测试绿 |
| `main.py`（FIX-150 lifespan event_bus） | 无条件绑定模块级单例 + 降级 WARNING + AsyncSessionLocal 局部名遮蔽顺带修 | **approve** | EventBus.__init__ 纯内存构造核实（event_bus.py:690-740，零 I/O）；`tests/core/test_lifespan_event_bus_redis_unavailable.py` 2/2 绿（真 lifespan redis=None 形态）；`event_bus is not None` 守卫语义无害 |
| `alembic/env.py`（FIX-151） | `fileConfig(..., disable_existing_loggers=False)` | **approve** | stdlib 语义探针（True 禁用/False 保留同一存量 logger 实测）+ 源码锁；alembic.ini logger 段不受影响 |
| `models/group_files.py`（FIX-149） | trust_level 补 `values_callable` | **approve** | sqlite 真轮回探针：默认写库 'member'、OFFICIAL 读回还原枚举；同向扫描复核：`grouprole` 在 baseline 迁移为**大写**标签（cc9383c4c29f:1030,2162-2164）与 ORM 按名绑定一致——view/download/manage_role 三列**非**同病（审查中一度怀疑，已用迁移源 overturn）；仅 groupfiletrustlevel 为小写标签（gkb001:26），修复面完整 |
| `aurora/friction_diagnosis.py`（FIX-146/147） | 否定作用域=最近后继词牌+重叠同判+词牌内否定字为内容；EN `n'?t` 词形族 | **approve** | 探针：无标点链「不是太难了是没时间」difficulty 否定/time 正向；「不是没时间是太难了」双否定 time 出局；「没时间太难了」词牌内‘没’不外溢双正向；dont/won't 同判 burnout 否定；两否定各毒化各的最近词牌；sha 双钉 test_a03 全绿（词面未动） |
| `services/seed_library_service.py`（FIX-148） | fence/screen 匹配投影（逐字符 NFKC+剥零宽族）+ span 映射回原文替换 + screen 双投影并集 | **approve** | 探针：软连字符/零宽非连字符插闭合标签被中和、ASCII 闭合零残留；全角+零宽混合探针 screen 捕获；正规内容字面保真（shipped 7 测+探针绿）；投影索引映射逐行核读（NFKC 多字符同指原 char、reversed 替换索引稳定） |
| `orchestration/validator.py`（FIX-77） | 关键词+跨句 from → 七族结构信号 | **fix-required**（V3-FIX-164） | 良性英文词序三条全过、注入经典六族全捕获、裸 delete-from 豁免（设计决策如实）；恒真式正则误拒数学真值问句（探针实录红） |
| `services/llm/fallback.py` + `services/llm/concurrency.py`（FIX-78/79） | 全断供预检零上游尝试、链总预算、typed error、排队深度 admission cap | **approve**（附 165 keyword finding） | shipped chaos 11 测绿（预检/扫尽/statechart typed 穿透/generic 仍包装/池 cap 触发与不触发双态/build_safe 映射）；`LLM_POOL_MAX_WAITING` 语义逐行核读（waiting>cap 即拒、锁内自增自减无虚假拒绝窗口）；FIX-156（pre-pool 瓶颈遮蔽）已在台账 OPEN，与本修复不矛盾 |
| `orchestration/statechart_engine.py`（wt460 补全） | typed fast-fail 异常原样穿透，其余维持 RuntimeError 包装 | **approve** | 三态测试绿（exhausted/overloaded 穿透+generic 包装）；isinstance 分支在 build_safe_chat_error 先于 provider 泛化分支核实 |
| `orchestration/response_builder.py`（FIX-80 + FIX-155 透传） | `resolve_metering_model_key`（no_generation/unattributed 显式标注）；generation_stream_truncated 进 metadata | **approve** | 专测 7 绿；三处调用点 `has_real_usage` 变量在 scope 且第三处合成 token 估算确认发生在判定之后（代码行 1634-1665 顺序核实） |
| `core/llm_router.py` + `services/llm/fallback.py reset_health` + `api/v1/llm_health_admin.py` + `api/v1/router.py`（FIX-81） | 双源复位单出口 | **approve** | 7 测绿（内存三相复位保持语义/单 key scope/未注册无操作/redis 三族键清/双源联动）；端点 superuser 依赖+audit 装饰器+redis 面失败 503 不回滚内存面（收敛操作语义正确） |
| `core/exceptions.py` + `core/safe_error_messages.py`（FIX-78/79 映射） | 两个 typed error + 专属文案/错误码 | **approve**（docstring 约束违反见 165） | isinstance 分支先于 provider 名标记分支（Overloaded 429 消息先命中 typed 分支实测）；关键词约束违反不影响用户可见面 |
| `agents/standard_workflow.py`（FIX-155 WS 面 + FIX-78/79 fast-fail） | stream_truncated→审计旗标+error 帧下行（suppress 包裹）；typed error 不进 rescue/模板 | **approve** | 源码锁测试绿；error 帧参数（ERROR_CODE_UNAVAILABLE retryable）与移动端失败态契约一致性由 wt466 契约锁+本窗口全链核读确认；gRPC 轨道落库残留已由 V3-FIX-160 如实在档（非新发现） |
| `gateway chat_orchestrator_chatflow.go`（FIX-155 网关面） | `sawUpstreamFinishReason` EOF 检测→saveExtra.truncated=true+退出语义缓存写入，synthetic STOP 保留 | **approve** | `sawUpstreamFinishReason` 在 resp.FinishReason!=NULL 处置位（:794-795）核实；truncated 键与 R2-GW-1 路径同键（:757/:1019）；缓存写入 `if !possiblyTruncated` 包裹核实；handler 包 `-count=1` 全量绿 |
| `gateway proxy_routes.go`（FIX-145） | 补挂 POST copy-to-library 代理 | **approve** | 引擎侧路由存在（community.py:2572）；双测绿 + handler 全量绿 |

## 抽查既有测试断言质量

- `test_v3_fix155_stream_eof_sentinel.py`（新）：断言携带疾病签名对照（事件链全列打印）而非裸布尔；异常路径测仅断言 raise、未断言「raise 前零截断标记混入」（本审查探针 P5 已补证，实现无问题）——建议后续把 P5/P1（零帧 EOF）断言吸收进正式测试。
- `test_v3_fix53_tool_call_stream_correlation.py`（窗口内修改）：加 finish_reason 终帧是哨兵语义下的**必要契约适配**（完整轮必须带终帧），四个聚合断言本体未动——非弱化。
- `test_v3_fix121` 族（窗口内 wt446）：钉旧值逐例裁决（40 更新/4 未控时钟/1 接线缺陷），抽查 event_bus_e2e（同库 URL 修正=增强）与 redis_failure_scenarios（failure_threshold=1 保原意图，附注释）——非弱化。
- 契约锁正则盲区见 V3-FIX-167。

## 已验证无问题（探针/测试全绿）清单

1. FIX-155 零帧 EOF/首帧 EOF 边界、reasoning/annotation 帧完整性、usage 空尾帧、异常不冒充截断
2. FIX-61 孤儿参数桶抑制在 FIX-155 重排（整块缩进进 else 分支）后零回归；FIX-53 index 归属/稳定 id 现状
3. FIX-61 抑制与 FIX-155 截断抑制叠加：截断轮零 tool_call_end、`tool_start` 已宣布时零执行零 tool_result、done(completed=false) 收束——无「双重 continue 丢必要事件」路径（tool_call_chunk 已实时下行，终态由 done 帧显式中断哨兵承担）
4. FIX-155 REST 轮不落库（部分文本不进 chat_messages）；错误路径 error+done(turn_failed) 双帧
5. FIX-146/147 否定作用域七项对抗探针 + sha 双钉词表零漂移
6. FIX-148 围栏/筛查 Unicode 投影（零宽/软连/全角）+ 字面保真
7. FIX-77 注入捕获面（六族经典载荷全捕获）+ 良性英文词序豁免
8. FIX-149 枚举值轮回 + 同族列迁移标签核查（overturned：role 三列非同病）
9. FIX-150 真 lifespan Redis 不可用两形态；EventBus 构造零 I/O 断言
10. FIX-151 fileConfig 语义与源码锁；FIX-62 双落点零消息文本现状
11. FIX-78/79 chaos 全套（预检/预算/cap/statechart 穿透/安全映射）；FIX-80 计量归因三态+合成估算时序；FIX-81 双源复位
12. FIX-145 网关双测+handler 全量（-count=1）；OpenAPI 快照重冻结恰一行
13. 窗口测试面改动（wt444 隔离/wt446 钉旧值裁决/wt464 扫尾/wt466 终帧适配）均为修复性而非弱化

## 环境与留痕

- 测试命令：`cd backend && DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v .venv/bin/python -m pytest <path> -q`（venv 复用主仓 backend/.venv，Python 3.11.15）；gateway：`go build ./... && go test ./internal/handler/ -count=1`
- 窗口内正式测试基线复跑：FIX-155(9)+FIX-146/147(10)+FIX-148(7)+FIX-77(20)+Q-06(13)+metering(7)+dual-source(7)+FIX-62(1)+lifespan-150(2)+semantic_meta(2)+FIX-53 关联(4)+SSE 路由(4)+a03(112) 全绿
- 探针文件已删除未提交；`backend/.venv`、`backend/app/gen`、`backend/gateway/gen` 为本地符号链接/拷贝（gitignore 覆盖），未入库
