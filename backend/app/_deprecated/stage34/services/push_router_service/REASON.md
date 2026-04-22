# push_router_service.py

- Stage 34 disposition: archived as orphan service.
- Reason: standalone push router no longer had a live import path in the current notification pipeline.
- Replacement: the active notification / push delivery stack under `push_delivery_service.py` and related services.
- Removal earliest: after push architecture review confirms this legacy branch is fully retired.
