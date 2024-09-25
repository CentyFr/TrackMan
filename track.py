import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, func, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///tracker.db')
Session = sessionmaker(bind=engine)

class UserActivity(Base):
    __tablename__ = 'user_activity'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    status = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

class GameActivity(Base):
    __tablename__ = 'game_activity'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    game = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

class VoiceActivity(Base):
    __tablename__ = 'voice_activity'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    channel_id = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

class ServerSettings(Base):
    __tablename__ = 'server_settings'
    id = Column(Integer, primary_key=True)
    server_id = Column(String, unique=True)
    track_status = Column(Boolean, default=True)
    track_games = Column(Boolean, default=True)
    track_voice = Column(Boolean, default=True)
    use_badges = Column(Boolean, default=True)
    notification_channel_id = Column(String, nullable=True)

Base.metadata.create_all(engine)

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='=', intents=intents)

# TrackMan's user ID
TRACKMAN_ID = None

# Badge (Role) definitions
BADGES = {
    'Online Streaker': {
        'Bronze': 'Online Streaker Bronze',
        'Silver': 'Online Streaker Silver',
        'Gold': 'Online Streaker Gold',
        'Platinum': 'Online Streaker Platinum'
    },
    'Night Owl': {
        'Bronze': 'Night Owl Bronze',
        'Silver': 'Night Owl Silver',
        'Gold': 'Night Owl Gold'
    },
    'Chatterbox': {
        'Bronze': 'Chatterbox Bronze',
        'Silver': 'Chatterbox Silver',
        'Gold': 'Chatterbox Gold',
        'Platinum': 'Chatterbox Platinum'
    },
    'Game Addict': {
        'Bronze': 'Game Addict Bronze',
        'Silver': 'Game Addict Silver',
        'Gold': 'Game Addict Gold',
        'Platinum': 'Game Addict Platinum'
    }
}

@bot.event
async def on_ready():
    global TRACKMAN_ID
    TRACKMAN_ID = bot.user.id
    await bot.change_presence(activity=discord.Game(name="Stalking Simulator"))
    bot.loop.create_task(track_activities())
    
    for guild in bot.guilds:
        channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
        if channel:
            await channel.send("TrackMan has started its tracking shenanigans again!")


@bot.event
async def on_disconnect():
    for guild in bot.guilds:
        channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
        if channel:
            await channel.send("TrackerMan dozes off, no more shenanigans :(")

@bot.event
async def on_error(event, *args, **kwargs):
    for guild in bot.guilds:
        channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
        if channel:
            await channel.send("That didn't work, messaging the dev real quick")
    # Here you could add code to actually message the developer

@bot.event
async def on_guild_join(guild):
    channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
    if channel:
        await channel.send(f"Thanks for adding TrackMan to {guild.name}! Please use the `=setup` command to configure the bot.")
async def track_activities():
    while True:
        session = Session()
        for guild in bot.guilds:
            settings = session.query(ServerSettings).filter_by(server_id=str(guild.id)).first()
            if not settings:
                continue

            for member in guild.members:
                if member.id == TRACKMAN_ID:
                    continue

                if settings.track_status:
                    current_status = str(member.status)
                    existing_activity = session.query(UserActivity).filter_by(
                        user_id=str(member.id), end_time=None
                    ).first()
                    
                    if existing_activity:
                        if existing_activity.status != current_status:
                            existing_activity.end_time = datetime.utcnow()
                            session.add(UserActivity(user_id=str(member.id), status=current_status, start_time=datetime.utcnow()))
                    else:
                        session.add(UserActivity(user_id=str(member.id), status=current_status, start_time=datetime.utcnow()))

                if settings.track_games:
                    if member.activity and member.activity.type == discord.ActivityType.playing:
                        game = member.activity.name
                        existing_game = session.query(GameActivity).filter_by(
                            user_id=str(member.id), end_time=None
                        ).first()
                        
                        if existing_game:
                            if existing_game.game != game:
                                existing_game.end_time = datetime.utcnow()
                                session.add(GameActivity(user_id=str(member.id), game=game, start_time=datetime.utcnow()))
                        else:
                            session.add(GameActivity(user_id=str(member.id), game=game, start_time=datetime.utcnow()))

                if settings.track_voice:
                    if member.voice:
                        existing_voice = session.query(VoiceActivity).filter_by(
                            user_id=str(member.id), end_time=None
                        ).first()
                        
                        if not existing_voice:
                            session.add(VoiceActivity(user_id=str(member.id), channel_id=str(member.voice.channel.id), start_time=datetime.utcnow()))
                    elif not member.voice:
                        existing_voice = session.query(VoiceActivity).filter_by(
                            user_id=str(member.id), end_time=None
                        ).first()
                        if existing_voice:
                            existing_voice.end_time = datetime.utcnow()

                if settings.use_badges:
                    await check_and_award_badges(member)

        session.commit()
        session.close()
        await asyncio.sleep(60)  # Update every minute

