# WT706-AURORA54 · V3-FIX-198 处置实录（「自称余 54 键」不实自述收口）

- 工号：wt706（2026-09-27 补位卡，来源=wt695 日终盘点 A1 队列 FIX-198 行）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt706-aurora54`（分支 `agent/node-b/wt706/aurora54`）
- base SHA：`63658aef`（main；工作期间 main 前移至 cb4e0719=wt697 docs 行，arb 未动，不影响本卡复核结论）
- 触达面：`v3/06_agent_fleet/DYNAMIC_ISSUES.md`（198 状态格改写+新登 403 行）+ 本 notes；**零产品码改动**

## 1. 结论 TL;DR

1. 台账 V3-FIX-198 状态格「OPEN（首卡落地@6780380c，**剩余 54 活键随后续卡**）」系不实自述，本卡撤下并注真实口径，置 `FIXED@9af3fa52`（首卡 copy-aurora-intro 的 main 链 SHA；台账原引 6780380c 为 wt491 分支 SHA，同一补丁，已证不在 main 祖先链）。
2. 「54」三重失实（§2）：①wt488 的 56 是 zh 单侧口径（漏 2 个 en-only 提及键），并集口径 base 实测 58；②56−2=54 算术错位——首卡两键原值「AI 导师」本不在自称集内，首卡实际效果是 +1（chatWelcomeTitle 改值后作为合法引入键入集）；③后续卡 200/201 均零自称键离场，base→HEAD 进出账=**离场 0 / 入场 1**，当前真实自称活键 **59**（31 aurora* + 28 非 aurora*；除引入键外 58）。
3. 剩余自称键不是本缺陷的未修面：§1.1 白话基线保留项（把握 {percent}% 等）+ V3-FIX-182 冻结拍板遗留为刻意保留；galaxy 黑话高危主体脱管面另立 **V3-FIX-403** 跟踪（§3）。
4. 本卡零 .py/.dart 触达 → 无新测试（按诚实性运动文档面先例以 grep 证据前后对照入 §5）；mypy 159=近期合并态真实基点（任务书 158 系旧合并态，389 行已注录），ruff 触达面为空。

## 2. 「54」口径考古与复核

### 2.1 自述面定位（修前 grep）

「54」全仓仅 3 处，无一在代码输出面：

| 面 | 位置 | 性质 | 处置 |
|---|---|---|---|
| 台账状态格（活口径） | DYNAMIC_ISSUES.md:154 | 运行状态权威 | **本卡改写** |
| wt695 日终盘点 A1 队列行 | v3-output/WT695-AUDIT/eod.md:51「首卡已落地，余 54 活键」 | 时点审计记录 | 不改（改史=伪造审计线）；由台账行闭账覆盖 |
| fleet_state 日志轮次 | .sparkle_v3_fleet_state.json 轮#193/#196 | 协调日志（append-only，fleet.py 事务面） | 不改（非本卡写面） |

另：wt488 PROPOSAL.md 的「56 键」为其自身分析结论（base 锚定、时点文档），不动。

### 2.2 三个口径的实测

方法（wt488 同口径+并集扩展）：双 arb 值含 `aurora`（大小写不敏感）取并集 × `l10n.<key>` 词边界 grep（`mobile/lib`+`mobile/test`，剔 `mobile/lib/l10n/` 生成物）≥1 引用文件为活。

| 时点 | zh 单侧口径 | zh∪en 并集口径 | aurora* / 非 aurora |
|---|---|---|---|
| base aa6a9667（wt488 盘点点） | 56（=wt488 发布数，复算吻合） | **58** | 31 / 27（并集） |
| HEAD 63658aef（本卡 base） | — | **59** | 31 / 28（并集） |

en-only 漏计的恰 2 键（zh 值无 Aurora、en 值有，base 值实证）：
- `auroraCorrectionInputHint`：zh「哪里判断错了？说说你的纠正…」/ en "What did Aurora get wrong? Share the correction…"
- `homeAuroraDialogHint`：zh「哪里判断错了？说说你的想法…」/ en "What did Aurora get wrong? Share your thoughts…"

### 2.3 base→HEAD 进出账（关键证据）

- 离场 0 键：V3-FIX-200（d6f33823 收割 38 死键）、V3-FIX-210 六批、V3-FIX-342 均未移除任何自称 Aurora 的活键。
- 入场 1 键：`chatWelcomeTitle`（首卡 9af3fa52 改值「你好，我是 Aurora」/"Hi, I'm Aurora"）——这是**合法命名引入**，不是违规自称；首卡两键（chatWelcomeTitle/Subtitle）改值前为「AI 导师」/"Hi, I'm your AI tutor"，本不在 56/58 自称集内，故「56−2=54」从其诞生起就未对应任何真实键集。
- 当前 59 键逐键清单（复核脚本 `/tmp/wt706_recount.py` 输出，临时文件不入库）：31 个 aurora* 前缀（auroraSensing/auroraCalibrated/auroraJudgmentTag 等状态芯片族+correction 族）+ 28 个非 aurora*（settings 面 settAuroraPref*、通知 notificationAurora*、任务 taskAuroraHelp/taskDiagnosis*、userAurora 显示名、sensoryAuroraLink*、studyMaterialsHeroSubtitle 等）。
- 治理归属：§1.1 保留项（白话基线刻意保留）、V3-FIX-182（visual/aurora 冻结拍板遗留）、V3-FIX-403（galaxy 黑话主体，见 §3）。

## 3. 连带新发现：V3-FIX-403（已登记，预占号亲证空闲）

复核「剩余 54 活键随后续卡」时核对了「后续卡」是否真的处理过这批键，发现 wt488 卡2（copy-galaxy-metaphor）的 zh 主体脱管：

- §1.2 A-D 高危 24 键中 **19 键黑话原值在架**（❌16：知识星族 9——galaxyDraftReviewPromptTitle「我们从 {documentName} 里找到了 {count} 颗知识星」等；上传/仿真/设置族 7——galaxyUploadTargetGalaxyCore「银河核心」/galaxyUploadStatusQueued「正在进入轨道...」/galaxyUploadFailedBody「滑了出去」/galaxyUploadAlreadyInProgress「飞向星图」/galaxySimCenterGravity「中心吸引力」/galaxySimLinkTension「连线牵引力」/galaxySimSettingsDesc「力场参数」；⚠️3：galaxyDraftReviewPromptBody/EmptyBody/CompletionReady 诗化原值）。
- 其余 5 键去向：1 键已替换（galaxyUploadTargetSelectedConstellation「所选领域」@380b31b1）、4 键已删（onboardingGalaxyFeature1-4，git log -S 坐实=e610853e/V3-FIX-342）。
- 19 键活键性逐一复核**全活**（1-2 引用文件/键，词边界 grep 剔生成物）。
- 201 闭账（3828f69f）口径=译名统一半边，其文本如实未称卡2 主体已动；但卡2 剩余主体自此无在挂台账行。
- 处置：新登 V3-FIX-403（P3，OPEN，owner=T-copy-galaxy-metaphor-zh-rest；建议词中英全文已在 PROPOSAL §1.2 可直接抄卡）。备用 404 未动。

## 4. 台账改动

1. 198 状态格：`OPEN（首卡 copy-aurora-intro 落地@6780380c，剩余 54 活键随后续卡）` → `FIXED@9af3fa52（…撤下不实自述并注真实口径…）`，全文见 DYNAMIC_ISSUES.md:154。
2. 追加 403 行（:339），7 列 8 裸管。

## 5. 验证记录（真实运行）

- **台账守卫**：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`
  → `verify：295 行 V3-FIX 行，裸管分布 {8: 295}，多数形态 8 / verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法`，exit=0。
