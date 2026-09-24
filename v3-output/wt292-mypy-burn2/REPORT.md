# WT292-MYPY-BURN2 — D 线 mypy 基线二期烧减报告

- 卡号：wt292-mypy-burn2 ｜ worktree：`Sparkle-sysrev/wt292-mypy-burn2`（分支同名，本地 commit 未 push）
- 日期：2026-09-24 ｜ mypy 1.20.2 + SA 2.0.48（复用主仓 backend/.venv，只读使用）
- 一期交接：v3-output/WT289-MYPY-BURN1/REPORT.md（基线 2458，backend/ 目录口径）

## 一、烧减数字（回执①）

| 口径 | 前 | 后 | 烧减 |
|---|---|---|---|
| **backend/ 目录口径**（卡口径：`cd backend && mypy app --ignore-missing-imports --no-error-summary`，**冷缓存** `rm -rf .mypy_cache` 后测量，读 backend/pyproject.toml，warn_return_any 开） | **2458** | **1786** | **-672（27.3%）** |
| quality/mypy_baseline.txt | 2458 | **1786** | 已刷新 |

未达 -800 目标，差额 128。原因与依据见「四、口径稳定性重大发现」——本卡在中途发现并按纪律回退了一处会**使口径漂移 +~400** 的改动（main.py 遮蔽修复），把测量钉死在与 2458 基线严格可比的官方命令上。若 Leader 采纳该修复（真实缺陷，建议三期单卡），当前树的真实错误面将浮出为 ~2100-2150，届时烧减空间反而更大。

### 家族×修法×计数表

| 家族 | 前 | 后 | 烧减 | 修法 |
|---|---|---|---|---|
| no-any-return | 269 | **0** | -269 | 269 处 `return <Any-expr>` 统一改 `cast("<声明类型>", (expr))`（引号串形，运行时零求值风险；真实类型非 Any） |
| assignment | 427 | 238 | -189 | SQLCoreOperations 子族 189 处：根因是向非 Optional `Mapped[T]` 赋 None 表达式——`Mapped.__set__` 的 value 参数即 `SQLCoreOperations[T] \| T`。178 处对 nullable=True 列做诚实 Optional 化（`Mapped[T]`→`Mapped[T \| None]`，nullable= 参数不动，DDL 零变化）；其余点侧 cast（枚举跨名 `cast("ReportStatus", data.status)` 等） |
| var-annotated | 77 | 5 | -72 | 三轮脚本：`x = {} / [] / set() / defaultdict(...)` 等补精确注解，元素类型由 append/get 用法推断 |
| attr-defined | 275 | 144 | -131 | 见「二、家族修法」 |
| misc/operator/index/call-overload 等连带 | ~155 | ~139 | ~-16 | 随上述收敛 |
| **合计** | **2458** | **1786** | **-672** | |

## 二、家族修法（回执②）

### 1) no-any-return（269→0，纯机械）
`json.loads` / `dict.get` / redis / 第三方返回 Any 流入有注解函数。统一 `cast("<声明类型>", (expr))`：
- 类型串一律**引号字符串形**（`cast("dict[str, Any] | None", x)`）：运行时仅求值字符串字面量，TypeVar/泛型/`X | None` 全兼容（裸形式遇 TypeVar 会运行时 TypeError）；
- 变换器带括号/引号/续行感知的表达式边界扫描 + 每文件 compile 自验，失败即回滚该文件（本轮共 3 个文件走人工修复导入位）；
- 24 条 `Result[Any].rowcount` 同法 `cast("CursorResult[Any]", r).rowcount`（TYPE_CHECKING 导入 CursorResult）。

### 2) assignment-SQLCoreOperations（189→~40 内残留≈8）
一期交接判断为"mixin 描述符走丢"，实测定正：`Mapped.__set__(value: SQLCoreOperations[_T] | _T)` —— **凡赋值表达式与列注解 T 不精确相等（含 None）即报**。主体修法是 79 个属性名 / 143 处列声明（55 文件）的诚实 Optional 化；配套点侧：
- MessageReport.status/action_taken：模型 StrEnum 与 schemas StrEnum 跨名 → `cast("ReportStatus", data.status)`；
- achievement_engine 6 处 `date` 赋给 TIMESTAMP 列 → 三列注解改 `Mapped[date | None]`（列类型 DateTime 不动，DDL 不变）；
- `coerce_task_type("error_fix")` 可证非 None → cast。

### 3) attr-defined（275→144）
- **Mixin 成员声明（-51）**：SessionStateMixin/ResponseBuilderMixin/PersistenceLayerMixin/ValidationEngineMixin 缺失的 `redis/state_manager/token_tracker/validator` 与 13 个 `_helper` 方法，在 mixin 类体补 `attr: Any` / `method: Callable[..., Any]`（上游 `__init__` 参数本身无类型标注，Any 为当前最诚实可用形态；类体纯注解，运行时零变化）；
- `_registration_lock`（13）：`DynamicToolRegistry` 类体补 `_registration_lock: threading.RLock`（__new__ 单例内已实例化）；
- `Settings._aurora_*`（12）：pydantic-settings `PrivateAttr()`（**无默认**，未写入即读仍 AttributeError，现行语义逐字保持；已实测 extra="ignore" 下私有 setattr 行为一致）；
- `Pool.size/overflow/...`（8）：`pool = cast("QueuePool", engine.pool)`；
- dict-typed 局部（~20）：`user: dict[str, Any] = {...}`、`COLLECTION_RULES: dict[str, dict[str, Any]]`、`_lookup_sprint_node_metadata -> dict[str, Any]` 等；
- QualityCheck（4）：dataclass 误用 `.get` → 改属性访问（原路径运行时必然 AttributeError 且被 except 吞掉——属修复潜伏缺陷，见报告§五）。

