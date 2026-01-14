import httpx
from loguru import logger
from google.protobuf import json_format

from app.config import settings
from app.gen.sparkle.signals.v1 import signals_pb2


class GatewayClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or settings.GATEWAY_URL).rstrip("/")
        self.api_key = api_key or settings.INTERNAL_API_KEY

    async def push_next_actions(self, candidate_set: signals_pb2.NextActionsCandidateSet) -> bool:
        if not candidate_set.user_id:
            logger.warning("Skipping push: missing user_id")
            return False
        payload = {
            "user_id": candidate_set.user_id,
            "request_id": candidate_set.request_id,
            "trace_id": candidate_set.trace_id,
            "schema_version": candidate_set.schema_version,
            "candidate_set": json_format.MessageToDict(
                candidate_set,
                preserving_proto_field_name=True,
                including_default_value_fields=False,
            ),
        }
        headers = {}
        if self.api_key:
            headers["X-Internal-API-Key"] = self.api_key
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.base_url}/internal/signals/push",
                    json=payload,
                    headers=headers,
                )
            if resp.status_code >= 300:
                logger.warning("Gateway push failed: %s %s", resp.status_code, resp.text)
                return False
        except Exception as exc:
            logger.warning(f"Gateway push failed: {exc}")
            return False
        return True
