# WT764 · J-02 Onboarding：Value Before Profile（补缺口施工）

- 工号：wt764 ｜ 日期：2026-09-27 ｜ worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt764-j02`
- 分支：`agent/node-b/wt764/j02` ｜ **base = main@3cbeb4a7**（轮#252），final SHA 见文末
- 卡面：`v3/07_tasks/cards/J-02.md` ｜ 必读：`v3/01_product/FIRST_3_MINUTES.md`（已读）
- 性质：wt759 三源核验判 J-02=partial（§3.2）后的缺口施工卡。先摸清 wt282 已交付（避免重做），再逐缺口红→绿。
- 状态：**READY_FOR_REVIEW**（残差明示于 §6，均在验收模型中归 Reviewer/首飞）

---

## 1. 已交付（前人，本卡只核对不重做）

| 面 | 交付人 | 证据 |
|---|---|---|
| 首跑价值字幕（N48 zh+en 具象场景词） | wt282 cd154f03 | v3-output/J02-VALUE-ONBOARD/REPORT.md；字幕测试在主干 |
| persona 草案 8 字段断点续存（debounce+clamp） | wt282 cd154f03 | persona_onboarding_draft.dart + 续存测试 |
| 注册硬跳移除 → 软墙 + OnboardingResumeCard（dashboardSections 挂载） | wt282 cd154f03 | routes.dart:211-222；wt287 互斥语义复核 |
| **GuestConversionCard growthSections 盲区**（wt759 §3.2 缺口⑤） | **wt287 已闭** | v3-output/wt287-convcard-blindspot/REPORT.md；dashboard_screen.dart:1122-1151 注释与挂载实况核对一致——wt759 报告此缺口已过时 |
| 两入口之「体验一个示例」（login 次级入口，走 guest/example 同源链路） | J-01 O5 面 | login_screen.dart:109-114/289-298 |
| first action 链真源（goal→Aurora→proposal→task） | wt371 02b82cd2 | first_action_service.py 只读 memory_goals；FirstActionCard 已挂 home |
| 种子 namespace 隔离机制 | V3-FIX-258/257/142 | demo 轮跳记忆推断（memory_inferred_write_lane.py:273-291）；转正清洗四表（guest_seed_service.py:3905+）；Plan.source=example+is_example badge |

## 2. wt759 缺口 → 本卡处置对照

| # | wt759 §3.2 缺口 | 本卡处置 |
|---|---|---|
| ① | 「两个入口与最小 goal capture」仅部分（草案续存≠入口重构）；「只问改变 first action 的问题；其他信息延后」未实现 | **本卡主体施工**：persona 屏步 1 快车道（§3）+ 服务端最小载荷契约钉（§4.1） |
| ② | 「guest example 与 real profile namespace 隔离」未在本卡闭合 | **本卡补 J-02 级证据面**：两个后端 pin 测试（§4.2）——机制属既有裁决（258/257/142），本卡不重建只钉住 |
| ③ | 「fresh user ≤3min 到 useful action」无实测证据 | **headless 等价证据（验算）**：§5；设备实测残差交 Reviewer（§6） |
| ④ | 「注册/游客/升级三端 session 稳定」无三端证据 | **router 级 widget 钉**：三身份 session 稳定三角（§3.3）；实机三端走查残差交 Reviewer |
| ⑤ | GuestConversionCard 盲区未闭 | **已被 wt287 闭合**（§1），本卡零工作 |

## 3. 本卡实现面（mobile，红→绿）

### 3.1 最小 goal capture 快车道（卡面 Work 1+2）

`persona_onboarding_screen.dart`：

- **步 1 目标非空即现快车道 CTA**（`ValueKey('j02-fast-path-cta')`，ghost 档不与「完成」primary 竞争）+ 一行说明（`personaFastPathHint`）。`ValueListenableBuilder` 直读 controller，输入即现，零防抖等待。
- **`_handleFastPathSubmit`**：只提交 `{learning_goal_type, learning_goal}` 两字段走既有 `POST /profile/onboarding`——服务端各显式偏好逐字段条件写入，goal-only 载荷 → 四项偏好零写入（学习风格/每日时长/基础档/回答偏好都不改变 first action）。
- **完成态语义（渐进画像闭环）**：goal-only 提交不产生 `study_time_preference/knowledge_level/response_style` 偏好 → mobile `onboardingCompleted` 推断保持 `false` → **OnboardingResumeCard 留存**「继续引导」入口，其余四问经它延后可达——**五问零裁减（TV-G3），只延后**（A-SPEC8B G1 裁决「压缩靠后置/对话化」的施工落地）。
- **续接面与全量提交同一处**：modeling 访谈（对话化画像，G4 改写采纳）。成功后草稿**步进到第一个延后问**（`PersonaOnboardingDraft.deferredAt(1)`），重进续答不重填目标。
- **竞态修复（红测揪出）**：输入后 400ms 内点快车道，迟到的防抖存稿定时器会用步 0 快照覆盖 deferred 草稿——落稿前先 `_draftSaveDebounce?.cancel()`。
- **失败诚实**：与全量提交同形制的可见 SnackBar + 重试；不跳转、不假装成功。
- l10n：`personaFastPathCta`/`personaFastPathHint` 双语键（app_zh.arb/app_en.arb），`flutter gen-l10n` 重生成 3 文件，diff 仅含本卡键。

### 3.2 红→绿实录

- 红（base 3cbeb4a7 + 仅测试文件/arb，无屏改动）：`persona_onboarding_fast_path_test.dart` **0 过 / 4 败**（全部 `j02-fast-path-cta` not found——行为不存在，机械红）。
- 绿（实现后）：同文件 **4/4 过**：①空目标无快车道 ②只上行 goal 两字段+续走 modeling ③草稿保留步进延后问 ④失败可见可重试。

### 3.3 三端 session 稳定（卡面 Acceptance 第 2 条，router 级）

`router_smoke_test.dart` 新增 2 用例，与既有软墙用例构成三身份三角：

- **注册端**（既有，wt282）：注册未完成 → 停 home 软墙，不被全域弹回 persona。
- **游客端**（本卡新增）：guest（registration_source='guest'）访问 persona 引导路由 → 折回 home（无未完成引导循环，session 稳定）。
- **升级端**（本卡新增）：guest 转正后（registration_source 翻转为注册身份、onboarding 未完成）→ persona 引导**保持可达**（供补完延后问），不被 completed/guest 折返分支吞掉。

## 4. 本卡实现面（backend，J-02 级证据 pin）

### 4.1 `tests/unit/test_j02_minimal_goal_capture.py`（2 例）

直调 `submit_onboarding` 钉服务端半边契约：①goal-only → `memory_goals` 恰 1 行（source_type=user_state、metadata.goal_type）∧ `user_preferences_center.explicit` 四键零写入 ∧ `first_message` 照常回包；②对照锚：全量载荷仍写 goal+全部偏好（五问全量路径不受影响）。

### 4.2 `tests/unit/test_j02_seed_memory_namespace.py`（2 例）

- **结构隔离**：`seed_guest_user_data` 种满演示内容后，该用户 `memory_goals`/`episodic_memories` 恒 0 行——种子只种演示内容面，从不触碰真实 Memory 域（goal 真源唯一写入口 = onboarding/用户陈述路径）。
- **demo 轮不进记忆 lane**（V3-FIX-258 分支此前**零测试覆盖**，本卡补钉）：`llm_service.demo_mode=True` 时 `process_chat_turn` 抽取前整轮短路（返回 None + `demo_skipped` 观测点递增），用户侧原文同轮跳过。

## 5. ≤3min 到 useful action —— headless 验算（等价证据口径）

**口径声明**：本节是**验算**（代码常量 + 既有实测段拼装），非设备实测。按卡面 Forbidden「不得只通过静态代码阅读宣称用户体验通过」，本卡**不**据此勾验收框；设备/simulator 实测留 Reviewer（§6）。

fresh 注册用户路径（prepared evaluator，各段依据）：

| # | 段 | 耗时验算 | 依据 |
|---|---|---|---|
| 1 | 冷启动到首屏可交互 | ≤0.5s | presentation budget 470ms（1ebcfe09）；splash 品牌窗 ≤400ms（ColdStartMotion.splash，认证并行不叠算） |
| 2 | 注册表单 7 项 + 提交 | ~40s（人为输入） | 表单 7 项零裁减（TV-G3 既辖，本卡不动注册面）；参照 V13 实测旧 6 页引导链 29s 量级（0886aaff） |
| 3 | 落 home（软墙） | <0.5s | dashboard 骨架快路径 <500ms（U-06）；resume 卡可见（无目标新注册用户走 hasNoGoals 分支，dashboardSections 渲染） |
| 4 | resume 卡 CTA → persona 步 1 | 1 tap，即时 | OnboardingResumeCard CTA（wt282） |
| 5 | 输入目标 + 快车道提交 | ~10s + 1 网络往返 | goal 文本即问即答；`POST /profile/onboarding` goal-only（本地栈 200-800ms 量级）；AI 预览 450ms 防抖可选、不阻塞 |
| 6 | modeling 访谈 skip（或答一问） | 1 tap，即时 | modeling 屏 ghost skip（既有）；skip 即 onboardingCompleted=true |
| 7 | home FirstActionCard → 生成 → 确认 | 2 taps + Aurora 推导 | goal 已在 memory_goals（J-04 链真源）；推导为 LLM 往返（本地栈秒级），失败有 503 诚实重试（wt371） |

**合计：≈5 taps + ~55-70s**（不含 #7 LLM 推导）；对 180s 预算留 **>100s 余量**——即使网络/推导各慢 3 倍仍在线内。游客端更短：login 屏「体验一个示例」1 tap → 种子 home（服务端种子 ~1-3s，V3-FIX-286 有失败可见性门），即刻有内容可玩；**种子零进真实 Memory**（§4.2 pin）。

升级端 session 连续性：转正原位翻转 registration_source（GJ02 路径），auth 中断面由既有转正事务承载（SAVEPOINT 清洗 257）；mobile 侧语义由 §3.3 升级端用例钉住。

## 6. 残差（Reviewer/首飞清单，非本卡工程缺口）

1. **设备/simulator 实测**：§5 验算的两条 acceptance 建议在 integration HEAD 或真机按 FIRST_3_MINUTES 的 automated simulator 清单走一遍（5 Persona 差异化已由 J-04 后端断言承载，此处主要是观感与秒表核）。
2. **review receipt**：按验收模型归独立未参与会话。
3. **首聊破冰（N49）**：访客首聊零问询破冰跨层卡，A-SPEC8B 明示留跨层卡，本卡不属（wt759 缺口清单亦未列）。

## 7. 验证汇总

| 面 | 结果 |
|---|---|
| 红测（base+测试文件，无实现） | `persona_onboarding_fast_path_test` 0 过 / 4 败（CTA not found，机械红） |
| 快车道绿 | 同文件 **4/4 过** |
| persona 回归 | draft_resume **8/8** + submit_feedback **3/3** 过（含 deferredAt/竞态修复面） |
| router 三端 | router_smoke **10/10 过**（既有 8 含昔日环境性失败用例本轮全绿 + 新增 2） |
| 相邻面 | first_run_value_subtitle **3/3** + onboarding_resume_card **5/5** 过 |
| 后端 pin | test_j02_minimal_goal_capture + test_j02_seed_memory_namespace **4/4 过**（sqlite 内存库，SECRET_KEY 测试环境变量）；black/ruff 双清 |
| l10n | arb×2 新键 → gen-l10n 再生 3 文件，diff 仅本卡键 |
| analyze gate | `check_flutter_analyze_gate.py` **0E/0W/0I PASS**（3 处新 lint 红→改写清零） |
| 治理守卫 | `run_all_rule_guards.sh` **exit=0 全绿**（worktree 需从主仓 `cp -RL` backend/app/gen、backend/gateway/gen、mobile/lib/gen——gitignored，BG/编译依赖；本机无 .env 属正常假红规避形态） |

环境注：本机 macOS arm64（16G/swap 16G）。开工 swap 空闲 757M，轮询至门禁边缘后以**无竞争进程 + load<2** 为准单文件串行跑测（`--concurrency=1`）；全程无模拟器/Gradle。

## 8. 交接与记账

- 不 push；commit 在分支 `agent/node-b/wt764/j02`；docker/运行栈/ns001 零触碰。
- FIX 号复核结论：495=wt760（已集成）、497=wt761（分支已登记）、496 疑被 wt760 任务口径预占（wt761 台账注记）→ **本卡备用号取 498**（集成 main@e9ec99d8 grep 0 命中亲证空闲）。本卡施工未发现需登记的新真缺陷（红测揪出的草稿竞态在本卡实现内就地修复，非既有产品缺陷，不占 FIX 号）。
- base SHA：`3cbeb4a7` ｜ final SHA：见分支 HEAD（commit 记录）。
- 集成提示：main 已前进至 e9ec99d8（轮#255）；本卡改动面（persona 屏/arb/l10n/router_smoke/后端两测试文件）与在航卡无已知交叠（锁 mobile-onboarding 持有）。

*—— wt764 施工完毕，READY_FOR_REVIEW。*
