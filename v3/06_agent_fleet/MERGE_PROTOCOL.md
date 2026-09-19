# Merge Protocol

- 一任务一 branch/worktree；
- 开始记录 base SHA；
- contract/schema 变更优先小 PR 先合并；
- generated files 通过官方 generator；
- rebase current integration before review；
- Reviewer 证据对应 rebased SHA；
- merge 后运行 card integration_checks；
- 若 integration red，任务回 CHANGES，不算 DONE；
- 对同一 DB/API/Memory semantics 不允许“最后解决冲突”；应提前串行 contract，随后并行实现。
