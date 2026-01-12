import psycopg2
import time
import logging
import argparse
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZeroDowntimeMigrator:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None

    def connect(self):
        self.conn = psycopg2.connect(self.db_url)
        self.conn.autocommit = True  # We'll manage transactions manually if needed, but for DDL we often need autocommit off or specific handling. 
        # Actually for DDL in Postgres, transactional DDL is supported.
        self.conn.autocommit = False

    def close(self):
        if self.conn:
            self.conn.close()

    def migrate_table(self, table_name: str, new_schema_sql: str = None):
        """
        Orchestrate the zero-downtime migration for a table.
        1. Create Shadow Table
        2. Setup Dual Write
        3. Backfill
        4. Validation
        5. Cutover (Atomic Rename)
        """
        shadow_table = f"{table_name}_new"
        
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            logger.info(f"Step 1: Creating shadow table {shadow_table}...")
            # Create shadow table (simplistic copy, real world usage would apply new schema here)
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {shadow_table} (LIKE {table_name} INCLUDING ALL)")
            if new_schema_sql:
                cursor.execute(new_schema_sql)
            self.conn.commit()
            
            logger.info("Step 2: Setting up Dual Write Triggers...")
            self._setup_dual_write(cursor, table_name, shadow_table)
            self.conn.commit()
            
            logger.info("Step 3: Backfilling Data...")
            self._backfill_data(cursor, table_name, shadow_table)
            self.conn.commit()
            
            logger.info("Step 4: Validating Consistency...")
            if not self._validate_data(cursor, table_name, shadow_table):
                raise Exception("Data validation failed!")
            
            logger.info("Step 5: Ready for Cutover.")
            # Cutover is usually manual or requires app config change + restart, 
            # or atomic rename if app handles connection reset.
            # Here we demonstrate atomic rename.
            self._cutover(cursor, table_name, shadow_table)
            self.conn.commit()
            
            logger.info("✅ Migration Successful!")
            
        except Exception as e:
            logger.error(f"❌ Migration Failed: {e}")
            if self.conn:
                self.conn.rollback()
            self.rollback(table_name)
        finally:
            self.close()

    def _setup_dual_write(self, cursor, table: str, shadow: str):
        # Create function
        func_name = f"sync_{table}_to_{shadow}"
        trigger_name = f"trg_sync_{table}"
        
        # Dynamic column list would be better, but assuming same columns for now or superset
        # For P1 demo, we use a generic PL/PGSQL block
        
        sql = f"""
        CREATE OR REPLACE FUNCTION {func_name}() RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO {shadow} VALUES (NEW.*);
                RETURN NEW;
            ELSIF TG_OP = 'UPDATE' THEN
                -- Simplified: assuming PK is id
                DELETE FROM {shadow} WHERE id = NEW.id;
                INSERT INTO {shadow} VALUES (NEW.*);
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                DELETE FROM {shadow} WHERE id = OLD.id;
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
        cursor.execute(sql)
        
        cursor.execute(f"""
            DROP TRIGGER IF EXISTS {trigger_name} ON {table};
            CREATE TRIGGER {trigger_name}
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION {func_name}();
        """)

    def _backfill_data(self, cursor, table: str, shadow: str):
        # Naive backfill. In production, use batching (LIMIT/OFFSET or ID keyset)
        logger.info("Starting backfill (naive)...")
        cursor.execute(f"INSERT INTO {shadow} SELECT * FROM {table} ON CONFLICT DO NOTHING")

    def _validate_data(self, cursor, table: str, shadow: str):
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count_old = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM {shadow}")
        count_new = cursor.fetchone()[0]
        
        logger.info(f"Row counts: Old={count_old}, New={count_new}")
        return count_old == count_new

    def _cutover(self, cursor, table: str, shadow: str):
        logger.warning("Acquiring EXCLUSIVE LOCK for Cutover...")
        # Brief lock to swap names
        cursor.execute(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE")
        
        old_backup = f"{table}_old_backup"
        cursor.execute(f"ALTER TABLE {table} RENAME TO {old_backup}")
        cursor.execute(f"ALTER TABLE {shadow} RENAME TO {table}")
        
        # Cleanup triggers? Maybe later.
        
    def rollback(self, table_name: str):
        logger.warning("Rolling back...")
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            shadow = f"{table_name}_new"
            func_name = f"sync_{table_name}_to_{shadow}"
            trigger_name = f"trg_sync_{table_name}"
            
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}")
            cursor.execute(f"DROP FUNCTION IF EXISTS {func_name}")
            # cursor.execute(f"DROP TABLE IF EXISTS {shadow}") # Optional: keep for debugging
            
            self.conn.commit()
            logger.info("Rollback complete.")
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
        finally:
            self.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--table", required=True)
    args = parser.parse_args()
    
    migrator = ZeroDowntimeMigrator(args.db_url)
    migrator.migrate_table(args.table)
