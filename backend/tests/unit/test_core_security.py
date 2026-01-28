"""
Unit tests for app.core.security module.
Tests password hashing, JWT token generation and validation.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from jose import JWTError

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    pwd_context
)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_returns_hash(self):
        """Test that password hashing returns a hash"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_hash_same_password_different_hashes(self):
        """Test that hashing same password twice produces different hashes (salt)"""
        password = "test_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different due to salt

    def test_verify_correct_password(self):
        """Test verifying correct password"""
        password = "correct_password"
        hashed = get_password_hash(password)

        result = verify_password(password, hashed)
        assert result is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        result = verify_password(wrong_password, hashed)
        assert result is False

    def test_verify_empty_password(self):
        """Test verifying empty password fails"""
        hashed = get_password_hash("some_password")

        result = verify_password("", hashed)
        assert result is False

    def test_hash_password_failure_raises(self):
        """Test that hashing failure raises ValueError"""
        with patch.object(pwd_context, 'hash', side_effect=Exception("Hash failed")):
            with pytest.raises(ValueError, match="Failed to hash password"):
                get_password_hash("test")

    def test_verify_password_exception_returns_false(self):
        """Test that verification exception returns False"""
        result = verify_password("test", "invalid_hash_format")
        assert result is False


class TestAccessTokenCreation:
    """Test JWT access token creation"""

    def test_create_access_token_default_expiry(self):
        """Test creating token with default expiry"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_custom_expiry(self):
        """Test creating token with custom expiry"""
        data = {"sub": "user123"}
        expiry = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expiry)

        assert token is not None

    def test_create_access_token_includes_required_claims(self):
        """Test that token includes required claims"""
        data = {"sub": "user123", "role": "user"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
        assert "type" in payload
        assert payload["type"] == "access"
        assert payload["sub"] == "user123"
        assert payload["role"] == "user"

    def test_create_access_token_expiration_time(self):
        """Test that token expiration is set correctly"""
        data = {"sub": "user123"}
        expiry = timedelta(minutes=15)
        before_creation = datetime.utcnow()

        token = create_access_token(data, expires_delta=expiry)

        after_creation = datetime.utcnow()
        payload = decode_token(token)

        # Check expiration is approximately 15 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        min_expected = before_creation + expiry
        max_expected = after_creation + expiry

        assert min_expected <= exp_time <= max_expected


class TestRefreshTokenCreation:
    """Test JWT refresh token creation"""

    def test_create_refresh_token(self):
        """Test creating refresh token"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_create_refresh_token_includes_correct_type(self):
        """Test that refresh token has correct type"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_create_refresh_token_longer_expiry(self):
        """Test that refresh token has longer expiry than access token"""
        data = {"sub": "user123"}

        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        # Refresh token should expire later than access token
        assert refresh_payload["exp"] > access_payload["exp"]


class TestTokenDecoding:
    """Test JWT token decoding"""

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "user123", "role": "admin"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"

    def test_decode_token_with_expected_type(self):
        """Test decoding token with type validation"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        payload = decode_token(token, expected_type="access")

        assert payload["type"] == "access"

    def test_decode_token_with_wrong_type_fails(self):
        """Test that wrong token type raises error"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        with pytest.raises(JWTError, match="Invalid token type"):
            decode_token(token, expected_type="refresh")

    def test_decode_invalid_token_raises(self):
        """Test that invalid token raises JWTError"""
        invalid_token = "invalid.token.string"

        with pytest.raises(JWTError):
            decode_token(invalid_token)

    def test_decode_token_missing_claims_raises(self):
        """Test that token without required claims raises error"""
        from jose import jwt

        # Create token without 'sub' claim
        token = jwt.encode(
            {"exp": 1234567890, "iat": 1234567800},
            "secret",
            algorithm="HS256"
        )

        with pytest.raises(JWTError, match="Token missing required claims"):
            decode_token(token)

    def test_decode_expired_token_raises(self):
        """Test that expired token raises error"""
        data = {"sub": "user123"}
        # Create token that expired 1 hour ago
        expiry = timedelta(hours=-1)
        token = create_access_token(data, expires_delta=expiry)

        with pytest.raises(JWTError):
            decode_token(token)


class TestTokenSecurity:
    """Test token security features"""

    def test_token_contains_unique_jti(self):
        """Test that each token has unique JTI (JWT ID)"""
        data = {"sub": "user123"}

        token1 = create_access_token(data)
        token2 = create_access_token(data)

        payload1 = decode_token(token1)
        payload2 = decode_token(token2)

        assert payload1["jti"] != payload2["jti"]

    def test_token_iat_is_set(self):
        """Test that token has issued-at time"""
        data = {"sub": "user123"}
        before_creation = datetime.utcnow()

        token = create_access_token(data)

        after_creation = datetime.utcnow()
        payload = decode_token(token)

        iat_time = datetime.fromtimestamp(payload["iat"])
        assert before_creation <= iat_time <= after_creation

    def test_different_users_different_tokens(self):
        """Test that different users get different tokens"""
        token1 = create_access_token({"sub": "user1"})
        token2 = create_access_token({"sub": "user2"})

        assert token1 != token2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_token_data(self):
        """Test creating token with minimal data"""
        token = create_access_token({})
        payload = decode_token(token)

        assert "sub" in payload  # Should be in payload

    def test_unicode_password(self):
        """Test password with unicode characters"""
        password = "密码🔒测试"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_very_long_password(self):
        """Test very long password"""
        password = "a" * 1000
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_token_with_additional_data(self):
        """Test token can carry additional data"""
        data = {
            "sub": "user123",
            "email": "user@example.com",
            "permissions": ["read", "write"],
            "metadata": {"key": "value"}
        }

        token = create_access_token(data)
        payload = decode_token(token)

        assert payload["sub"] == "user123"
        assert payload["email"] == "user@example.com"
        assert payload["permissions"] == ["read", "write"]
        assert payload["metadata"] == {"key": "value"}
