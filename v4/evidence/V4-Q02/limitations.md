# V4-Q02 · limitations（如实申报）

## 1. L2 live-model 层 BLOCKED_EXPLICIT——M11/M12 终判缺席

四臂 live 层（协议 LIVE_MODEL_SYNTHETIC，M11 的「点估计≥+10pp 且簇 bootstrap 95% 下界>0」终判面）**未运行**：批量收费模型预算未授权（卡面 `heavy_token_required=false`；`budget.example.json` 冻结 `enabled=false/max_spend=null`）。本卡零模型调用（账目在 run_manifest）。**任何 M11/M12 的 L1 数字都不得外推为 live/真人结论**；真人留存/偏好永未测量（NOT_MEASURED_HUMAN）。

## 2. C/D 臂在 L1 决策回路面结构性恒等（本卡最重要的面边界）

I02 效用门的唯一集成面是 `context_pack.build`（chat 编排装配面）；A-08 harness 的决策回路（StuckJourneyService + FrictionChatWiringService + D-05/A-05 回路）**不经过该面**。同时 harness 的 patch 载荷为 `{intervention, direction: prefer}`（无 do_not_apply/precondition 键），I05 live 的 decision 门出无可触发条件；admission 收益门在本 harness 的 auto 激活记录上未出现「无收益却会自动激活」的形态。因此 **A≡C≡D 逐记录恒等是本 harness 激励分布下的结构性结果**：

- 这**不是**「V4 机制无效」的证据——I05 live 门行为差分由其自身服务面测试承载（107 测绿，含收益门三档对照/有界窗/门出），I02 门差分由 Surface-2 选择面实证；
- 但它**是**「当前 L1 harness 无法对四臂 C/D 产生决策级激励差分」的证据。四臂协议若要在 L1 层产生 C/D 差分，需要 harness 世界产生「无收益 patch 会自动激活」或「context_pack 进入决策回路」的形态——前者属注入不利刺激（有合成针对性强加给被评对象之嫌，本卡不做），后者属 harness 结构扩展（超出本验证卡差量）。
- 后续路径：C/D 的决策级差分判定在 L2（live model 走真实 context_pack 装配链）进行——即 BLOCKED 解除后的第一优先。

## 3. holdout 生成者与实现者未会话隔离（单会话现实，缓解措施在案）

协议要求测试生成者与实现者隔离、holdout 集冻结前不存在。本卡为单 agent 会话：生成规则（种子化 vocabulary 抽样）与 runner 同 commit 提交，seed 显式（20260928 主判定/20260929 敏感性），冻结清单先于 holdout 生成落盘（`--phase freeze` 与 `--phase holdout` 分离调用）；但生成规则的可读性隔离（实现者不可见）未达成。缓解：生成规则是声明式 vocabulary 抽样（非对被评机制调参）、不读 hidden truth 之外的任何实现内部、AUT 输入只有词牌话语与授权历史（用户模拟器 truthful 回答沿 A-08 既有规则）。审查若判隔离不足，重跑成本=单命令（种子在案）。

## 4. 效应量落在噪声域；A−B 符号跨集不稳定

A−B resolve-rate：dev −3.3pp / s1 +3.3pp CI[-4.2,+10.8] / s2 +5.8pp CI[-2.5,+15.0]——符号不稳定、CI 全部跨 0；冻结 utility（A−B）两 seed 稳定为负（-1.25/-1.82，CI 不跨 0）。本卡**不宣称**任何方向的净收益；反例的「记忆面净贡献未证明为正」在 L1 维持。样本量（30 profile/臂/seed）对 +10pp 量级的检验力不足——即使点估计方向有利也不构成翻案证据。

## 5. 冻结反例「可翻条件」未满足，反例保持 OPEN

B03 冻结行翻案条件=「修后重跑在冻结 utility 下 full−no_memory≥+10pp」。当前 SHA 复跑=精确复现原值（−10pp），四臂新 holdout 亦无满足该条件的形态。反例状态保持 OPEN_AS_V4_BASELINE；Q04 首轮数字仍 NOT_REMEASURED（非本卡范围）。

## 6. 复现的三类记录级分歧已声明但值得后续跟进

a) `friction_diagnosis_version` v1_2→v1_3：冻结后诊断引擎版本推进（含 342 行 diff）——聚合行为面逐数不变，但该版本 bump 的独立评审归其实现卡；b) applied 归因收窄（I05 对齐 FIX-67）：已修正的归因缺陷，方向检查实证只收窄；c) 随机 UUID 盐：固有。三者在 `reproduce_counterexample.py` 中以归一化+方向检查固化，任何超出这三类的未来分歧将使复现判红。

## 7. 选择面场景为 B03 CTX 族的实现化种子（非 CTX 全量覆盖）

Surface-2 九场景对应 CTX-01..08+正例；ctx04（否认旧画像）在选择面只覆盖 conflict_penalty 计量，否认全语义（deny-quiet/conflict resolver）归既有权威，本卡不重建；LAT 族（速度/成本 4 对）需 live 栈，全部落在 L2 BLOCKED；COR 族（纠正通路 8 对）主属 Q03 范围。CTX 族的「同项目示例偏好」等语义以种子行近似（summary/tag 显式在 `q02_surface2.py`），非生产数据。

## 8. 双 seed 敏感性=生成 seed，非运行噪声

两次 seed 检查改变的是 holdout 生成的抽样形态（profile 构成）；同一 seed 内运行全确定性（PYTHONHASHSEED=0、受控时钟、隔离世界）。协议原文的「两次 seed 检查敏感性」按此口径执行。

## 9. 环境性事实

- worktree 无未跟踪生成物可拷（`backend/app/gen` 从主检出复制后测试可跑；gen 产物 gitignore 不入 commit）。
- LLM Provider 初始化 ERROR 日志（dashscope key 空）为隔离环境预期噪声——零请求发出，全链确定性。
- 运行产物在 `v4/evidence/V4-Q02/runs/`（gitignore）；判据以脚本+种子+`artifacts_sha256.json` 为准，重跑可复现。
