import asyncio
import uuid
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.services.personalization import get_personalization_engine
from app.orchestration.prompts import build_system_prompt
from app.core.cache import cache_service
import redis.asyncio as redis

async def verify():
    # 1. Setup
    user_id = uuid.UUID("006848e2-7961-4e46-a72c-375749013d0e")
    
    import os
    db_url = os.environ["DATABASE_URL"]
    redis_url = os.environ["REDIS_URL"]
    
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Setup Redis for cache_service
    r = redis.from_url(redis_url)
    cache_service.redis = r
    
    async with async_session() as session:
        # 2. Initial State Check
        p_engine = get_personalization_engine(session, r)
        llm_profile = await p_engine.get_llm_profile(user_id)
        print("--- INITIAL LLM PROFILE ---")
        print(f"Temperature: {llm_profile.temperature}")
        print(f"Verbosity: {llm_profile.verbosity_target}")
        
        # 3. Simulate UI Update (Update DB + Invalidate Cache)
        print("\n--- SIMULATING UI UPDATE (Depth -> 0.9, Persona -> Anime) ---")
        # Update UserPreferencesCenter
        await session.execute(text("""
            UPDATE user_preferences_center 
            SET explicit = jsonb_set(jsonb_set(explicit, '{depth_preference}', '0.9'), '{persona_type}', '"anime"'),
                version = version + 1,
                last_explicit_update = now()
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        await session.commit()
        
        # Invalidate Cache
        keys_to_del = [
            f"user:prefs:center:{user_id}",
            f"user:context:{user_id}",
            f"user:context:snapshot:{user_id}"
        ]
        await r.delete(*keys_to_del)
        print(f"Deleted cache keys: {keys_to_del}")
        
        # 4. Verify AI System Recognizes Change
        # Use a new session to ensure fresh data
        async with async_session() as session2:
            p_engine_new = get_personalization_engine(session2, r)
            llm_profile_new = await p_engine_new.get_llm_profile(user_id)
            
            print("\n--- NEW LLM PROFILE ---")
            print(f"Temperature: {llm_profile_new.temperature}")
            print(f"Verbosity: {llm_profile_new.verbosity_target}")
            
            # Verify Prompt Generation (Mocking context to bypass DB errors)
            mock_user_context = {
                "user_context": {"nickname": "SparkleTester"},
                "preferences": {"depth_preference": 0.9, "curiosity_preference": 0.5},
                "llm_profile": {
                    "system_prompt_additions": llm_profile_new.system_prompt_additions,
                    "verbosity_target": llm_profile_new.verbosity_target,
                    "temperature": llm_profile_new.temperature,
                }
            }
            
            sys_prompt = build_system_prompt(mock_user_context)
            
            print("\n--- GENERATED SYSTEM PROMPT (Personalization Section) ---")
            if "## 用户偏好适配指令" in sys_prompt:
                start = sys_prompt.find("## 用户偏好适配指令")
                print(sys_prompt[start:start+400])
            else:
                print("Error: Personalization section not found in prompt!")

    await engine.dispose()
    await r.aclose()

if __name__ == "__main__":
    asyncio.run(verify())
