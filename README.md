# WayPoint Discord Bot

<div align="center">

**A comprehensive Discord bot for Apex Legends players**

*Real-time stats tracking • Server status monitoring • RP session management*

</div>

---

## 📖 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technical Architecture](#technical-architecture)
- [Commands Reference](#commands-reference)
- [Database Schema](#database-schema)
- [API Integration](#api-integration)
- [Setup & Configuration](#setup--configuration)
- [Deployment Options](#deployment-options)
- [Periodic Tasks](#periodic-tasks)
- [Error Handling & Logging](#error-handling--logging)
- [Future Roadmap](#future-roadmap)
- [Contributing](#contributing)

---

## 🎯 Overview

WayPoint is a feature-rich Discord bot built specifically for Apex Legends players and communities. It provides real-time access to player statistics, server status monitoring across multiple regions and platforms, and automated RP tracking for ranked sessions. The bot leverages the Mozambique Here API to fetch live game data and presents it through beautifully formatted Discord embeds that update automatically.

Built with Python 3.11+ and Discord.py, WayPoint uses an SQLite database to store user preferences and server configurations, enabling persistent tracking across sessions and automatic updates for registered channels.

---

## ✨ Key Features

### 🏆 Player Statistics Tracking
- **Comprehensive Stats Display**: View detailed ranked statistics including current rank, division, and RP
- **Dynamic Rank Colors**: Embeds automatically color-code based on rank tier (Predator gold, Master purple, Diamond blue, etc.)
- **Predator Cap Tracking**: Real-time display of RP required to reach Predator rank for each platform
- **Auto-Updating Embeds**: Stats embeds refresh every 1 minute with latest data
- **Platform Support**: Full support for PC, Xbox (X1), and PlayStation (PS4) platforms

### 🗺️ Live Map & Mode Information
- **Current & Next Maps**: Displays active ranked map with time remaining and upcoming rotation
- **LTM Tracking**: Shows current Limited Time Mode, duration, and next scheduled event
- **Rotation Timing**: Precise countdown timers for map and mode rotations

### 🌐 Server Status Monitoring
- **Multi-Region Coverage**: Monitors matchmaking servers across US-East, US-West, US-Central, EU-East, EU-West, EU-Central, Asia, and South America
- **Crossplay Server Status**: Dedicated tracking for crossplay-enabled servers
- **Console Platform Tracking**: Individual status monitoring for Xbox, PlayStation, and Switch platforms
- **Visual Status Indicators**: Color-coded emojis (🟢 UP, 🟡 SLOW, 🔴 DOWN) for quick status assessment
- **Auto-Refresh**: Server status embeds update every 5 minutes automatically

### ⏱️ RP Session Tracking
- **Session Timer**: Track RP gains/losses over custom time periods
- **Detailed Session Reports**: See total RP gained or lost with precise session duration
- **Time Formatting**: Human-readable session duration (days, hours, minutes, seconds)
- **Historical Tracking**: Database stores RP snapshots for comparison

### 🔧 Server Configuration
- **Persistent Settings**: Server-specific configurations stored in SQLite database
- **Automatic Registration**: Bot auto-registers when joining new Discord servers
- **Channel Management**: Dedicated channels for server status and player stats
- **Admin Controls**: Role-based permissions for sensitive commands

---

## 🏗️ Technical Architecture

### Technology Stack
- **Language**: Python 3.11+
- **Discord API**: discord.py 2.x with app_commands (slash commands)
- **Database**: SQLite with aiosqlite for async operations
- **HTTP Client**: requests library for API calls
- **Environment Management**: python-dotenv for configuration
- **Logging**: Python's native logging module with file output

### Core Components

#### 1. **Database Layer** (`server.db`)
- **Servers Table**: Stores Discord server configurations and channel IDs
- **Users Table**: Manages user registrations, platform preferences, and RP tracking
- **Async Operations**: All database operations use aiosqlite for non-blocking I/O

#### 2. **API Integration**
- **Mozambique Here API**: Primary data source for Apex Legends information
- **Endpoints Used**:
  - `/predator`: Predator rank thresholds by platform
  - `/maprotation`: Current and upcoming map rotations
  - `/servers`: Real-time server status across all regions
  - `/bridge`: Player statistics and profile data
- **Rate Limiting**: Careful management of API calls with periodic caching

#### 3. **Periodic Task System**
- **Stats Updater**: Runs every 1 minute to refresh all registered player stat embeds
- **Server Status Updater**: Runs every 5 minutes to update server status messages
- **Background Execution**: Uses asyncio task loops for non-blocking updates

#### 4. **Embed Generation**
- **Player Stats Embeds**: Dynamic embeds with rank colors, thumbnails, and comprehensive data
- **Server Status Embeds**: Organized display of server health across regions and platforms
- **Timestamp Management**: All embeds include Eastern Time (ET) timestamps

---

## 📋 Commands Reference

### Player Commands

#### `/register`
Registers your Apex Legends account with the bot.
- **Parameters**:
  - `gamertag` (string): Your Origin ID (PC), Xbox gamertag, or PSN ID
  - `platform` (string): Your platform (`PC`, `X1`, or `PS4`)
- **Example**: `/register JohnDoe123 PC`
- **Database Action**: Stores Discord ID, Apex UID, and platform preference

#### `/stats`
Displays or updates your personal stats embed.
- **Requirements**: Must be registered first
- **Behavior**: Creates a new embed or updates existing one in the current channel
- **Updates**: Automatically refreshes every 1 minute
- **Data Shown**: Rank, RP, RP to Predator, map rotation, LTM info, server status

#### `/start_tracking`
Begins an RP tracking session.
- **Requirements**: Must be registered first
- **Action**: Records current RP and timestamp
- **Use Case**: Start before a ranked session to track gains/losses

#### `/stop_tracking`
Ends RP tracking and displays session results.
- **Requirements**: Must have an active tracking session
- **Output**: Total RP change, session duration, and final RP count
- **Format**: Human-readable time duration with RP gained/lost

### Admin Commands

#### `/register_server_id`
Manually registers the current Discord server in the database.
- **Permissions**: Requires "Admin" role
- **Note**: Auto-registration occurs when bot joins, making this mostly redundant

#### `/register_server_status`
Sets up automatic server status updates in a channel.
- **Permissions**: Requires "Admin" role
- **Action**: Posts a server status embed that auto-updates every 5 minutes
- **Behavior**: Edits existing message or creates new one if not found

---

## 🗄️ Database Schema

### `servers` Table
```sql
discord_server_id INTEGER PRIMARY KEY    -- Unique Discord server/guild ID
apex_server_channel_id INTEGER           -- Channel for server status updates
apex_server_message_id INTEGER           -- Message ID of server status embed
```

### `users` Table
```sql
discord_id INTEGER PRIMARY KEY           -- Unique Discord user ID
discord_server_id INTEGER                -- Associated Discord server
apex_uid TEXT                            -- Apex Legends unique identifier
platform TEXT                            -- Player platform (PC/X1/PS4)
current_RP INTEGER                       -- RP at session start
time_registered TIMESTAMP                -- Session start timestamp
stats_message_id INTEGER                 -- Message ID of stats embed
stats_channel_id INTEGER                 -- Channel ID of stats embed
```

**Migration Support**: Database automatically adds missing columns on startup for backward compatibility.

---

## 🔌 API Integration

### Mozambique Here API
**Base URL**: `https://api.mozambiquehe.re`

#### Endpoints Used

1. **Predator Thresholds** (`/predator`)
   - Returns minimum RP for Predator rank by platform
   - Cached in `predcap_data` global variable

2. **Map Rotation** (`/maprotation`)
   - Current and next maps for ranked mode
   - LTM schedule and timing information
   - Stored in `map_data` and `ltm_data`

3. **Server Status** (`/servers`)
   - Real-time status for matchmaking servers
   - Crossplay server status
   - Console platform-specific status
   - Stored in `matchmaking_server_data`, `crossplay_server_data`, `console_server_data`

4. **Player Stats** (`/bridge`)
   - Comprehensive player statistics
   - Rank, RP, and profile information
   - Called dynamically per-user as needed

**Authentication**: All endpoints require API key passed via `auth` parameter.

---

## ⚙️ Setup & Configuration

### Prerequisites
- Python 3.11 or higher
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Mozambique Here API Key ([Apex Legends API](https://apexlegendsapi.com/))

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone <your-repository-url>
   cd WayPoint
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   
   Create a `.env` file in the project root:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   APEX_API_KEY=your_apex_api_key_here
   ```

4. **Run the Bot**
   ```bash
   python main.py
   ```

5. **Verify Startup**
   - Check console for "✅ {Bot Name} is online and connected to Discord!"
   - Confirm API data loaded successfully
   - Verify command sync completed

---

## 🚀 Deployment Options

WayPoint can be hosted using several methods:

### Cloud Hosting Services
- **Render** (Web Service or Background Worker)
- **Railway** (Standard deployment)
- **Heroku** (Free tier alternatives)
- **DigitalOcean** (App Platform)
- **AWS** (EC2 or Lambda)
- **Azure** (App Service)
- **Google Cloud Platform** (Compute Engine)

### Local/Self-Hosted
- **Raspberry Pi** (24/7 home server)
- **Personal Computer** (with auto-start scripts)
- **NAS** (Docker container)
- **VPS** (Virtual Private Server)

**Note**: If deploying as a web service (not background worker), some platforms may require a web server to expose a port. WayPoint is designed as a Discord bot and doesn't include HTTP endpoints by default.

---

## ⚡ Periodic Tasks

### Stats Update Loop
```python
async def update_stats_periodically():
    while True:
        await update_stats_message()
        await asyncio.sleep(60 * 1)  # Every 1 minute
```
- Updates all registered player stat embeds
- Fetches fresh API data before each update cycle
- Handles missing messages/channels gracefully

### Server Status Update Loop
```python
async def update_server_stats_periodically():
    while True:
        await update_server_message()
        await asyncio.sleep(60 * 5)  # Every 5 minutes
```
- Refreshes all server status embeds across registered Discord servers
- Pulls latest server health data from API
- Error handling for deleted messages/inaccessible channels

Both tasks start automatically when the bot comes online.

---

## 🔍 Error Handling & Logging

### Logging Configuration
- **File**: `discord.log` in project root
- **Level**: DEBUG for comprehensive output
- **Handler**: FileHandler with UTF-8 encoding
- **Format**: Timestamp, log level, and message

### Error Handling Patterns
- **API Failures**: Try-except blocks with user-friendly error messages
- **Missing Messages**: Graceful handling when embeds are deleted
- **Permission Issues**: Detection and reporting of insufficient bot permissions
- **Database Errors**: Transaction safety with commit/rollback
- **Interaction Timeouts**: Deferred responses to prevent "Unknown Interaction" errors

---

## 🛣️ Future Roadmap

### Priority 1 (High Impact)
- ✅ Implement comprehensive error handling for API requests
- 🔄 Add Steam API integration for automatic RP tracking on PC
- 🔄 Fix database schema to support same user across multiple servers

### Priority 2 (Quality of Life)
- 📋 `/unregister` command to remove user from database
- 📊 `/view_profile` command to see registered information
- ⏱️ `/current_session` command to view active RP tracking session
- 🏅 `/leaderboard` command to display top 3 players by RP in server
- ✏️ `/update_profile` command to change Apex UID or platform
- 📢 Notification system for RP milestones and rank changes

### Under Consideration
- Multi-language support
- Custom embed colors per server
- Integration with other game APIs
- Web dashboard for stats visualization

---

## 🤝 Contributing

Contributions are welcome! Whether it's bug fixes, new features, or documentation improvements, your help is appreciated.

### How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add comments for complex logic
- Update documentation for new features

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for full details.

---

## 🙏 Acknowledgments

- **Mozambique Here API** for providing comprehensive Apex Legends data
- **Discord.py** community for excellent documentation and support
- Apex Legends players for feature requests and testing

---

<div align="center">

**Built with ❤️ for the Apex Legends community**

*For questions or support, please open an issue on GitHub*

</div>