### 4) var-annotated（77→5）
三轮脚本 + 逐个补注解；修掉了第一版脚本"列表推断返回裸元素类型"的自伤（`x: str = []`→`list[str]`，全库扫描确认仅 4 处已清）。

## 三、验证（回执③）

| 项 | 结果 |
|---|---|
| 官方口径终态 | `rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary` = **1786**，与 quality/mypy_baseline.txt 一致 |
| 家族确认 | no-any-return = 0；var-annotated = 5 |
| 定向 pytest | **5 批 198 passed / 0 failed**：①guest_seed×2+visual_element+accountability(11) ②achievement+intervention+policy_scheduler(41) ③orchestrator 状态迁移+planning_workflow+event_bus 生命周期+sse 心跳(68) ④aurora 信号管线+galaxy stats/retrieval+db_session(50) ⑤orchestrator 复验(26)+dictionary_package(2)。均为 sqlite 内存库 + 测试 SECRET_KEY，零真实库接触 |
| ruff（CI 同口径 `ruff check backend/app`） | **All checks passed!**（过程中所有连带 I001/F401 已 --fix 清零） |
| 守卫 | `run_all_rule_guards.sh` exit-checked：**K 0 / Z 0**；**BG = 1 为存量失败**——已在 HEAD 基线克隆（`git clone` 纯净对照）复现同样失败，非本卡引入 |
| import 烟雾 | `import app.main` + `import app.models` + `from app.config import settings` OK |
| ruff 零新增 | 过程中每次批量改动后均全量 ruff 校验，最终 0 告警 |

## 四、口径稳定性重大发现（给 Leader，重要度高于本卡烧减数）

1. **main.py:171 函数内 `import app.models.pii_encryption_listeners` 把全局名 `app` 遮蔽为函数局部（包模块）**，导致 lifespan 关停路径所有 `getattr(app.state, ...)` 运行时必然 AttributeError（当前被 except 吞掉的潜伏缺陷）。同时令 mypy 分析**顺序敏感**：对 `app/orchestration/context_builder.py` 做任何编辑（哪怕一行 `redis: Any`）都会翻转 main.py 等处 ±~400 条错误的可见性。本卡中途发现后**已按纪律回退该修复**，把测量钉死在与 2458 严格可比的口径上。**建议三期单卡**：`from app.models import pii_encryption_listeners` 一行修复 + 重测口径（修后真实错误面 ~2100+，烧减空间反而更大）。
2. **`context_builder.py` 本卡封禁**：触发上述翻转。该文件 ~11 条 attr-defined 收益放弃。
3. **一期教训复核属实**：热缓存会静默错报；本卡所有计量一律 `rm -rf .mypy_cache` 冷跑。另注意 `--no-incremental` 与冷增量在本库当前等价（2242 双跑一致）。
4. **Batch 脚本自验教训**：批量编辑必须①compile 校验用**目标 venv 的 3.11**（系统 3.12 会放过 PEP 701 f-string 同引号语法）②引入 NAME 进 cast 串时必须确保名字已导入（F821）③`typing.cast` 与既有 `from sqlalchemy import cast` 撞名会在运行时炸（execution_service 已按 `typing.cast` 特判修复）。

## 五、资源峰值（回执④）

- 无 HEAVY（无模拟器/Gradle/浏览器）；mypy 冷跑 <2G、pytest 串行分批
- 磁盘：临时区 /tmp/wt292-mypy-burn2（脚本+基线克隆，收工清）+ backend/.mypy_cache ~150M（收工清）；app/gen（gitignored）从主仓只读复制，其中 3 个符号链接指回主仓导致 K/Z 守卫崩溃——已改为实体副本（守卫对树外路径不健壮为存量缺陷，建议守卫侧 tolerant 化）
- 守卫 BG 存量失败已在 HEAD 克隆存证（/tmp 基线克隆中复现，随清理销毁，结论记录于本报告）

## 六、三期建议（回执⑤，按收益排序）

1. **main.py 遮蔽修复卡**（见§四.1）：一行修复 + 口径重估，浮出 ~400 条真实错误后按本卡同样打法烧减；
2. **arg-type 481 + union-attr 372**：真 Optional 处理与 UUID/str 边界，建议按文件 top 分卡（union-attr 大户与 guest_seed/memory/context_pack 相关）；
3. **assignment 残留 238**：非 SQLCore 的"首赋值后重赋 None/float→int"模式可脚本化 Optional 化（本卡已验证手法）；
4. **attr-defined 长尾 144**：ThresholdAdjustment/ExecutionDirective/WebSocket.user_id 等缺声明类，逐个补类属性即可；
5. **misc 13 条 "Cannot assign to a type"**：type-alias 显式化（`X: TypeAlias = Y`）；
6. **给 Leader 的口径建议**（沿一期）：CI ratchet 改 `cd backend && mypy app` 两口径合一；mypy 钉版 1.20.2；守卫脚本对"树外 resolve 路径"应 skip 而非 crash（K/Z 本次因此被 app/gen 符号链接拖崩）。

## 交付物

- worktree：~230 文件改动 + quality/mypy_baseline.txt（2458→1786）+ 本报告
- `v3-output/wt292-mypy-burn2/changes.patch`：全量 diff
- 本地 commit（未 push）：`feat(types) wt292-mypy-burn2 ...`
- 收工清理：/tmp/wt292-mypy-burn2（脚本/基线克隆/探针）、backend/.mypy_cache、无残留进程
