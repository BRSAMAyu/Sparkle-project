"""
Unit tests for app.services.user_service module.
Tests user CRUD operations, caching, and preferences.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import UserRegister


class TestUserServiceInit:
    """Test UserService initialization"""

    def test_init_with_redis(self):
        """Test initialization with Redis client"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        service = UserService(mock_db, mock_redis)

        assert service.db is mock_db
        assert service.redis is mock_redis
        assert service.cache_ttl == 1800

    def test_init_without_redis(self):
        """Test initialization without Redis client"""
        mock_db = AsyncMock()

        service = UserService(mock_db, redis_client=None)

        assert service.db is mock_db
        assert service.redis is None


class TestGetByEmail:
    """Test get_by_email static method"""

    @pytest.mark.asyncio
    async def test_get_existing_user_by_email(self):
        """Test getting existing user by email"""
        mock_db = AsyncMock()
        mock_user = Mock()
        mock_user.email = "test@example.com"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await UserService.get_by_email(mock_db, "test@example.com")

        assert result is mock_user
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_by_email(self):
        """Test getting nonexistent user returns None"""
        mock_db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await UserService.get_by_email(mock_db, "nonexistent@example.com")

        assert result is None


class TestCreateUser:
    """Test create user method"""

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Test successful user creation"""
        mock_db = AsyncMock()

        user_in = UserRegister(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!",
            nickname="Test User"
        )

        # Mock database operations
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch('app.services.user_service.get_password_hash') as mock_hash:
            mock_hash.return_value = "hashed_password"

            user = await UserService.create(mock_db, user_in)

            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.registration_source == "email"
            assert user.is_active is True
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_without_nickname(self):
        """Test creating user without nickname uses username"""
        mock_db = AsyncMock()

        user_in = UserRegister(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!"
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch('app.services.user_service.get_password_hash') as mock_hash:
            mock_hash.return_value = "hashed_password"

            user = await UserService.create(mock_db, user_in)

            # Should use username as nickname
            assert user.nickname == "testuser"

    @pytest.mark.asyncio
    async def test_create_user_password_hashed(self):
        """Test that password is hashed during creation"""
        mock_db = AsyncMock()

        user_in = UserRegister(
            username="testuser",
            email="test@example.com",
            password="plain_password"
        )

        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch('app.services.user_service.get_password_hash') as mock_hash:
            mock_hash.return_value = "hashed_password"

            user = await UserService.create(mock_db, user_in)

            # Password should be hashed, not stored plain
            mock_hash.assert_called_once_with("plain_password")
            assert user.hashed_password == "hashed_password"


class TestGetUserById:
    """Test get_user_by_id method"""

    @pytest.mark.asyncio
    async def test_get_user_by_id_from_cache(self):
        """Test getting user from cache"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        # Mock cache hit
        user_id = uuid4()
        cached_user = {"id": str(user_id), "email": "test@example.com"}
        mock_redis.get.return_value = cached_user.encode()

        service = UserService(mock_db, mock_redis)
        result = await service.get_user_by_id(user_id)

        # Should not query DB
        mock_db.execute.assert_not_called()
        # Should hit cache
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_id_cache_miss_db_hit(self):
        """Test getting user from DB after cache miss"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        user_id = uuid4()
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"

        # Mock cache miss
        mock_redis.get.return_value = None

        # Mock DB hit
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        # Mock cache set
        mock_redis.set.return_value = None

        service = UserService(mock_db, mock_redis)
        result = await service.get_user_by_id(user_id)

        assert result is mock_user
        mock_db.execute.assert_called_once()
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self):
        """Test getting nonexistent user returns None"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        user_id = uuid4()

        # Mock cache miss
        mock_redis.get.return_value = None

        # Mock DB miss
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = UserService(mock_db, mock_redis)
        result = await service.get_user_by_id(user_id)

        assert result is None


class TestUserPreferences:
    """Test user preferences methods"""

    @pytest.mark.asyncio
    async def test_update_user_preferences(self):
        """Test updating user preferences"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        user_id = uuid4()
        preferences = {"theme": "dark", "language": "zh"}

        # Mock DB update
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None

        # Mock cache invalidation
        mock_redis.delete.return_value = 1

        service = UserService(mock_db, mock_redis)

        with patch.object(service, '_invalidate_user_cache') as mock_invalidate:
            await service.update_user_preferences(user_id, preferences)

            mock_db.execute.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_invalidate.assert_called_once_with(user_id)


class TestCacheInvalidation:
    """Test cache invalidation"""

    @pytest.mark.asyncio
    async def test_invalidate_user_cache(self):
        """Test user cache invalidation"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        user_id = uuid4()
        mock_redis.delete.return_value = 1

        service = UserService(mock_db, mock_redis)
        await service._invalidate_user_cache(user_id)

        mock_redis.delete.assert_called_once()
        # Verify cache key pattern
        call_args = mock_redis.delete.call_args[0][0]
        assert "user" in call_args
        assert str(user_id) in call_args


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_get_by_email_db_error(self):
        """Test get_by_email handles DB errors gracefully"""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB connection failed")

        with pytest.raises(Exception):
            await UserService.get_by_email(mock_db, "test@example.com")

    @pytest.mark.asyncio
    async def test_create_user_db_error(self):
        """Test create user handles DB errors"""
        mock_db = AsyncMock()
        mock_db.add.side_effect = Exception("Insert failed")

        user_in = UserRegister(
            username="testuser",
            email="test@example.com",
            password="password"
        )

        with pytest.raises(Exception):
            await UserService.create(mock_db, user_in)


class TestUserContext:
    """Test user context methods"""

    @pytest.mark.asyncio
    async def test_get_user_context(self):
        """Test getting user context with preferences"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        user_id = uuid4()
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"

        # Mock user retrieval
        with patch.object(UserService, 'get_user_by_id', return_value=mock_user):
            service = UserService(mock_db, mock_redis)
            context = await service.get_user_context(user_id)

            assert context is not None
            assert context.user_id == user_id
            assert context.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_context_user_not_found(self):
        """Test getting context for nonexistent user"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        user_id = uuid4()

        # Mock user not found
        with patch.object(UserService, 'get_user_by_id', return_value=None):
            service = UserService(mock_db, mock_redis)
            context = await service.get_user_context(user_id)

            assert context is None
