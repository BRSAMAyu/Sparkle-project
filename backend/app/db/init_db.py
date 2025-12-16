"""
Database Initialization
初始化数据库数据
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserRegister
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


async def init_db(db: AsyncSession) -> None:
    """
    Initialize database with initial data
    """
    # Create initial user if table is empty
    # For now, we just check if the specific admin user exists
    
    admin_email = "admin@sparkle.com"
    user = await UserService.get_by_email(db, email=admin_email)
    
    if not user:
        user_in = UserRegister(
            username="admin",
            email=admin_email,
            password="sparkle_admin",
            nickname="Admin",
        )
        user = await UserService.create(db, user_in)
        logger.info(f"Created initial user: {user.email}")
    else:
        logger.info(f"Initial user {admin_email} already exists")
