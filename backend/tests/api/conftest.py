import pytest
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.vocabulary import router as vocabulary_router
from app.api.deps import get_current_user
from app.db.session import get_db


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(vocabulary_router, prefix="/vocabulary")

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    with TestClient(app) as test_client:
        yield test_client
