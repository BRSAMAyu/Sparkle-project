# AI-Opaque Data Sources

- `backend/app/models/notification_interaction.py`
  - Reason: interaction rows describe notification delivery behavior, not learner intent semantics.
- `backend/app/models/shop.py` (`PhotonTransactionHistory`)
  - Reason: photon economy/audit records are product transactions and should not be injected into prompt reasoning.
- `backend/app/models/visual_element.py` (`UserVisualElement`)
  - Reason: visual unlock/equipment state is cosmetic product state, not reliable cognitive evidence.

Stage 34 keeps these models intact, marks them explicitly as AI-opaque, and excludes them from new prompt/data wire-on work.
