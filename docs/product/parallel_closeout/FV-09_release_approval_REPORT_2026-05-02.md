# FV-09 · Release Approval Workflow Report · 2026-05-02

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 新建 release approval 状态机 | Done | `backend/app/services/release_approval.py:25` defines draft -> pending_review -> approved/rejected -> applied; service transition methods start at `backend/app/services/release_approval.py:118`. |
| 2 | c20 release approvals 迁移 | Done | `backend/alembic/versions/c20_20260502_release_approvals.py:31` creates `release_approval_requests` with status/category checks and indexes. |
| 3 | 覆盖适用对象 | Done | `backend/app/services/release_approval.py:33` defines policy publish, experiment promote, skill systemize, domain pack release, kill switch promote, and high risk config categories. |
| 4 | 审批人配置 | Done | `backend/app/config/settings.py:378` adds `RELEASE_APPROVERS_BY_CATEGORY`; service resolves category and wildcard approvers at `backend/app/services/release_approval.py:340`. |
| 5 | 双人审批强制 | Done | `backend/app/services/release_approval.py:42` marks policy_publish, experiment_promote, and skill_systemize as two-approval categories. |
| 6 | API CRUD + approve/reject | Done | `backend/app/api/v1/release_approvals.py:89` exposes create/list/get/update/delete plus submit, approve, reject, and apply endpoints. |
| 7 | 简化 admin UI | Done | `backend/app/api/v1/release_approvals.py:130` exposes an escaped HTML admin tab fragment with red-dot metadata. `admin_dashboard.py` was not directly modified because the FV-09 exclusive file list omitted it. |
| 8 | 通知集成 | Done | `backend/app/services/release_approval.py:399` creates admin notifications and sends approval emails through the existing email service when enabled. |
| 9 | 单测 + 集成测 | Partial | `backend/tests/unit/test_release_approval_service.py:35` covers state machine, two-person approval, self-approval block, rejection, kill-switch validation, and notification creation. Pytest collection is currently blocked by unrelated `community_privacy.py` metadata naming error. |

## 2. 文件变更清单

```
backend/app/services/release_approval.py                         new, 480 lines
backend/app/api/v1/release_approvals.py                          new, 242 lines
backend/alembic/versions/c20_20260502_release_approvals.py        new, 111 lines
backend/tests/unit/test_release_approval_service.py               new, 141 lines
backend/app/api/v1/router.py                                      append release_approvals import/include
backend/app/config/settings.py                                    append RELEASE_APPROVERS_BY_CATEGORY
```

Note: `router.py` and `settings.py` already contain unrelated dirty hunks from other FV work in this shared workspace; FV-09 only appended the release approval router/config lines.

## 3. 测试证据

### 单测

```
$ cd backend && pytest tests/unit/test_release_approval_service.py -q
ImportError while loading conftest '/Users/brsama/code/GitHub/Sparkle-project/backend/tests/conftest.py'.
...
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

Blocker source: unrelated untracked `backend/app/models/community_privacy.py` imported from `app/models/__init__.py`.

### 集成测

```
$ cd backend && alembic heads
...
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

Alembic is blocked by the same unrelated model import before it can enumerate heads.

### Lint / 类型 / Guard

```
$ python3 -m py_compile backend/app/services/release_approval.py backend/app/api/v1/release_approvals.py backend/tests/unit/test_release_approval_service.py backend/alembic/versions/c20_20260502_release_approvals.py
# PASS

$ cd backend && ruff check app/services/release_approval.py app/api/v1/release_approvals.py tests/unit/test_release_approval_service.py alembic/versions/c20_20260502_release_approvals.py
All checks passed!
```

## 4. 用户视角变化

> In the admin release flow, operators can now create a release approval request for high-risk Sparkle changes, see it in the admin queue, require the configured reviewers, and record approval/rejection before applying it.

具体场景：
- 之前：policy, experiment, skill, DomainPack, and kill-switch promotions had no shared governance workflow.
- 之后：these promotions can create a durable request, notify admins, enforce one- or two-person review, and expose pending counts for the admin dashboard red dot.

## 5. 与其他卡片的协调

- 与 FV-01/FV-02/FV-04：their promotion endpoints can create requests through `ReleaseApprovalService.create_request(...)` once their endpoints are merged.
- 与 FV-08：approval endpoints are superuser-only and ready for the admin-audit decorator once FV-08's middleware lands.
- 与 Architect：merge the `router.py` and `settings.py` append-only hunks carefully because this workspace has concurrent FV changes in the same files.
- 与 admin dashboard：direct `admin_dashboard.py` editing was skipped to respect FV-09's exclusive file list; `/api/v1/release_approvals/admin-tab` provides the HTML fragment and red-dot data.

## 6. 已知限制 / 后续

- No production callback mutates policy/experiment/skill/domain-pack systems yet; `apply` records the approved application. Dependent FV endpoints should call it after their own guarded application succeeds.
- Local pytest and Alembic verification are blocked by unrelated `community_privacy.py` using reserved SQLAlchemy attribute `metadata`.
- `c20_20260502` currently revises `c12_20260502`; Architect should decide final merge revision ordering once FV-01..08 migrations are consolidated.

## 7. 验收命令一键回放

```bash
python3 -m py_compile backend/app/services/release_approval.py backend/app/api/v1/release_approvals.py backend/tests/unit/test_release_approval_service.py backend/alembic/versions/c20_20260502_release_approvals.py
cd backend && ruff check app/services/release_approval.py app/api/v1/release_approvals.py tests/unit/test_release_approval_service.py alembic/versions/c20_20260502_release_approvals.py
cd backend && pytest tests/unit/test_release_approval_service.py -q
cd backend && alembic heads
```
