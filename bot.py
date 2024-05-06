import os
import sys
import asyncio
from datetime import datetime, time, timedelta
import pytz
import asyncpg
import random
from copy import deepcopy

import discord
import discord.ext.commands as extra
from discord.ext import commands, tasks

from my_utils import *


sys.stdout = open(last_log, 'a')
# redirect stderr after connecting to discord to avoid spamming the error log with connection messages

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
intents = discord.Intents.default()
client = discord.Client(intents=intents)


async def has_permission(id: int, ctx: commands.Context = None):
    """Check if caller has perms to use command. Only Sam or Bizzy can use commands that call this function."""
    if (id not in admin_ids):
        if (ctx != None):
            await ctx.send(f'You do not have permission to use this command', ephemeral=True)
        return False

    return True

@bot.event
async def on_ready():
    global last_log_date
    sys.stderr = open(f'./logs/{last_log_date}_stderr.log', 'a')

    eventreminders.add_exception_type(asyncpg.PostgresConnectionError)
    eventreminders.start()
    syncreminders.start()
    latest_log.start()

    log(f'Bot "{bot.user.name}" has connected to Discord. Starting log')

    log("Syncing reminders and events\n")


#check ---------------------Command List-----------------------------
@bot.tree.command(name="commands", description="Display all bot commands. Usage: /commands", guilds=[discord.Object(id=val_server)])
@discord.app_commands.choices(
    short=[
        discord.app_commands.Choice(name="(Optional) Shorten", value=1),
    ]
)
@discord.app_commands.describe(
    short="Whether to display the full list of commands or a shortened list"

)
async def commands(interaction: discord.Interaction, short: typing.Optional[int] = 0):
    """Displays all bot commands. Usage: `/commands`"""
    if (interaction.channel.id not in [debug_channel, bot_channel]):
        return

    target_role = prem_role if interaction.guild.id == val_server else debug_role
    target_role = discord.utils.get(interaction.guild.roles, name=target_role)

    common_commands = [   "**Commands**:",
                          "- **HELP**:",
                          " - **/commands** - _Display all bot commands_",
                          " - **!help** - _(WIP. use at your own risk) Displays better and more detailed help message_",

                          "- **INFO**:",
                          " - **/schedule** - _Display the premier event schedule_",
                          " - **/mappool** - _Display the current competitive map pool_",
                          " - **/mapvotes** - _Display each member's map vote_",
                          " - **/mapweights** - _Display the total weights for each map_",

                          "- **VOTING**:",
                          " - **prefermaps <map name> +/~/-** - _Vote for a map with a weight of +/~/- (want/neutral/don't want)_",
                          " - **prefermaps maps** - _Display all maps available for voting (all maps in the game, not just the competitive map pool)_",]
    
    fun_commands = [      '- **"FUN"**:',
                          " - **/hello** - _Say hello_",
                          " - **/feed** - _Feed the bot_",
                          " - **/unfeed** - _Unfeed the bot_",]

    admin_commands = [    "- **ADMIN ONLY**:",
                          f" - **/role add/remove <@member>** (__admin__) - _Add or remove the '{target_role.mention}' role from a member_",
                          f" - **/remind <interval> (s)econd/(m)inute/(h)our <message>** (__admin__) - _Set a reminder for the '{target_role.mention}' role_",
                          " - **/mappool [clear | (add/remove <map name>]** (__admin__) - _Modify the map pool_",
                          " - **/cancelevent <map_name> [all]** (__admin__) - _Cancel a premier map for today/all days_",
                          " - **/clear <amount> [bot/user/both]** (__admin__) - _Clear the last <amount> **commands** from the chat from the bot, user, or both. Defaults to last message sent._",]

    my_commands = [       "- **BIZZY ONLY**:",
                          " - **!sync** (__Bizzy__) - _Initialize the slash commands_",
                          " - **/sync** (__Bizzy__) - _Update the slash commands (ensure that they have been initialized first)_",
                          " - **!clearslash** (__Bizzy__) - _Clear all slash commands_",
                          " - **/clearlogs [all/all_logs]** (__Bizzy__) - _Clear the stdout log(s)_",
                          " - **/kill [reason]** (__Bizzy__) - _Kill the bot_"
                   ]

    output = common_commands

    if(not short):
        if (interaction.user.id in admin_ids):
            output += admin_commands

        if (interaction.user.id == my_id):
            output += my_commands

        output += fun_commands
    
    await interaction.response.send_message('\n'.join(output), ephemeral=True, silent=True)

