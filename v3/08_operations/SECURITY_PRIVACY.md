# Security & Privacy V3

- tenant/user filter 在 retrieval 前；
- prompt injection 来自用户材料时不能升级 tool permission；
- tool capability allowlist；
- high-risk side effect explicit approval；
- memory sensitivity/purpose；
- document deletion tombstone+index removal；
- account switch clear local caches；
- export/delete journey；
- logs redact secrets/PII；
- SSRF allowlist 继续保留；
- Agent runtime budget/timeout；
- community authorization 独立于 personal memory；
- seed/demo namespace 隔离。

高风险任务必须两个独立 Reviewer。
