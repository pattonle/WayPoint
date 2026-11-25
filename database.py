"""
Database operations using aiosqlite for the WayPoint Discord bot.
"""
import aiosqlite
from config import DB_PATH


class Database:
    """Handles all database operations for the bot."""

    def __init__(self, db_path=None):
        """Initialize the Database instance."""
        self.db_path = db_path or DB_PATH

    async def init(self):
        """Initialize the database, create tables, and run migrations."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    discord_server_id INTEGER PRIMARY KEY,
                    apex_server_channel_id INTEGER,
                    apex_server_message_id INTEGER,
                    sessions_channel_id INTEGER
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    discord_id INTEGER PRIMARY KEY,
                    discord_server_id INTEGER,
                    apex_uid TEXT,
                    platform TEXT,
                    current_RP INTEGER,
                    time_registered TIMESTAMP,
                    stats_message_id INTEGER,
                    stats_channel_id INTEGER,
                    steam_id TEXT,
                    session_start_RP INTEGER,
                    session_start_time TIMESTAMP,
                    is_in_game INTEGER DEFAULT 0
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id INTEGER NOT NULL,
                    discord_server_id INTEGER,
                    start_rp INTEGER NOT NULL,
                    end_rp INTEGER NOT NULL,
                    rp_change INTEGER NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP NOT NULL,
                    source TEXT NOT NULL
                )
            ''')

            await db.commit()

            # Migrations for existing databases
            async with db.execute("PRAGMA table_info(users)") as cursor:
                user_cols = [row[1] for row in await cursor.fetchall()]

            user_migrations = []
            if 'platform' not in user_cols:
                user_migrations.append("ALTER TABLE users ADD COLUMN platform TEXT")
            if 'current_RP' not in user_cols:
                user_migrations.append("ALTER TABLE users ADD COLUMN current_RP INTEGER")
            if 'stats_message_id' not in user_cols:
                user_migrations.append("ALTER TABLE users ADD COLUMN stats_message_id INTEGER")
            if 'stats_channel_id' not in user_cols:
                user_migrations.append("ALTER TABLE users ADD COLUMN stats_channel_id INTEGER")
            if 'steam_id' not in user_cols:
                user_migrations.append("ALTER TABLE users ADD COLUMN steam_id TEXT")
            if 'session_start_RP' not in user_cols:
                user_migrations.append("ALTER TABLE users ADD COLUMN session_start_RP INTEGER")
            if 'session_start_time' not in user_cols:
                user_migrations.append("ALTER TABLE users ADD COLUMN session_start_time TIMESTAMP")
            if 'is_in_game' not in user_cols:
                user_migrations.append("ALTER TABLE users ADD COLUMN is_in_game INTEGER DEFAULT 0")

            async with db.execute("PRAGMA table_info(servers)") as cursor:
                server_cols = [row[1] for row in await cursor.fetchall()]

            server_migrations = []
            if 'sessions_channel_id' not in server_cols:
                server_migrations.append("ALTER TABLE servers ADD COLUMN sessions_channel_id INTEGER")

            for migration in user_migrations + server_migrations:
                await db.execute(migration)
                print(f"⚙️ Migrated: {migration}")

            await db.commit()
            print("✅ Database initialized and ready!")

    async def get_user(self, discord_id):
        """Get a user row by their Discord ID, or None if not found."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)) as cursor:
                return await cursor.fetchone()

    async def save_user(self, discord_id, discord_server_id, apex_uid, platform, current_RP=0):
        """Save or update a user's registration in the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO users (discord_id, discord_server_id, apex_uid, platform, current_RP)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(discord_id) DO UPDATE SET
                    discord_server_id=excluded.discord_server_id,
                    apex_uid=excluded.apex_uid,
                    platform=excluded.platform
            ''', (discord_id, discord_server_id, apex_uid, platform, current_RP))
            await db.commit()

    async def delete_user(self, discord_id):
        """Remove a user from the database. Returns True if a row was deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM users WHERE discord_id = ?", (discord_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def update_user_steam_id(self, discord_id, steam_id):
        """Update a user's Steam ID. Returns True if a row was updated."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE users SET steam_id = ? WHERE discord_id = ?",
                (steam_id, discord_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def set_session_start(self, discord_id, start_RP, start_time):
        """Mark the user as in-game and record session start RP/time."""
        started_iso = start_time.isoformat() if hasattr(start_time, "isoformat") else start_time
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET session_start_RP = ?, session_start_time = ?, is_in_game = 1 WHERE discord_id = ?",
                (start_RP, started_iso, discord_id)
            )
            await db.commit()

    async def set_session_end(self, discord_id, final_RP):
        """Mark the user as not in-game, update current RP, and clear Steam session fields."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET current_RP = ?, session_start_RP = NULL, session_start_time = NULL, is_in_game = 0 WHERE discord_id = ?",
                (final_RP, discord_id)
            )
            await db.commit()

    async def get_all_users(self):
        """Get all users from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM users") as cursor:
                return await cursor.fetchall()

    async def get_server_users(self, discord_server_id):
        """Get all users registered in a specific Discord server."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM users WHERE discord_server_id = ?",
                (discord_server_id,)
            ) as cursor:
                return await cursor.fetchall()

    async def update_user_tracking(self, discord_id, current_RP, time_registered=None):
        """Update user tracking information (RP and manual tracking start timestamp)."""
        ts = time_registered.isoformat() if hasattr(time_registered, "isoformat") else time_registered
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET current_RP = ?, time_registered = ? WHERE discord_id = ?",
                (current_RP, ts, discord_id)
            )
            await db.commit()

    async def update_user_stats_message(self, discord_id, stats_message_id, stats_channel_id):
        """Update user's auto-updating stats message and channel IDs."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET stats_message_id = ?, stats_channel_id = ? WHERE discord_id = ?",
                (stats_message_id, stats_channel_id, discord_id)
            )
            await db.commit()

    async def record_session(self, discord_id, discord_server_id, start_rp, end_rp, started_at, ended_at, source="manual"):
        """Persist a completed RP session for historical progress tracking."""
        started_iso = started_at.isoformat() if hasattr(started_at, "isoformat") else str(started_at)
        ended_iso = ended_at.isoformat() if hasattr(ended_at, "isoformat") else str(ended_at)
        rp_change = int(end_rp) - int(start_rp)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO sessions (discord_id, discord_server_id, start_rp, end_rp, rp_change, started_at, ended_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (discord_id, discord_server_id, int(start_rp), int(end_rp), rp_change, started_iso, ended_iso, source))
            await db.commit()

    async def get_user_sessions(self, discord_id, limit=8):
        """Return the most recent completed sessions for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT start_rp, end_rp, rp_change, started_at, ended_at, source
                FROM sessions
                WHERE discord_id = ?
                ORDER BY id DESC
                LIMIT ?
            ''', (discord_id, limit)) as cursor:
                return await cursor.fetchall()

    async def get_user_session_totals(self, discord_id):
        """Return (session_count, total_rp_change, best_rp_change, worst_rp_change) for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT COUNT(*), COALESCE(SUM(rp_change), 0), COALESCE(MAX(rp_change), 0), COALESCE(MIN(rp_change), 0)
                FROM sessions
                WHERE discord_id = ?
            ''', (discord_id,)) as cursor:
                return await cursor.fetchone()

    async def get_server(self, discord_server_id):
        """Get server configuration by Discord server ID."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM servers WHERE discord_server_id = ?",
                (discord_server_id,)
            ) as cursor:
                return await cursor.fetchone()

    async def save_server_config(
        self,
        discord_server_id,
        apex_server_channel_id=None,
        apex_server_message_id=None,
        sessions_channel_id=None,
    ):
        """Insert or update server config. Only overwrites columns when a non-None value is provided."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM servers WHERE discord_server_id = ?',
                (discord_server_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                await db.execute('''
                    INSERT INTO servers (discord_server_id, apex_server_channel_id, apex_server_message_id, sessions_channel_id)
                    VALUES (?, ?, ?, ?)
                ''', (discord_server_id, apex_server_channel_id, apex_server_message_id, sessions_channel_id))
            else:
                if apex_server_channel_id is not None:
                    await db.execute(
                        'UPDATE servers SET apex_server_channel_id = ? WHERE discord_server_id = ?',
                        (apex_server_channel_id, discord_server_id)
                    )
                if apex_server_message_id is not None:
                    await db.execute(
                        'UPDATE servers SET apex_server_message_id = ? WHERE discord_server_id = ?',
                        (apex_server_message_id, discord_server_id)
                    )
                if sessions_channel_id is not None:
                    await db.execute(
                        'UPDATE servers SET sessions_channel_id = ? WHERE discord_server_id = ?',
                        (sessions_channel_id, discord_server_id)
                    )

            await db.commit()
            print(f"✅ Server {discord_server_id} configuration saved/updated!")

    async def get_all_servers(self):
        """Get all servers from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM servers") as cursor:
                return await cursor.fetchall()
