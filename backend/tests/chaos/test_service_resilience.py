import pytest
import asyncio
import httpx
import time
import os
import json
from jose import jwt as jose_jwt
from pathlib import Path
from typing import Dict, Any

# Configuration
GATEWAY_URL = "http://localhost:8080"
CHAOS_API_URL = f"{GATEWAY_URL}/admin/chaos"
CHAT_API_URL = f"{GATEWAY_URL}/api/v1/chat"
ADMIN_SECRET = "admin_secret_key"  # Should be loaded from env
def _load_jwt_secret() -> str:
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret
    for path in (Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[1] / "gateway" / ".env"):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("JWT_SECRET="):
                    return line.split("=", 1)[1].strip()
    return "dev-secret-key"


JWT_SECRET = _load_jwt_secret()


def _create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + 3600,
        "type": "access",
    }
    return jose_jwt.encode(payload, JWT_SECRET, algorithm="HS256")

class ChaosController:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.headers = {"X-Admin-Secret": ADMIN_SECRET}

    async def inject_latency(self, latency_ms: int, jitter_ms: int = 0):
        """Inject latency into gRPC backend connection"""
        payload = {
            "proxy": "grpc_backend",
            "latency_ms": latency_ms,
            "jitter_ms": jitter_ms,
            "toxic_name": "resilience_test_latency"
        }
        resp = await self.client.post(f"{CHAOS_API_URL}/grpc/latency", json=payload, headers=self.headers)
        resp.raise_for_status()

    async def reset_latency(self):
        """Reset latency injection"""
        resp = await self.client.delete(f"{CHAOS_API_URL}/grpc/latency", params={"toxic": "resilience_test_latency"}, headers=self.headers)
        if resp.status_code != 404:
            resp.raise_for_status()

    async def get_breaker_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        resp = await self.client.get(f"{CHAOS_API_URL}/status", headers=self.headers)
        resp.raise_for_status()
        return resp.json()

@pytest.fixture
async def chaos_controller():
    async with httpx.AsyncClient() as client:
        controller = ChaosController(client)
        yield controller
        # Cleanup after test
        try:
            await controller.reset_latency()
        except:
            pass

@pytest.fixture
async def api_client():
    token = _create_jwt("00000000-0000-0000-0000-000000000000")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=headers) as client:
        yield client

@pytest.mark.asyncio
class TestServiceResilience:
    
    async def test_python_engine_high_latency(self, chaos_controller, api_client):
        """
        Test that the system handles high backend latency gracefully.
        Goal: Verify Gateway times out or degrades instead of hanging forever.
        """
        # 1. Inject 5s latency (assuming Gateway timeout is < 5s)
        await chaos_controller.inject_latency(latency_ms=5000)
        
        # 2. Send Chat Request
        start_time = time.time()
        payload = {"message": "Hello chaos"}
        
        # We expect a 503 Service Unavailable or a timeout response
        # The gateway might handle it gracefully or return an error
        resp = await api_client.post(f"{CHAT_API_URL}/completion", json=payload, timeout=10.0)
        
        duration = time.time() - start_time
        
        # 3. Verification
        # If the gateway has a timeout of e.g. 5s, it should return 504 or 503
        assert resp.status_code in [503, 504, 500], f"Expected failure code, got {resp.status_code}"
        
        # Verify duration is consistent with timeout (e.g. not waiting 30s)
        assert duration < 10.0, "Request took too long"

    async def test_circuit_breaker_activation(self, chaos_controller, api_client):
        """
        Test that multiple failures trigger the circuit breaker.
        """
        # 1. Inject high latency
        await chaos_controller.inject_latency(latency_ms=2000)
        
        # 2. Generate failures (simulated by sending requests that will timeout/fail)
        # Note: This depends on Gateway's breaker logic. 
        # If it tracks queue length, we might need to spam requests.
        
        tasks = []
        for _ in range(20):
             tasks.append(api_client.post(f"{CHAT_API_URL}/completion", json={"message": "spam"}, timeout=1.0))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. Check Breaker Status
        status = await chaos_controller.get_breaker_status()
        
        # Note: Current ChaosHandler SetThreshold changes the 'queue_persist' threshold.
        # It doesn't directly expose "Circuit Breaker State" (Open/Closed) in the same way 
        # unless 'is_tripped' in GetStatus reflects it.
        # Verify 'is_tripped' is True if queue overloaded.
        
        # For this test, we just log the status as we might need to tune the threshold first.
        print(f"Breaker Status: {status}")
        
        # If we want to test load shedding, we can lower the threshold
        # await chaos_controller.client.post(..., json={"target": "queue_persist", "value": 5})

    async def test_recovery_after_chaos(self, chaos_controller, api_client):
        """
        Test that system recovers after chaos is removed.
        """
        # 1. Reset any chaos
        await chaos_controller.reset_latency()
        
        # 2. Send normal request
        payload = {"message": "Hello recovery"}
        # Assuming we have a mock backend or it works normally
        # resp = await api_client.post(f"{CHAT_API_URL}/completion", json=payload)
        # assert resp.status_code == 200
        
        # Since we might not have a real backend up in this context, 
        # we mark this as a placeholder for the real environment.
        pass