- **grep 前后对照**：修前 :154 状态格含「剩余 54 活键随后续卡」（本文件 §2.1 表）；修后同位置含「系不实自述，wt706 复核撤下并注真实口径」+FIXED@9af3fa52；「54 活键」全仓残留面仅剩 eod.md/fleet_state 两处历史记录（§2.1，刻意保留）。
- **mypy**：cwd=worktree/backend、rm -rf .mypy_cache 后 `…/backend/.venv/bin/python -m mypy app` → `Found 159 errors in 129 files (checked 1384 source files)`。本卡 diff 仅 1 个 .md（`git diff --name-only HEAD`=v3/06_agent_fleet/DYNAMIC_ISSUES.md），零 .py 触达 → 159 与基点零差且与本卡无关；任务书「当前合并态 158」系旧合并态数字，台账 389 行（wt699）已注录「mypy 159=main 同基点 NO-DIFF；任务书基线 158 系旧合并态」，与本机实测一致。
- **ruff**（0.15.8）：触达 .py 文件集为空，不适用。
- **flutter 测试**：零 .dart 触达，不适用；活键性/进出账证据以词边界 grep 产出（§2.2/§2.3），符合任务步骤 5 文档面条款。

## 6. 复现命令要点

```bash
# 并集口径活键计数（当前工作树）
python3 - <<'PY'
import json,re,subprocess
ks=set()
for side in ('zh','en'):
    arb=json.load(open(f'mobile/lib/l10n/app_{side}.arb'))
    ks|={k for k,v in arb.items() if not k.startswith('@') and isinstance(v,str) and re.search(r'aurora',v,re.I)}
live={k for k in ks if subprocess.run(['grep','-rlE',r'l10n\.'+re.escape(k)+r'\b','mobile/lib','mobile/test','--include=*.dart'],capture_output=True,text=True).stdout.strip() and [f for f in subprocess.run(['grep','-rlE',r'l10n\.'+re.escape(k)+r'\b','mobile/lib','mobile/test','--include=*.dart'],capture_output=True,text=True).stdout.splitlines() if not f.startswith('mobile/lib/l10n/')]}
print(len(live))
PY
# base 回放（注意 git grep 词边界用 [[:>:]] 而非 \b）
git grep -lE 'l10n\.auroraSensing[[:>:]]' aa6a9667 -- mobile/lib mobile/test
```