async def check_and_award_badges(member):
    session = Session()
    settings = session.query(ServerSettings).filter_by(server_id=str(member.guild.id)).first()
    
    if not settings or not settings.use_badges:
        session.close()
        return

    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    # Check Online Streaker badge
    online_days = session.query(func.count(func.distinct(func.date(UserActivity.start_time)))).filter(
        UserActivity.user_id == str(member.id),
        UserActivity.status == 'online',
        UserActivity.start_time >= week_ago
    ).scalar()

    if online_days >= 7:
        await award_badge(member, 'Online Streaker', 'Bronze')
    if online_days >= 14:
        await award_badge(member, 'Online Streaker', 'Silver')
    if online_days >= 30:
        await award_badge(member, 'Online Streaker', 'Gold')

    # Check Chatterbox badge
    voice_time = session.query(func.sum(func.julianday(func.coalesce(VoiceActivity.end_time, func.current_timestamp())) - func.julianday(VoiceActivity.start_time)) * 24).filter(
        VoiceActivity.user_id == str(member.id),
        VoiceActivity.start_time >= month_ago
    ).scalar() or 0

    if voice_time >= 10:
        await award_badge(member, 'Chatterbox', 'Bronze')
    if voice_time >= 25:
        await award_badge(member, 'Chatterbox', 'Silver')
    if voice_time >= 50:
        await award_badge(member, 'Chatterbox', 'Gold')
    if voice_time >= 100:
        await award_badge(member, 'Chatterbox', 'Platinum')

    session.close()

async def award_badge(member, badge_name, badge_tier):
    role_name = BADGES[badge_name][badge_tier]
    role = discord.utils.get(member.guild.roles, name=role_name)
    
    if not role:
        # Create the role if it doesn't exist
        role = await member.guild.create_role(name=role_name)
    
    if role not in member.roles:
        await member.add_roles(role)
        await send_badge_notification(member, badge_name, badge_tier)

async def send_badge_notification(member, badge_name, badge_tier):
    message = f"🎉 Congratulations, {member.mention}! You've earned the {badge_name} ({badge_tier}) badge!"
    
    session = Session()
    settings = session.query(ServerSettings).filter_by(server_id=str(member.guild.id)).first()
    
    if settings and settings.notification_channel_id:
        channel = member.guild.get_channel(int(settings.notification_channel_id))
        if channel:
            await channel.send(message)
    else:
        await member.send(message)
    
    session.close()

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    session = Session()
    settings = session.query(ServerSettings).filter_by(server_id=str(ctx.guild.id)).first()
    
    if settings:
        await ctx.send("This server is already set up. Use `=config` to modify settings.")
        return

    await ctx.send("Welcome to TrackMan setup! Let's configure your server.")
    
    # Ask about features
    features = ['status tracking', 'game tracking', 'voice tracking', 'badge system']
    enabled_features = []
    
    for feature in features:
        response = await ask_yes_no(ctx, f"Do you want to enable {feature}?")
        enabled_features.append(response)
    
    # Ask about notification channel
    notification_channel = await ask_channel(ctx, "Please mention the channel for notifications (or type 'skip' to skip):")

    # Create server settings
    new_settings = ServerSettings(
        server_id=str(ctx.guild.id),
        track_status=enabled_features[0],
        track_games=enabled_features[1],
        track_voice=enabled_features[2],
        use_badges=enabled_features[3],
        notification_channel_id=str(notification_channel.id) if notification_channel else None
    )
    session.add(new_settings)
    session.commit()

    await ctx.send("Setup complete! Use `=config` to modify settings later.")

    # Create badge roles if badge system is enabled
    if enabled_features[3]:
        await create_badge_roles(ctx.guild)

    session.close()

