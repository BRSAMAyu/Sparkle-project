# WT343-KILLSWITCH-TAIL — kill_switch 服务级邻批 8 个存量败清尾 报告

- **base SHA**: `9dc5ef6e`（main，含 wt341 批次；其 §移交 的 8 个失败在本批清尾）
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt343-killswitch-tail`
- **触碰面**: `backend/tests/unit/` 21 文件（20 改 + 1 新 helper，+155/−377）。**零产品代码改动**；write_mode/cache_service 产品代码未动（wt341 已定性产品无罪）；galaxy/aurora runtime、goal 链、chat_mode、mobile、gateway 零触碰。

## 一、复现（逐字）

`DATABASE_URL="sqlite+aiosqlite:///:memory:"`（主仓 backend/.venv python，worktree 无 .env，SECRET_KEY 走环境变量）跑三文件：**8 failed, 2 passed**，失败集与 wt341 移交清单完全一致（worktree 即 main 基线克隆，未动一行先跑=存量实证）：

| 测试 | 失败点 | 实际 vs 期望 |
|---|---|---|
| foresight×4（master/attractor/deviation/jitai_off） | `_configure` 写 mode 后断言快照清空 | 写入被忽略→翻转不可观察 |
| idiographic #1 auto_downgrades_live_mode | `get_mode()=='shadow'` | `'live' != 'shadow'` |
| idiographic #3 shadow_does_not_expose_aggregator_summary | `summary is None` | `<AsyncMock>`（mode 回落 live→照常计算） |
| metacognition #1 language_contract_hit_disables_runtime_modes | `get_mode()=='off'` | `'live' != 'off'` |

共同日志：`kill_switch write_mode called without Redis for NN/xxx; write ignored`（kill_switch.py:142）。

## 二、7 个同根因 → 同款内存桩修复

与 wt341 §二 定性完全同链：kill_switch 写路径无 Redis 按设计告警并忽略（控制面状态禁进程内兜底，AUTH-DEEP A-2 同源），测试把 `cache_service.redis` 置 None/靠缺省 None 使翻转不可观察，读回落 settings 默认全 "live"。修法=注入内存桩（monkeypatch 逐测恢复）。

**桩提炼为共享 helper（卡面授权项）**：先例核查发现两层惯例并存——15 个测试文件各自就地复制 `_InMemoryKillSwitchRedis`（get/set 二方法版×8、五方法版×7），同时 `tests/unit/foresight_test_helpers.py` 证明 `tests.unit.*_test_helpers` 共享模块惯例成立（4 文件引用）。故新建 `tests/unit/kill_switch_test_helpers.py` 收敛全部 15 份就地副本 + 供 3 个目标文件使用，方法面为各副本的严格超集：get / set(key, value, ex=) / setex / delete / incr / incrby / expire / scan_iter（后两者为 cache_service.set 固定 ex= 关键字调用 cache.py:195 与 delete_pattern 的 scan_iter 契约所需，见 §四-2）。净 **−222 行**重复。

## 三、"另族" 定性：**不成立另族，实为同根因的掩蔽症状**

wt341 移交假设：idiographic `no such table: idiographic_associations` 是全局 engine `:memory:` 空 schema 的独立装配问题。本批证据链推翻其独立性问题定性、但证实其观察的机制：

1. 失败日志：`write ignored (mode=shadow)`——测试 L36 的 shadow 从未落键；
2. 读路径回落 `AURORA_IDIOGRAPHIC_MODE` settings 默认 `"live"`（settings.py:403）；
3. 代码：recompute_user 的**全部 DB 访问**（`_upsert_*`、`build_aggregator_summary`→`_session_scope`→全局 engine）严格在 `if mode == "live":` 分支内（idiographic_association_service.py:218-243）；shadow 分支只走已 monkeypatch 的纯计算路径，**不触任何 DB**；
4. 因果链：mode 写不进→误入 live 分支→真查库→全局 engine 每连接空库→no such table。**SQL 报错是症状，mode 不可观察才是病根**；
5. **反证实验**：仅注入桩（零装配/零产品改动）→ idiographic 3/3 绿。若空 schema 是独立根因，仅桩不可能绿。
6. 处置：修桩即愈，无需动装配、更无需动产品。wt341 假设的"全局 engine 与 fixture 不同源"机制真实存在，但该测试在正确 shadow 语义下根本不应触 DB——留此定性供后续参考。

## 四、清尾过程中新暴露的存量问题（均基线克隆 /tmp/wt343-baseline @ 9dc5ef6e 实证存量，非本批引入）

1. **test_srl_kill_switch.py:14 settings 单例裸赋值泄漏**：`settings.AURORA_SRL_MODE = "shadow"` 未走 monkeypatch→永不恢复→污染同进程后续所有 stage29 模式解析（实测致 test_srl_phase_tracker 4 测合批红、单跑绿）。修=改 `monkeypatch.setattr(settings, ..., raising=False)`，语义零变化+自动恢复。同族装配缺陷，一行修复，文件本就在本批触碰面内。
2. **test_foresight_snapshot_schema.py jitai_not_live 同根因败**：`write ignored (mode=shadow)`（27/jitai）——与 8 个完全同链的同族存量红（不在 wt341 26 文件批内故其未登记）。修=同款桩注入 `_configure_modes`（helper 加 monkeypatch 参数，5 个调用点全量显式化，其中 4 个原本"碰巧绿"的测试同步获得精确语义）。
3. **test_metacognition_service.py dashboard 裸模板期望过时**：测试断言 body 为裸占位符 `"你过去 {sample_size} 次..."`，产品实际输出插值成文 `"你过去 24 次对完成时间估得偏乐观 2.3 小时。"`。定性=**测试期望过时，产品正确且有意**：build_dashboard_payload 对注册模板调 `render_template(template_id, sample_size=..., display_value=...)`（metacognition_service.py:648-652，专用 `_format_display_value` 格式化），语言契约 `_enforce_language_contract` 跑在渲染后文本上（:653-655，裸占位符过契约无意义），且仪表盘向用户裸露 `{sample_size}` 显然是缺陷；"只用注册模板"的本意由 template_id 断言（:98）继续守住。修=期望改为插值成文，断言保护力不减反增（同 wt338 过时期望处置判例）。

## 五、结果

- 8/8 有归宿：**全绿**（foresight×4、idiographic×3、metacognition×1）。
- 涉及 21 文件逐一验证全绿；**40 文件 kill_switch/memory 邻批：179 passed, 0 failed**（wt341 同口径批次 137P/8F → 本批全绿清零）。
- 收敛成果：桩单一事实源 `kill_switch_test_helpers.py`（16 处引用），后续新测试直接复用。

## 六、收工门

| 门 | 结果 |
|---|---|
| `bash scripts/run_all_rule_guards.sh` | **EXIT 0**（83 条；gen 三件套已 cp -RL：backend/app/gen、gateway/gen、mobile/lib/gen） |
| 冷 mypy（`rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary \| grep -c 'error:'`） | **1278 = 棘轮基线，零漂移**（本批零产品代码改动） |
| ruff（被碰 21 文件） | **0**（顺带清 I001×1 + SIM300×1，均为本批引入即清） |
| 回归 | 8 目标绿 + 40 文件邻批 179 passed |

## 七、/tmp 自产清理

删除：/tmp/wt343-baseline（基线克隆）、/tmp/wt343_guards.log、/tmp/wt343_mypy_cold.txt。
