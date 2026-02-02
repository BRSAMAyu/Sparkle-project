
import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def create_user():
    # 使用正确的数据库配置
    engine = create_async_engine('postgresql+asyncpg://postgres:change-me@sparkle_db:5432/sparkle')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    username = "debug_student_001"
    email = "debug_student_001@sparkle.com"
    password_hash = "$2b$12$x9pZqzpBzQFh.VdV61qxsuPDKnOThH825n8iVjNJCatsbAXI5mVNu" 
    
    async with async_session() as session:
        # 1. 获取或创建用户
        result = await session.execute(text("SELECT id FROM users WHERE username = :username"), {"username": username})
        user = result.fetchone()
        
        if user:
            user_id = user[0]
            await session.execute(text("DELETE FROM user_preferences_center WHERE user_id = :id"), {"id": user_id})
            await session.execute(text("DELETE FROM push_preferences WHERE user_id = :id"), {"id": user_id})
            await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        
        user_id = uuid.uuid4()
        # 创建用户 (所有 NOT NULL 字段)
        await session.execute(text("""
            INSERT INTO users (
                id, username, email, hashed_password, is_active, 
                created_at, updated_at, flame_level, flame_brightness, 
                depth_preference, curiosity_preference, registration_source, 
                age_verified, avatar_status, status, is_superuser, photon_balance
            )
            VALUES (
                :id, :username, :email, :password_hash, true, 
                now(), now(), 1, 0.5, 
                0.5, 0.5, 'email', 
                false, 'APPROVED', 'OFFLINE', false, 0
            )
        """), {
            "id": user_id, "username": username, "email": email, "password_hash": password_hash
        })
        
        # 创建推送偏好 (补全 consecutive_ignores)
        await session.execute(text("""
            INSERT INTO push_preferences (
                id, user_id, timezone, enable_curiosity, persona_type, 
                daily_cap, consecutive_ignores, created_at, updated_at
            )
            VALUES (:id, :user_id, 'Asia/Shanghai', true, 'coach', 5, 0, now(), now())
        """), {
            "id": uuid.uuid4(), "user_id": user_id
        })
        
        # 创建偏好中心
        await session.execute(text("""
            INSERT INTO user_preferences_center (
                id, user_id, version, schema_version, explicit, inferred, created_at, updated_at
            )
            VALUES (:id, :user_id, 1, 1, '{"depth_preference": 0.5, "curiosity_preference": 0.5, "persona_type": "coach"}', '{}', now(), now())
        """), {
            "id": uuid.uuid4(), "user_id": user_id
        })
        
        await session.commit()
        print(f"SUCCESS: Recreated user {username}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_user())
