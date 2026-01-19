import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add backend to path to import models if needed, but let's just use raw SQL for simplicity and speed
# to avoid complex import issues.

async def create_user():
    engine = create_async_engine('postgresql+asyncpg://postgres:password@127.0.0.1:5432/sparkle')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    user_id = uuid.uuid4()
    username = "testuser"
    email = "test@example.com"
    password_hash = "fake_hash" # For testing, we don't need real password check for manual token generation
    
    async with async_session() as session:
        # Create user
        await session.execute(text("""
            INSERT INTO users (id, username, email, hashed_password, is_active, created_at, updated_at, flame_level, flame_brightness, depth_preference, curiosity_preference, registration_source, age_verified)
            VALUES (:id, :username, :email, :password_hash, true, now(), now(), 1, 0.5, 0.5, 0.5, 'email', false)
        """), {
            "id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash
        })
        
        # Create push preference
        await session.execute(text("""
            INSERT INTO push_preferences (id, user_id, timezone, enable_curiosity, persona_type, daily_cap, created_at, updated_at)
            VALUES (:id, :user_id, 'Asia/Shanghai', true, 'coach', 5, now(), now())
        """), {
            "id": uuid.uuid4(),
            "user_id": user_id
        })
        
        # Create user preferences center (the new table)
        await session.execute(text("""
            INSERT INTO user_preferences_center (id, user_id, version, schema_version, explicit, inferred, created_at, updated_at)
            VALUES (:id, :user_id, 1, 1, '{"depth_preference": 0.5, "curiosity_preference": 0.5, "persona_type": "coach"}', '{}', now(), now())
        """), {
            "id": uuid.uuid4(),
            "user_id": user_id
        })
        
        await session.commit()
        print(f"USER_ID:{user_id}")
        print(f"USERNAME:{username}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_user())
