import discord
from discord.ext import commands
from discord import app_commands, Object
import asyncio

from my_utils import *

class AdminPremierCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        # print("AdminPremier cog loaded")
        pass
    
    @app_commands.command(name="addevents", description=command_descriptions["addevents"])
    @app_commands.describe(
        map_list="The map order enclosed in quotes with each map separated with a space (e.g. 'map1 map2 map3')",
        date="The date (mm/dd) of the Thursday that starts the first event. Events will be added for Thursday, Saturday, and Sunday."
    )
    async def addevents(self, interaction: discord.Interaction, map_list: str, date: str):
        """Add all premier events to the schedule"""
        # THERE IS A RATELIMIT OF 5 EVENTS/MINUTE

        # don't need to send a message here, has_permission will do it
        if not await has_permission(interaction.user.id, interaction):
            return

        if interaction.channel.id not in [bot_channel, debug_channel]:
            await wrong_channel(interaction)
            return

        guild = interaction.guild

        # remove commas and split by space
        new_maps = "".join(map_list.split(",")).split()

        prem_length = len(new_maps)
        try:
            input_date = tz.localize(datetime.strptime(
                date, "%m/%d").replace(year=datetime.now().year))
        except ValueError:
            await interaction.response.send_message(f'Invalid date format. Please provide a Thursday date (mm/dd)', ephemeral=True)
            return

        thur_time = datetime(year=datetime.now(
        ).year, month=input_date.month, day=input_date.day, hour=22, minute=0, second=0)
        sat_time = (thur_time + timedelta(days=2)).replace(hour=23)
        sun_time = (thur_time + timedelta(days=3))

        weekday = input_date.weekday()

        start_times = [tz.localize(d) for d in [thur_time, sat_time, sun_time]]

        if weekday != 3:
            await interaction.response.send_message(f'Invalid day. Please provide a Thursday date (mm/dd)', ephemeral=True)
            return
        if datetime.now() > thur_time:
            await interaction.response.send_message(f'Invalid date. Please provide a **future** Thursday date (mm/dd)', ephemeral=True)
            return

        # await interaction.response.send_message("This is a test message", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)

        output = ""
        vc_object = discord.utils.get(guild.voice_channels, id=voice_channel) if interaction.channel.id == bot_channel else discord.utils.get(
            guild.voice_channels, id=1217649405759324236)

        for _map in new_maps:
            _map = _map.lower()
            if _map not in map_pool:
                await interaction.followup.send(f'{_map} is not in the map pool and I only add premier events. Ensure your maplist is formatted properly and that /mappool is updated. (exiting...)\n', ephemeral=True)
                return

            for start_time in start_times:
                event_name = "Premier"
                event_desc = _map.title()

                if _map == new_maps[-1].lower() and start_time == start_times[-1]:
                    event_name = "Premier Playoffs" 
                    event_desc = "Playoffs"

                await guild.create_scheduled_event(name=event_name, description=event_desc, channel=vc_object,
                                                start_time=start_time, end_time=start_time +
                                                timedelta(hours=1),
                                                entity_type=discord.EntityType.voice, privacy_level=discord.PrivacyLevel.guild_only)

            start_times = [start_time + timedelta(days=7)
                        for start_time in start_times]

        log(f'{interaction.user.display_name} has posted the premier schedule starting on {date} with maps: {", ".join(new_maps)}')
        await interaction.followup.send(f'{output}\nPremier schedule has been created.', ephemeral=True)

    @app_commands.command(name="cancelevent", description=command_descriptions["cancelevent"])
    @app_commands.choices(
        _map=[
            app_commands.Choice(name=s.title(), value=s) for s in map_pool] + [app_commands.Choice(name="Playoffs", value="Playoffs")],
        amount=[
            app_commands.Choice(name="(Optional) All", value="all"),
        ]
    )
    @app_commands.describe(
        _map="The map to cancel the closest event for",
        amount="Cancel all events for the specified map"
    )
    async def cancelevent(self, interaction: discord.Interaction, _map: str, amount: str = ""):
        """Cancel a premier event"""

        if not await has_permission(interaction.user.id, interaction):
            return

        if interaction.channel.id not in [bot_channel, debug_channel]:
            await wrong_channel(interaction)
            return

        amount = amount.lower()

        _map = _map.title()

        if _map.lower() not in map_pool and _map.lower() != "playoffs":
            await interaction.response.send_message(f'{_map.title()} is not in the map pool. I only cancel premier events.', ephemeral=True)
            return

        guild = interaction.guild
        events = guild.scheduled_events

        await interaction.response.defer(ephemeral=True, thinking=True)
        message = "Event not found in the schedule."

        for event in events:
            if "Premier" in event.name and event.description.lower() == _map.lower():
                try:
                    await event.cancel()
                except ValueError as e:
                    pass
                try:
                    await event.end()
                except ValueError as e:
                    await event.delete()

                log(f'{interaction.user.display_name} cancelled event - {event.name} on {event.description} for {event.start_time.date()}')
                if amount != "all":
                    e_name = event.name
                    e_date = event.start_time.date()
                    message = f'{e_name} on {_map} for {e_date} has been cancelled'
                    break
                else:
                    message = f'All events on {_map} have been cancelled'
        await interaction.followup.send(message)

        log(f"{interaction.user.display_name} cancelled event - {event.name} on {event.description} for {event.start_time.date()}")

    @app_commands.command(name="addpractices", description=command_descriptions["addpractices"])
    async def addpractices(self, interaction: discord.Interaction):
        """Add all practice events to the schedule"""
        # THERE IS A RATELIMIT OF 5 EVENTS/MINUTE

        if not await has_permission(interaction.user.id, interaction):
            return

        if interaction.channel.id not in [bot_channel, debug_channel]:
            await wrong_channel(interaction)
            return

        guild = interaction.guild
        events = guild.scheduled_events

        if len(events) == 0:
            await interaction.response.send_message(f'Please add the premier events first using the /addevents command', ephemeral=True)
            return

        wed_hour = est_to_utc(time(hour=22)).hour
        fri_hour = wed_hour + 1

        await interaction.response.defer(ephemeral=True, thinking=True)

        for event in events:
            if event.start_time.astimezone(tz).weekday() != 3 or "premier" not in event.name.lower():
                continue

            wed_time = fri_time = event.start_time.astimezone(pytz.utc)
            wed_time = wed_time.replace(hour=wed_hour) - timedelta(days=1)
            fri_time = fri_time.replace(hour=fri_hour) + timedelta(days=1)

            for start_time in [wed_time, fri_time]:
                if start_time < datetime.now().astimezone(pytz.utc):
                    continue

                event_name = "Premier Practice"
                event_desc = event.description

                await guild.create_scheduled_event(name=event_name, description=event_desc, channel=event.channel,
                                                start_time=start_time, end_time=start_time +
                                                timedelta(hours=1),
                                                entity_type=discord.EntityType.voice, privacy_level=discord.PrivacyLevel.guild_only)

        log(f'{interaction.user.display_name} has posted the premier practice schedule')
        await interaction.followup.send(f'Added premier practice events to the schedule', ephemeral=True)

    @app_commands.command(name="cancelpractice", description=command_descriptions["cancelpractice"])
    @app_commands.choices(
        _map=[
            app_commands.Choice(name=s.title(), value=s) for s in map_pool
        ],
        amount=[
            app_commands.Choice(name="(Optional) All", value="all"),
        ]
    )
    @app_commands.describe(
        _map="The map to cancel the closest practice for",
        amount="Cancel all events for the specified map"
    )
    async def cancelpractice(self, interaction: discord.Interaction, _map: str, amount: str = ""):
        """Cancel a practice event for the specified map"""

        if not await has_permission(interaction.user.id, interaction):
            return

        if interaction.channel.id not in [bot_channel, debug_channel]:
            await wrong_channel(interaction)
            return

        _map = _map.title()
        amount = amount.lower()

        if _map.lower() not in map_pool:
            await interaction.response.send_message(f'{_map.title()} is not in the map pool. I only cancel premier events.', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        events = guild.scheduled_events

        message = f"No practices found for {_map} in the schedule."

        for event in events:
            if event.name == "Premier Practice" and event.description.lower() == _map.lower():
                try:
                    await event.cancel()
                except ValueError as e:
                    pass
                try:
                    await event.end()
                except ValueError as e:
                    await event.delete()

                log(f'{interaction.user.display_name} cancelled {event.name} on {event.description} for {event.start_time.date()}')

                if amount != "all":
                    e_name = event.name
                    e_date = event.start_time.date()
                    message = f'{e_name} on {_map} for {e_date} has been cancelled'
                    break
                else:
                    message = f'All practices on {_map} have been cancelled'

        await interaction.followup.send(message)

        log(f"{interaction.user.display_name} cancelled practice(s) - {message}")

    @app_commands.command(name="clearschedule", description=command_descriptions["clearschedule"])
    @app_commands.choices(
        confirm=[
            app_commands.Choice(name="Confirm", value="confirm"),
        ]
    )
    @app_commands.describe(
        confirm='Confirm clear. Note: This will clear all events with "Premier" in the name.'
    )
    async def clearschedule(self, interaction: discord.Interaction, confirm: str):
        """Clear all premier and practice events from the schedule"""

        if not await has_permission(interaction.user.id, interaction):
            return

        if interaction.channel.id not in [bot_channel, debug_channel]:
            await wrong_channel(interaction)
            return


        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        events = guild.scheduled_events


        for event in events:
            if "Premier" in event.name:
                try:
                    await event.cancel()
                except ValueError as e:
                    pass
                try:
                    await event.end()
                except ValueError as e:
                    await event.delete()

        log(f'{interaction.user.display_name} has cleared the premier schedule')
        await interaction.followup.send(f'Cleared the premier schedule', ephemeral=True)

    @app_commands.command(name="addnote", description=command_descriptions["addnote"])
    @app_commands.describe(
        _map="The map to add a note for",
        note_id="The message ID of the note to add",
        description="Provide a short description of the note. Used to identify the note when using `/notes`"
    )
    @app_commands.choices(
        _map=[
            app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
        ]
    )
    async def addnote(self, interaction: discord.Interaction, _map: str, note_id: str, description: str):
        """Create a practice note from a pre-existing note message"""
        if not await has_permission(interaction.user.id, interaction):
            return

        if interaction.channel.id != notes_channel:
            await wrong_channel(interaction)
            return

        note_id = int(note_id)
        try:
            interaction.channel.get_partial_message(note_id)
        except discord.errors.NotFound:
            await interaction.response.send_message(f'Invalid message ID.', ephemeral=True)
            return

        if _map not in practice_notes:
            practice_notes[_map] = {}

        practice_notes[_map][note_id] = description

        save_notes(practice_notes)

        log(f'{interaction.user.display_name} has added a practice note. Note ID: {note_id}')

        await interaction.response.send_message(f'Added a practice note for {_map.title()}. Access using `/notes {_map}`', ephemeral=True)


class AdminManageCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @commands.Cog.listener()
    async def on_ready(self):
        # print("AdminManage cog loaded")
        pass
    
    @app_commands.command(name="remind", description=command_descriptions["remind"])
    @app_commands.choices(
        unit=[
            app_commands.Choice(name="Hours", value="hours"),
            app_commands.Choice(name="Minutes", value="minutes"),
            app_commands.Choice(name="Seconds", value="seconds"),
        ]
    )
    @app_commands.describe(
        interval="The number of units to wait for the reminder",
        unit="The unit of time associated with the interval",
        message="The reminder message to send to the premier role"
    )
    async def remind(self, interaction: discord.Interaction, interval: int, unit: str, *, message: str):
        """Set a reminder for the target role"""

        if not await has_permission(interaction.user.id, interaction):
            return

        if interaction.channel.id not in [bot_channel, debug_channel]:
            await wrong_channel(interaction)
            return

        if interval <= 0:
            await interaction.response.send_message(f'Please provide a valid interval greater than 0', ephemeral=True)
            return

        message = message.strip()

        if message == "":
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
        elif unit == "hours":  # could be else, but elif for clarity
            when = current_time + timedelta(hours=interval)
            output = f'(reminder) I will remind {role} in {interval} hour(s) with the message: "{message}"'
            interval *= 3600

        await interaction.response.send_message(output, ephemeral=True)

        dt_when = datetime.fromtimestamp(when.timestamp()).isoformat()

        reminders[str(g.id)].update(
            {dt_when: message})

        save_reminders(reminders)

        log(f"Saved a reminder from {interaction.user.display_name}: {output}")

        reminder_channel = self.bot.get_channel(
            prem_channel) if g.id == val_server else self.bot.get_channel(debug_channel)

        await asyncio.sleep(interval)

        await reminder_channel.send(message)
        log("Posted reminder: " + message)

        del reminders[str(g.id)][dt_when]
        save_reminders(reminders)


    @app_commands.command(name="pin", description=command_descriptions["pin"])
    @app_commands.describe(
        message_id="The ID of the message to pin"
    )
    async def pin(self, interaction: discord.Interaction, message_id: str):
        """Pin a message"""
        if not await has_permission(interaction.user.id, interaction):
            return

        try:
            message_id = int(message_id)
            message = interaction.channel.get_partial_message(message_id)
        except (ValueError, discord.errors.NotFound):
            await interaction.response.send_message(f'Invalid message ID.', ephemeral=True)
            return

        interaction.response.defer(ephemeral=True, thinking=True)
        await message.pin()
        await interaction.response.send_message(f'Message pinned', ephemeral=True)

        log(f'{interaction.user.display_name} pinned message {message_id}')


    @app_commands.command(name="unpin", description=command_descriptions["unpin"])
    @app_commands.describe(
        message_id="The ID of the message to unpin"
    )
    async def unpin(self, interaction: discord.Interaction, message_id: str):
        """Unpin a message"""
        if not await has_permission(interaction.user.id, interaction):
            return

        if message_id == "":
            await interaction.response.send_message(f'Please provide a message ID.', ephemeral=True)
            return

        try:
            message_id = int(message_id)
            message = await interaction.channel.fetch_message(message_id)
        except (ValueError, discord.errors.NotFound):
            await interaction.response.send_message(f'Invalid message ID.', ephemeral=True)
            return

        await message.unpin()

        await interaction.response.send_message(f'Message unpinned', ephemeral=True)

        log(f'{interaction.user.display_name} unpinned message {message_id}')

    @app_commands.command(name="clear", description=command_descriptions["clear"])
    @app_commands.choices(
        usertype=[
            app_commands.Choice(name="Bot", value="bot"),
            app_commands.Choice(name="User", value="user"),
            app_commands.Choice(name="Both", value="both"),
        ]
    )
    @app_commands.describe(
        amount="The number of messages to clear",
        usertype="The type of messages to clear"
    )
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 200] = 1, usertype: str="both"):
        """Clear chats from <usertype> in the last 200 messages."""
        if interaction.channel.id == debug_channel:  # just nuke the debug channel
            await interaction.channel.purge()
            return

        if not await has_permission(interaction.user.id, interaction):
            return

        if interaction.channel.id not in all_channels:
            await wrong_channel(interaction)
            return

        if amount < 1:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        messages = []
        async for message in interaction.channel.history(limit=200):
            # don't delete reminders
            if usertype == "bot" and message.author == self.bot.user and not message.content.startswith("(reminder)"):
                messages.append(message)
            elif usertype == "user" or usertype == "both":
                # don't delete regular chat
                # if a message is from a user and not a command, don't delete it
                if not message.content.startswith("!") and message.author.id != self.bot.user.id:
                    continue
                messages.append(message)

            if len(messages) >= amount:
                break

        await interaction.channel.delete_messages(messages)

        for message in messages:  # log the deleted messages
            with open(f"./logs/chat_deletion.log", 'a') as file:
                creation_time = message.created_at.astimezone(
                    tz).strftime("%Y-%m-%d %H:%M:%S")

                deletion_time = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")

                file.write(
                    f'[{creation_time} EST] {message.author}: "{message.content}"\t| deleted by {interaction.user} at {deletion_time} EST\n')

        await interaction.followup.send(f'Deleted {len(messages)} messages', ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminPremierCommands(bot), guilds=[Object(val_server), Object(debug_server)])
    await bot.add_cog(AdminManageCommands(bot), guilds=[Object(val_server), Object(debug_server)])