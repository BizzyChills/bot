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


# ---------------------Command List-----------------------------
@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def commands(ctx, short: bool = False):
    """Displays all bot commands. Usage: `/commands`"""
    if (ctx.channel.id not in [debug_channel, bot_channel]):
        return

    target_role = prem_role if ctx.guild.id == val_server else debug_role
    target_role = discord.utils.get(ctx.guild.roles, name=target_role)
    # header = "**Commands**:"

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
                          " - **/votemap <map name> +/~/-** - _Vote for a map with a weight of +/~/- (want/neutral/don't want)_",
                          " - **/votemap maps** - _Display all maps available for voting (all maps in the game, not just the competitive map pool)_",]
    
    fun_commands = [      '- **"FUN"**:',
                          " - **/hello** - _Say hello_",
                          " - **/feed** - _Feed the bot_",
                          " - **/unfeed** - _Unfeed the bot_",]

    admin_commands = ["- **ADMIN ONLY**:",
                          f" - **/role add/remove <@member>** (__admin__) - _Add or remove the '{target_role.mention}' role from a member_",
                          f" - **/remind <interval> (s)econd/(m)inute/(h)our <message>** (__admin__) - _Set a reminder for the '{target_role.mention}' role_",
                          " - **/mappool [add/remove/clear <map name>]** (__admin__) - _Modify the map pool_",
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

    if (ctx.author.id in admin_ids and not short):
        output += admin_commands

    if (ctx.author.id == my_id and not short):
        output += my_commands

    output += fun_commands
    
    await ctx.send('\n'.join(output), ephemeral=True, silent=True)

# --------------------Useless commands--------------------------
@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def hello(ctx):
    """Says hello. Usage: `/hello`"""
    if (ctx.channel.id not in [debug_channel, bot_channel]):
        return

    await ctx.send(f'Hello {ctx.author.mention}!', ephemeral=True)


@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def feed(ctx):
    """Feed the bot. Usage: `/feed`"""
    if (ctx.channel.id not in [debug_channel, bot_channel]):
        return

    await ctx.send(f'Yum yum! Thanks for the food!', ephemeral=True)


@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def unfeed(ctx):
    """Unfeed the bot. Usage: `/unfeed`"""
    if (ctx.channel.id not in [debug_channel, bot_channel]):
        return

    options = ["pukes", "poops", "performs own liposuction"]

    option = options[random.randint(0, len(options) - 1)]

    await ctx.send(f'\*looks at you with a deadpan expression\* ... \*{option}\*', ephemeral=True)

# ------------------Functional commands-------------------------
@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def role(ctx, action: str, member: discord.Member):
    """Add or remove the premier role from a member. Usage: /role {add|remove} <display_name>"""

    usage = "Usage: `/role {add|remove} @member`"
    if (ctx.channel.id not in [debug_channel, bot_channel] or not await has_permission(ctx.author.id, ctx)):
        return

    role = discord.utils.get(ctx.guild.roles, name=prem_role) if ctx.guild.id == val_server else discord.utils.get(
        ctx.guild.roles, name=debug_role)

    notif_channel = bot.get_channel(
        prem_channel) if ctx.guild.id == val_server else bot.get_channel(debug_channel)

    if action == "add":
        await member.add_roles(role)
        log(f'Added {member.display_name} to {role.name}')
        await notif_channel.send(f'Welcome to the rathole {member.mention}')
    elif action == "remove":
        await member.remove_roles(role)
        await ctx.send(f'{member.mention} has been removed from the rathole', ephemeral=True)
        log(f'Removed {member.display_name} from {role.name}')
    else:
        await ctx.send('Invalid action.' + usage, ephemeral=True)


@role.error
async def role_error(ctx, error):
    usage = "Usage: `/role {add|remove} @member`"
    if isinstance(error, extra.MemberNotFound):
        await ctx.send('Invalid action. ' + usage, ephemeral=True)
    if isinstance(error, extra.MissingRequiredArgument):
        if (error.param.name == "action"):
            await ctx.send('Please provide an action and user. ' + usage, ephemeral=True)
        elif (error.param.name == "member"):
            await ctx.send(f'Please provide a member. ' + usage, ephemeral=True)


@bot.hybrid_command(aliases=["reminder"])
@discord.app_commands.guilds(discord.Object(id=val_server))
async def remind(ctx, interval: int = 0, unit: str = "", *, message: str = ""):
    """Set a reminder for the target role. Usage: /remind <interval> (s)econd/(m)inute/(h)our <message>"""
    if (ctx.channel.id not in [bot_channel, debug_channel] or not await has_permission(ctx.author.id, ctx)):
        return

    if (interval == 0 and unit == ""):
        await ctx.send(f'Please provide an interval and a unit. Usage: `/remind <interval> (s)econds/(m)inutes/(h)ours <message>`', ephemeral=True)
        return

    if (interval <= 0):
        await ctx.send(f'Please provide a valid interval', ephemeral=True)
        return

    if (unit not in ["seconds", "second", "sec", "s", "minutes", "minute", "min", "m", "hours", "hour", "h"]):
        await ctx.send(f'Invalid unit. Use seconds, minutes, or hours', ephemeral=True)
        return

    current_time = datetime.now()
    if message == "":
        await ctx.send(f'Please provide a reminder message', ephemeral=True)
        return

    g = ctx.guild
    r = prem_role if g.id == val_server else debug_role
    role = discord.utils.get(g.roles, name=r)

    message = role.mention + " " + message
    output = ""

    if unit == "seconds" or unit == "second" or unit == "sec" or unit == "s":
        output = f'(reminder) I will remind {role} in {interval} second(s) with the message: "{message}"'
        when = current_time + timedelta(seconds=interval)
    elif unit == "minutes" or unit == "minute" or unit == "min" or unit == "m":
        when = current_time + timedelta(minutes=interval)
        output = f'(reminder) I will remind {role} in {interval} minute(s) with the message: "{message}"'
        interval *= 60
    elif unit == "hours" or unit == "hour" or unit == "h":
        when = current_time + timedelta(hours=interval)
        output = f'(reminder) I will remind {role} in {interval} hour(s) with the message: "{message}"'
        interval *= 3600
    else:
        await ctx.send(f'Invalid unit. Use seconds, minutes, or hours', ephemeral=True)
        return

    await ctx.send(output, ephemeral=True)

    dt_when = datetime.fromtimestamp(when.timestamp()).isoformat()

    reminders[str(g.id)].update(
        {dt_when: message})

    save_reminders(reminders)

    log(f"Saved a reminder from {ctx.author.display_name}: {output}")
    reminder_channel = bot.get_channel(
        prem_channel) if ctx.guild.id == val_server else bot.get_channel(debug_channel)

    await asyncio.sleep(interval)

    await reminder_channel.send(message)
    log("Posted reminder: " + message)

    del reminders[str(g.id)][dt_when]
    save_reminders(reminders)


# --------------------Premier commands--------------------------
@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def schedule(ctx):
    """Display the upcoming events. Usage: /schedule"""
    if (ctx.channel.id not in all_channels):
        return

    guild = bot.get_guild(
        val_server) if ctx.guild.id == val_server else bot.get_guild(debug_server)
    events = guild.scheduled_events

    message = "Upcoming events:\n"
    for event in events:
        message += f"{event.name}: {event.description} at {discord_local_time(event.start_time)}\n"

    ephem = True if ctx.channel.id == bot_channel else False

    await ctx.send(message, ephemeral=ephem)


@bot.hybrid_command(aliases=["maplist", "maps"])
@discord.app_commands.guilds(discord.Object(id=val_server))
@discord.app_commands.choices(
    action=[
        discord.app_commands.Choice(name="Add", value="add"),
        discord.app_commands.Choice(name="Remove", value="remove"),
        discord.app_commands.Choice(name="Clear", value="clear"),
    ],
    map=[
        discord.app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys() # mappool only has maps that are currently playable, need to get all maps
    ]
)
async def mappool(ctx, action: str = "", map: str = ""):
    """Add or remove maps from the map pool. Usage: /mappool [add/remove/clear <map name>]"""
    if (ctx.channel.id not in all_channels):
        ctx.send(f'You cannot use this command in this channel', ephemeral=True)
        return

    if action == "" and map == "" :
        ephem = True
        if (ctx.channel.id == prem_channel):
            ephem = False  # when listing the map pool, don't make it ephemeral in the premier channel so it can be seen by everyone
        if (len(map_pool) == 0):
            await ctx.send(f'The map pool is empty', ephemeral=ephem)
        else:
            await ctx.send(f'Current map pool: {", ".join(map_pool)}', ephemeral=ephem)
        return

    if (not await has_permission(ctx.author.id, ctx) and ctx.channel.id != bot_channel):
        return

    if action == "" or map == "":
        await ctx.send(f'Please provide an action and a map. Usage: `/mappool [add/remove/clear <map name>]`', ephemeral=True)
        return

    output = ""

    if action == "add":
        if map not in map_pool:
            map_pool.append(map)
            output = f'{map} has been added to the map pool'
        else:
            await ctx.send(f'{map} is already in the map pool', ephemeral=True)
            return
    elif action == "remove":
        if map in map_pool:
            map_pool.remove(map)
            output = f'{map} has been removed from the map pool'
        else:
            await ctx.send(f'{map} is not in the map pool', ephemeral=True)
            return
    elif action == "clear":
        map_pool.clear()
        output = f'The map pool has been cleared'
    else:
        await ctx.send(f'Invalid action. Usage: `/mappool [add/remove/clear <map name>]`', ephemeral=True)
        return

    ephem = True
    if (ctx.channel.id == prem_channel):
        ephem = False  # when modifying/listing the map pool, don't make it ephemeral in the premier channel so it can be seen by everyone

    await ctx.send(output, ephemeral=ephem)

    log(output)

    save_pool(map_pool)


@bot.tree.command(name="test", description="Add or remove maps from the map pool. Usage: /mappool [add/remove/clear <map name>]", guilds=[discord.Object(id=val_server)])
@discord.app_commands.choices(
    action=[
        discord.app_commands.Choice(name="Add", value="add"),
        discord.app_commands.Choice(name="Remove", value="remove"),
        discord.app_commands.Choice(name="Clear", value="clear"),
    ],

    map=[
        # mappool only has maps that are currently playable, need to get all maps
        discord.app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
    ]
)
async def test(interaction: discord.Interaction, action: str = "", map: str = ""):
    """Add or remove maps from the map pool. Usage: /mappool [add/remove/clear <map name>]"""
    if (interaction.channel.id not in all_channels):
        interaction.response.send_message(f'You cannot use this command in this channel', ephemeral=True)
        return

    if action == "" and map == "":
        ephem = True
        if (interaction.channel.id == prem_channel):
            ephem = False  # when listing the map pool, don't make it ephemeral in the premier channel so it can be seen by everyone
        if (len(map_pool) == 0):
            await interaction.response.send_message(f'The map pool is empty', ephemeral=ephem)
        else:
            await interaction.response.send_message(f'Current map pool: {", ".join(map_pool)}', ephemeral=ephem)
        return

    if (not await has_permission(interaction.user.id, interaction) and interaction.channel.id != bot_channel):
        return

    if action == "" or map == "":
        await interaction.response.send_message(f'Please provide an action and a map. Usage: `/mappool [add/remove/clear <map name>]`', ephemeral=True)
        return

    output = ""

    if action == "add":
        if map not in map_pool:
            map_pool.append(map)
            output = f'{map} has been added to the map pool'
        else:
            await interaction.response.send_message(f'{map} is already in the map pool', ephemeral=True)
            return
    elif action == "remove":
        if map in map_pool:
            map_pool.remove(map)
            output = f'{map} has been removed from the map pool'
        else:
            await interaction.response.send_message(f'{map} is not in the map pool', ephemeral=True)
            return
    elif action == "clear":
        map_pool.clear()
        output = f'The map pool has been cleared'
    else:
        await interaction.response.send_message(f'Invalid action. Usage: `/mappool [add/remove/clear <map name>]`', ephemeral=True)
        return

    ephem = True
    if (interaction.channel.id == prem_channel):
        ephem = False  # when modifying/listing the map pool, don't make it ephemeral in the premier channel so it can be seen by everyone

    await interaction.response.send_message(output, ephemeral=ephem)

    log(output)

    save_pool(map_pool)


@bot.hybrid_command(aliases=["vote", "votemaps"])
@discord.app_commands.guilds(discord.Object(id=val_server))
async def votemap(ctx, map: str = "", weight: str = ""):
    """Vote for a map with a weight. Usage: /votemap <map name> +/~/-."""
    global map_preferences
    global map_weights
    if (ctx.channel.id not in [bot_channel, debug_channel]):
        await ctx.send(f'You cannot vote in this channel', ephemeral=True)
        return

    output = ""

    if map in ["maps", "maplist", "pool", "mappool", ""]:
        header = "All maps available for voting:"
        maps = list(map_preferences.keys())
        output = [header] + [m.title() for m in maps if m != ""]
        output = "\n- ".join(output)
        await ctx.send(output, ephemeral=True)
        return

    map = map.lower()

    if map not in map_preferences or weight not in ["+", "~", "-"]:
        if (map not in map_preferences):
            output += f'{map} is not a valid map.'
        if (weight not in ["+", "~", "-"]):
            output += f' Weight must be +, ~, - (not {weight})' if output != "" else f'Weight must be +, ~, - (not {weight})'

        await ctx.send(output, ephemeral=True)
        return

    old_weight = ""
    if (str(ctx.author.id) in map_preferences[map]):
        old_weight = map_preferences[map][str(ctx.author.id)]
        if (old_weight == weight):
            await ctx.send(f'{ctx.author.mention} you have already marked {map.title()} with a weight of {weight}', ephemeral=True)
            return

        output = f'Your vote for {map.title()} has been changed from {old_weight} to {weight}'
        old_weight = 1 if old_weight == "+" else 0 if old_weight == "~" else -1
        map_weights[map] -= old_weight

    map_preferences[map][str(ctx.author.id)] = weight
    if (old_weight == ""):
        output = f'You voted for {map.title()} with a weight of {weight}'
    weight = 1 if weight == "+" else 0 if weight == "~" else -1
    map_weights[map] += weight

    await ctx.send(output, ephemeral=True)
    if('your' in output):
        output = output.replace('your', f'{ctx.author.display_name}\'s')
    else:
        output = output.replace('You', f'{ctx.author.display_name}')
    
    log(output)

    save_prefrences(map_preferences)
    save_weights(map_weights)


@bot.hybrid_command(aliases=["votes"])
@discord.app_commands.guilds(discord.Object(id=val_server))
async def mapvotes(ctx):
    """Display the map votes for each user. Usage: /mapvotes"""
    global map_preferences
    if (ctx.channel.id not in all_channels):
        return

    role = prem_role if ctx.guild.id == val_server else debug_role
    all_users = discord.utils.get(ctx.guild.roles, name=role).members

    output = ""

    for map in map_pool:
        header = f'- {map.title()}:\n'
        body = ""
        for user in all_users:
            if user.id == bot.user.id:
                continue
            if str(user.id) in map_preferences[map]:
                body += f' - {user.mention}: {map_preferences[map][str(user.id)]}\n'
            else:
                body += f' - {user.mention}: no vote\n'
            
            if (body == ""):
                body = "No votes for this map."
            
        output += header + body
        

    if (output == ""):
        output = "No votes for maps in the map pool."

    ephem = True if ctx.channel.id == bot_channel else False

    await ctx.send(output, ephemeral=ephem, silent=True)


@bot.hybrid_command(aliases=["weights"])
@discord.app_commands.guilds(discord.Object(id=val_server))
async def mapweights(ctx):
    """Display the map weights (sorted). Usage: /mapweights"""
    global map_weights
    if (ctx.channel.id not in all_channels):
        return

    output = ""

    map_weights = dict(sorted(map_weights.items(
    ), key=lambda item: item[1], reverse=True))  # sort the weights in descending order

    for map in map_weights.keys():
        if map not in map_pool:
            continue

        output += f'{map.title()}: {map_weights[map]}\n'

    if (output == ""):
        output = "No weights to show for maps in the map pool."

    ephem = True if ctx.channel.id == bot_channel else False

    await ctx.send(output, ephemeral=ephem)

@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def addevents(ctx, map_list: str, date: str):
    '''Add all prem events to the schedule. Usage: /addevent "<map1> <map2> ..." <mm/dd>
    
        Parameters
        ----------
        map_list : str
            The map order enclosed in quotes with each map separated with a space (e.g. "map1 map2 map3")
        date : str
            The date (mm/dd) of the Thursday that starts the first event. Events will be added for Thursday, Saturday, and Sunday.
    '''
    
    if (ctx.channel.id not in [bot_channel, debug_channel] or not await has_permission(ctx.author.id, ctx)):
        return

    guild = ctx.guild
    events = guild.scheduled_events
    scheduled_maps = []
    new_maps = "".join(map_list.split(",")).split() # remove commas and split by space
    log(str(new_maps))


    prem_length = len(new_maps)
    input_date = tz.localize(datetime.strptime(date, "%m/%d").replace(year=datetime.now().year))
    thur_time = datetime(year=datetime.now().year, month=input_date.month, day=input_date.day, hour=22, minute=0, second=0)
    sat_time = (thur_time + timedelta(days=2)).replace(hour=23)
    sun_time = (thur_time + timedelta(days=3))

    weekday = input_date.weekday()

    start_times = [tz.localize(d) for d in [thur_time, sat_time, sun_time]]

    if weekday != 3:
        await ctx.send(f'Invalid day. Please provide a Thursday date (mm/dd)', ephemeral=True)
        return

    for event in events:
        if(event.creator_id == bot.user.id):
            await event.delete()
            continue
    
        scheduled_maps.append(event.description)

    
    vc_object = discord.utils.get(guild.voice_channels, id=voice_channel) if ctx.channel.id == bot_channel else discord.utils.get(guild.voice_channels, id=1217649405759324236)

    for map in new_maps:
        map = map.lower()
        if map not in map_pool:
            await ctx.send(f'{map} is not in the map pool. I only add premier events. (skipping)', ephemeral=True)
            continue
        
        map = map.title()
        if map in scheduled_maps:
            await ctx.send(f'{map} is already in the schedule. (skipping)', ephemeral=True)
            continue

        for start_time in start_times:
            await guild.create_scheduled_event(name="Premier", description=map, channel=vc_object,
                                            start_time=start_time, end_time=start_time + timedelta(hours=1),
                                            entity_type=discord.EntityType.voice, privacy_level=discord.PrivacyLevel.guild_only)
        
        start_times = [start_time + timedelta(days=7) for start_time in start_times]


        
    await ctx.send(f'Added {prem_length} premier map(s) to the schedule', ephemeral=True)

            


# -------------------------Tasks--------------------------------
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

# -----------------Bizzy/Delicate Commands----------------------
@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def pin(ctx, message_id=0, unpin=False):
    """Pin a message. Usage: `/pin <message_id>`"""
    if (ctx.channel.id not in [bot_channel, debug_channel] or not await has_permission(ctx.author.id, ctx)):
        return

    message = await ctx.channel.fetch_message(message_id)
    if (unpin):
        await message.unpin()
        await ctx.send(f'Message unpinned', ephemeral=True)
        return
    
    await message.pin()

    await asyncio.sleep(1) # wait for the message to be pinned before deleting the command message

    delete_these = []
    deleted_mine = False
    async for message in ctx.channel.history(limit=3):
        if not deleted_mine and message.type == discord.MessageType.pins_add:
            delete_these.append(message)
            deleted_mine = True
        elif message.id == ctx.message.id:
            delete_these.append(message)
    
    await ctx.channel.delete_messages(delete_these)

    await ctx.send(f'Message pinned', ephemeral=True)


@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def cancelevent(ctx, map: str = "", amount: str = ""):
    """Cancel an event. Usage: /cancelevent <map_name> [all]"""

    if (ctx.channel.id not in [bot_channel, debug_channel] or not await has_permission(ctx.author.id, ctx)):
        return

    map = map.lower()
    amount = amount.lower()

    if map == "":
        await ctx.send(f'Please provide a map. Usage: `/cancelevent <map_name> [all]`', ephemeral=True)
        return

    if map not in map_pool:
        await ctx.send(f'{map.title()} is not in the map pool. I only cancel premier events.', ephemeral=True)
        return

    guild = ctx.guild
    events = guild.scheduled_events

    if (amount != "all" and amount != ""):
        ctx.send(
            f"Invalid amount. Usage: `/cancelevent <map_name> [all]`.", ephemeral=True)
        return

    for event in events:
        if event.description.lower() == map:
            await event.cancel()
            await event.end()
            log(f'{ctx.author.display_name} cancelled event - {event.name} on {event.description} for {event.start_time.date()}')
            if (amount != "all"):
                break
    
    message = f'{event.name} on {event.description} for {event.start_time.date()} has been cancelled' if amount != "all" else f'All events on {event.description} have been cancelled'
    await ctx.send(message, ephemeral=True)


@bot.hybrid_command()
@discord.app_commands.guilds(discord.Object(id=val_server))
async def clear(ctx, amount: int = 1, usertype: str = "both"):
    """Clear chats from <usertype> in the last 200 messages. Usage: `/clear <amount> [bot/user/both]`"""
    if (ctx.channel.id == debug_channel):  # just nuke the debug channel
        await ctx.channel.purge()
        return

    if (ctx.channel.id not in all_channels or not await has_permission(ctx.author.id, ctx)):
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
