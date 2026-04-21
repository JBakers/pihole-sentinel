"""
Tests for cleanup_old_data database maintenance function.

Validates that old status_history and events rows are deleted according to
configured retention periods, and that errors are handled gracefully.
"""

import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def monitor(monkeypatch, tmp_path):
    """Import dashboard.monitor with test environment variables."""
    env = {
        "PRIMARY_IP": "10.10.100.10",
        "PRIMARY_PASSWORD": "test_password",
        "SECONDARY_IP": "10.10.100.20",
        "SECONDARY_PASSWORD": "test_password",
        "VIP_ADDRESS": "10.10.100.2",
        "CHECK_INTERVAL": "10",
        "DB_PATH": str(tmp_path / "monitor.db"),
        "API_KEY": "test_api_key",
        "NOTIFY_CONFIG_PATH": str(tmp_path / "notify_settings.json"),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop("dashboard.monitor", None)
    return importlib.import_module("dashboard.monitor")


# ============================================================================
# Helpers
# ============================================================================

async def create_tables(db_path: str) -> None:
    """Create the required database tables."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                primary_state TEXT, secondary_state TEXT,
                primary_has_vip BOOLEAN, secondary_has_vip BOOLEAN,
                primary_online BOOLEAN, secondary_online BOOLEAN,
                primary_pihole BOOLEAN, secondary_pihole BOOLEAN,
                primary_dns BOOLEAN, secondary_dns BOOLEAN,
                dhcp_leases INTEGER, primary_dhcp BOOLEAN, secondary_dhcp BOOLEAN
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT, message TEXT
            )
        """)
        await db.commit()


async def insert_status_row(db_path: str, days_ago: int) -> None:
    """Insert a status_history row with a timestamp set `days_ago` days in the past."""
    ts = (datetime.now() - timedelta(days=days_ago)).isoformat()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO status_history (timestamp, primary_state) VALUES (?, ?)",
            (ts, "MASTER"),
        )
        await db.commit()


async def insert_event_row(db_path: str, days_ago: int) -> None:
    """Insert an events row with a timestamp set `days_ago` days in the past."""
    ts = (datetime.now() - timedelta(days=days_ago)).isoformat()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO events (timestamp, event_type, message) VALUES (?, ?, ?)",
            (ts, "test", "test event"),
        )
        await db.commit()


async def count_rows(db_path: str, table: str) -> int:
    """Return the number of rows in the given table."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
        return (await cursor.fetchone())[0]


# ============================================================================
# Cleanup tests
# ============================================================================

class TestCleanupOldData:
    """Tests for cleanup_old_data database maintenance."""

    @pytest.mark.asyncio
    async def test_removes_old_status_history(self, monitor, tmp_path, monkeypatch):
        """Rows older than RETENTION_DAYS_HISTORY are deleted from status_history."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await create_tables(db_path)
        await insert_status_row(db_path, days_ago=35)   # old — must be removed
        await insert_status_row(db_path, days_ago=1)    # recent — must be kept

        monkeypatch.setenv("RETENTION_DAYS_HISTORY", "30")
        monkeypatch.setenv("RETENTION_DAYS_EVENTS", "90")

        await monitor.cleanup_old_data()

        assert await count_rows(db_path, "status_history") == 1

    @pytest.mark.asyncio
    async def test_removes_old_events(self, monitor, tmp_path, monkeypatch):
        """Rows older than RETENTION_DAYS_EVENTS are deleted from events."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await create_tables(db_path)
        await insert_event_row(db_path, days_ago=95)    # old — must be removed
        await insert_event_row(db_path, days_ago=1)     # recent — must be kept

        monkeypatch.setenv("RETENTION_DAYS_HISTORY", "30")
        monkeypatch.setenv("RETENTION_DAYS_EVENTS", "90")

        await monitor.cleanup_old_data()

        assert await count_rows(db_path, "events") == 1

    @pytest.mark.asyncio
    async def test_preserves_recent_data(self, monitor, tmp_path, monkeypatch):
        """Data within the retention window is not deleted."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await create_tables(db_path)
        await insert_status_row(db_path, days_ago=10)
        await insert_event_row(db_path, days_ago=10)

        monkeypatch.setenv("RETENTION_DAYS_HISTORY", "30")
        monkeypatch.setenv("RETENTION_DAYS_EVENTS", "90")

        await monitor.cleanup_old_data()

        assert await count_rows(db_path, "status_history") == 1
        assert await count_rows(db_path, "events") == 1

    @pytest.mark.asyncio
    async def test_empty_database_no_error(self, monitor, tmp_path, monkeypatch):
        """Cleanup on an empty database completes without error."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await create_tables(db_path)

        monkeypatch.setenv("RETENTION_DAYS_HISTORY", "30")
        monkeypatch.setenv("RETENTION_DAYS_EVENTS", "90")

        await monitor.cleanup_old_data()  # must not raise

    @pytest.mark.asyncio
    async def test_custom_short_retention(self, monitor, tmp_path, monkeypatch):
        """Retention period of 3 days removes rows that are 5 days old."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await create_tables(db_path)
        await insert_status_row(db_path, days_ago=5)    # old enough to delete
        await insert_status_row(db_path, days_ago=1)    # recent — kept
        await insert_event_row(db_path, days_ago=5)     # old enough to delete
        await insert_event_row(db_path, days_ago=1)     # recent — kept

        monkeypatch.setenv("RETENTION_DAYS_HISTORY", "3")
        monkeypatch.setenv("RETENTION_DAYS_EVENTS", "3")

        await monitor.cleanup_old_data()

        assert await count_rows(db_path, "status_history") == 1
        assert await count_rows(db_path, "events") == 1

    @pytest.mark.asyncio
    async def test_database_error_is_handled_gracefully(self, monitor, tmp_path, monkeypatch):
        """When the database file is inaccessible, exception is caught and not re-raised."""
        monitor.CONFIG["db_path"] = "/nonexistent/path/monitor.db"

        monkeypatch.setenv("RETENTION_DAYS_HISTORY", "30")
        monkeypatch.setenv("RETENTION_DAYS_EVENTS", "90")

        # Must not raise
        await monitor.cleanup_old_data()

    @pytest.mark.asyncio
    async def test_multiple_old_rows_all_removed(self, monitor, tmp_path, monkeypatch):
        """Multiple old rows are all removed in a single cleanup run."""
        db_path = str(tmp_path / "monitor.db")
        monitor.CONFIG["db_path"] = db_path

        await create_tables(db_path)
        for days in [31, 45, 60, 90]:
            await insert_status_row(db_path, days_ago=days)
            await insert_event_row(db_path, days_ago=days)
        await insert_status_row(db_path, days_ago=1)  # recent
        await insert_event_row(db_path, days_ago=1)   # recent

        monkeypatch.setenv("RETENTION_DAYS_HISTORY", "30")
        monkeypatch.setenv("RETENTION_DAYS_EVENTS", "30")

        await monitor.cleanup_old_data()

        assert await count_rows(db_path, "status_history") == 1
        assert await count_rows(db_path, "events") == 1
