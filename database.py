"""
Database operations using aiosqlite for the WayPoint Discord bot.
"""
import aiosqlite
from datetime import datetime
from config import DB_PATH, TIMEZONE_ET


class Database:
    """Handles all database operations for the bot."""
    
    def __init__(self):
        """Initialize the Database instance."""
        self.db_path = DB_PATH
    
    async def init(self):
        """Initialize the database and create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Create servers table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    discord_server_id INTEGER PRIMARY KEY,
                    apex_server_channel_id INTEGER,
                    apex_server_message_id INTEGER
                )
            ''')
            
            # Create users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    discord_id INTEGER PRIMARY KEY,
                    discord_server_id INTEGER,
                    apex_uid TEXT,
                    platform TEXT,
                    current_RP INTEGER,
                    time_registered TIMESTAMP,
                    stats_message_id INTEGER,
                    stats_channel_id INTEGER
                )
            ''')
            
            await db.commit()
            
            # Migration: ensure required columns exist
            async with db.execute("PRAGMA table_info(users)") as cursor:
                cols = [row[1] for row in await cursor.fetchall()]
            
            migrations = []
            if 'platform' not in cols:
                migrations.append("ALTER TABLE users ADD COLUMN platform TEXT")
            if 'current_RP' not in cols:
                migrations.append("ALTER TABLE users ADD COLUMN current_RP INTEGER")
            if 'stats_message_id' not in cols:
                migrations.append("ALTER TABLE users ADD COLUMN stats_message_id INTEGER")
            if 'stats_channel_id' not in cols:
                migrations.append("ALTER TABLE users ADD COLUMN stats_channel_id INTEGER")
            
            for migration in migrations:
                await db.execute(migration)
                print(f"⚙️ Migrated: {migration}")
            
            await db.commit()
            print("✅ Database initialized and ready!")
    
    async def get_user(self, discord_id):
        """
        Get a user by their Discord ID.
        
        Args:
            discord_id (int): The Discord user ID
            
        Returns:
            tuple: User data tuple or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)) as cursor:
                return await cursor.fetchone()
    
    async def save_user(self, discord_id, discord_server_id, apex_uid, platform, current_RP=0):
        """
        Save or update a user in the database.
        
        Args:
            discord_id (int): Discord user ID
            discord_server_id (int): Discord server ID
            apex_uid (str): Apex Legends UID
            platform (str): Gaming platform (PC, PS4, X1)
            current_RP (int): Current rank points (default 0)
        """
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
    
    async def get_all_users(self):
        """
        Get all users from the database.
        
        Returns:
            list: List of user data tuples
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM users") as cursor:
                return await cursor.fetchall()
    
    async def update_user_tracking(self, discord_id, current_RP, time_registered=None):
        """
        Update user tracking information (RP and time).
        
        Args:
            discord_id (int): Discord user ID
            current_RP (int): Current rank points
            time_registered (datetime): Registration timestamp (None to clear tracking)
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET current_RP = ?, time_registered = ? WHERE discord_id = ?",
                (current_RP, time_registered, discord_id)
            )
            await db.commit()
    
    async def update_user_stats_message(self, discord_id, stats_message_id, stats_channel_id):
        """
        Update user's stats message IDs.
        
        Args:
            discord_id (int): Discord user ID
            stats_message_id (int): Message ID for stats embed
            stats_channel_id (int): Channel ID where stats are posted
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET stats_message_id = ?, stats_channel_id = ? WHERE discord_id = ?",
                (stats_message_id, stats_channel_id, discord_id)
            )
            await db.commit()
    
    async def get_server(self, discord_server_id):
        """
        Get server configuration by Discord server ID.
        
        Args:
            discord_server_id (int): Discord server ID
            
        Returns:
            tuple: Server data tuple or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM servers WHERE discord_server_id = ?",
                (discord_server_id,)
            ) as cursor:
                return await cursor.fetchone()
    
    async def save_server_config(self, discord_server_id, apex_server_channel_id=None, apex_server_message_id=None):
        """
        Insert or update server config. Only overwrite columns when a non-None value is provided.
        
        Args:
            discord_server_id (int): Discord server ID
            apex_server_channel_id (int, optional): Channel ID for server status
            apex_server_message_id (int, optional): Message ID for server status
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM servers WHERE discord_server_id = ?',
                (discord_server_id,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row is None:
                # No existing row — insert whatever values were provided
                await db.execute('''
                    INSERT INTO servers (discord_server_id, apex_server_channel_id, apex_server_message_id)
                    VALUES (?, ?, ?)
                ''', (discord_server_id, apex_server_channel_id, apex_server_message_id))
            else:
                # Update only the provided columns
                if apex_server_channel_id is not None:
                    await db.execute('''
                        UPDATE servers
                        SET apex_server_channel_id = ?
                        WHERE discord_server_id = ?
                    ''', (apex_server_channel_id, discord_server_id))
                
                if apex_server_message_id is not None:
                    await db.execute('''
                        UPDATE servers
                        SET apex_server_message_id = ?
                        WHERE discord_server_id = ?
                    ''', (apex_server_message_id, discord_server_id))
            
            await db.commit()
            print(f"✅ Server {discord_server_id} configuration saved/updated!")
    
    async def get_all_servers(self):
        """
        Get all servers from the database.
        
        Returns:
            list: List of server data tuples
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM servers") as cursor:
                return await cursor.fetchall()