@bot.command()
@commands.has_permissions(administrator=True)
async def config(ctx):
    session = Session()
    settings = session.query(ServerSettings).filter_by(server_id=str(ctx.guild.id)).first()
    
    if not settings:
        await ctx.send("This server hasn't been set up yet. Use `=setup` to configure the bot.")
        return

    embed = discord.Embed(title="TrackMan Configuration", color=discord.Color.blue())
    embed.add_field(name="Status Tracking", value="Enabled" if settings.track_status else "Disabled", inline=False)
    embed.add_field(name="Game Tracking", value="Enabled" if settings.track_games else "Disabled", inline=False)
    embed.add_field(name="Voice Tracking", value="Enabled" if settings.track_voice else "Disabled", inline=False)
    embed.add_field(name="Badge System", value="Enabled" if settings.use_badges else "Disabled", inline=False)
    embed.add_field(name="Notification Channel", value=f"<#{settings.notification_channel_id}>" if settings.notification_channel_id else "Not set", inline=False)

    await ctx.send(embed=embed)
    await ctx.send("To change a setting, use `=toggle <feature>` or `=setchannel <channel>`")

    session.close()

@bot.command()
@commands.has_permissions(administrator=True)
async def toggle(ctx, feature: str):
    session = Session()
    settings = session.query(ServerSettings).filter_by(server_id=str(ctx.guild.id)).first()
    
    if not settings:
        await ctx.send("This server hasn't been set up yet. Use `=setup` to configure the bot.")
        return

    feature = feature.lower()
    if feature == "status":
        settings.track_status = not settings.track_status
        state = "enabled" if settings.track_status else "disabled"
    elif feature == "games":
        settings.track_games = not settings.track_games
        state = "enabled" if settings.track_games else "disabled"
    elif feature == "voice":
        settings.track_voice = not settings.track_voice
        state = "enabled" if settings.track_voice else "disabled"
    elif feature == "badges":
        settings.use_badges = not settings.use_badges
        state = "enabled" if settings.use_badges else "disabled"
        if settings.use_badges:
            await create_badge_roles(ctx.guild)
    else:
        await ctx.send("Invalid feature. Choose from: status, games, voice, badges")
        return

    session.commit()
    await ctx.send(f"{feature.capitalize()} tracking has been {state}.")
    session.close()

@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx, channel: discord.TextChannel):
    session = Session()
    settings = session.query(ServerSettings).filter_by(server_id=str(ctx.guild.id)).first()
    
    if not settings:
        await ctx.send("This server hasn't been set up yet. Use `=setup` to configure the bot.")
        return

    settings.notification_channel_id = str(channel.id)
    session.commit()
    await ctx.send(f"Notification channel has been set to {channel.mention}")
    session.close()

async def ask_yes_no(ctx, question):
    await ctx.send(question + " (yes/no)")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        return msg.content.lower() == 'yes'
    except asyncio.TimeoutError:
        await ctx.send("No response received. Defaulting to 'no'.")
        return False

async def ask_channel(ctx, question):
    await ctx.send(question)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and (m.channel_mentions or m.content.lower() == 'skip')

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        if msg.content.lower() == 'skip':
            return None
        return msg.channel_mentions[0]
    except asyncio.TimeoutError:
        await ctx.send("No response received. Skipping channel setup.")
        return None

async def create_badge_roles(guild):
    for badge_type in BADGES.values():
        for role_name in badge_type.values():
            if not discord.utils.get(guild.roles, name=role_name):
                await guild.create_role(name=role_name)
    await guild.owner.send("Badge roles have been created for your server.")

