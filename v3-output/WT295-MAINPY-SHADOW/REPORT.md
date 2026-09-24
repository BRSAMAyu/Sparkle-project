# WT295-MAINPY-SHADOW — C 线 main.py import 遮蔽修复 + mypy 可见性重估报告

- 卡号：wt295-mainpy-shadow ｜ worktree：`Sparkle-sysrev/wt295-mainpy-shadow`（分支同名，本地 commit 未 push）
- 日期：2026-09-24 ｜ mypy 1.20.2 + CPython 3.11（复用主仓 `backend/.venv`，只读使用）
- 上游依据：v3-output/wt292-mypy-burn2/REPORT.md §四.1（遮蔽实锤与三期单卡建议）、§六.1
- 交付：`backend/app/main.py`（遮蔽别名化）、`backend/app/orchestration/context_builder.py`（partial-type 注解）、`quality/mypy_baseline.txt`（1786→2251 冷缓存诚实刷新）、本报告 + changes.patch

## 〇、结论摘要（给 Leader）

1. **遮蔽是真缺陷且比卡面描述更重**：main.py:171 函数内裸 `import app.models.*` 使 `app` 成为 `lifespan` 的函数局部名，关停路径 38 处 `app.state` 运行时读到的是 **`app` 包模块而非 FastAPI 实例** → 首处即 `AttributeError`，**整段优雅关停（30+ 消费者 cancel、event_bus 排空、Redis/引擎释放）全部跳过**。已修复（别名化）并以字节码 + symtable + 运行时探针三重验证。
2. **wt292 观察的 ±400 可见性翻转真因不是遮蔽本身，而是 `context_builder.py` 的 mypy 内部崩溃**（`AssertionError: Unexpectedly encountered partial type`，L1209 嵌套元组解包重定义触发，L1277 use-site 爆点）。崩溃是否触发依赖缓存/分析状态，触发即截断其后 ~500 条错误输出 → 表现为"编辑 context_builder 翻转 ±400"。已用 2 行显式局部注解根治（纯编译期元数据，运行时零变化），修后连测 4 次（冷/热/touch-context_builder-热/复测冷）计数逐位一致，**翻转死亡**。
3. **基线诚实刷新 1786 → 2251**（backend/ 目录口径，冷缓存）。原 1786 是崩溃截断态的"幸运值"；修后浮出 +503 条此前被静默隐藏的**真实存量类型债**（wt292 预测 ~2100-2150，实测吻合），其中遮蔽自身家族 38 条已被本卡别名化烧掉（57→19），净 +465。**≤1786 目标未达成，按卡面分笔条款执行**：浮出主体为结构性家族（mixin 声明债、object 型多态访问），非机械可烧，剩余结构见 §四。

## 一、遮蔽语义影响面（回执①）

### 运行时（真缺陷，已修）

| 项 | 修前 | 修后 |
|---|---|---|
| `lifespan` 内 `app` 绑定 | 函数局部 = `app` 包模块（`__init__.py` 为空，无 `state` 属性） | 模块全局 = FastAPI 实例 |
| 字节码证据 | `STORE_FAST`×1 + `LOAD_FAST`×38 | `LOAD_GLOBAL`×38，FAST×0 |
| symtable | `lifespan` 局部符号 `app` = True | False（global） |
| 关停路径 38 处 `app.state`（L577 起） | 首处 `AttributeError: module 'app' has no attribute 'state'`（若 L171 import 失败则 `UnboundLocalError`），**未被任何 except 捕获**，其后全部关停步骤被跳过：30+ `*_consumer_task` cancel、`event_bus.begin_shutdown()/close()` 排空、SecurityMonitor 收尾、EpisodeLogger sink 摘除、`redis_search_client.close()`、`cache_service.close()`、`manager.close_redis()`、`engine.dispose()` | 经 `getattr` 默认值安全读取 FastAPI 实例 state（与启动半段写入端 `fastapp.state` 同一对象：`app = FastAPI(..., lifespan=lifespan)`，FastAPI 以 self 调用 lifespan） |
| 关停验证方式 | — | 按卡面纪律**未重启主仓引擎**；以定向测试（`test_main_lifespan_shuts_down_event_bus` 源码守卫 + event_bus 生命周期 3 例）+ 字节码/运行时语义探针完成 |