#check --------------------Useless commands--------------------------
@bot.tree.command(name="hello", description="Says hello. Usage: /hello", guilds=[discord.Object(id=val_server)])
async def hello(interaction: discord.Interaction):
    """Says hello. Usage: `/hello`"""

    await interaction.response.send_message(f'Hello {interaction.user.mention}!', ephemeral=True)


@bot.tree.command(name="feed", description="Feed the bot. Usage: /feed", guilds=[discord.Object(id=val_server)])
async def feed(interaction: discord.Interaction):
    """Feed the bot. Usage: `/feed`"""
    await interaction.response.send_message(f'Yum yum! Thanks for the food!', ephemeral=True)


@bot.tree.command(name="unfeed", description="Unfeed the bot. Usage: /unfeed", guilds=[discord.Object(id=val_server)])
async def unfeed(interaction: discord.Interaction):
    """Unfeed the bot. Usage: `/unfeed`"""

    options = ["pukes", "poops", "performs own liposuction"]

    option = options[random.randint(0, len(options) - 1)]

    await interaction.response.send_message(f'\*looks at you with a deadpan expression\* ... \*{option}\*', ephemeral=True)

#check ------------------Functional commands-------------------------
@bot.tree.command(name="role", description="Add or remove the premier role from a member. Usage: /role {add|remove} <@member>", guilds=[discord.Object(id=val_server)])
@discord.app_commands.choices(
    action=[
        discord.app_commands.Choice(name="Add", value="add"),
        discord.app_commands.Choice(name="Remove", value="remove"),
    ],
)
@discord.app_commands.describe(
    action="What to do with the role",
    member="The member act on"
)
async def role(interaction: discord.Interaction, action: str, member: discord.Member):
    """Add or remove the premier role from a member. Usage: /role {add|remove} <display_name>"""

    usage = "Usage: `/role {add|remove} @member`"

    if (not await has_permission(interaction.user.id, interaction)):
        return
    
    if (interaction.channel.id not in [debug_channel, bot_channel]):
        await wrong_channel(interaction)
        return
    

    role = discord.utils.get(interaction.guild.roles, name=prem_role) if interaction.guild.id == val_server else discord.utils.get(
        interaction.guild.roles, name=debug_role)

    notif_channel = bot.get_channel(
        prem_channel) if interaction.guild.id == val_server else bot.get_channel(debug_channel)

    rats = discord.utils.get(interaction.guild.roles, name="Rathole").members

    if action == "add":
        if member in rats:
            await interaction.response.send_message(f'{member.display_name} is already in the rathole', ephemeral=True)
            return
        await member.add_roles(role)
        log(f'Added {member.display_name} to {role.name}')
        await notif_channel.send(f'Welcome to the rathole {member.mention}')
    elif action == "remove":
        if member not in rats:
            await interaction.response.send_message(f'{member.display_name} was not found in the rathole', ephemeral=True)
            return
        await member.remove_roles(role)
        await interaction.response.send_message(f'{member.mention} has been removed from the rathole', ephemeral=True)
        log(f'Removed {member.display_name} from {role.name}')