@bot.command()
async def status(ctx, member: discord.Member = None):
    if ctx.author.id == TRACKMAN_ID:
        await ctx.send("Hey now, you can't stalk the stalker, go run away :)")
        return
    
    member = member or ctx.author
    session = Session()
    week_ago = datetime.utcnow() - timedelta(days=7)
    activities = session.query(UserActivity).filter(
        UserActivity.user_id == str(member.id),
        UserActivity.start_time >= week_ago
    ).all()
    
    status_times = {'online': 0, 'idle': 0, 'dnd': 0, 'offline': 0}
    for activity in activities:
        end_time = activity.end_time or datetime.utcnow()
        duration = (end_time - activity.start_time).total_seconds()
        status_times[activity.status] += duration
    
    embed = discord.Embed(title=f"{member.name}'s Activity", 
                          description="Activity breakdown for the past week",
                          color=discord.Color.blue())
    
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    for status, time in status_times.items():
        hours = time // 3600
        minutes = (time % 3600) // 60
        embed.add_field(name=status.capitalize(), 
                        value=f"{hours:.0f} hours, {minutes:.0f} minutes",
                        inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author.name}", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    
    await ctx.send(embed=embed)
    session.close()

@bot.command()
async def gametime(ctx, member: discord.Member = None):
    if ctx.author.id == TRACKMAN_ID:
        await ctx.send("Hey now, you can't stalk the stalker, go run away :)")
        return
    
    member = member or ctx.author
    session = Session()
    week_ago = datetime.utcnow() - timedelta(days=7)
    game_activities = session.query(GameActivity).filter(
        GameActivity.user_id == str(member.id),
        GameActivity.start_time >= week_ago
    ).all()
    
    game_times = {}
    for activity in game_activities:
        end_time = activity.end_time or datetime.utcnow()
        duration = (end_time - activity.start_time).total_seconds()
        game_times[activity.game] = game_times.get(activity.game, 0) + duration
    
    embed = discord.Embed(title=f"{member.name}'s Game Activity", 
                          description="Game time breakdown for the past week",
                          color=discord.Color.green())
    
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    for game, time in sorted(game_times.items(), key=lambda x: x[1], reverse=True):
        hours = time // 3600
        minutes = (time % 3600) // 60
        embed.add_field(name=game, 
                        value=f"{hours:.0f} hours, {minutes:.0f} minutes",
                        inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author.name}", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    
    await ctx.send(embed=embed)
    session.close()

@bot.command()
async def voicetime(ctx, member: discord.Member = None):
    if ctx.author.id == TRACKMAN_ID:
        await ctx.send("Hey now, you can't stalk the stalker, go run away :)")
        return
    
    member = member or ctx.author
    session = Session()
    week_ago = datetime.utcnow() - timedelta(days=7)
    voice_activities = session.query(VoiceActivity).filter(
        VoiceActivity.user_id == str(member.id),
        VoiceActivity.start_time >= week_ago
    ).all()
    
    total_time = 0
    for activity in voice_activities:
        end_time = activity.end_time or datetime.utcnow()
        duration = (end_time - activity.start_time).total_seconds()
        total_time += duration
    
    hours = total_time // 3600
    minutes = (total_time % 3600) // 60
    
    embed = discord.Embed(title=f"{member.name}'s Voice Activity", 
                          description="Voice channel time for the past week",
                          color=discord.Color.purple())
    
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Total Time", value=f"{hours:.0f} hours, {minutes:.0f} minutes", inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author.name}", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    
    await ctx.send(embed=embed)
    session.close()

