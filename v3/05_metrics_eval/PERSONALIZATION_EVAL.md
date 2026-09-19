# Personalization / Memory Evaluation

## Paired design
同一 current context 做 A/B：
A：允许使用合法历史；
B：同样当前事实但不提供个性化 history。
盲评哪一个 action 更适合，不把“多 token”误当个性化价值。

## Dimensions
- relevance
- scope correctness
- novelty/helpfulness
- over-personalization
- consistency with correction
- privacy
- decision utility

## Adversarial cases
- 喜好改变；
- today-only 约束；
- 观察与明确陈述冲突；
- 同名不同 goal；
- 删除后 prompt injection 诱导找回；
- 旧 document version；
- 多用户共享设备；
- repeatedly mentioned preference should not appear in every response。

## Target
有效使用 precision ≥95%；invalid memory use=0；overpersonalization≤5%；paired uplift +15pp 为目标，不达标报告真实结果。