@bot.tree.command(name="remind", description="Set a reminder for the target role. Usage: /remind <interval> (s)econd/(m)inute/(h)our <message>", guilds=[discord.Object(id=val_server)])
@discord.app_commands.choices(
    unit = [
        discord.app_commands.Choice(name="Hours", value="hours"),
        discord.app_commands.Choice(name="Minutes", value="minutes"),
        discord.app_commands.Choice(name="Seconds", value="seconds"),
    ]
)
@discord.app_commands.describe(
    interval="The number of units to wait for the reminder",
    unit="The unit of time associated with the interval",
    message="The reminder message to send to the premier role"
)
async def remind(interaction: discord.Interaction, interval: int = 0, unit: str = "", *, message: str = ""):
    """Set a reminder for the target role. Usage: /remind <interval> (s)econd/(m)inute/(h)our <message>"""
    
    if (not await has_permission(interaction.user.id, interaction)):
        return
    
    if (interaction.channel.id not in [bot_channel, debug_channel]):
        await wrong_channel(interaction)
        return

    if (interval <= 0):
        await interaction.response.send_message(f'Please provide a valid interval greater than 0', ephemeral=True)
        return
    
    if (message == ""):
        await interaction.response.send_message(f'Please provide a reminder message', ephemeral=True)
        return

    current_time = datetime.now()

    g = interaction.guild
    r = prem_role if g.id == val_server else debug_role
    role = discord.utils.get(g.roles, name=r)

    message = f"(reminder) {role.mention} {message}"
    output = ""

    if unit == "seconds":
        output = f'(reminder) I will remind {role} in {interval} second(s) with the message: "{message}"'
        when = current_time + timedelta(seconds=interval)
    elif unit == "minutes":
        when = current_time + timedelta(minutes=interval)
        output = f'(reminder) I will remind {role} in {interval} minute(s) with the message: "{message}"'
        interval *= 60
    elif unit == "hours": # could be else, but elif for clarity
        when = current_time + timedelta(hours=interval)
        output = f'(reminder) I will remind {role} in {interval} hour(s) with the message: "{message}"'
        interval *= 3600

    await interaction.response.send_message(output, ephemeral=True)

    dt_when = datetime.fromtimestamp(when.timestamp()).isoformat()

    reminders[str(g.id)].update(
        {dt_when: message})

    save_reminders(reminders)

    log(f"Saved a reminder from {interaction.user.display_name}: {output}")
    
    reminder_channel = bot.get_channel(
        prem_channel) if g.id == val_server else bot.get_channel(debug_channel)

    await asyncio.sleep(interval)

    await reminder_channel.send(message)
    log("Posted reminder: " + message)

    del reminders[str(g.id)][dt_when]
    save_reminders(reminders)


@bot.tree.command(name="pin", description="Pin a message. Usage: /pin <message_id>", guilds=[discord.Object(id=val_server)])
@discord.app_commands.describe(
    message_id="The ID of the message to pin"
)
async def pin(interaction: discord.Interaction, message_id: str = ""):
    """Pin a message. Usage: `/pin <message_id>`"""
    if (not await has_permission(interaction.user.id, interaction)):
        return
    
    if(message_id == ""):
        await interaction.response.send_message(f'Please provide a message ID. Usage: `/pin <message_id>`', ephemeral=True)
        return

    try:
        message_id = int(message_id)
        message = await interaction.channel.fetch_message(message_id)
    except (ValueError, discord.errors.NotFound):
        await interaction.response.send_message(f'Invalid message ID. Usage: `/pin <message_id>`', ephemeral=True)
        return

    await message.pin()

    # wait for the message to be pinned before deleting the command message
    await asyncio.sleep(1)

    async for message in interaction.channel.history(limit=10):
        if message.type == discord.MessageType.pins_add and bot.user.display_name in message.content:
            await message.delete()  # delete the pinned notification message
            break

    await interaction.response.send_message(f'Message pinned', ephemeral=True)

    log(f'{interaction.user.display_name} pinned message {message_id}')


@bot.tree.command(name="unpin", description="Unpin a message. Usage: /unpin <message_id>", guilds=[discord.Object(id=val_server)])
@discord.app_commands.describe(
    message_id="The ID of the message to unpin"
)
async def unpin(interaction: discord.Interaction, message_id: str = ""):
    """Unpin a message. Usage: `/unpin <message_id>`"""
    if (not await has_permission(interaction.user.id, interaction)):
        return
    
    if(message_id == ""):
        await interaction.response.send_message(f'Please provide a message ID. Usage: `/unpin <message_id>`', ephemeral=True)
        return

    try:
        message_id = int(message_id)
        message = await interaction.channel.fetch_message(message_id)
    except (ValueError, discord.errors.NotFound):
        await interaction.response.send_message(f'Invalid message ID. Usage: `/unpin <message_id>`', ephemeral=True)
        return

    await message.unpin()

    await interaction.response.send_message(f'Message unpinned', ephemeral=True)

    log(f'{interaction.user.display_name} unpinned message {message_id}')


# --------------------Premier commands--------------------------
@bot.tree.command(name="schedule", description="Display the premier schedule. Usage: /schedule", guilds=[discord.Object(id=val_server)])
async def schedule(interaction: discord.Interaction):
    """Display the premier schedule. Usage: /schedule"""
    if (interaction.channel.id not in all_channels):
        await wrong_channel(interaction)
        return

    guild = bot.get_guild(
        val_server) if interaction.guild.id == val_server else bot.get_guild(debug_server)
    events = guild.scheduled_events

    message = "Upcoming Premier Events:\n"
    for event in events:
        message += f"{event.name}: {event.description} at {discord_local_time(event.start_time)}\n"

    ephem = True if interaction.channel.id == bot_channel else False

    await interaction.response.send_message(message, ephemeral=ephem)