@bot.command()
async def leaderboard(ctx, category: str):
    session = Session()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    if category == 'online':
        query = session.query(
            UserActivity.user_id,
            func.sum(func.julianday(func.coalesce(UserActivity.end_time, func.current_timestamp())) - func.julianday(UserActivity.start_time)) * 24 * 60 * 60
        ).filter(
            UserActivity.start_time >= week_ago,
            UserActivity.status == 'online',
            UserActivity.user_id != str(TRACKMAN_ID)
        ).group_by(UserActivity.user_id).order_by(func.sum(func.julianday(func.coalesce(UserActivity.end_time, func.current_timestamp())) - func.julianday(UserActivity.start_time)).desc()).limit(5)
        
        title = "Online Time Leaderboard"
        
    elif category == 'games':
        query = session.query(
            GameActivity.user_id,
            func.sum(func.julianday(func.coalesce(GameActivity.end_time, func.current_timestamp())) - func.julianday(GameActivity.start_time)) * 24 * 60 * 60
        ).filter(
            GameActivity.start_time >= week_ago,
            GameActivity.user_id != str(TRACKMAN_ID),
            GameActivity.game != "Stalking Simulator"
        ).group_by(GameActivity.user_id).order_by(func.sum(func.julianday(func.coalesce(GameActivity.end_time, func.current_timestamp())) - func.julianday(GameActivity.start_time)).desc()).limit(5)
        
        title = "Gaming Time Leaderboard"
        
    elif category == 'voice':
        query = session.query(
            VoiceActivity.user_id,
            func.sum(func.julianday(func.coalesce(VoiceActivity.end_time, func.current_timestamp())) - func.julianday(VoiceActivity.start_time)) * 24 * 60 * 60
        ).filter(
            VoiceActivity.start_time >= week_ago,
            VoiceActivity.user_id != str(TRACKMAN_ID)
        ).group_by(VoiceActivity.user_id).order_by(func.sum(func.julianday(func.coalesce(VoiceActivity.end_time, func.current_timestamp())) - func.julianday(VoiceActivity.start_time)).desc()).limit(5)
        
        title = "Voice Channel Time Leaderboard"
    
    else:
        await ctx.send("Invalid category. Choose 'online', 'games', or 'voice'.")
        return
    
    results = query.all()
    
    embed = discord.Embed(title=title, 
                          description="Top 5 users for the past week",
                          color=discord.Color.gold())
    
    for i, (user_id, time) in enumerate(results, 1):
        user = ctx.guild.get_member(int(user_id))
        if user:
            hours = time // 3600
            minutes = (time % 3600) // 60
            embed.add_field(name=f"{i}. {user.name}", 
                            value=f"{hours:.0f} hours, {minutes:.0f} minutes",
                            inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author.name}", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    
    await ctx.send(embed=embed)
    session.close()

@bot.command()
async def mostplayedgame(ctx):
    session = Session()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    query = session.query(
        GameActivity.game,
        func.sum(func.julianday(func.coalesce(GameActivity.end_time, func.current_timestamp())) - func.julianday(GameActivity.start_time)) * 24 * 60 * 60
    ).filter(
        GameActivity.start_time >= week_ago,
        GameActivity.game != "Stalking Simulator"
    ).group_by(GameActivity.game).order_by(func.sum(func.julianday(func.coalesce(GameActivity.end_time, func.current_timestamp())) - func.julianday(GameActivity.start_time)).desc()).first()
    
    if query:
        game, time = query
        hours = time // 3600
        minutes = (time % 3600) // 60
        
        embed = discord.Embed(title="Most Played Game", 
                              description=f"For the past week",
                              color=discord.Color.orange())
        
        embed.add_field(name=game, value=f"{hours:.0f} hours, {minutes:.0f} minutes", inline=False)
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("No game activity recorded in the past week.")
    
    session.close()

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="Pong! 🏓", 
                          description=f"Latency: **{latency}ms**",
                          color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name='commands')
async def show_commands(ctx):
    embed = discord.Embed(title="TrackMan Commands", 
                          description="Here are the available commands:",
                          color=discord.Color.purple())
    
    commands_list = [
        ("=status [@user]", "Shows a user's online activity breakdown"),
        ("=gametime [@user]", "Shows a user's game activity"),
        ("=voicetime [@user]", "Shows a user's voice channel activity"),
        ("=leaderboard <category>", "Shows leaderboard for online, games, or voice"),
        ("=mostplayedgame", "Shows the most played game on the server"),
        ("=ping", "Checks bot's latency"),
        ("=commands", "Displays this help message"),
        ("=setup", "Initial bot setup (admin only)"),
        ("=config", "View current bot configuration (admin only)"),
        ("=toggle <feature>", "Toggle a feature on/off (admin only)"),
        ("=setchannel <channel>", "Set notification channel (admin only)")
    ]
    
    for command, description in commands_list:
        embed.add_field(name=command, value=description, inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author.name}", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    
    await ctx.send(embed=embed)

bot.run(TOKEN)