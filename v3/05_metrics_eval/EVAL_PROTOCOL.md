# V3 Evaluation Protocol

## 1. 四层评测
### L1 deterministic tests
schema / permission / TTL / scope / idempotency / state machine / cache epoch。
### L2 model offline eval
固定 scenarios + hidden expected rubric，重复多次统计稳定性。
### L3 simulator journeys
真实 app + 真 backend + 真模型，截图/录屏/日志关联。
### L4 longitudinal simulation
多天/多 session persona，产生矛盾、纠正、目标变化、删除、回归，评估 flywheel。

## 2. 不允许模型自评作为唯一证据
LLM-as-judge 可用于加速，但关键质量需 deterministic labels / cross-model review / behavior outcome 之一支持。

## 3. Repetition
随机模型路径至少 5 次/关键案例；否则不宣称稳定。

## 4. Regression
所有已修复 P0/P1 用户可见缺陷加入 journey 或 guard，防止 V3 重构复发。

## 5. Evidence bundle
每轮包含：git SHA、app build、server config snapshot、actual model、seed/persona、case IDs、screenshots/video、trace IDs、raw metrics、summary。