@bot.tree.command(name="mappool", description="Add or remove maps from the map pool. Usage: /mappool [clear | (add/remove <map name>]", guilds=[discord.Object(id=val_server)])
@discord.app_commands.choices(
    action=[
        discord.app_commands.Choice(name="Add", value="add"),
        discord.app_commands.Choice(name="Remove", value="remove"),
        discord.app_commands.Choice(name="Clear", value="clear"),
    ],

    _map=[
        # mappool only has maps that are currently playable, need to get all maps
        discord.app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
    ]
)
@discord.app_commands.describe(
    action="The action to take on the map pool",
    _map="The map to add or remove"
)
async def mappool(interaction: discord.Interaction, action: str = "", _map: str = ""):
    """Add or remove maps from the map pool. Usage: /mappool [clear | (add/remove <map name>]"""
    if (interaction.channel.id not in all_channels):
        await wrong_channel(interaction)
        return

    if action == "" and _map == "":
        ephem = True if interaction.channel.id == bot_channel else False # when listing the map pool, don't make it ephemeral in the premier channel so it can be seen by everyone
        
        if (len(map_pool) == 0):
            output = f'The map pool is empty'
        else:
            output = f'Current map pool: {", ".join(map_pool)}'
        
        await interaction.response.send_message(output, ephemeral=ephem)
        return

    if (not await has_permission(interaction.user.id, interaction)):
        return
    
    if interaction.channel.id != bot_channel:
        wrong_channel(interaction)
        return

    if action == "" or _map == "" or action != "clear": # clear doesn't need a map
        await interaction.response.send_message(f'Please provide an action and a map. Usage: `/mappool [clear | (add/remove <map name>]`', ephemeral=True)
        return

    output = ""

    if action == "clear":
        map_pool.clear()
        output = f'The map pool has been cleared'
        log_message = f'{interaction.user.display_name} has cleared the map pool'
    elif action == "add":
        if _map not in map_pool:
            map_pool.append(_map)
            output = f'{_map} has been added to the map pool'
            log_message = f'{interaction.user.display_name} has added {_map} to the map pool'
        else:
            await interaction.response.send_message(f'{_map} is already in the map pool', ephemeral=True)
            return
    elif action == "remove":
        if _map in map_pool:
            map_pool.remove(_map)
            output = f'{_map} has been removed from the map pool'
            log_message = f'{interaction.user.display_name} has removed {_map} from the map pool'
        else:
            await interaction.response.send_message(f'{_map} is not in the map pool', ephemeral=True)
            return
    else:
        await interaction.response.send_message(f'Invalid action. Usage: `/mappool [clear | (add/remove <map name>]`', ephemeral=True)
        return

    ephem = True
    if (interaction.channel.id == prem_channel):
        ephem = False  # when modifying/listing the map pool, don't make it ephemeral in the premier channel so it can be seen by everyone

    await interaction.response.send_message(output, ephemeral=ephem)

    log(log_message)

    save_pool(map_pool)


@bot.tree.command(name="prefermaps", description="Mark your preferences for each map. Usage: /prefermaps <map name> +/~/-", guilds=[discord.Object(id=val_server)])
@discord.app_commands.choices(
    _map=[
        discord.app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
    ],

    preference=[
        discord.app_commands.Choice(name="Like/Will Play", value="+"),
        discord.app_commands.Choice(name="Neutral/Don't Care", value="~"),
        discord.app_commands.Choice(name="Dislike/Won't Play", value="-"),
    ]

)
@discord.app_commands.describe(
    _map="The map to vote for",
    preference="Your preference for the map"
)
async def prefermaps(interaction: discord.Interaction, _map: str = "", preference: str = ""):
    """Mark preferences for each map"""
    global map_preferences
    global map_weights
    if (interaction.channel.id not in [bot_channel, debug_channel]):
        await interaction.response.send_message(f'You cannot vote in this channel', ephemeral=True)
        return

    if _map == "" or preference == "":
        await interaction.response.send_message(f'Please provide a map and a preference.', ephemeral=True)
        return

    output = ""
    preferences = {"+":"like", "~":"neutral", "-":"dislike"}

    _map = _map.lower()

    old_preferences = ""
    if (str(interaction.user.id) in map_preferences[_map]): # if you've voted for this map before
        old_preferences = map_preferences[_map][str(interaction.user.id)]
        if (old_preferences == preference):
            await interaction.response.send_message(f'{interaction.user.mention} you have already marked {_map.title()} with a weight of {preferences[preference]}', ephemeral=True)
            return

        output = f'{interaction.user.mention}\'s vote for {_map.title()} has been changed from {preferences[old_preferences]} to {preferences[preference]}'
        old_preferences = 1 if old_preferences == "" else 0 if old_preferences == "~" else -1
        map_weights[_map] -= old_preferences

    map_preferences[_map][str(interaction.user.id)] = preference
    if (old_preferences == ""):
        output = f'{interaction.user.mention} voted for {_map.title()} with a weight of {preference}'
    preference = 1 if preference == "+" else 0 if preference == "~" else -1
    map_weights[_map] += preference

    await interaction.response.send_message(output, ephemeral=True)
    
    log(output)

    save_prefrences(map_preferences)
    save_weights(map_weights)


