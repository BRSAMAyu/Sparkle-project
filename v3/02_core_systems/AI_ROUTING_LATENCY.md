# AI Routing / Latency / Cost V3

## Cognition Ladder
- L0 No Model：确定性逻辑；
- L1 Fast Semantic：轻分类/抽取/简单生成；
- L2 Deliberate Decision：复杂 friction / planning / conflict / action synthesis；
- L3 Agent Run：多步骤工具执行。

## 路由原则
按 capability + latency class + cost + current health 选，不按历史模型名硬编码。

当前快照：qwen3.8-flash 为各 tier 主力，thinking/计费差异；MiniMax M3 glm_batch 用于异步分析。V3 第一批必须 runtime probe 重新确认。

## Fast-first
简单消息不得因为隐藏分类/画像/RAG/反思被拖进深推理。首个可见状态尽快返回。

## Waiting UX
不展示内部 reasoning token。展示可验证阶段事件与真实 tool progress。

## Fallback
fallback 必须保持 required capability；如果结构化工具调用能力缺失，不得换成“会说话但不能执行”的模型后仍宣称成功。

## Observability
requested/actual provider+model/tier、reason、fallback、TTFT、total latency、input/output tokens、usage source、cost、error、quality eval。

## Cost Principle
优化 cost per valuable progress loop，而非 cost per chat。异步 batch 用于不需要实时的 reflection/aggregation。
