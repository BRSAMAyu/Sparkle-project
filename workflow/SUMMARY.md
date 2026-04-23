# ISSUE 汇总索引

> 三专家共同维护的唯一事实表。每 ISSUE 一行。Auditor 创建时追加行；Fixer/Verifier 就地更新状态字段；任何人**不得删除**他人写的行（已关闭行 7 日后由 Verifier 归档到 `closed/ARCHIVE_<yyyymm>.md`）。

## 活动 ISSUE

| ID | Slice | P | Status | Title | Claimed | Updated |
|----|-------|---|--------|-------|---------|---------|
| ISSUE-20260424-001 | 01 | P1 | open | Go validateJWT 不检查 session_revoked:{sid}，设备下线不立即生效 | - | 19:05 |
| ISSUE-20260424-002 | 01 | P1 | open | AppleLogin UpdateUserLastLogin 和 UpsertUserSession 错误静默丢弃 | - | 19:05 |
| ISSUE-20260424-003 | 01 | P1 | open | Guest login 限流 100/15min 过于宽松，可被滥用刷号 | - | 19:05 |
| ISSUE-20260424-004 | 01 | P2 | open | Guest login SELECT-INSERT 竞态条件，并发同 guest_id 返回 500 | - | 19:05 |
| ISSUE-20260424-005 | 01 | P2 | open | AppleLogin 用户创建/链接竞态，无 IntegrityError 处理 | - | 19:05 |
| ISSUE-20260424-006 | 01 | P2 | open | Go/Python JWT issuer/audience claims 处理需验证一致性 | - | 19:05 |

## 最近 7 日已关闭（趋势观察）

| ID | Slice | P | Verdict | Closed |
|----|-------|---|---------|--------|
<!-- Verifier 判 PASS 后追加 -->

## 统计快照（Verifier 每轮 loop 更新一次）

- round 0 进行中
- open: 6
- verifying: 0
- closed (7d): 0
- escalated: 0
- last_update: 2026-04-24T19:10:00+08:00
- slice_01_audit: 3 P1 + 3 P2, anchors personally read (7 files, 6 grep queries)