@bot.tree.command(name="mapvotes", description="Display the map votes for each user. Usage: /mapvotes", guilds=[discord.Object(id=val_server)])
async def mapvotes(interaction: discord.Interaction):
    """Display the map votes for each user. Usage: /mapvotes"""
    global map_preferences
    if (interaction.channel.id not in all_channels):
        await wrong_channel(interaction)
        return

    role = prem_role if interaction.guild.id == val_server else debug_role
    all_users = discord.utils.get(interaction.guild.roles, name=role).members

    output = ""

    for _map in map_pool:
        header = f'- {_map.title()}:\n'
        body = ""
        for user in all_users:
            if str(user.id) in map_preferences[_map]:
                body += f' - {user.mention}: {map_preferences[_map][str(user.id)]}\n'
            
            if (body == ""):
                body = "No votes for this map."
            
        output += header + body
        

    if (output == ""):
        output = "No votes for any maps in the map pool."

    ephem = True if interaction.channel.id == bot_channel else False

    await interaction.response.send_message(output, ephemeral=ephem, silent=True)


@bot.tree.command(name="mapweights", description="Display the map weights (sorted). Usage: /mapweights", guilds=[discord.Object(id=val_server)])
async def mapweights(interaction: discord.Interaction):
    """Display the map weights (sorted). Usage: /mapweights"""
    global map_weights
    if (interaction.channel.id not in all_channels):
        await wrong_channel(interaction)
        return

    output = ""

    map_weights = dict(sorted(map_weights.items(
    ), key=lambda item: item[1], reverse=True))  # sort the weights in descending order

    for _map in map_weights.keys():
        if _map not in map_pool:
            continue

        output += f'{_map.title()}: {map_weights[_map]}\n'

    if (output == ""):
        output = "No weights to show for maps in the map pool."

    ephem = True if interaction.channel.id == bot_channel else False

    await interaction.response.send_message(output, ephemeral=ephem)

