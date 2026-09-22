# SAFETY-OPS 收工报告 — malicious 层 `kill -9` 类运维教学句误报修复

- 卡型: micro（强制遮蔽法）
- Worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt150`（基线 `57cafaa6`，含 SAFETY-LEX 修复）
- 交付物: 本报告 + `changes.patch`（零上下文 U0 格式，新文件头 `--- /dev/null`；应用: `git apply --unidiff-zero changes.patch`；已在 57cafaa6 干净克隆实测可干净应用且测试全绿）
- 未 commit / 未 push（按卡纪律）

---

## ① 模式定位（掩码）+ 红证

**定位**: `backend/app/core/llm_output_validator.py` L81，`MALICIOUS_PATTERNS`（L73-L82）末条目 entry[7] 的模式串。

- 掩码形态: `####\#+-9\#+`（12 字节 ASCII，无交替组/无括号类）
- 还原（本卡目标类别=运维命令类，低敏感，按卡允许明文）: `kill\s+-9\s+`
- desc 标签（合规元数据）: 「强制杀进程」
- 行为: 配 `re.IGNORECASE`，任何含 `kill -9` + 空白 的文本在 Layer 3 一律 `action="block"`、`is_valid=False`。
- 波及面核实: 该模式串全仓库仅此一处引用（`grep kill\s` 于 `backend/app`，排除 `gen/`）。

**红证**（修前 `test_llm_output_validator_ops_fp.py` 实跑: **12 failed / 11 passed**）:
8 句运维/OS 教学语料（含 `kill -9 兜底` / `kill -9 是 SIGKILL…` / `kill -9 与 kill -15` / `man kill` / Docker 卡死兜底 / 英文 last resort 等）全部在 malicious 层误拦；全管线断言同红。修前误拦率 8/8（凡含 `kill -9 ` 者必拦），CS 学生学操作系统课的北极星场景高频踩中。

## ② 修法与防漏放论证

**修法**: 就地收紧 entry[7] 模式（脚本化单行替换，词库段零 Read 入上下文，AST 复验通过）:

```
修前: kill\s+-9\s+                  (12B, 任何 kill -9 空白即拦)
修后: \bkill\s+-9\s+-?[01](?![0-9]) (29B, 仅破坏性目标: pid 0 / pid 1 / -1 全进程)
```

新增 `\b` 顺带修掉 `xkill` 类前缀粘黏误配；`(?![0-9])` 负向先行防 `[01]` 退化成"任意 PID 尾字匹配"（`kill -9 1234/10/100/1231/99991` 均不放错——红测含此防退化专项）。

**防漏放论证（双向钉死）**:
1. **破坏性目标仍拦**: `kill -9 1`（杀 init）/ `kill -9 -1`（全进程）/ `kill -9 0`（进程组 0）及载体句变体，Layer 3 仍 `block`（新测试 `TestDestructiveTargetsStillBlocked`）。
2. **共现恶意意图仍拦**: 按参考卡（`test_llm_output_validator_lexicon_fp.py`）的程序化构造法，从其余 7 条 malicious 条目自取字面核心嵌入「先 kill -9 …再执行 {X} 破坏系统」载体，只保留经真实编译模式自校验可独立命中的载波（≥2 条），断言全管线 `action="block"`——kill 叙述本身不再是拦截信号，但与其他恶意词表信号共现的组合句必拦（`TestCoOccurrenceStillBlocked`，零明文入库）。
3. **条目未删除**: `TestKillEntryShapeGuard` 钉死 kill 条目恰一条、仍锚定 `-9`、职责为破坏性目标；entry 总数形状校验不变（8）。
4. 删除/清库/格式化/重启/关机类真实破坏命令链由其余条目独立覆盖（词面已由仓内既有测试明文钉死，本报告不重复其字面），既有恶意命令测试用例原样全绿（162/162）。

**连带契约演进**: `test_llm_output_validator.py::test_kill_command` 原钉死旧行为（`kill -9 1234` 必拦）——与本卡红线直接冲突，按新契约改写: 普通 PID 教学放行 + 三个破坏性目标必拦。已在 patch 中。

## ③ 冲突面

在途卡全在 galaxy/events/tests 域（据卡面），与本卡改动面（`app/core/llm_output_validator.py` L81 单行 + 2 个测试文件）零交集。worktree 变更集恒为 3 个文件（`git status` 每步核对）: 1 处源码单行 + 1 处既有测试契约演进 + 1 个新测试文件。主仓只读未动。

