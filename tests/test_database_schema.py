"""
Tests for M1-P1 Task 1.2: Database schema redesign and migration (monitor.py)
"""

import os
import sqlite3
import pytest
import asyncio
from pathlib import Path
import tempfile
import sys

# Add dashboard to path
dashboard_path = Path(__file__).parent.parent / "dashboard"
sys.path.insert(0, str(dashboard_path))

# Patch CONFIG before importing monitor to avoid env var errors
# Now import monitor
import monitor
from monitor import init_db, _migrate_old_schema_to_new


class TestDatabaseSchema:
    """Tests for new N-node normalized schema"""
    
    @pytest.fixture
    async def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Set CONFIG db_path
            monitor.CONFIG["db_path"] = str(db_path)
            
            # Initialize database
            await init_db()
            
            yield db_path
            
            # Cleanup
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_new_schema_tables_exist(self, temp_db):
        """Verify new normalized tables are created"""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        
        # Check poll_cycles table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='poll_cycles'"
        )
        assert cursor.fetchone() is not None, "poll_cycles table should exist"
        
        # Check node_status table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='node_status'"
        )
        assert cursor.fetchone() is not None, "node_status table should exist"
        
        # Check events table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
        )
        assert cursor.fetchone() is not None, "events table should exist"
        
        conn.close()
    
    @pytest.mark.asyncio
    async def test_poll_cycles_schema(self, temp_db):
        """Verify poll_cycles table structure"""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(poll_cycles)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type
        
        assert "id" in columns
        assert "timestamp" in columns
        assert "dhcp_leases" in columns
        
        conn.close()
    
    @pytest.mark.asyncio
    async def test_node_status_schema(self, temp_db):
        """Verify node_status table structure"""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(node_status)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type
        
        required_columns = [
            "id", "poll_id", "node_index", "node_name",
            "vrrp_state", "has_vip", "online", "pihole_ok", "dns_ok", "dhcp_ok"
        ]
        for col in required_columns:
            assert col in columns, f"Column {col} should exist in node_status"
        
        conn.close()
    
    @pytest.mark.asyncio
    async def test_indexes_created(self, temp_db):
        """Verify indexes are created for performance"""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        
        expected_indexes = [
            "idx_poll_cycles_timestamp",
            "idx_node_status_poll_id",
            "idx_node_status_node_index",
            "idx_status_timestamp",
            "idx_events_timestamp",
            "idx_events_type"
        ]
        
        for idx in expected_indexes:
            assert idx in indexes, f"Index {idx} should exist"
        
        conn.close()