@bot.tree.command(name="addevents", description="Add all prem events to the schedule. Usage: /addevent <map_list> <date>", guilds=[discord.Object(id=val_server)])
# @discord.app_commands.choices(
#     map_list=[
#         discord.app_commands.Choice(name=m, value=m) for m in map_pool
#     ]
# )
@discord.app_commands.describe(
    map_list="The map order enclosed in quotes with each map separated with a space (e.g. 'map1 map2 map3')",
    date="The date (mm/dd) of the Thursday that starts the first event. Events will be added for Thursday, Saturday, and Sunday."
)
async def addevents(interaction: discord.Interaction, map_list: str, date: str):
    '''Add all prem events to the schedule. Usage: /addevent "<map1> <map2> ..." <mm/dd>
    
        Parameters
        ----------
        map_list : str
            The map order enclosed in quotes with each map separated with a space (e.g. "map1 map2 map3")
        date : str
            The date (mm/dd) of the Thursday that starts the first event. Events will be added for Thursday, Saturday, and Sunday.
    '''
    
    if (not await has_permission(interaction.user.id, interaction)): # don't need to send a message here, has_permission will do it
        return
    
    if (interaction.channel.id not in [bot_channel, debug_channel]):
        await wrong_channel(interaction)
        return

    
    guild = interaction.guild
    events = guild.scheduled_events
    scheduledMaps = []
    newMaps = "".join(map_list.split(",")).split() # remove commas and split by space
    log(str(newMaps))


    prem_length = len(newMaps)
    input_date = tz.localize(datetime.strptime(date, "%m/%d").replace(year=datetime.now().year))
    thur_time = datetime(year=datetime.now().year, month=input_date.month, day=input_date.day, hour=22, minute=0, second=0)
    sat_time = (thur_time + timedelta(days=2)).replace(hour=23)
    sun_time = (thur_time + timedelta(days=3))

    weekday = input_date.weekday()

    start_times = [tz.localize(d) for d in [thur_time, sat_time, sun_time]]

    if weekday != 3:
        await interaction.response.send_message(f'Invalid day. Please provide a Thursday date (mm/dd)', ephemeral=True)
        return

    for event in events:
        if(event.creator_id == bot.user.id):
            await event.delete()
            continue
    
        scheduledMaps.append(event.description)

    
    vc_object = discord.utils.get(guild.voice_channels, id=voice_channel) if interaction.channel.id == bot_channel else discord.utils.get(guild.voice_channels, id=1217649405759324236)

    for _map in newMaps:
        _map = _map.lower()
        if _map not in map_pool:
            await interaction.response.send_message(f'{_map} is not in the map pool. I only add premier events. (skipping)', ephemeral=True)
            continue
        
        _map = _map.title()
        if _map in scheduledMaps:
            await interaction.response.send_message(f'{_map} is already in the schedule. (skipping)', ephemeral=True)
            continue

        for start_time in start_times:
            await guild.create_scheduled_event(name="Premier", description=_map, channel=vc_object,
                                            start_time=start_time, end_time=start_time + timedelta(hours=1),
                                            entity_type=discord.EntityType.voice, privacy_level=discord.PrivacyLevel.guild_only)
        
        start_times = [start_time + timedelta(days=7) for start_time in start_times]
        
    await interaction.response.send_message(f'Added {prem_length} premier map(s) to the schedule', ephemeral=True)
    log(f'{interaction.user.display_name} has posted the premier schedule starting on {date} with maps: {", ".join(newMaps)}')

#check -------------------------Tasks--------------------------------
@tasks.loop(time=premier_reminder_times)
async def eventreminders():
    """Send reminders for upcoming events"""

    log("Checking for event reminders")

    guild = bot.get_guild(val_server)
    prem_events = guild.scheduled_events

    debug_guild = bot.get_guild(debug_server)
    debug_events = debug_guild.scheduled_events

    current_time = datetime.now(pytz.utc).time()

    current_day = datetime.now().weekday() # get current day based on my timezone

    if current_day not in [3,5,6]: # only check for events on thursday, saturday, and sunday
        return  

    log(f"Checking for reminders at {current_time}")
    for event in list(prem_events) + list(debug_events):
        g = event.guild
        r = prem_role if g.id == val_server else debug_role
        role = discord.utils.get(g.roles, name=r)
        subbed_users = []
        async for user in event.users():
            subbed_users.append(user)

        start_time = event.start_time
        current_time = datetime.now(pytz.utc)

        time_remaining = (start_time - current_time).total_seconds()

        reminder_messages = {premier_reminder_classes[0]: f"(reminder) {role.mention} {event.name} on _{event.description}_ has started (at {discord_local_time(start_time)}). JOIN THE VC!",
                             premier_reminder_classes[1]: f"(reminder) {role.mention} {event.name} on _{event.description}_ is starting in 10 minutes (at {discord_local_time(start_time)})! JOIN THE VC!",
                             premier_reminder_classes[2]: f"(reminder) {role.mention} {event.name} on _{event.description}_ is starting in 1 hour (at {discord_local_time(start_time)})! Make sure you have RSVP'ed if you're joining!",
                             premier_reminder_classes[3]: f"(reminder) {role.mention} {event.name} on _{event.description}_ is today at {discord_local_time(start_time)}! Make sure you have RSVP'ed if you're joining!"}

        reminder_class = ""
        if time_remaining <= 0:  # allow this reminder until 30 minutes after the event has already started
            if time_remaining >= -3600 * .5:
                reminder_class = "start"
            elif time_remaining <= -3600 * 1:  # remove the event
                await event.cancel()
        elif time_remaining <= 60 * 10:
            reminder_class = "prestart"
        elif time_remaining <= 3600:
            reminder_class = "hour"
        elif time_remaining <= 3600 * 3:
            reminder_class = "day"


        if reminder_class != "":  # there is an event reminder to send
            log_message = f"Posted '{reminder_class}' reminder for event: {event.name} on {event.description} starting at {start_time.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')} EST"
              
            with open(last_log, "r") as file:
                log_contents = file.read()
            
            if(log_message in log_contents): # if the reminder has already been posted, skip it
                    continue

            message = reminder_messages[reminder_class]
            
            channel = bot.get_channel(
                prem_channel) if g.id == val_server else bot.get_channel(debug_channel)
            
            is_silent = True if len(subbed_users) >= 5 and reminder_class == "hour" else False

            if (len(subbed_users) < 5): # if we don't have enough people, actually ping the role
                message += f"\nWe don't have enough people for {event.name} on _{event.description}_ yet!"
                message += " Please RSVP before it's too late!" if reminder_class not in ["start", "prestart"] else " Please join the VC so we can start!"
                is_silent = False
            
            if is_silent:
                message += "\n\n(This message was sent silently)"

            await channel.send(message, silent=is_silent)
            
            log(log_message)

            if len(subbed_users) > 0:
                message = " RSVP'ed users: \n" + \
                    "- " + "\n- ".join([user.mention for user in subbed_users])
            else:
                message = "No one has RSVP'ed yet."

            message += "\n\n(This message was sent silently)"
                
            await channel.send(message, silent=True)

