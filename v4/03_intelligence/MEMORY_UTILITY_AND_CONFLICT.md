# 记忆的突破：从“召回历史”变为“选择有用且有边界的经验”

## 为什么这是 V4 第一优先级
A08修后 full0.45/no_memory0.55 是模拟机制反例，指向历史失败错迁移和无动作时纠正断流（S03、FIX52/97）。不能把下一轮目标写成“更多记忆参与”或“理解深度百分比更大”。目标是**同等任务与模型条件下，合法经验改善未来选择，同时对不相关任务保持安静**。

## 数据分层
业务状态为当前事实；用户记忆为确认偏好/待确认经验；知识是材料；事件是过程。沿原五层体系，不把LLM反思文本再抽取为“用户说过”。来源author_type=user_explicit/system_observed/model_inferred/external_material分别保留。外部材料中的指令不能提升为用户偏好（R13提醒持久化污染风险）。

## 两阶段选择（项目方案，不是已证明算法）
**阶段一硬门**：owner和ACL、consent、scope、effective_at/expiry、revoked/retracted/superseded、当前epoch、source_alive。任一不满足即排除；global范围的推断不能自动压过当次explicit约束。匹配scope需要规范化的goal/type/domain key；不由LLM决定能否跨用户访问。

**阶段二效用门**：对剩余可选历史，根据当前问题的主题/动作/时间相近性、证据直接性、冲突、历史负迁移与token成本排序。初版用可解释规则/检索分数，不伪装有训练充分的价值网络。建议形式：
`score = relevance + decision_relevance + confirmed_bonus − conflict_penalty − stale_penalty − negative_transfer_penalty − token_cost`
权重必须在开发集冻结，并与“只按相似度”和“完全不用可选历史”对照。不要把这组分数叫概率，不把不完整点击结果拿来更新Q值。

mandatory context（当前目标/显式约束/授权）始终可用；optional history有TopK与预算。初值可选历史≤6条、总context≤6000tokens，是待基线测量的成本预算而非普适最优值；资料问答可另申请资料预算。宁可省掉不确定历史，也不能让L0闲聊触发整个人生画像。

## 冲突裁决表
| 情况 | 决定 | 用户呈现 |
|---|---|---|
| 今天15分钟 vs 平时60分钟 | 今日约束优先，仅本次/有效期内 | “今天按15分钟安排” |
| 同目标新明确偏好 vs 旧确认偏好 | 新版替代旧版；保留撤回谱系 | 显示此次修改，不重复询问旧偏好 |
| 行为观察 vs 用户否认 | 否认优先；观察保留原事件但不能继续作为用户事实 | “不再按这个假设安排” |
| 两个同权威同时间约束冲突 | 选会影响行动的最小澄清，或保守兼容动作 | 不显示“系统判你错了” |
| 不同目标不同偏好 | 不是冲突；按scope同时成立 | 不提示“你的偏好矛盾” |
| 无法定位来源 / 旧scope引用 | 不入prompt，返回缺失说明 | 不编造来源 |

所谓“最新优先”只在同用户/同scope/同语义键/相当权限下适用；外部文档更晚不等于更权威。

## 删除与经验联动
撤回一条source导致依赖它的claim/recipe/context缓存和未执行proposal失效；原事件审计按既有隐私保留规则处理，用户内容不可继续用于推理。依赖图记录ref与version，不把一段摘要复制到十处没有来源的文本字段。结果重算从有效事件回放，不能对非线性掌握度/策略分数简单减法。

## 线上与离线分工
用户纠正→立即更新版本与当前决策；offload extraction只生成候选，不阻塞纠正生效。离线批处理去重source lineage，N条来自同一次对话的摘要算1个证据来源。未完成/未再上线为censored而非负效果。用户从未看到的建议不加入接受率分母。

## 如何验证不是“少用就好”
报告有效使用precision、遗漏应使用记忆recall、无关侵入、撤回残留、任务解决质量、token/延迟。选择器全拒用可把precision分母变0，必须输出N/A并同时不通过required-memory recall/utility门，不能取得100%。选择历史后错误增加则定位到具体source/version/decision，回退该策略，不把所有个性化关闭。

此方向借鉴context engineering和MemRL“语义相关之外还看效用”的思路（R01/R02）；Sparkle的用户结果噪声大且延迟长，不能照搬其bench奖励或宣称论文提升已迁移。