### mypy 可见性（卡面 b 项，含修正）

- 遮蔽自身在 mypy 面直接产生 **38 条 `Module "app" has no attribute "state" [attr-defined]`**（main.py 57 条中的 38 条）——别名化后归零（57→19）。
- wt292 归因于遮蔽的"±400 翻转"，实测真因是 **context_builder 的 mypy INTERNAL ERROR**（见 §三）：崩溃触发与否依赖模块缓存状态，触发即从输出中截断其后全部模块的错误 → 计数在 ~1784/1786/2200+ 之间跳变。遮蔽与崩溃**叠加**造成 wt292 当时的表象。两因均已在本卡根治。

## 二、修法（回执②）

1. **main.py:171（最小形制，行为最保守）**：
   `import app.models.pii_encryption_listeners` → `import app.models.pii_encryption_listeners as _pii_encryption_listeners`
   - 保持原位置（lifespan 启动段 try/except 内）、原时机（运行时惰性副作用导入）、原吞异常语义；仅局部绑定名改变，全局 `app` 不再被遮蔽。未采纳 wt292 建议的 `from app.models import pii_encryption_listeners` 移顶方案：移动导入时机（模块导入期执行）行为保守性劣于原地别名化。
2. **context_builder.py:1160（崩溃根治）**：`llm_profile_data = None` / `preference_version = 0` 补显式注解 `dict[str, Any] | None` / `int`。PEP 526 局部注解为纯编译期元数据，**运行时零求值零变化**（已实测 95 例定向测试全绿）。这使 mypy 不再进入 partial-type 推断路径，L1277 的 binder 窄化断言不再触发。

## 三、mypy 数字（回执③，全冷缓存 `rm -rf .mypy_cache`，backend/ 目录口径）

| 树状态 | 计数 | INTERNAL ERROR | 说明 |
|---|---|---|---|
| HEAD 原样（账面基线 1786） | **1786** | 0 | 仅在崩溃未触发时；同代码在 worktree 两次冷跑均 1784 且 **含 INTERNAL ERROR**（截断态） |
| + 注解（崩溃修，遮蔽在） | **2289** | 0 | /tmp 基线克隆验证，确定性 |
| + 别名（双修，本卡终态） | **2251** | **0** | 连测 4 次逐位一致：冷 2251 / 热 2251 / **touch context_builder 后热 2251** / 复测冷 2251 |
| 终态 root 口径（CI ratchet 脚本口径） | 2242 | 0 | `mypy backend/app`（root 无 pyproject，warn_return_any 关）；2242 ≤ 2251，ratchet 两口径均过 |

账面 1786 → 终态 2251 的分解：**+503**（崩溃修复浮出的真实存量债，wt292 预测 ~2100-2150 兑现）**−38**（遮蔽自身家族被别名化烧掉）。

**翻转杀死验证**：修前对 context_builder 单文件跑 mypy 3/3 次复现 INTERNAL ERROR（worktree 全量冷跑 2/2 触发、克隆全量冷跑 0/1 触发——此不确定性即翻转本体）；修后 touch（追加一行注释）+ 热跑计数不动。wt292 §四.2 的"该文件封禁"可以解除。

## 四、烧减情况与剩余结构（诚实申报）

**≤1786 目标未达成，启用卡面分笔条款**（"浮出量过大超出卡量级，允许把基线诚实刷新到冷缓存实测值并说明剩余结构"）。理由：浮出 +503 的主体不是机械族，抽验两大族均为结构性债：