@tasks.loop(count=1)
async def syncreminders():
    """Resync reminder timers in case the bot went offline """
    global reminders

    iterable = deepcopy(reminders)

    for server in iterable.keys():
        for time, message in iterable[server].items():
            channel = bot.get_channel(
                prem_channel) if server == str(val_server) else bot.get_channel(debug_channel)

            time_dt = datetime.fromisoformat(time)

            if (time_dt < datetime.now()):
                await channel.send(message + "\n(bot was offline when this reminder was supposed to go off at " + discord_local_time(time_dt) + ".")
                log("Bot missed a reminder during its downtime, but sent it now. Message: " + message)
                reminders[server].pop(time)
            else:
                await asyncio.sleep((time_dt - datetime.now()).total_seconds())
                await channel.send(message)
                log("Posted reminder: " + message)
                reminders[server].pop(time)

        save_reminders(reminders)

## wait until 1 minute after midnight to start new log in case of delay
@tasks.loop(time=est_to_utc(time(hour=0, minute=1, second=0)))
async def latest_log():

    """Create a new log file at midnight"""
    global last_log
    global last_log_date

    log_date = datetime.now().strftime("%Y-%m-%d")

    if log_date != last_log_date:
        log("Starting new log file")
        last_log_date = log_date
        last_log = f"./logs/{last_log_date}_stdout.log"
        sys.stdout.close()
        sys.stdout = open(last_log, 'a')

#check -----------------Bizzy/Delicate Commands----------------------
@bot.tree.command(name="cancelevent", description="Cancel an event. Usage: /cancelevent <map_name> [all]", guilds=[discord.Object(id=val_server)])
@discord.app_commands.choices(
    amount=[
        discord.app_commands.Choice(name="(Optional) All", value="all"),
    ]
)
@discord.app_commands.describe(
    _map="The map to cancel the latest event for",
    amount="Cancel all events for the specified map"
)
async def cancelevent(interaction: discord.Interaction, _map: str = "", amount: typing.Optional[str] = ""):
    """Cancel an event. Usage: /cancelevent <map_name> [all]"""

    if (not await has_permission(interaction.user.id, interaction)):
        return
    
    if (interaction.channel.id not in [bot_channel, debug_channel]):
        await wrong_channel(interaction)
        return
    

    _map = _map.lower()
    amount = amount.lower()

    if _map == "":
        await interaction.response.send_message(f'Please provide a map. Usage: `/cancelevent <map_name> [all]`', ephemeral=True)
        return

    if _map not in map_pool:
        await interaction.response.send_message(f'{_map.title()} is not in the map pool. I only cancel premier events.', ephemeral=True)
        return

    guild = interaction.guild
    events = guild.scheduled_events

    if (amount != "all" and amount != ""):
        await interaction.response.send_message(
            f"Invalid amount. Usage: `/cancelevent <map_name> [all]`.", ephemeral=True)
        return

    for event in events:
        if event.description.lower() == _map:
            await event.cancel()
            await event.end()
            log(f'{interaction.user.display_name} cancelled event - {event.name} on {event.description} for {event.start_time.date()}')
            if (amount != "all"):
                break
    
    message = f'{event.name} on {event.description} for {event.start_time.date()} has been cancelled' if amount != "all" else f'All events on {event.description} have been cancelled'
    await interaction.response.send_message(message, ephemeral=True)

    log(f"{interaction.user.display_name} cancelled event - {event.name} on {event.description} for {event.start_time.date()}")


