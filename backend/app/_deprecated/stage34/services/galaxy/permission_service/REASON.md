# galaxy/permission_service.py

- Stage 34 disposition: archived as orphan service.
- Reason: nested galaxy permission helper had no runtime import path and duplicated the surviving top-level `permission_service.py`.
- Replacement: `backend/app/services/permission_service.py`.
- Removal earliest: after community/galaxy permission boundaries are re-validated.
