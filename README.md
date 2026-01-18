# WayPoint Discord Bot

## Overview
WayPoint is a Discord bot designed to provide Apex Legends players with real-time game statistics, map rotations, and server status updates. The bot is built using Python and leverages the Discord.py library for interaction with Discord's API. It also integrates with the Apex Legends API to fetch and display relevant game data.

## Features
- **Player Stats**: Fetch and display player statistics using the `/stats` command.
- **Server Status**: Provide real-time server status updates for Apex Legends servers.
- **Map Rotation**: Display the current and upcoming map rotations for Apex Legends.
- **Channel Registration**: Allow users to register a channel for periodic server status updates using the `/register_server_status` command.

## Requirements
- Python 3.11 or higher
- Discord bot token
- Apex Legends API key
- Render account (for hosting)

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd WayPoint
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add the following:
   ```env
   DISCORD_TOKEN=your_discord_bot_token
   APEX_API_KEY=your_apex_legends_api_key
   ```

4. Run the bot locally:
   ```bash
   python main.py
   ```

## Hosting on Render
1. Create a new Web Service on Render.
2. Add the following environment variables in the Render dashboard:
   - `DISCORD_TOKEN`
   - `APEX_API_KEY`
3. Add a dummy web server to `main.py` to satisfy Render's port requirement:
   ```python
   from flask import Flask

   app = Flask(__name__)

   @app.route('/')
   def home():
       return "WayPoint Bot is running!"

   if __name__ == "__main__":
       import os
       from threading import Thread

       def run():
           app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

       t = Thread(target=run)
       t.start()
   ```
4. Deploy the bot to Render.

## Commands
- `/stats <player_name>`: Fetch and display the stats of a specific player.
- `/register_server_status`: Register a channel to receive periodic server status updates.
- `/map_rotation`: Display the current and upcoming map rotations.

## Troubleshooting
- **Unknown Interaction Error**: Ensure the bot uses `defer()` in commands to prevent interaction timeouts.
- **Empty Embeds**: Verify that the global variables (`matchmaking_server_data`, etc.) are being populated correctly by the `fetch_api_data()` function.
- **No Open Ports Detected on Render**: Add a dummy web server using Flask to satisfy Render's port requirement.

## Contributing
Contributions are welcome! Feel free to fork the repository and submit a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.