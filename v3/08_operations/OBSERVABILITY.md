# Observability

## Trace spine
一个 user action 分配 trace_id，贯穿 Flutter event → Gateway → gRPC → Context Compiler → Aurora → LLM → tool/run → DB receipt → UI。

## Dashboards
- journey success/error；
- latency by cognition tier/provider；
- model fallback/429/error；
- Context candidate/filter/token；
- Memory use/reject/overpersonalization；
- Agent runs by state；
- proactive accepted/dismissed/muted；
- WVPL pipeline；
- cost/WVPL；
- queue depth/Celery health；
- restore storm indicators。

## Logging
PII/Memory 内容默认不进结构化日志；使用 IDs / hashes / classes。
