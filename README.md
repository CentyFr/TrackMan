# TrackMan Discord Bot

TrackMan is a Discord bot that tracks user activity, awards badges (roles), and provides various features for server administrators.

## Invite it to your server

Ignore the nerdy stuff, just click this link to invite it to your server: https://bit.ly/TrackManBot
    

## Features

- Track user online status, game activity, and voice channel usage
- Award badges based on user activity
- Provide leaderboards for online time, game time, and voice time
- Display individual user statistics
- Server-specific configuration options

## Setup

1. Clone this repository
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_discord_token_here
   ```
4. Run the bot:
   ```
   python trackman.py
   ```

## Commands

- `=status [@user]`: Shows a user's online activity breakdown
- `=gametime [@user]`: Shows a user's game activity
- `=voicetime [@user]`: Shows a user's voice channel activity
- `=leaderboard <category>`: Shows leaderboard for online, games, or voice
- `=mostplayedgame`: Shows the most played game on the server
- `=ping`: Checks bot's latency
- `=commands`: Displays help message
- `=setup`: Initial bot setup (admin only)
- `=config`: View current bot configuration (admin only)
- `=toggle <feature>`: Toggle a feature on/off (admin only)
- `=setchannel <channel>`: Set notification channel (admin only)

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Developer

    https://github.com/CentyFr


:D
