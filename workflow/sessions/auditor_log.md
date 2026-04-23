# Auditor Session Log

> 每次 loop 追加一段。最老的条目超过 14 日后可由自己归档到 `ARCHIVE_<yyyymm>.md`。

<!--
格式：
## <iso-timestamp> round=<r> slice=<NN-name>
- directives_read: [DIRECTIVE-... | none]
- produced: <n> issues  (P0=a P1=b P2=c P3=d)
- deferred: <m>         (超出单 loop 上限留到下轮)
- anchors_personally_read: [path:line, ...]
- grep_queries: [...]
- deviations: <偏离正常节奏的说明>
- next_cursor: <cursor+1>
- commit: <sha-workflow-only>
-->
