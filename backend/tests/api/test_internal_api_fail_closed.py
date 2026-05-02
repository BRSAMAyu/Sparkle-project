from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.v1.files import verify_internal_token as verify_files_internal_token
from tests._credentials import TEST_INTERNAL_API_KEY


@pytest.mark.asyncio
async def test_files_internal_token_fails_closed_when_key_missing():
    with patch("app.api.v1.files.settings.INTERNAL_API_KEY", ""):
        with pytest.raises(HTTPException) as exc_info:
            await verify_files_internal_token(None)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Internal API key not configured"


@pytest.mark.asyncio
async def test_files_internal_token_rejects_wrong_secret():
    with patch("app.api.v1.files.settings.INTERNAL_API_KEY", TEST_INTERNAL_API_KEY):
        with pytest.raises(HTTPException) as exc_info:
            await verify_files_internal_token("wrong-key")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid internal token"
