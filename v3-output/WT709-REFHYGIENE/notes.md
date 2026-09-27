# WT709 引链纠指卫生批（notes）

- 会话：wt709（node-b，纯文档单文件卫生卡；未新登 FIX 号——409/410 维持备用，见 §7）
- 补记：首扫以 `^\| V3-FIX-` 为行过滤器，漏捞 V3-FIX-301（其 ID 格前置「（集成重编号…）」注记）；批后全表复查（verify 行数 296 vs 解析 295 对账）发现后按同法补批。
- 基线：main HEAD `f48451b3`；worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt709-refhygiene`，分支 `agent/node-b/wt709/refhygiene`（全部 commit 在本分支，未 push）
- 对象：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 状态格指针（FIXED@/CLOSED@/WONTFIX@ 前缀引用）；只动指针与注记，不动状态语义、不动其余列
- 方法：严格复用 wt695 §3 已验证的 patch-id 法并升级为三级证据（见 §2）；每批落表后 `ledger_union_merge.py --verify` 零 FAIL

## 1. 处理统计（三类计数）

状态格指针共 240 个（196 显式 SHA + 44 别名，行状态 FIXED@ 223 / CLOSED@ 3 / WONTFIX@ 1——比 wt695 时点（0b1f58e3）多 3 行，因 main 前进带来的新闭账；含 V3-FIX-301 一条 ID 格前置撞号注记的非常规行首行，补捞入scope）：

| 类别 | 计数 | 说明 |
|---|---:|---|
| **可达（跳过）** | **15** | `git merge-base --is-ancestor` 即过，未触碰 |
| **纠指（改为集成 SHA 双注形态）** | **224** | 169 patch-id 全等 + 12 打包/漂移取证 + 43 别名解析（§2 分级） |
| **悬置（加「引链悬置」注记）** | **0** | 无一条落入；判定依据见 §4 |
| 复合别名保留（非悬置） | 1 | FIX-16 `CLOSED@E05X+LIVE`，见 §4 |

纠指证据分级：**PID=patch-id 全等 175**（169 状态指针 + 5 内嵌 SHA 别名 WT418/xxxx 族 + 1 本卡别名 FIX-365）；**PF=变更集逐文件/取证 12**（165/166/167/201/214/238/254/263/350/351/352/114）；**GR=subject 与闭账记录定位 37**（早期 ACCEPT merge 自指、批次卡名、wtNNN 别名等）。

校验：纠指后全表 `FIXED@/CLOSED@/WONTFIX@` 前缀指针 **239 个全部 main 可达（`rev-parse --verify` + `is-ancestor` 逐个断言）**，不可达 0，残留别名仅 FIX-16 一条（设计内）。独立抽查 5 对 worker→集成 patch-id（7f13c161→a6b6e19b、fdd25867→6dfe2ad5、3fec64f6→301eed3c、9268b35f→e610853e、c8142703→936ae4f7）全等，且与 wt695 §3 抽样结论逐条交叉吻合。

## 2. 方法与三级证据

1. **PID（最强）**：`git show <worker> | git patch-id --stable` 与 main 全量索引（`git log -p main --no-merges | git patch-id --stable`，1479 条）比对，全等且候选唯一即改指。168/180 不可达 SHA 一步命中，**零多候选歧义**。
2. **PF（次强）**：对打包集成/生成物漂移案例（12 条），按 subject/fix 号 grep 候选后做逐文件 diff 比对（tier A=去 index 行全等；tier B=±行集相等），并对生成物差异（openapi 快照、mypy 基线计数、l10n gen 风格）单独取证——共享的代码/测试文件全部逐文件全等，差异仅在生成物/随车文件，且逐条核实其去向（如 FIX-254 随车测试文件经 V3-FIX-190 通道 a1ff051f 落地、blob 与 main HEAD 全等；FIX-214 脚本迁移款被 main「不迁 devtools、后经 1fa4c51d 终绝删除」裁决取代）。改指时在双注内**如实注明差异与去向**。
3. **GR（定位级，仅用于无 worker SHA 可验的别名）**：`git log main --grep`（subject 边界匹配）定位集成提交，依据逐条记录：subject 显式闭账背书（WIRING-1「FIX-33/34/43 closed」、95dff6bf body「DYNAMIC_ISSUES 54/55/57 置 FIXED@WT408-SWEEP4」、d98a70c1「FIX-45 closed」）、diff 内注释直证（5776b430 内含「V3-FIX-118：类属性实名是…」）、交叉引用（dd7b7486「D-04（5ed3d20d 双审）」）、撞号重编号记录（a5437a0d 证 143=旧 142；01585b78 证 372=旧 359；8ac6bad5/9806d582 证 365=旧 360）。`git log -S` 唯一命中用于 FIX-119/201 内容核验。
4. 行内注记中的 fix-pointer 引用（`落地@/修复@` 形态）全表扫描仅 2 条不可达（FIX-16@3d05edf8、FIX-201@89e9da23），均 patch-id 验证后就近改为集成 SHA 双注；其余行内 SHA（修前红实录、worktree base 等历史证据引用）**不属指针，一律不动**。

## 3. 抽样 10 条纠指前后对照

**V3-FIX-329**
- 改前：`FIXED@7f13c161（2026-09-27 wt627 worktree wt627-flame：三处日界照抄同族先例修——``local_date`` 取用户本地今日 + ``local_midnight_as_utc_naive`` 换算 ``Ta…`
- 改后：`FIXED@a6b6e19b（原 worker 7f13c161 重提交；2026-09-27 wt627 worktree wt627-flame：三处日界照抄同族先例修——``local_date`` 取用户本地今日 + ``local_midnight_as_utc_naive`` 换算 ``…`
**V3-FIX-114**
- 改前：`FIXED@1ec531a4（wt438：`_gate_silent_diagnosis_payload` 纯函数投影——question 置 None（与顶层一致）；suggested_clarifying_question 渲染全文→封闭库 questio…`
- 改后：`FIXED@86003e04（原 worker 1ec531a4 重提交；diff 上下文随基线漂移，±行集逐文件核等；wt438：`_gate_silent_diagnosis_payload` 纯函数投影——question 置 None（与顶层一致）；suggested_clarifying_…`
**V3-FIX-165**
- 改前：`FIXED@cb30ec63（wt478：修法=类名映射消毒+结构化字段双轨——fallback.py 新增 _sterilized_error_class_label（_FALLBACK_MSG_KEYWORDS 词表与 _detect_fallback_r…`
- 改后：`FIXED@0e44092e（原 worker cb30ec63 重提交；9 代码/测试文件逐文件全等；openapi 快照重刷款未随集成（main 生成物另行管理）；wt478：修法=类名映射消毒+结构化字段双轨——fallback.py 新增 _sterilized_error_class_la…`
**V3-FIX-201**
- 改前：`FIXED@3828f69f（wt498：EN 值级统一裁决=map 系词表——专名/标题/按钮 Star Map、句中 the/your star map、知识星图 knowledge map、群星图 Group Map、上传选区星域 Selected do…`
- 改后：`FIXED@920b75e4（原 worker 3828f69f 重提交；subject 同名+并行 l10n 批/gen 引号风格漂移；本卡行集 git log -S 核验全落本提交；wt498：EN 值级统一裁决=map 系词表——专名/标题/按钮 Star Map、句中 the/your st…`
**V3-FIX-214**
- 改前：`FIXED@0c912a97（wt506 V3-FIX-210 第二批顺手处置：TRANSLATIONS 镜像裁剪 18 条死条目 495→477（本行登记批一 9+批二 taskExecution* 6+FIX-200 期 galaxyEmptyMessag…`
- 改后：`FIXED@9807c2a7（原 worker 0c912a97 重提交；镜像裁剪 5 个 l10n 文件逐文件全等；脚本迁移款未随集成（main 裁决不迁 devtools，脚本后经 1fa4c51d 终绝删除）；wt506 V3-FIX-210 第二批顺手处置：TRANSLATIONS 镜像裁剪…`
**V3-FIX-238**
- 改前：`FIXED@b04697cc（wt518：消费面盘点 28 处（26 json_call + 2 direct safe_llm_json_call）后裁决「宽型诚实化+调用方收窄」而非卡面建议的收窄方案——收窄为 dict-only 会让三个 prompt …`
- 改后：`FIXED@597df310（原 worker b04697cc 重提交；10 个代码/测试文件逐文件全等；mypy 基线 2 行随集成合并态校准（928→927）；wt518：消费面盘点 28 处（26 json_call + 2 direct safe_llm_json_call）后裁决「宽型诚…`
**V3-FIX-254**
- 改前：`FIXED@c3bb7e03（wt530：63 文件 +245/−305 纯等价重构；flutter analyze ERROR=0；触达 18 测试文件 122 passed+1 designed skip（sync_engine @Skip 迁 libra…`
- 改后：`FIXED@c38a17c7（原 worker c3bb7e03 重提交；63 文件逐文件全等；随车测试文件 release_flags_provider_test.dart 经 V3-FIX-190 通道 a1ff051f 落地（blob 与 main HEAD 全等）；wt530：63 文件 +…`
**V3-FIX-263**
- 改前：`FIXED@c9cf78f8`
- 改后：`FIXED@b53d0098（原 worker c9cf78f8 重提交；74 个代码文件逐文件全等；mypy 基线随集成合并态校准（869→861））`
**V3-FIX-60**
- 改前：`FIXED@WT418/b97dc471（提示卡+待审 pill 右避让缩进 88，几何锁 galaxy_rail_cta_clearance_test：按钮热区∩rail 49.5px 红转绿）`
- 改后：`FIXED@af2a412a（原 worker WT418/b97dc471 重提交；提示卡+待审 pill 右避让缩进 88，几何锁 galaxy_rail_cta_clearance_test：按钮热区∩rail 49.5px 红转绿）`
**V3-FIX-361**
- 改前：`FIXED@wt685（2026-09-25，worktree agent/node-b/wt685/l10ndebt）：8 键 6 面全部定性化——4 百分比键（sourceExplanationConfidence/intentConfidenceLabe…`
- 改后：`FIXED@53414f8a（原引用 wt685，wt709 引链纠指定位集成重提交（依据：subject 显式「wt685 V3-FIX-361/362 l10n 债修复批」；与 wt695 审计定位一致）；2026-09-25，worktree agent/node-b/wt685/l10nde…`

## 4. 悬置清单（全文）

**空**——无一条「引链悬置：worker 原 SHA 未定位到集成重提交」注记。181 条不可达 SHA 全部定位到确凿集成提交（169 条 patch-id 级、12 条逐文件/取证级），43 条别名全部解析为可解析 SHA 形态（37 条 GR + 5 条内嵌 SHA patch-id 级 + 1 条本卡别名 patch-id 级）。

唯一未改指针：**FIX-16 `CLOSED@E05X+LIVE`**——复合闭账别名（E05X 卡代码 + live 窗口补验多提交共同闭账），强行单 SHA 化会改变状态语义；行内锚点 3fc71ce1/808ba5a1/f8dcbd56 逐个验证**均 main 可达**，卫星修复款 `@3d05edf8` 已就地纠指为 `@1c03108a（原 worker 3d05edf8 重提交）`。该行已具备可解析性，非悬置。

## 5. 提交列表（6 批，每批约 40 行，批后 verify 零 FAIL）

| commit | 批次 | 内容 |
|---|---|---|
| `641ba396` | 1/6 | FIX-01~067 段 40 行 |
| `0be3bb86` | 2/6 | 40 行（FIX-068~166 段） |
| `8018f179` | 3/6 | 40 行（FIX-167~249 段） |
| `bd567789` | 4/6 | 40 行（FIX-253~303 段） |
| `e605d2f3` | 5/6 | 40 行（FIX-304~350 段） |
| `b5932b4f` | 6/6 | 23 行（FIX-351~389 段）+ 本 notes |
| `9581b0c8` | 补批 | V3-FIX-301（ID 格前置撞号注记的非常规行首，首扫过滤器漏捞、全表复核补捞）754ca447→055a8b7f patch-id 全等 |

（第 1 版提交信息批序号笔误已按同内容重写为上述 6 条；文件内容逐批与首版完全一致，均为 cherry-pick 原树。）

## 6. 附录：PF/GR 级纠指全清单（PID 级 174 条的双注已在台账行内自证，不重复列）

| 行 | 原指针 | 纠指至 | 依据 |
|---|---|---|---|
| V3-FIX-114 | 1ec531a4 | 86003e04 | 逐文件/取证：diff 上下文随基线漂移，±行集逐文件核等 |
| V3-FIX-165 | cb30ec63 | 0e44092e | 逐文件/取证：9 代码/测试文件逐文件全等；openapi 快照重刷款未随集成（main 生成物另行管理） |
| V3-FIX-166 | cb30ec63 | 0e44092e | 逐文件/取证：9 代码/测试文件逐文件全等；openapi 快照重刷款未随集成（main 生成物另行管理） |
| V3-FIX-167 | cb30ec63 | 0e44092e | 逐文件/取证：9 代码/测试文件逐文件全等；openapi 快照重刷款未随集成（main 生成物另行管理） |
| V3-FIX-201 | 3828f69f | 920b75e4 | 逐文件/取证：subject 同名+并行 l10n 批/gen 引号风格漂移；本卡行集 git log -S 核验全落本提交 |
| V3-FIX-214 | 0c912a97 | 9807c2a7 | 逐文件/取证：镜像裁剪 5 个 l10n 文件逐文件全等；脚本迁移款未随集成（main 裁决不迁 devtools，脚本后经 1fa4c51d 终绝删除） |
| V3-FIX-238 | b04697cc | 597df310 | 逐文件/取证：10 个代码/测试文件逐文件全等；mypy 基线 2 行随集成合并态校准（928→927） |
| V3-FIX-254 | c3bb7e03 | c38a17c7 | 逐文件/取证：63 文件逐文件全等；随车测试文件 release_flags_provider_test.dart 经 V3-FIX-190 通道 a1ff051f 落地（blob 与 main HEAD 全等） |
| V3-FIX-263 | c9cf78f8 | b53d0098 | 逐文件/取证：74 个代码文件逐文件全等；mypy 基线随集成合并态校准（869→861） |
| V3-FIX-350 | 79ad6a90 | c575e6a4 | 逐文件/取证：9 个代码/测试文件逐文件全等；openapi 快照并行批漂移、增删行终态核等 |
| V3-FIX-351 | 79ad6a90 | c575e6a4 | 逐文件/取证：9 个代码/测试文件逐文件全等；openapi 快照并行批漂移、增删行终态核等 |
| V3-FIX-352 | 79ad6a90 | c575e6a4 | 逐文件/取证：9 个代码/测试文件逐文件全等；openapi 快照并行批漂移、增删行终态核等 |
| V3-FIX-01 | V3-FIX-01 | 4c963ef4 | subject/闭账记录：subject 精确匹配（ACCEPT merge） |
| V3-FIX-02 | V3-FIX-02 | 6470a6fb | subject/闭账记录：subject 精确匹配（ACCEPT merge） |
| V3-FIX-03 | D-04 | 5ed3d20d | subject/闭账记录：subject 精确匹配；dd7b7486 交叉引用「D-04（5ed3d20d 双审）」 |
| V3-FIX-04 | V3-FIX-04 | 7251128e | subject/闭账记录：subject 精确匹配（ACCEPT merge） |
| V3-FIX-11 | V3-FIX-11 | db652302 | subject/闭账记录：subject 精确匹配（ACCEPT merge） |
| V3-FIX-12 | E-02 | 690541e3 | subject/闭账记录：subject 精确匹配（E-02 ACCEPT merge，含 rework+delta，与行注双路验收一致） |
| V3-FIX-28 | X-05B | 238abe22 | subject/闭账记录：subject 精确匹配（X-05B 卡双审合入） |
| V3-FIX-29 | X-05B | 238abe22 | subject/闭账记录：subject 精确匹配（X-05B 卡双审合入） |
| V3-FIX-33 | WIRING-1 | 7c6cb867 | subject/闭账记录：subject 显式「FIX-33/34/43 closed」 |
| V3-FIX-34 | WIRING-1 | 7c6cb867 | subject/闭账记录：subject 显式「FIX-33/34/43 closed」 |
| V3-FIX-35 | V3-FIX-3536 | 3c2ca32c | subject/闭账记录：subject 精确匹配 fix(V3-FIX-35+36) |
| V3-FIX-36 | V3-FIX-3536 | 3c2ca32c | subject/闭账记录：subject 精确匹配 fix(V3-FIX-35+36) |
| V3-FIX-41 | V3-FIX-41 | 1ae6a9e1 | subject/闭账记录：subject 精确匹配 |
| V3-FIX-43 | WIRING-1 | 7c6cb867 | subject/闭账记录：subject 显式「FIX-33/34/43 closed」 |
| V3-FIX-45 | DEBT-BATCH1 | d98a70c1 | subject/闭账记录：subject 显式「debt-batch1…FIX-45 closed」 |
| V3-FIX-47 | FIX-47-HARDENING | f9df4a5a | subject/闭账记录：subject 显式 fix(FIX-47) autoexec hardening (closed) |
| V3-FIX-54 | WT408-SWEEP4 | 95dff6bf | subject/闭账记录：提交 body 显式收口②V3-FIX-54 且尾注「DYNAMIC_ISSUES 54/55/57 置 FIXED@WT408-SWEEP4」 |
| V3-FIX-55 | WT408-SWEEP4 | 95dff6bf | subject/闭账记录：提交 body 显式收口④V3-FIX-55 且尾注同上 |
| V3-FIX-57 | WT408-SWEEP4 | 95dff6bf | subject/闭账记录：提交 body 显式收口①V3-FIX-57 且尾注同上 |
| V3-FIX-110 | WT428 | 8541ddde | subject/闭账记录：subject 显式「V3-FIX-110/111/115」摩擦门语义缺陷族 |
| V3-FIX-111 | WT428 | 8541ddde | subject/闭账记录：subject 显式「V3-FIX-110/111/115」摩擦门语义缺陷族 |
| V3-FIX-115 | WT428 | 8541ddde | subject/闭账记录：subject 显式「V3-FIX-110/111/115」摩擦门语义缺陷族 |
| V3-FIX-118 | wt426 | 5776b430 | subject/闭账记录：5776b430 diff 内注释直证（+行「V3-FIX-118：类属性实名是 _classify_cache_ttl_seconds」） |
| V3-FIX-119 | wt426 | 5776b430 | subject/闭账记录：git log -S「Apply database migrations」唯一命中 5776b430；行内补记段本已引 5776b430 |
| V3-FIX-140 | WT430 | 5aaf2c1a | subject/闭账记录：5aaf2c1a=wt430 O10/O11 双修，diff 含 proxy_routes.go analyze-intent 补挂（与行注一致） |
| V3-FIX-141 | WT430 | 5aaf2c1a | subject/闭账记录：5aaf2c1a=wt430 O10/O11 双修，diff 含 goal_repository.dart POST /goals/ 改造（与行注一致） |
| V3-FIX-143 | WT440 | 62241e59 | subject/闭账记录：62241e59 subject=O1 种子示例标识（旧号 142）；a5437a0d 记载 wt440 O1 撞号顺延改 143 |
| V3-FIX-163 | wt520-black163 | d4cb1f82 | subject/闭账记录：subject 精确匹配（wt520 V3-FIX-163 black 收正） |
| V3-FIX-181 | 主会话直修 | b8c94477 | subject/闭账记录：subject 与行注逐项一致（#1/#2 补 V3-FIX-03 交叉指针+维护规则立规约） |
| V3-FIX-279 | W558-R2 | 0532f068 | subject/闭账记录：0532f068 即 W558 审计 R2 回扫事件本体（台账修复提交，subject 显式销账本行） |
| V3-FIX-357 | wt671 | 938e1f34 | subject/闭账记录：subject 显式「wt671 U-01 复核样板项…（V3-FIX-357/358）」，与行注 SCAN_ROOTS 删 onboarding 项一致 |
| V3-FIX-361 | wt685 | 53414f8a | subject/闭账记录：subject 显式「wt685 V3-FIX-361/362 l10n 债修复批」；与 wt695 审计定位一致 |
| V3-FIX-362 | wt685 | 53414f8a | subject/闭账记录：subject 显式「wt685 V3-FIX-361/362 l10n 债修复批」 |
| V3-FIX-371 | 注释直修 | 7aa46c04 | subject/闭账记录：subject 精确匹配（四处注释旧号直修，纯注释零行为） |
| V3-FIX-372 | wt674 | 01585b78 | subject/闭账记录：subject 显式「wt674 U-08 续——58 处占位语义标签全清…（登记时旧号 359，撞号顺延为 372）」 |
| V3-FIX-374 | wt683 | fc4f4a43 | subject/闭账记录：subject 精确匹配（wt683 卡 U-02 F5 收口 V3-FIX-374） |
| V3-FIX-378 | wt687 | f00c44d6 | subject/闭账记录：subject 精确匹配（wt687 卡 U-04 续做 V3-FIX-378） |

## 7. 观察项与新发现处置（不占号说明）

- **未登记 V3-FIX-409/410**：本批全程只发现指针断链（已尽数修复），无新的产品/代码缺陷达登记门槛。一个非登记观察项如实留档：FIX-165~167 集成（0e44092e）未随带 worker 的 openapi 快照重刷款（worker 新增 1 行不在 main HEAD 快照、删除 1 行仍在），main 快照可能相对已集成的 typed-error 代码滞后——该快照由工具再生管理、且无法确证现行契约检查会因此红，不满足「如实、可证」的登记门槛，仅留观察。
- 别名 `FIXED@V3-FIX-3536`（FIX-35/36 共享指针）解析为 3c2ca32c（subject 显式 fix(V3-FIX-35+36)）。
- wt695 §4 的其余卫生欠账（11 条实质已修行状态待维护、3 条疑陈旧、FIX-293 挂人事项补登）不在本卡范围，未动。

## 8. 已知局限

- GR 级 37 条的证据强度为「subject/闭账记录/交叉引用定位」，低于 patch-id 全等（其 worker 原 SHA 本就不存在或不可考，已是可达的最强定位）；每条依据已在台账行内双注与本附录留痕，可复核。
- PF 级 12 条中，生成物差异（openapi 快照/mypy 基线/l10n gen）以「逐文件全等 + 差异去向取证」替代 patch-id 全等，双注内逐条注明；如审查会话对任一条存疑，按附录原指针可直接复算。
- 行内注记中非 fix-pointer 的历史 SHA（修前实录、base 号）未做可达性普查（不在指针范围）；其中被引用为「证据」的对象若日后清理 worktree 分支可能不可达，属上游形态、非本批引入。
