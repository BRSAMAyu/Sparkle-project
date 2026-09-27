# WT781 — FIX-506 实施记录（guest 种子演示群 demo 标记）

- 卡：**V3-FIX-506**（P3，wt775 登记）——S-03 验收「seed/demo group 明确标演示」的后端半边未兑现
- 分支：`agent/node-b/wt781/c506`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt781-506`，base main@9a4ea3d4）
- 证据源：v3-output/WT775-DOC-UPSG/S-line.md §S.2-S-03/§S.5（台账行 V3-FIX-506 所指）

## 1. 修法

**方案裁决：名称尾部后缀标记，不加列不加迁移。**

修前三案取舍：
1. **加 `is_demo` 列+读面透传**——`models/community.py` Group 无任何标记列，引入即触 Alembic 迁移+`make sync-db`+网关 schema 快照重导出+全部群读面序列化面改动。P3 小修不成比例，弃。
2. **复用 `Plan.source="example"` 同构机制**——Group 没有对应既有列，同案 1，弃（判例对照：J-01/O1 选 source 列是因为该列已存在，本群无此前提）。
3. **名称尾部「（演示）」后缀（采纳）**——与 mobile 侧既有双端约定同词同形：mock_community_repository.dart:120-122 demo-mode mock 群一律尾部带 `l10n demoGroupSuffix`（zh「（演示）」/en " (demo)"），S-03 验收语义原文即「列表/详情/聊天各表面都能看到」。后端落同一词，真实访客看到的种子群与 demo-mode mock 群标记口径一致；name 进所有群读面（我的群组 GET /groups、群详情、群聊天、目录），任何读面（人读即见、程序读经导出谓词）可区分。

**实现（backend/app/services/guest_seed_service.py 单文件）：**

- 模块级契约三件套（种子写入面与判定面单一来源）：
  - `GUEST_SEED_DEMO_GROUP_SUFFIX = "（演示）"`；
  - `demo_group_name(base_name)`：基础名→落库名；
  - `is_demo_group_name(name)`：任一读面程序化判定谓词。
- `_ensure_group`（6 个种子群唯一建群出口，全仓无其他调用方，grep 亲证）成为打标单点：调用方仍传基础名（6 个调用点零改动），函数内部一律按 `demo_group_name(name)` 查重/落库；**存量收敛**：修前已播种库里的无标记同名群在种子重播时就地改名（连同行内既有成员/消息/任务归属），随后走既有全字段覆写语义——不另建带标记副本留下无标记双份；不存在才新建带标记群。幂等性保持（FIX-13 起的 ensure 语义不变）。

**零 schema 变更**：无迁移、无 `make sync-db` 需求、网关快照不动。运行栈未触碰。

## 2. 红→绿

红测：`backend/tests/services/test_guest_seed_demo_group_marker.py`（3 测，新增）。

- **契约红**（基线版）：`is_demo_group_name`/`demo_group_name`/`GUEST_SEED_DEMO_GROUP_SUFFIX` 零命中 → collection ImportError（ModuleNotFoundError 型红，78ff5538 先例形制）。
- **行为红**（仅加契约函数、`_ensure_group` 保持修前无标记落库时）：
  - 红测① `test_guest_seed_groups_are_marked_demo_in_my_groups_read_surface` FAILED——`V3-FIX-506：我的群组读面存在无演示标记的种子群（base 红：demo 与真实群不可区分）：['算法冲刺小队', '期末自习室', '英语口语晨读营', '产品设计共学社']`（GET /groups 同构读面 `GroupService.get_my_groups` 实取，2 failed 1 passed 实录）；
  - 红测③ `test_legacy_unmarked_seed_group_heals_to_marked_name_on_reseed` FAILED——存量无标记群未被收敛（`assert False is True`）。
- **绿**：修法就位后 3/3 passed。

红测内容钉三面：①读面（get_my_groups 返回的每一名都带标记+库面 6 个种子群全带标记、逐一按 `demo_group_name(基础名)` 对名）；②契约（后缀与 mobile mock demoGroupSuffix 同词「（演示）」钉死；真实自建名含「演示」字样但无后缀不得误判）；③存量收敛（重播不改名双份）。

## 3. 测试与验证

- **触达面回归 54 passed 零回退**（路径先 find）：guest_seed 既有测试面全量+群发现面——`tests/services/test_guest_seed_{demo_group_marker,example_marker,savepoint,service}.py`、`test_guest_upgrade_seed_statistics_cleanup.py`、`tests/unit/test_guest_access_ttl_refresh.py`、`test_guest_seed_{calendar_wall_clock,local_day,streak_wiring}.py`、`test_j02_seed_memory_namespace.py`、`test_v3_fix286_guest_seed_failure_visibility.py`、`test_v3_fix55_guest_seed_observability.py`、`test_gseed_guest_seed_retype_migration_sqlite.py`、`tests/api/test_group_discovery_cohort_filter.py`。既有断言无一种子群名硬编码（`joined_groups >= 4` 计数型，亲证）。
- **mypy**：`mypy app --ignore-missing-imports` 冷缓存 **76 errors in 67 files = 基线逐数吻合零新增**；`guest_seed_service.py` 在输出零命中（修前修后同净）。（口径沿 WT768-MYPY10/notes.md：主仓 .venv+独立 MYPY_CACHE_DIR，本 worktree 沿用。）
- **ruff**：触及两文件 All checks passed。
- **black**：新测试文件已 black 收口；`guest_seed_service.py` 修前修后 black diff hunk 数 28=28（该文件既有漂移，本修零新增 hunk、未顺手重格式化无关行）。
- **台账 verify**：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` 修前基线通过（352 行 V3-FIX 行）；506 行状态格改写后复跑通过，**零 FAIL**。

## 4. 台账

- **V3-FIX-506 → FIXED@<fix commit>**（行内注记修法/红绿/验证摘要；台账编辑随收尾 commit 落分支，指针指向修复 commit 本体）。
- **新发现预占：无。** 本次顺审两项复核过、判不构成新发现（不占号，留此备查）：
  1. `backend/scripts/seed_demo_user.py:538-543`、`seed_demo_user_enhanced.py:889` 自建的「算法冲刺小队」无演示标记——两者是 scripts/devtools 一次性开发播种脚本、非 guest 产品路径（FIX-506 面仅 guest_seed_service），不另立行；若 V4 动演示面可顺带。
  2. 种子 feed 帖文案「欢迎来算法冲刺小队一起测」按内容精确匹配幂等查重（`Post.content == content`），本修未改动帖文案——群改名后该句为对旧名的软引用，纯演示文案级瑕疵，不涉判定面。
- 号位核验：本 worktree（base 9a4ea3d4）台账在册最高 511；506 已由 wt775 占用（本次销账），507-511 已占用；协调方口径 520/521 已用——**后续新发现自 522 起预占**（全仓 grep `V3-FIX-522` 零命中，空闲可占）。

## 5. 变更清单

- `backend/app/services/guest_seed_service.py`：契约三件套+`_ensure_group` 打标与存量收敛（+~40 行，含 FIX-506 语义注释块）。
- `backend/tests/services/test_guest_seed_demo_group_marker.py`：新增 3 测。
- `v3-output/WT781-506/notes.md`：本文件。
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：506 行 OPEN→FIXED@（收尾 commit）。
