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
        map_list="The map order separated by commas (whitespace between maps does not matter). Ex: 'map1, map2, map3'",
        date="The date (mm/dd) of the Thursday that starts the first event. Events will be added for Thursday, Saturday, and Sunday."
    )
    async def addevents(self, interaction: discord.Interaction, map_list: str, date: str):
        """Add all premier events to the schedule"""
        # THERE IS A RATELIMIT OF 5 EVENTS/MINUTE

        # don't need to send a message here, has_permission will do it
        if not await has_permission(interaction.user.id, interaction):
            return

        guild = interaction.guild

        # remove commas and split by space
        # split by comma and remove whitespace
        new_maps = [m.strip().lower() for m in map_list.split(",")]

        for _map in new_maps:
            if _map not in map_pool:
                await interaction.response.send_message(f'{_map.title()} is not in the map pool. I only add premier events. Ensure that {inline_code("map_list")} is formatted properly and that {inline_code("/mappool")} has been updated.', ephemeral=True)
                return

        try:
            input_date = tz.localize(datetime.strptime(
                date, "%m/%d").replace(year=datetime.now().year))
        except ValueError:
            await interaction.response.send_message(f'Invalid date format. Please provide a date in the format mm/dd (ex: "07/10" for July 10th)', ephemeral=True)
            return

        if input_date.weekday() != 3:
            await interaction.response.send_message(f'Date is not a Thursday. Please provide a Thursday date (mm/dd)', ephemeral=True)
            return

        thur_time = datetime(year=datetime.now(
        ).year, month=input_date.month, day=input_date.day, hour=22, minute=0, second=0)
        sat_time = (thur_time + timedelta(days=2)).replace(hour=23)
        sun_time = (thur_time + timedelta(days=3))

        start_times = [tz.localize(d) for d in [thur_time, sat_time, sun_time]]

        await interaction.response.defer(ephemeral=True, thinking=True)

        output = ""

        now = tz.localize(datetime.now())

        vc_object = discord.utils.get(guild.voice_channels, id=voice_channel) if interaction.guild.id == val_server else discord.utils.get(
            guild.voice_channels, id=debug_voice)

        for i, _map in enumerate(new_maps):
            for j, start_time in enumerate(start_times):
                if now > start_time:
                    output = "Detected that input date is in the past. Any maps that are in the past were skipped."
                    continue
                event_name = "Premier"
                event_desc = _map.title()

                # last map and last day is playoffs
                if i == len(new_maps) - 1 and j == len(start_times) - 1:
                    event_name = "Premier Playoffs"
                    event_desc = "Playoffs"

                await guild.create_scheduled_event(name=event_name, description=event_desc, channel=vc_object,
                                                   start_time=start_time, end_time=start_time +
                                                   timedelta(hours=1),
                                                   entity_type=discord.EntityType.voice, privacy_level=discord.PrivacyLevel.guild_only)

            start_times = [start_time + timedelta(days=7)
                           for start_time in start_times]

        log(f'{interaction.user.display_name} has posted the premier schedule starting on {date} with maps: {", ".join(new_maps)}')
        await interaction.followup.send(f'The Premier schedule has been created.\n{output}', ephemeral=True)

    @app_commands.command(name="cancelevent", description=command_descriptions["cancelevent"])
    @app_commands.choices(
        _map=[
            app_commands.Choice(name=s.title(), value=s) for s in map_pool] + [app_commands.Choice(name="playoffs", value="playoffs")],
        all_events=[
            app_commands.Choice(name="(Optional) All", value=1),
        ]
    )
    @app_commands.describe(
        _map="The map to cancel the closest event for",
        all_events="Cancel all events for the specified map"
    )
    async def cancelevent(self, interaction: discord.Interaction, _map: str, all_events: int = 0):
        """Cancel a premier event"""

        if not await has_permission(interaction.user.id, interaction):
            return

        if _map not in map_pool and _map != "playoffs":
            await interaction.response.send_message(f'{_map.title()} is not in the map pool. I only cancel premier events.', ephemeral=True)
            return

        guild = interaction.guild
        events = guild.scheduled_events

        await interaction.response.defer(ephemeral=True, thinking=True)
        message = "Event not found in the schedule."

        for event in events:
            if "Premier" in event.name and event.description.lower() == _map:  # map is already lower
                if event.status == discord.EventStatus.scheduled:
                    await event.cancel()
                elif event.status == discord.EventStatus.active:
                    await event.end()
                else:
                    await event.delete()

                if not all_events:
                    e_name = event.name
                    e_desc = event.description
                    e_date = event.start_time.date()
                    message = f'{e_name} on {e_desc} for {e_date} has been cancelled'
                    break
                else:
                    message = f'All events on {_map.title()} have been cancelled'

        if message != "Event not found in the schedule.":
            log(f'{interaction.user.display_name} cancelled event - {message}')

        await interaction.followup.send(message)

        log(f"{interaction.user.display_name} cancelled event - {message}")

    @app_commands.command(name="addpractices", description=command_descriptions["addpractices"])
    async def addpractices(self, interaction: discord.Interaction):
        """Add all practice events to the schedule"""
        # THERE IS A RATELIMIT OF 5 EVENTS/MINUTE

        if not await has_permission(interaction.user.id, interaction):
            return

        guild = interaction.guild
        events = guild.scheduled_events

        if len([event for event in events if event.name == "Premier" and event.description != "Playoffs"]) == 0:
            await interaction.response.send_message(f'Please add the premier events first using the `/addevents` command', ephemeral=True)
            return

        wed_hour = est_to_utc(time(hour=22)).hour
        fri_hour = wed_hour + 1

        await interaction.response.defer(ephemeral=True, thinking=True)

        for event in events:
            if event.start_time.astimezone(tz).weekday() != 3 or "Premier" not in event.name:
                continue

            wed_time = fri_time = event.start_time.astimezone(pytz.utc)
            wed_time = wed_time.replace(hour=wed_hour) - timedelta(days=1)
            fri_time = fri_time.replace(hour=fri_hour) + timedelta(days=1)

            for start_time in [wed_time, fri_time]:
                if start_time < tz.localize(datetime.now()):
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
        all_practices=[
            app_commands.Choice(name="(Optional) All", value=1),
        ]
    )
    @app_commands.describe(
        _map="The map to cancel the next practice for",
        all_practices="Cancel all events for the specified map"
    )
    async def cancelpractice(self, interaction: discord.Interaction, _map: str, all_practices: int = 0):
        """Cancel a practice event for the specified map"""

        if not await has_permission(interaction.user.id, interaction):
            return

        if _map not in map_pool:
            await interaction.response.send_message(f'{_map.title()} is not in the map pool. I only cancel premier events. Ensure that {inline_code("/mappool")} is updated.', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        events = guild.scheduled_events

        message = f"No practices found for {_map.title()} in the schedule."

        for event in events:
            if event.name == "Premier Practice" and event.description.lower() == _map:
                if event.status == discord.EventStatus.scheduled:
                    await event.cancel()
                elif event.status == discord.EventStatus.active:
                    await event.end()
                else:
                    await event.delete()

                if not all_practices:
                    e_name = event.name
                    e_date = event.start_time.date()
                    message = f'{e_name} on {_map.title()} for {e_date} has been cancelled'
                    break
                else:
                    message = f'All practices on {_map.title()} have been cancelled'

        if message != f"No practices found for {_map.title()} in the schedule.":
            log(f'{interaction.user.display_name} cancelled practice: {message}')

        await interaction.followup.send(message)

        log(f"{interaction.user.display_name} cancelled practice(s) - {message}")

    @app_commands.command(name="clearschedule", description=command_descriptions["clearschedule"])
    @app_commands.choices(
        confirm=[
            app_commands.Choice(
                name="I acknowledge all events with 'Premier' in the name will be deleted.", value="confirm"),
        ]
    )
    @app_commands.describe(
        confirm='Confirm clear. Note: This will clear all events with "Premier" in the name.'
    )
    async def clearschedule(self, interaction: discord.Interaction, confirm: str):
        """Clear all premier and practice events from the schedule"""
        # confirm is automatically chcecked by discord, so we just need to ensure it is a required argument to "confirm"

        if not await has_permission(interaction.user.id, interaction):
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        events = guild.scheduled_events

        for event in events:
            if "Premier" in event.name:
                if event.status == discord.EventStatus.scheduled:
                    await event.cancel()
                elif event.status == discord.EventStatus.active:
                    await event.end()
                else:
                    await event.delete()

        log(f'{interaction.user.display_name} has cleared the premier schedule')
        await interaction.followup.send(f'Cleared the premier schedule', ephemeral=True)

    @app_commands.command(name="addnote", description=command_descriptions["addnote"])
    @app_commands.choices(
        _map=[
            app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
        ]
    )
    @app_commands.describe(
        _map="The map to add a note for",
        note_id="The message ID of the note to add a reference to",
        description="Provide a short description of the note. Used to identify the note when using /notes"
    )
    async def addnote(self, interaction: discord.Interaction, _map: str, note_id: str, description: str):
        """Create a practice note from a pre-existing note message"""
        if not await has_permission(interaction.user.id, interaction):
            return

        note_id = int(note_id)
        try:
            message = interaction.channel.get_partial_message(note_id)
        except (discord.HTTPException, discord.errors.NotFound):
            await interaction.response.send_message(f'Message not found', ephemeral=True)
            return

        if message.channel.id != notes_channel:
            await interaction.response.send_message(f'Invalid message ID. The message must be in the notes channel.', ephemeral=True)
            return

        if _map not in practice_notes:
            practice_notes[_map] = {}

        practice_notes[_map][note_id] = description

        save_notes(practice_notes)

        log(f'{interaction.user.display_name} has added a practice note. Note ID: {note_id}')

        await interaction.response.send_message(f'Added a practice note for {_map.title()}. Access using `/notes {_map}`', ephemeral=True)

    @app_commands.command(name="removenote", description=command_descriptions["removenote"])
    @app_commands.choices(
        _map=[
            app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
        ]
    )
    @app_commands.describe(
        _map="The map to remove the note reference from",
        note_number="The note number to remove (1-indexed). Leave empty to see options."
    )
    async def removenote(self, interaction: discord.Interaction, _map: str, note_number: int = 0):
        """Remove a practice note from the notes list"""
        if not await has_permission(interaction.user.id, interaction):
            return

        if _map not in practice_notes or len(practice_notes[_map]) == 0:
            await interaction.response.send_message(f'No notes found for {_map.title()}', ephemeral=True)
            return

        if note_number < 0 or note_number > len(practice_notes[_map]):
            await interaction.response.send_message(f'Invalid note number. Leave blank to see all options.', ephemeral=True)
            return

        if note_number == 0:
            notes_list = practice_notes[_map]
            output = f'**Practice notes for _{_map.title()}_:**\n'
            for i, note_id in enumerate(notes_list.keys()):
                output += f'- **Note {i+1}**: _{notes_list[note_id]}_\n'

            await interaction.response.send_message(output, ephemeral=True)
            return

        note_id = list(practice_notes[_map].keys())[note_number - 1]
        practice_notes[_map].pop(note_id)

        await interaction.response.send_message(f'Removed a practice note for {_map.title()}', ephemeral=True)

        save_notes(practice_notes)
        log(f'{interaction.user.display_name} has removed a practice note. Note ID: {note_id}')


class AdminMessageCommands(commands.Cog):
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

        if interval <= 0:
            await interaction.response.send_message(f'Please provide a valid interval greater than 0', ephemeral=True)
            return

        message = message.strip()

        current_time = datetime.now()

        g = interaction.guild
        if g.id == val_server:
            r = prem_role
            reminder_channel = self.bot.get_channel(prem_channel)
        else:
            r = debug_role
            reminder_channel = self.bot.get_channel(debug_channel)

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

        await asyncio.sleep(interval)

        await reminder_channel.send(message)
        log(f"Posted a reminder from {interaction.user.display_name} for {role.name}: {message}")

        reminders[str(g.id)].pop(dt_when)
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
            message = interaction.channel.get_partial_message(int(message_id))
            await message.pin()
        except (discord.HTTPException, discord.errors.NotFound):
            await interaction.response.send_message(f'Message not found.', ephemeral=True)
            return

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

        try:
            message = interaction.channel.get_partial_message(int(message_id))
            await message.unpin()
        except (discord.HTTPException, discord.errors.NotFound):
            await interaction.response.send_message(f'Message not found.', ephemeral=True)
            return

        await interaction.response.send_message(f'Message unpinned', ephemeral=True)

        log(f'{interaction.user.display_name} unpinned message {message_id}')

    @app_commands.command(name="deletemessage", description=command_descriptions["deletemessage"])
    @app_commands.describe(
        message_id="The ID of the message to delete"
    )
    async def deletemessage(self, interaction: discord.Interaction, message_id: str):
        """Delete a message by ID"""
        if not await has_permission(interaction.user.id, interaction):
            return

        try:
            await interaction.channel.get_partial_message(int(message_id)).delete()
        except (ValueError, discord.errors.NotFound):
            await interaction.response.send_message(f'Message not found.', ephemeral=True)
            return

        await interaction.response.send_message(f'Message deleted', ephemeral=True)

        log(f'{interaction.user.display_name} deleted message {message_id}')


async def setup(bot):
    await bot.add_cog(AdminPremierCommands(bot), guilds=[Object(val_server), Object(debug_server)])
    await bot.add_cog(AdminMessageCommands(bot), guilds=[Object(val_server), Object(debug_server)])