class TestSchemaMigration:
    """Tests for migration from old 2-node schema to new N-node schema"""
    
    @pytest.fixture
    async def db_with_old_schema(self):
        """Create database with old schema and sample data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_old.db"
            
            # Create old schema manually
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    primary_state TEXT,
                    secondary_state TEXT,
                    primary_has_vip BOOLEAN,
                    secondary_has_vip BOOLEAN,
                    primary_online BOOLEAN,
                    secondary_online BOOLEAN,
                    primary_pihole BOOLEAN,
                    secondary_pihole BOOLEAN,
                    primary_dns BOOLEAN,
                    secondary_dns BOOLEAN,
                    dhcp_leases INTEGER,
                    primary_dhcp BOOLEAN,
                    secondary_dhcp BOOLEAN
                )
            """)
            
            cursor.execute("""
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    message TEXT
                )
            """)
            
            # Insert sample data
            test_data = [
                ("2026-05-01 10:00:00", "MASTER", "BACKUP", True, False, True, True, True, True, True, True, 10, True, False),
                ("2026-05-01 10:10:00", "MASTER", "BACKUP", True, False, True, True, True, True, False, True, 10, True, False),
                ("2026-05-01 10:20:00", "BACKUP", "MASTER", False, True, True, True, True, True, True, True, 12, False, True),
            ]
            
            for data in test_data:
                cursor.execute("""
                    INSERT INTO status_history
                    (timestamp, primary_state, secondary_state, primary_has_vip, secondary_has_vip,
                     primary_online, secondary_online, primary_pihole, secondary_pihole,
                     primary_dns, secondary_dns, dhcp_leases, primary_dhcp, secondary_dhcp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
            
            conn.commit()
            conn.close()
            
            # Set CONFIG db_path
            monitor.CONFIG["db_path"] = str(db_path)
            
            yield db_path
            
            # Cleanup
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_migration_creates_new_tables(self, db_with_old_schema):
        """Migration should create new normalized tables"""
        # Initialize (triggers migration)
        await init_db()
        
        conn = sqlite3.connect(str(db_with_old_schema))
        cursor = conn.cursor()
        
        # Verify new tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='poll_cycles'"
        )
        assert cursor.fetchone() is not None
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='node_status'"
        )
        assert cursor.fetchone() is not None
        
        conn.close()
    
    @pytest.mark.asyncio
    async def test_migration_converts_data(self, db_with_old_schema):
        """Migration should convert old data to new schema"""
        # Initialize (triggers migration)
        await init_db()
        
        conn = sqlite3.connect(str(db_with_old_schema))
        cursor = conn.cursor()
        
        # Check old table still exists
        cursor.execute(
            "SELECT COUNT(*) FROM status_history"
        )
        old_count = cursor.fetchone()[0]
        assert old_count == 3, "Old schema should still have 3 rows"
        
        # Check new tables have converted data
        # 3 old rows → 3 poll_cycles + 6 node_status rows
        cursor.execute("SELECT COUNT(*) FROM poll_cycles")
        poll_count = cursor.fetchone()[0]
        assert poll_count == 3, f"Should have 3 poll_cycles, got {poll_count}"
        
        cursor.execute("SELECT COUNT(*) FROM node_status")
        node_count = cursor.fetchone()[0]
        assert node_count == 6, f"Should have 6 node_status rows (3 * 2 nodes), got {node_count}"
        
        conn.close()
    
    @pytest.mark.asyncio
    async def test_migration_preserves_timestamps(self, db_with_old_schema):
        """Migration should preserve timestamps from old data"""
        await init_db()
        
        conn = sqlite3.connect(str(db_with_old_schema))
        cursor = conn.cursor()
        
        # Get old timestamps
        cursor.execute("SELECT timestamp FROM status_history ORDER BY timestamp")
        old_timestamps = [row[0] for row in cursor.fetchall()]
        
        # Get new timestamps
        cursor.execute("SELECT timestamp FROM poll_cycles ORDER BY timestamp")
        new_timestamps = [row[0] for row in cursor.fetchall()]
        
        # Should match exactly
        assert old_timestamps == new_timestamps, "Timestamps should be preserved"
        
        conn.close()
    
    @pytest.mark.asyncio
    async def test_migration_idempotent(self, db_with_old_schema):
        """Migration should be safe to run multiple times"""
        # First migration
        await init_db()
        
        conn = sqlite3.connect(str(db_with_old_schema))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM poll_cycles")
        count1 = cursor.fetchone()[0]
        conn.close()
        
        # Second init (should skip migration)
        await init_db()
        
        conn = sqlite3.connect(str(db_with_old_schema))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM poll_cycles")
        count2 = cursor.fetchone()[0]
        conn.close()
        
        # Count should be the same
        assert count1 == count2, "Migration should be idempotent"


class TestBackwardCompatibility:
    """Tests for backward compatibility during migration"""
    
    @pytest.mark.asyncio
    async def test_old_schema_preserved(self, temp_db):
        """Old status_history table should still exist after migration"""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='status_history'"
        )
        assert cursor.fetchone() is not None, "Old status_history table should exist"
        
        conn.close()
    
    @pytest.fixture(scope="function")
    async def temp_db(self):
        """Create temporary database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            monitor.CONFIG["db_path"] = str(db_path)
            await init_db()
            yield db_path
            if db_path.exists():
                db_path.unlink()