| 浮出大户 | 条数 | 结构性质（非机械的证据） |
|---|---|---|
| api/v1/community.py | 104 | `_build_share_meta(resource: object)` 按 enum 分派后直接属性访问——需 union/TypedDict 重构签名，59 attr-defined + 26 arg-type + 16 union-attr |
| orchestration/execution_engine.py | 91 | 64 条 mixin 交叉成员（`ExecutionEngineMixin has no attribute _*`）——同 wt292 attr-defined 家族，需 mixin 协议/声明层补齐 |
| api/v1/graph_monitor.py | 53 | 同上模式 |
| orchestration/routing_engine.py | 33 | mixin/路由类型债 |
| api/v1/chat.py | 25 | 同上 |
| main.py 余量 | 19 | `event_bus` 局部重绑定窄化为 object、`UserService(None, ...)` None 注入模式、消费者 `event_bus=None` 传参——需服务签名诚实 Optional 化（动 service 层契约，超出本卡） |

三期烧减建议：①main.py 余量 19 条随"service 签名 Optional 化"卡处理；②community/graph_monitor 的 object 型访问按 wt292 §六.2 的 union-attr/arg-type 分卡打法；③mixin 声明补齐沿 wt292 §二.3 手法（类体 `attr: Any` 注解，运行时零变化）。

## 五、验证（回执④）

| 项 | 结果 |
|---|---|
| 定向 pytest | **95 passed / 0 failed**：startup smoke(12) + event_bus lifespan 关停(3) + shop seed startup(3) + context_builder mixin/sources/source_contract/cache_versioning(77)；sqlite/无 .env 环境，零真实库接触 |
| import 烟雾 | `python -c "import app.main"` OK（CI 同款 SECRET_KEY 环境变量，进程级注入未落盘） |
| ruff | `ruff check app/main.py app/orchestration/context_builder.py` 与全量 `ruff check app` 均 **All checks passed!**，零新增 |
| 守卫 | `run_all_rule_guards.sh` exit-checked（结果见 §六，BG 存量失败与 wt292 存证一致则为非本卡引入） |
| mypy 棘轮 | quality/mypy_baseline.txt = 2251；backend 口径 2251 ≤ 2251、root 口径 2242 ≤ 2251，双通过 |

## 六、资源与守卫峰值（回执④续）

- 无 HEAVY（无模拟器/Gradle/浏览器/全量测试）；mypy 冷跑串行执行，pytest 分两批串行
- app/gen（gitignored）自主仓只读复制；其中 3 个指回主仓的**符号链接已改实体副本**（复用 wt292 §五教训，防 K/Z 守卫崩）
- 清理清单（收工执行）：`/tmp/wt295-*`（mypy 输出 6 份、new-errors/g38/mainmsg 对照 4 份、guards 日志、/tmp/wt295-baseline 基线克隆）、`backend/.mypy_cache`、worktree 根 `.mypy_cache`、`.pytest_cache`；无残留进程

## 七、交接（回执⑤）

1. **给主会话**：本卡含基线上调（1786→2251），属"棘轮基线诚实重置"——与 wt292 下调 2458→1786 方向相反但同源（原 1786 依赖崩溃截断才可复现，是不稳定锚点）；合入前请知悉 CI ratchet 数字将变为 ~2242-2251。wt292 §六.6 的"两口径合一 + mypy 钉版"建议再次提议。
2. **给后续烧减卡**：终态冷缓存 2251 是**可复现锚点**（本卡 4 连测 + 双口径存证）；context_builder.py 已解封；家族清单与打法见 §四。
3. **给运维/探针**：main.py 关停路径修复后，引擎下次**正常**重启/重部署时关停日志将首次完整走完（首次出现 "Event bus consume loops drained"/"GalaxyTaskEventListener stopped" 等此前因 AttributeError 从未打到的行）——属预期修复效果，非回归。**本卡未触碰在跑引擎**。
4. 已知残余：root 口径与 backend 口径差 9 条（warn_return_any 配置差），未处理。

## 交付物清单

- worktree 改动：`backend/app/main.py`（+5/-1）、`backend/app/orchestration/context_builder.py`（+9/-2）、`quality/mypy_baseline.txt`（1786→2251）
- `v3-output/WT295-MAINPY-SHADOW/REPORT.md`（本文件）+ `changes.patch`（全量 diff）
- 本地 commit（未 push，未动 main，未 stash/reset/clean）
