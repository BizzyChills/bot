import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands, Object
import asyncio

from datetime import datetime, time, timedelta
from pytz import utc

from global_utils import global_utils


class AdminPremierCommands(commands.Cog):
    def __init__(self, bot: commands.bot) -> None:
        """Initializes the AdminPremierCommands cog and stored the IDs of the voice channels for premier events

        Parameters
        ----------
        bot : discord.ext.commands.bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot
        self.debug_voice_id = 1217649405759324236  # debug voice channel
        self.voice_channel_id = 1100632843174031476  # premier voice channel

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the AdminPremierCommands cog is ready
        """
        # global_utils.log("AdminPremier cog loaded")
        pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """A global check for all app commands in this cog to ensure the user is an admin

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command

        Returns
        -------
        bool
            True if the user is an admin, False otherwise
        """
        return await global_utils.is_admin(interaction)

    async def cog_check(self, ctx: Context) -> bool:
        """A global check for all text commands in this cog to ensure the user is an admin

        Parameters
        ----------
        ctx : discord.ext.commands.Context
            The context object that initiated the command

        Returns
        -------
        bool
            True if the user is an admin, False otherwise
        """
        return await global_utils.is_admin(ctx)

    @app_commands.command(name="add-map", description=global_utils.command_descriptions["add-map"])
    @app_commands.describe(
        map_name="The name of the map that was added to the game"
    )
    async def add_map(self, interaction: discord.Interaction, map_name: str) -> None:
        """[command] Adds a new map to the list of all maps in the game

        Parameters
        ----------
        map_name : str
            The map to add
        """
        map_name = map_name.lower()
        map_display_name = global_utils.style_text(map_name.title(), 'i')

        if map_name in global_utils.map_preferences:
            await interaction.response.send_message(f'Map "{map_display_name}" is already in the game.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        global_utils.map_preferences = {
            map_name: {}} | global_utils.map_preferences
        global_utils.map_weights = {map_name: 0} | global_utils.map_weights

        # note: this function also calls save_weights
        global_utils.save_preferences()

        await interaction.response.send_message(f'{map_display_name} has been added to the game. Some commands will not list it as a choice until the bot is reloaded (tell Bizzy).', ephemeral=True, delete_after=global_utils.delete_after_seconds)

    @app_commands.command(name="remove-map", description=global_utils.command_descriptions["remove-map"])
    @app_commands.describe(
        map_name="The name of the map that was removed from the game"
    )
    @app_commands.choices(
        map_name=[
            app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_preferences.keys()
        ]
    )
    async def remove_map(self, interaction: discord.Interaction, map_name: str) -> None:
        """[command] Removes a new map to the list of all maps in the game

        Parameters
        ----------
        map_name : str
            The map to remove
        """
        map_name = map_name.lower()
        map_display_name = global_utils.style_text(map_name.title(), 'i')

        # if its in the mappool, remove it
        try:
            where = global_utils.map_pool.index(map_name)
            global_utils.map_pool.pop(where)
        except ValueError:
            pass
        # if there is a practice note for it, remove the reference
        try:
            global_utils.practice_notes.pop(map_name)
            global_utils.save_notes()
        except KeyError:
            pass

        global_utils.map_preferences.pop(map_name)
        global_utils.map_weights.pop(map_name)

        global_utils.save_pool()
        # note: this function also calls save_weights
        global_utils.save_preferences()

        await interaction.response.send_message(f'{map_display_name} removed from the game. Some commands will continue to list it as a choice until the bot is reloaded (tell Bizzy).', ephemeral=True, delete_after=global_utils.delete_after_seconds + 3)

    @app_commands.command(name="add-events", description=global_utils.command_descriptions["add-events"])
    @app_commands.describe(
        map_list="The map order separated by commas (whitespace between maps does not matter). Ex: 'map1, map2, map3'",
        date="The date (mm/dd) of the Thursday that starts the first event. Events will be added for Thursday, Saturday, and Sunday."
    )
    async def addevents(self, interaction: discord.Interaction, map_list: str, date: str) -> None:
        """[command] Adds all premier events to the schedule at a rate of 5 events/minute

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        map_list : str
            The season's map order separated by commas (whitespace between maps does not matter). Ex: 'map1, map2, map3'
        date : str
            The date (mm/dd) of the Thursday that starts the first event. Events will be added for Thursday, Saturday, and Sunday.
        """
        # THERE IS A RATELIMIT OF 5 EVENTS/MINUTE

        guild = interaction.guild

        # split by comma and remove extra whitespace
        new_maps = [m.strip().lower() for m in map_list.split(",")]

        for map_name in new_maps:
            if map_name not in global_utils.map_pool:
                map_display_name = global_utils.style_text(map_name.title(), 'i')
                map_list = global_utils.style_text('map_list', 'c')
                map_pool = global_utils.style_text('/mappool', 'c')
                part_1 = f"{map_display_name} is not in the map pool and I only add premier events."
                part_2 = f"Ensure that {map_list} is formatted properly and that {map_pool} has been updated."
                await interaction.response.send_message(f"{part_1} {part_2}", ephemeral=True, delete_after=global_utils.delete_after_seconds)
                return

        try:
            input_date = global_utils.tz.localize(datetime.strptime(
                date, "%m/%d").replace(year=datetime.now().year))
        except ValueError:
            example = f"(ex. {global_utils.style_text('07/10', 'c')} for July 10th)"
            format_hint = f"Please provide a date in the format {global_utils.style_text('mm/dd', 'c')}. {example}"
            await interaction.response.send_message(f'Invalid date format. {format_hint}', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        if input_date.weekday() != 3:
            await interaction.response.send_message(f'Date is not a Thursday. Please provide a Thursday date.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        thur_time = datetime(year=datetime.now(
        ).year, month=input_date.month, day=input_date.day, hour=22, minute=0, second=0)
        sat_time = (thur_time + timedelta(days=2)).replace(hour=23)
        sun_time = (thur_time + timedelta(days=3))

        start_times = [global_utils.tz.localize(
            d) for d in [thur_time, sat_time, sun_time]]

        await interaction.response.defer(ephemeral=True, thinking=True)

        output = ""

        now = global_utils.tz.localize(datetime.now())

        voice_channel = discord.utils.get(guild.voice_channels, id=self.voice_channel_id) if interaction.guild.id == global_utils.val_server_id else discord.utils.get(
            guild.voice_channels, id=self.debug_voice_id)

        for i, map_name in enumerate(new_maps):
            for j, start_time in enumerate(start_times):
                if now > start_time:
                    output = "Detected that input date is in the past. Any maps that are in the past were skipped."
                    continue
                event_name = "Premier"
                event_desc = map_name.title()

                # last map and last day is playoffs
                if i == len(new_maps) - 1 and j == len(start_times) - 1:
                    event_name = "Premier Playoffs"
                    event_desc = "Playoffs"

                await guild.create_scheduled_event(name=event_name, description=event_desc, channel=voice_channel,
                                                   start_time=start_time, end_time=start_time +
                                                   timedelta(hours=1),
                                                   entity_type=discord.EntityType.voice, privacy_level=discord.PrivacyLevel.guild_only)

            start_times = [start_time + timedelta(days=7)
                           for start_time in start_times]

        new_maps = [global_utils.style_text(m, 'i') for m in ", ".join(new_maps)]
        global_utils.log(
            f'{interaction.user.display_name} has posted the premier schedule starting on {date} with maps: {new_maps}')

        m = await interaction.followup.send(f'The Premier schedule has been created.\n{output}', ephemeral=True)
        await m.delete(delay=global_utils.delete_after_seconds)

    @app_commands.command(name="cancel-event", description=global_utils.command_descriptions["cancel-event"])
    @app_commands.choices(
        map_name=[
            app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_pool] + [app_commands.Choice(name="playoffs", value="playoffs")],
        all_events=[
            app_commands.Choice(name="Yes", value=1),
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        map_name="The map to cancel the closest event for",
        all_events="Cancel all events for the specified map",
        announce="Announce the cancellation when used in the premier channel"
    )
    async def cancelevent(self, interaction: discord.Interaction, map_name: str, all_events: int = 0, announce: int = 0) -> None:
        """[command] Cancels the next premier event (or all events on a map). It's important to note that events are not practices.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        map_name : str
            The map to cancel the closest event for
        all_events : int, optional
            Treated as a boolean. Cancel all events for the specified map, by default 0
        announce : int, optional
            Treated as a boolean. Announce the cancellation when used in the premier channel, by default 0
        """
        map_display_name = global_utils.style_text(map_name.title(), 'i')

        if map_name not in global_utils.map_pool and map_name != "playoffs":
            await interaction.response.send_message(f'{map_display_name} is not in the map pool and I only cancel premier events.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        ephem = interaction.channel.id != global_utils.prem_channel_id or not announce
        await interaction.response.defer(ephemeral=ephem, thinking=True)

        guild = interaction.guild
        events = guild.scheduled_events

        message = "Event not found in the schedule."

        for event in events:
            if "Premier" in event.name and event.description.lower() == map_name:  # map is already lower
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
                    message = f'All events on {map_display_name} have been cancelled'

        if message != "Event not found in the schedule.":
            global_utils.log(
                f'{interaction.user.display_name} cancelled event - {message}')

        m = await interaction.followup.send(message, ephemeral=ephem)
        await m.delete(delay=global_utils.delete_after_seconds)

        global_utils.log(
            f"{interaction.user.display_name} cancelled event - {message}")

    @app_commands.command(name="add-practices", description=global_utils.command_descriptions["add-practices"])
    async def addpractices(self, interaction: discord.Interaction) -> None:
        """[command] Adds all premier practice events to the schedule at a rate of 5 practices/minute. Ensure that the premier events have been added first using /addevents

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        # THERE IS A RATELIMIT OF 5 EVENTS/MINUTE

        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild
        events = guild.scheduled_events

        if len([event for event in events if event.name == "Premier" and event.description != "Playoffs"]) == 0:
            m = await interaction.followup.send(f'Please add the premier events first using the `/addevents` command', ephemeral=True)
            await m.delete(delay=global_utils.delete_after_seconds)
            return

        wed_hour = global_utils.est_to_utc(time(hour=22)).hour
        fri_hour = wed_hour + 1

        for event in events:
            if event.start_time.astimezone(global_utils.tz).weekday() != 3 or "Premier" not in event.name:
                continue

            wed_time = fri_time = event.start_time.astimezone(utc)
            wed_time = wed_time.replace(hour=wed_hour) - timedelta(days=1)
            fri_time = fri_time.replace(hour=fri_hour) + timedelta(days=1)

            for start_time in [wed_time, fri_time]:
                if start_time < datetime.now().astimezone(utc):
                    continue

                event_name = "Premier Practice"
                event_desc = event.description

                await guild.create_scheduled_event(name=event_name, description=event_desc, channel=event.channel,
                                                   start_time=start_time, end_time=start_time +
                                                   timedelta(hours=1),
                                                   entity_type=discord.EntityType.voice, privacy_level=discord.PrivacyLevel.guild_only)

        global_utils.log(
            f'{interaction.user.display_name} has posted the premier practice schedule')

        m = await interaction.followup.send(f'Added premier practice events to the schedule', ephemeral=True)
        await m.delete(delay=global_utils.delete_after_seconds)

    @app_commands.command(name="cancel-practice", description=global_utils.command_descriptions["cancel-practice"])
    @app_commands.choices(
        map_name=[
            app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_pool
        ],
        all_practices=[
            app_commands.Choice(name="Yes", value=1),
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        map_name="The map to cancel the next practice for",
        all_practices="Cancel all events for the specified map",
        announce="Announce the cancellation when used in the premier channel"
    )
    async def cancelpractice(self, interaction: discord.Interaction, map_name: str, all_practices: int = 0, announce: int = 0) -> None:
        """[command] Cancels the next premier practice event (or all practices on a map)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        map_name : str
            The map to cancel the next practice for
        all_practices : int, optional
            Treated as a boolean. Cancel all practices for the specified map, by default 0
        announce : int, optional
            Treated as a boolean. Announce the cancellation when used in the premier channel, by default 0
        """
        map_display_name = global_utils.style_text(map_name.title(), 'i')

        if map_name not in global_utils.map_pool:
            hint = f"Ensure that {global_utils.style_text('/mappool', 'c')} is updated."
            await interaction.response.send_message(f"{map_display_name} is not in the map pool and I only cancel premier events. {hint}", ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        ephem = interaction.channel.id != global_utils.prem_channel_id or not announce
        await interaction.response.defer(ephemeral=ephem, thinking=True)

        guild = interaction.guild
        events = guild.scheduled_events

        message = f"No practices found for {map_display_name} in the schedule."

        for event in events:
            if event.name == "Premier Practice" and event.description.lower() == map_name:
                if event.status == discord.EventStatus.scheduled:
                    await event.cancel()
                elif event.status == discord.EventStatus.active:
                    await event.end()
                else:
                    await event.delete()

                if not all_practices:
                    e_name = event.name
                    e_date = event.start_time.date()
                    message = f'{e_name} on {map_display_name} for {e_date} has been cancelled'
                    break
                else:
                    message = f'All practices on {map_display_name} have been cancelled'

        if message != f"No practices found for {map_display_name} in the schedule.":
            global_utils.log(
                f'{interaction.user.display_name} cancelled practice: {message}')

        m = await interaction.followup.send(message, ephemeral=ephem)
        await m.delete(delay=global_utils.delete_after_seconds)

        global_utils.log(
            f"{interaction.user.display_name} cancelled practice(s) - {message}")

    @app_commands.command(name="clear-schedule", description=global_utils.command_descriptions["clear-schedule"])
    @app_commands.choices(
        confirm=[
            app_commands.Choice(
                name="I acknowledge all events with 'Premier' in the name will be deleted.", value="confirm"),
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        confirm='Confirm clear. Note: This will clear all events with "Premier" in the name.',
        announce="Announce that the schedule has been cleared when used in the premier channel"
    )
    async def clearschedule(self, interaction: discord.Interaction, confirm: str, announce: int = 0) -> None:
        """[command] Clears the premier schedule (by deleting all events with "Premier" in the name)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        confirm : str
            Confrims the schedule clear (discord indirectly ensures the user has confirmed this by requiring the argument to be present)
        announce : int, optional
            Treated as a boolean. Announce the schedule clear when used in the premier channel, by default 0
        """
        # confirm is automatically chcecked by discord, so we just need to ensure it is a required argument to "confirm"

        ephem = interaction.channel.id != global_utils.prem_channel_id or not announce

        await interaction.response.defer(ephemeral=ephem, thinking=True)

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

        global_utils.log(
            f'{interaction.user.display_name} has cleared the premier schedule')

        m = await interaction.followup.send(f'Cleared the premier schedule', ephemeral=ephem)
        await m.delete(delay=global_utils.delete_after_seconds)

    @app_commands.command(name="add-note", description=global_utils.command_descriptions["add-note"])
    @app_commands.choices(
        map_name=[
            app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_preferences.keys()
        ]
    )
    @app_commands.describe(
        map_name="The map to add a note for",
        note_id="The message ID of the note to add a reference to",
        description="Provide a short description of the note. Used to identify the note when using /notes"
    )
    async def addnote(self, interaction: discord.Interaction, map_name: str, note_id: str, description: str) -> None:
        """[command] Creates a "symbolic" link/reference to a practice note for the specified map (used to reference notes in the notes channel)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        map_name : str
            The map to add a note for
        note_id : str
            The message ID of the note to add a reference to
        description : str
            The description of the note. Used to easily identify this note when using /notes
        """
        note_id = int(note_id)
        try:
            message = interaction.channel.get_partial_message(note_id)
        except (discord.HTTPException, discord.errors.NotFound):
            await interaction.response.send_message(f'Message not found', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        if message.channel.id != global_utils.notes_channel_id:
            await interaction.response.send_message(f'Invalid message ID. The message must be in the notes channel.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        if map_name not in global_utils.practice_notes:
            global_utils.practice_notes[map_name] = {}

        global_utils.practice_notes[map_name][note_id] = description

        global_utils.save_notes()

        global_utils.log(
            f'{interaction.user.display_name} has added a practice note. Note ID: {note_id}')

        display_map_name = global_utils.style_text(map_name.title(), 'i')
        access_command = global_utils.style_text(
            f'/notes {map_name.title()}', 'c')

        await interaction.response.send_message(f'Added a practice note for {display_map_name}. Access using {access_command}', ephemeral=True, delete_after=global_utils.delete_after_seconds)

    @app_commands.command(name="remove-note", description=global_utils.command_descriptions["remove-note"])
    @app_commands.choices(
        map_name=[
            app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_preferences.keys()
        ]
    )
    @app_commands.describe(
        map_name="The map to remove the note reference from",
        note_number="The note number to remove (1-indexed). Leave empty to see options."
    )
    async def removenote(self, interaction: discord.Interaction, map_name: str, note_number: int = 0) -> None:
        """[command] Removes a practice note reference for the specified map (this does not remove the original message)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        map_name : str
            The map to remove the note reference from
        note_number : int, optional
            The note number to remove (1-indexed). Leave empty/0 to see options, by default 0
        """
        map_display_name = global_utils.style_text(map_name.title(), 'i')

        if map_name not in global_utils.practice_notes or len(global_utils.practice_notes[map_name]) == 0:
            await interaction.response.send_message(f'No notes found for {map_display_name}', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        if note_number < 0 or note_number > len(global_utils.practice_notes[map_name]):
            await interaction.response.send_message(f'Invalid note number. Leave blank to see all options.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        if note_number == 0:
            notes_list = global_utils.practice_notes[map_name]
            output = global_utils.style_text("Practice notes for ", 'b')
            output += global_utils.style_text(map_display_name, 'b') + ":\n"
            for i, note_id in enumerate(notes_list.keys()):
                note_number = f"Note {i+1}"
                output += f"- {global_utils.style_text(note_number, 'b')}: {global_utils.style_text(notes_list[note_id], 'i')}\n"

            await interaction.response.send_message(output, ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        note_id = list(global_utils.practice_notes[map_name].keys())[
            note_number - 1]
        global_utils.practice_notes[map_name].pop(note_id)

        await interaction.response.send_message(f"Removed a practice note for {map_display_name}", ephemeral=True, delete_after=global_utils.delete_after_seconds)

        global_utils.save_notes()
        global_utils.log(
            f'{interaction.user.display_name} has removed a practice note. Note ID: {note_id}')


class AdminMessageCommands(commands.Cog):
    def __init__(self, bot: commands.bot) -> None:
        """Initializes the AdminMessageCommands cog

        Parameters
        ----------
        bot : discord.ext.commands.bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the AdminMessageCommands cog is ready
        """
        # global_utils.log("AdminManage cog loaded")
        pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """A global check for all app commands in this cog to ensure the user is an admin

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command

        Returns
        -------
        bool
            True if the user is an admin, False otherwise
        """
        return await global_utils.is_admin(interaction)

    async def cog_check(self, ctx: Context) -> bool:
        """A global check for all text commands in this cog to ensure the user is an admin

        Parameters
        ----------
        ctx : discord.ext.commands.Context
            The context object that initiated the command

        Returns
        -------
        bool
            True if the user is an admin, False otherwise
        """
        return await global_utils.is_admin(ctx)

    @app_commands.command(name="remind", description=global_utils.command_descriptions["remind"])
    @app_commands.choices(
        unit=[
            app_commands.Choice(name="hours", value="hours"),
            app_commands.Choice(name="minutes", value="minutes"),
            app_commands.Choice(name="seconds", value="seconds"),
        ]
    )
    @app_commands.describe(
        interval="The number of units to wait for the reminder",
        unit="The unit of time associated with the interval",
        message="The reminder message to send to the premier role"
    )
    async def remind(self, interaction: discord.Interaction, interval: int, unit: str, *, message: str) -> None:
        """[command] Sends a reminder to the premier role (and in the premier channel) after a specified interval

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        interval : int
            The number of units to wait for the reminder
        unit : str
            The unit of time associated with the interval (hours, minutes, seconds)
        message : str
            The reminder message to send to the premier role
        """
        if interval <= 0:
            await interaction.response.send_message(f'Please provide a valid interval greater than 0', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        message = message.strip()

        current_time = datetime.now()

        g = interaction.guild
        if g.id == global_utils.val_server_id:
            role_name = global_utils.prem_role_name
            reminder_channel = self.bot.get_channel(
                global_utils.prem_channel_id)
        else:
            role_name = global_utils.debug_role_name
            reminder_channel = self.bot.get_channel(
                global_utils.debug_channel_id)

        role = discord.utils.get(g.roles, name=role_name)

        message = f"(reminder) {role.mention} {message}"
        output = ""

        if unit == "seconds":
            output = f'(reminder) I will remind {role} in {interval} second(s) with the message: "{message}"'
            when = current_time + timedelta(seconds=interval)
        elif unit == "minutes":
            when = current_time + timedelta(minutes=interval)
            output = f'(reminder) I will remind {role} in {interval} minute(s) with the message: "{message}"'
            interval *= 60
        elif unit == "hours":
            when = current_time + timedelta(hours=interval)
            output = f'(reminder) I will remind {role} in {interval} hour(s) with the message: "{message}"'
            interval *= 3600

        await interaction.response.send_message(output, ephemeral=True)

        dt_when = datetime.fromtimestamp(when.timestamp()).isoformat()

        global_utils.reminders[str(g.id)].update(
            {dt_when: message})

        global_utils.save_reminders()

        global_utils.log(
            f"Saved a reminder from {interaction.user.display_name}: {output}")

        await asyncio.sleep(interval)

        await reminder_channel.send(message)
        global_utils.log(
            f"Posted a reminder from {interaction.user.display_name} for {role.name}: {message}")

        global_utils.reminders[str(g.id)].pop(dt_when)
        global_utils.save_reminders()

    @app_commands.command(name="pin", description=global_utils.command_descriptions["pin"])
    @app_commands.describe(
        message_id="The ID of the message to pin"
    )
    async def pin(self, interaction: discord.Interaction, message_id: str) -> None:
        """[command] Pins a message by ID

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        message_id : str
            The ID of the message to pin
        """
        try:
            message = interaction.channel.get_partial_message(int(message_id))
            await message.pin()
        except (discord.HTTPException, discord.errors.NotFound):
            await interaction.response.send_message(f'Message not found.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        await interaction.response.send_message(f'Message pinned', ephemeral=True, delete_after=global_utils.delete_after_seconds)

        global_utils.log(
            f'{interaction.user.display_name} pinned message {message_id}')

    @app_commands.command(name="unpin", description=global_utils.command_descriptions["unpin"])
    @app_commands.describe(
        message_id="The ID of the message to unpin"
    )
    async def unpin(self, interaction: discord.Interaction, message_id: str) -> None:
        """[command] Unpins a message by ID

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        message_id : str
            The ID of the message to unpin
        """
        try:
            message = interaction.channel.get_partial_message(int(message_id))
            await message.unpin()
        except (discord.HTTPException, discord.errors.NotFound):
            await interaction.response.send_message(f'Message not found.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        await interaction.response.send_message(f'Message unpinned', ephemeral=True, delete_after=global_utils.delete_after_seconds)

        global_utils.log(
            f'{interaction.user.display_name} unpinned message {message_id}')

    @app_commands.command(name="delete-message", description=global_utils.command_descriptions["delete-message"])
    @app_commands.describe(
        message_id="The ID of the message to delete"
    )
    async def deletemessage(self, interaction: discord.Interaction, message_id: str) -> None:
        """[command] Deletes a message by ID

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        message_id : str
            The ID of the message to delete
        """
        try:
            await interaction.channel.get_partial_message(int(message_id)).delete()
        except (ValueError, discord.errors.NotFound):
            await interaction.response.send_message(f'Message not found.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        await interaction.response.send_message(f'Message deleted', ephemeral=True, delete_after=global_utils.delete_after_seconds)

        global_utils.log(
            f'{interaction.user.display_name} deleted message {message_id}')

    @commands.hybrid_command(name="kill", description=global_utils.command_descriptions["kill"])
    @app_commands.guilds(Object(id=global_utils.val_server_id), Object(global_utils.debug_server_id))
    async def kill(self, ctx: Context, *, reason: str = "no reason given") -> None:
        """[command] Kills the bot (shutdown)

        Parameters
        ----------
        ctx : discord.ext.commands.Context
            The context object that initiated the command
        reason : str, optional
            The reason for killing the bot, by default "no reason given"
        """
        await ctx.send(f'Goodbye cruel world!', ephemeral=True, delete_after=global_utils.delete_after_seconds)
        await ctx.message.delete(delay=global_utils.delete_after_seconds)

        global_utils.log(f"Bot killed. reason: {reason}")

        await self.bot.close()


async def setup(bot: commands.bot) -> None:
    """Adds the AdminPremierCommands and AdminMessageCommands cogs to the bot

    Parameters
    ----------
    bot : discord.ext.commands.Bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(AdminPremierCommands(bot), guilds=[Object(global_utils.val_server_id), Object(global_utils.debug_server_id)])
    await bot.add_cog(AdminMessageCommands(bot), guilds=[Object(global_utils.val_server_id), Object(global_utils.debug_server_id)])