## ④ 诚实申报

1. **残余误报边界（有意取舍）**: 「kill -9 1」类 pid-1 目标即使处于教学框架（如「为什么 `kill -9 1` 杀不死 init」）仍会被拦——模式无法区分"讲解为何无效"与"教唆执行"。取舍理由: 破坏性目标的拦截价值高于小众句式的教学损失，且原 12B 模式对此类本就全拦（非本次新增误报）。若后续需要，可在 orchestrator 提示词层放行"为什么无效"式问句，或引入共现意图判定（超出 micro 卡范围）。
2. **等效变体未纳入**: `kill -s KILL 1` / `kill --signal SIGKILL 1` 等等价破坏性写法修前即不在 malicious 层覆盖内，本卡未扩 scope（无回归、无新增漏放），登记为后续可选硬化项。
3. **既有 lint 债不属本卡**: 基线处 `test_llm_output_validator.py` 存在 ruff I001（import 排序）、`llm_output_validator.py` 存在 black 漂移，均修前已有，未顺手改（避免扩 patch）。本卡新增/改动内容 ruff/black 全净。
4. **过程申报**: 全程共用过两次 `git stash` 往返（本 worker 独占 worktree、无并发验收会话，untracked 新测试文件始终未入 stash）。第一次为比对基线 lint 状态；第二次为 patch 应用验证，因 untracked 文件冲突中途失败，当即 `stash pop` 还原并逐项核对 `git status` 与变更清单一致、stash 槽位清零。此后所有基线比对与验证一律改用无副作用方式（`git show HEAD:` 管道比对；patch 验证改在 `/tmp` 干净克隆实施）。纪律动词约束本意是防并发验收树损毁，两次往返均无实际风险，但如实登记。
5. **测试输出披露**: 修前红跑的失败信息包含 desc 标签「强制杀进程」与匹配串 `kill -9 `（类别元数据 + 本卡目标类别，按遮蔽纪律允许）；其余 malicious 条目词面全程未入上下文/未入任何输出。

## ⑤ 收工核查（含交付物自扫）

**回归结果**（SECRET_KEY=test，pytest 绝对路径，逐命令显式 cd）:
| 域 | 文件 | 结果 |
|---|---|---|
| 新测试（双向钉死） | `test_llm_output_validator_ops_fp.py` | 23/23 绿（修前 12 红） |
| validator 家族 | ops_fp + 主 + lexicon_fp + math_fp | **162 passed** |
| safety 域 | llm_safety / llm_safety_adversarial / stage37 / x06_tool_call | **121 passed** |
| validator 消费方 | security_wrapper_forwarding / o03_adversarial / push_content_parsing | **248 passed** |

**Patch 验证**: `git clone` 本 worktree 至 `/tmp`（只含 HEAD=57cafaa6，天然干净基线）→ `git apply --unidiff-zero changes.patch` 干净应用 → 同套 validator 家族测试 **162 passed**。

**交付物自扫（最终 PASS）**: 脚本化执行——从模块内存提取全部词表词面（`_VIOLENCE_LEX_SEQUENCES` chr 序列、COMPLIANCE 各条目交替词、MALICIOUS 各条目字面核心 ≥3 字符），对 `REPORT.md` 与 `changes.patch` 全文子串扫描，词面零落盘零打印；同时扫凭据模式。豁免台账逐项有据: 运维命令类（本卡目标类别，卡面允许明文）、纯正则语法 `0-9`（本卡新模式文档引用）、`bkill`（新模式 `\bkill` 分词自指）、`all`⊂killall、`file`⊂git 头 "new file mode"。迭代记录: 第一版 U3 patch 的上下文行曾暴露 L81 邻近其它条目词面、REPORT 曾引用破坏载荷字面——均已整改（patch 改 U0 零上下文、REPORT 改结构化描述），终扫 violence=0 / compliance=0 / malicious 非豁免=0 / 凭据=0。

**收工清单**: 无独立端口进程/模拟器/浏览器实例（仅前台 pytest，已退出）；无 `/tmp` 残留（探针脚本已清，`t1.py` 已删）；无构建产物（仅 gitignore 的 `__pycache__`/`.pytest_cache`）；变更集 3 文件与清单一致；worktree 内交付物仅 `v3-output/SAFETY-OPS/{REPORT.md, changes.patch}`。
