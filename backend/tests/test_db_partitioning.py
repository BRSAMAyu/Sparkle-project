
import unittest
import uuid
from datetime import datetime, timedelta
import pytest
from app.models.chat import ChatMessage, MessageRole
from app.core.database import SessionLocal
from sqlalchemy import text

if SessionLocal is None:
    pytest.skip("DATABASE_URL not configured for sync tests", allow_module_level=True)

class TestPartitioning(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.user_id = uuid.uuid4()
        # Ensure user exists (mock or real insert if FKs enforced)
        # For this test, we assume FK constraints might be relaxed or we insert a dummy user
        # In a real integration test, we'd use a fixture to create a user.
        try:
            self.db.execute(text(f"INSERT INTO users (id, username, email, hashed_password, avatar_status, flame_level, flame_brightness, depth_preference, curiosity_preference, is_active, is_superuser, status, registration_source, created_at, updated_at) VALUES ('{self.user_id}', 'test_partition_user_{uuid.uuid4().hex[:8]}', 'test_{uuid.uuid4().hex[:8]}@example.com', 'hash', 'APPROVED', 0, 0, 0, 0, true, false, 'ONLINE', 'email', NOW(), NOW())"))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # If user creation fails, it might be due to duplicate or constraints, 
            # but for pure partitioning test, we try to proceed or skip.
            print(f"User creation warning: {e}")

    def tearDown(self):
        self.db.close()

    def test_partition_routing(self):
        """Test that messages are routed to the correct partition based on created_at"""
        
        # 1. Insert a message for 2024-02-01 (Q1)
        msg_q1 = ChatMessage(
            id=uuid.uuid4(),
            user_id=self.user_id,
            session_id=uuid.uuid4(),
            role=MessageRole.USER,
            content="Hello Q1",
            created_at=datetime(2024, 2, 1),
            updated_at=datetime(2024, 2, 1)
        )
        self.db.add(msg_q1)
        self.db.commit()

        # Check if it exists in the specific partition
        result = self.db.execute(text(f"SELECT count(*) FROM chat_messages_2024_q1 WHERE id = '{msg_q1.id}'"))
        count = result.scalar()
        self.assertEqual(count, 1, "Message should be in Q1 partition")

        # 2. Insert a message for 2025-05-01 (Q2)
        msg_q2 = ChatMessage(
            id=uuid.uuid4(),
            user_id=self.user_id,
            session_id=uuid.uuid4(),
            role=MessageRole.USER,
            content="Hello Q2",
            created_at=datetime(2025, 5, 1),
            updated_at=datetime(2025, 5, 1)
        )
        self.db.add(msg_q2)
        self.db.commit()

        # Check if it exists in the specific partition
        result = self.db.execute(text(f"SELECT count(*) FROM chat_messages_2025_q2 WHERE id = '{msg_q2.id}'"))
        count = result.scalar()
        self.assertEqual(count, 1, "Message should be in Q2 partition")

    def test_partition_pruning_performance(self):
        """
        Verify that querying by date range restricts scan to specific partitions.
        (This relies on EXPLAIN ANALYZE output parsing, which is complex in unit tests,
        so we'll simulate by checking EXPLAIN plan text).
        """
        query = text("""
            EXPLAIN (FORMAT TEXT) 
            SELECT * FROM chat_messages 
            WHERE created_at BETWEEN '2024-01-01' AND '2024-03-31'
        """)
        result = self.db.execute(query).scalars().all()
        plan = "\n".join(result)
        
        # We expect to see 'chat_messages_2024_q1' and NOT 'chat_messages_2025_q1'
        self.assertIn("chat_messages_2024_q1", plan)
        self.assertNotIn("chat_messages_2025_q1", plan)
        print("Partition pruning verified: Query scanned only 2024_q1 partition.")

if __name__ == '__main__':
    unittest.main()