@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def clear(ctx, amount: int = 1, usertype: str = "both"):
    """Clear chats from <usertype> in the last 200 messages. Usage: `/clear <amount> [bot/user/both]`"""
    if (ctx.channel.id == debug_channel):  # just nuke the debug channel
        await ctx.channel.purge()
        return
    
    if not await has_permission(ctx.author.id, ctx):
        return

    if (ctx.channel.id not in all_channels):
        await wrong_channel(ctx)
        return

    if (usertype not in ["bot", "user", "both"]):
        await ctx.send(f'Invalid type. Usage: `/clear <amount> [bot/user/both]`', ephemeral=True)
        return

    amount += 1  # include the command message

    if (amount < 1):
        return

    messages = []
    async for message in ctx.channel.history(limit=200):
        # don't delete reminders
        if (usertype == "bot" and message.author == bot.user and message.content[0:10] != "(reminder)"):
            messages.append(message)
        elif (usertype == "user" or usertype == "both"):
            # don't delete regular chat
            # if a message is from a user and not a command, don't delete it
            if (not message.content.startswith("!") and message.author.id != bot.user.id):
                continue
            messages.append(message)

        if (len(messages) >= amount):
            break

    await ctx.channel.delete_messages(messages)

    messages.pop(0)  # don't log the command message

    for message in messages:  # log the deleted messages
        with open(f"./logs/chat_deletion.log", 'a') as file:
            creation_time = message.created_at.astimezone(
                tz).strftime("%Y-%m-%d %H:%M:%S")

            deletion_time = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")

            file.write(
                f'[{creation_time} EST] {message.author}: "{message.content}"\t| deleted by {ctx.author} at {deletion_time} EST\n')


@bot.hybrid_command(aliases=["clearlog", "clear_logs", "clear_log"])
@discord.app_commands.guilds(discord.Object(id=val_server))
async def clearlogs(ctx, all_logs: str = ""):
    """Clear the stdout log for today, or all logs. Usage: `/clear_log [all/all_logs]`"""
    global last_log

    if (ctx.author.id != my_id):
        await ctx.send(f'You do not have permission to use this command', ephemeral=True)
        return

    if (ctx.channel.id not in [debug_channel, bot_channel]):
        return

    if (all_logs != "" and all_logs not in ["all", "all_logs"]):
        await ctx.send(f'Invalid argument. Usage: `/clear_logs [all/all_logs]`', ephemeral=True)
        return

    message = "Log cleared"

    if (all_logs):  # empty string is false and we already checked for "all" if it's not empty
        for file in os.listdir('./logs'):
            if not file.endswith("stdout.log"):
                continue
            with open(f'./logs/{file}', 'w') as file:
                file.write(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    
    message = "All stdout logs cleared"

    log(f"{message}")

    await ctx.send(message, ephemeral=True)


@bot.command()
async def clearslash(ctx):
    """Clear all slash commands. Usage: `!clearslash`"""
    if (ctx.author.id != my_id or ctx.channel.id not in [debug_channel, bot_channel]):
        await ctx.send(f'You do not have permission to use this command', ephemeral=True)
        return


    g = discord.Object(id=val_server)

    ctx.bot.tree.clear_commands(guild=g)
    await ctx.bot.tree.sync(guild=g)

    log(f"All Bot commands cleared in the val server")

    await ctx.send(f'Cleared all slash commands')


@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def sync(ctx):
    """Add slash commands specific to this server. Only run this when commands are updated Usage: `!sync`"""
    if (ctx.channel.id not in [debug_channel, bot_channel] or ctx.author.id != my_id):
        return

    synced = await ctx.bot.tree.sync(guild=discord.Object(id=val_server))
    await ctx.send(f'Commands synced: {len(synced)}', ephemeral=True)

    log(f"Bot commands synced for {ctx.guild.name}")


@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def kill(ctx, *, reason: str = "no reason given"):
    """Kill the bot. Usage: `/kill`"""
    if not await has_permission(ctx.author.id, ctx):
        return

    if ctx.channel.id not in [debug_channel, bot_channel]:
        return

    await ctx.send(f'Goodbye cruel world!', ephemeral=True)

    log(
        f"Bot killed for reason: {reason}")

    await bot.close()


bot.run(bot_token)
