# Conflict Resolver — 多系统不再各说各话

## 1. 为什么需要
用户会改变；模块会有不同时间与证据；“今天只有20分钟”和“通常晚上能学习一小时”可以同时成立。冲突不能靠 context pack 裁剪顺序隐式解决。

## 2. Resolution Tuple
比较：
`(scope match, epistemic class, explicitness, recency, evidence strength, validity, user correction)`

## 3. 默认优先级
当前明确用户陈述/纠正
> 同 scope 更新的 confirmed preference
> verified current system fact
> confirmed older fact
> repeated outcome/observation
> single observation
> inference/hypothesis

但“scope 更匹配”可高于全局陈述。例如 today-only 时间约束不覆盖永久偏好。

## 4. 冲突类型
- TEMPORAL_CHANGE：偏好真的变了；
- SCOPE_DIFFERENCE：两个都真但范围不同；
- SOURCE_DISAGREEMENT：系统/用户来源冲突；
- INFERENCE_CONTRADICTION：推断与事实冲突；
- UNSAFE_AMBIGUITY：继续决策风险大。

## 5. 行为
- 自动 resolve：低风险且规则明确；
- ask once：用户答案会显著改变 decision；
- preserve both：scope 不同；
- revoke inference：明确事实反驳推断；
- abstain：高风险无法判断。

所有 resolution 产生记录，可用于 debug/eval，但不要求用户看到内部分数。
