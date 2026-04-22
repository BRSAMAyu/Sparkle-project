# file_cascade_service.py

- Stage 34 disposition: archived as orphan service.
- Reason: legacy cascade delete helper was no longer imported by the active file pipeline.
- Replacement: current document/file flows own their own deletion logic.
- Removal earliest: after file lifecycle audit confirms no manual recovery is needed.
