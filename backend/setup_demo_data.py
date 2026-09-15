import asyncio
from datetime import datetime, timedelta
import random
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.db.session import Base
# from app.core.security import get_password_hash
from app.models import (
    User, Group, GroupType, GroupRole, GroupMember, 
    Friendship, FriendshipStatus, PrivateMessage, GroupMessage
)

def get_password_hash(password):
    # Hardcoded hash for "password" (bcrypt)
    return "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4hG5F9m7.q"

# Demo Data
USERS = [
    {"username": "demo", "nickname": "DemoUser", "role": "admin"},
    {"username": "alice", "nickname": "Alice Chen"},
    {"username": "bob", "nickname": "Bob Smith"},
    {"username": "charlie", "nickname": "Charlie Zhang"},
    {"username": "david", "nickname": "David Li"},
    {"username": "eve", "nickname": "Eve Wang"},
    {"username": "frank", "nickname": "Frank Zhou"},
    {"username": "grace", "nickname": "Grace Liu"},
    {"username": "heidi", "nickname": "Heidi Wu"},
    {"username": "ivan", "nickname": "Ivan Yang"},
    {"username": "judy", "nickname": "Judy Zhao"},
]

GROUPS = [
    {"name": "CS Study Squad", "desc": "Let's master CS!", "type": GroupType.SQUAD},
    {"name": "Flutter Learners", "desc": "Flutter is awesome.", "type": GroupType.SQUAD},
    {"name": "Python Enthusiasts", "desc": "Pythonic way.", "type": GroupType.SQUAD},
    {"name": "Final Exam Sprint", "desc": "Survive the finals.", "type": GroupType.SPRINT},
    {"name": "Algorithm Club", "desc": "LeetCode daily.", "type": GroupType.SQUAD},
]

async def setup_demo_data():
    print("Setting up demo data...")
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Create Tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create Users
        user_objs = {}
        for u in USERS:
            res = await db.execute(select(User).where(User.username == u["username"]))
            existing = res.scalar_one_or_none()
            if not existing:
                new_user = User(
                    username=u["username"],
                    email=f"{u['username']}@example.com",
                    hashed_password=get_password_hash("password"),
                    nickname=u["nickname"],
                    is_active=True,
                    flame_level=random.randint(1, 10),
                    flame_brightness=random.random()
                )
                db.add(new_user)
                await db.flush()
                await db.refresh(new_user)
                user_objs[u["username"]] = new_user
                print(f"Created user: {u['username']}")
            else:
                user_objs[u["username"]] = existing

        # Create Friendships (Demo User with everyone)
        demo_user = user_objs["demo"]
        friends = [u for k, u in user_objs.items() if k != "demo"]
        
        for friend in friends:
            # Standardize order
            u_id, f_id = demo_user.id, friend.id
            if str(u_id) > str(f_id): u_id, f_id = f_id, u_id
            
            res = await db.execute(select(Friendship).where(
                Friendship.user_id == u_id,
                Friendship.friend_id == f_id
            ))
            if not res.scalar_one_or_none():
                fs = Friendship(
                    user_id=u_id,
                    friend_id=f_id,
                    initiated_by=demo_user.id,
                    status=FriendshipStatus.ACCEPTED
                )
                db.add(fs)
        
        # Create Groups
        group_objs = []
        for g in GROUPS:
            res = await db.execute(select(Group).where(Group.name == g["name"]))
            existing = res.scalar_one_or_none()
            if not existing:
                new_group = Group(
                    name=g["name"],
                    description=g["desc"],
                    type=g["type"],
                    deadline=datetime.utcnow() + timedelta(days=30) if g["type"] == GroupType.SPRINT else None
                )
                db.add(new_group)
                await db.flush()
                await db.refresh(new_group)
                group_objs.append(new_group)
                print(f"Created group: {g['name']}")
                
                # Add Demo user as Owner/Admin
                member = GroupMember(
                    group_id=new_group.id,
                    user_id=demo_user.id,
                    role=GroupRole.OWNER
                )
                db.add(member)
                
                # Add random members
                for f in random.sample(friends, k=random.randint(3, 8)):
                    # Check if already member
                    res = await db.execute(select(GroupMember).where(
                        GroupMember.group_id == new_group.id,
                        GroupMember.user_id == f.id
                    ))
                    if not res.scalar_one_or_none():
                        m = GroupMember(
                            group_id=new_group.id,
                            user_id=f.id,
                            role=GroupRole.MEMBER
                        )
                        db.add(m)
            else:
                group_objs.append(existing)

        await db.commit()
        
        # Create Messages
        # Private Messages
        for friend in friends:
            # Demo -> Friend
            pm1 = PrivateMessage(
                sender_id=demo_user.id,
                receiver_id=friend.id,
                content=f"Hi {friend.nickname}, how are you?",
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24))
            )
            db.add(pm1)
            # Friend -> Demo
            pm2 = PrivateMessage(
                sender_id=friend.id,
                receiver_id=demo_user.id,
                content=f"I'm good! Working on Sparkle.",
                created_at=datetime.utcnow()
            )
            db.add(pm2)

        # Group Messages
        for group in group_objs:
            # Find members
            res = await db.execute(select(GroupMember).where(GroupMember.group_id == group.id))
            members = [m.user_id for m in res.scalars().all()]
            
            for _ in range(10):
                sender_id = random.choice(members)
                gm = GroupMessage(
                    group_id=group.id,
                    sender_id=sender_id,
                    content=f"This is a message in {group.name}",
                    created_at=datetime.utcnow() - timedelta(minutes=random.randint(1, 60))
                )
                db.add(gm)

        await db.commit()
        print("Demo data setup complete!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(setup_demo_data())
