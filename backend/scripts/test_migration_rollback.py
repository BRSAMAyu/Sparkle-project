import unittest
from unittest.mock import MagicMock, patch
from zero_downtime_migration import ZeroDowntimeMigrator

class TestZeroDowntimeMigration(unittest.TestCase):
    
    @patch('psycopg2.connect')
    def test_migrate_success(self, mock_connect):
        # Setup Mock DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Validation returns equal counts
        mock_cursor.fetchone.side_effect = [(100,), (100,)] 
        
        migrator = ZeroDowntimeMigrator("postgres://user:pass@localhost/db")
        migrator.migrate_table("users")
        
        # Verify Steps
        # 1. Create Shadow
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS users_new" in str(call) for call in mock_cursor.execute.call_args_list))
        # 2. Trigger
        self.assertTrue(any("CREATE TRIGGER trg_sync_users" in str(call) for call in mock_cursor.execute.call_args_list))
        # 3. Cutover
        self.assertTrue(any("ALTER TABLE users RENAME TO users_old_backup" in str(call) for call in mock_cursor.execute.call_args_list))
        
        # Verify Commit
        self.assertTrue(mock_conn.commit.called)

    @patch('psycopg2.connect')
    def test_migrate_validation_fail(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Validation returns UNEQUAL counts
        mock_cursor.fetchone.side_effect = [(100,), (99,)] 
        
        migrator = ZeroDowntimeMigrator("postgres://...")
        migrator.migrate_table("users")
        
        # Should rollback
        self.assertTrue(mock_conn.rollback.called)
        # Should call cleanup
        self.assertTrue(any("DROP TRIGGER IF EXISTS trg_sync_users" in str(call) for call in mock_cursor.execute.call_args_list))

if __name__ == '__main__':
    unittest.main()
