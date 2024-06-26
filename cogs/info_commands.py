from discord.ext import commands
from discord import Interaction, errors, Object
from discord import app_commands

from datetime import datetime

from global_utils import global_utils


class InfoCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the InfoCommands cog

        Parameters
        ----------
        bot : discord.ext.commands.Bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the InfoCommands cog is ready
        """
        # global_utils.log("Info cog loaded")
        pass

    def format_schedule(self, schedule: list[tuple[str, datetime, str]], header: str = None) -> str:
        """Formats the schedule for display in Discord

        Parameters
        ----------
        schedule : list[tuple[str, datetime, str]]
            The schedule to format. This should be a list of tuples with the following structure: [(event_display_string, event_datetime, event_map), ...]
        header : str, optional
            The header to display at the top of the schedule, by default None

        Returns
        -------
        str
            The formatted schedule as a string to display in Discord
        """
        schedule = sorted(schedule, key=lambda x: x[1])

        subsections = {entry[2]: [] for entry in schedule}

        for m in schedule:
            map_name = m[2]
            event_display = m[0]  # just use variables for readability

            subsections[map_name].append(event_display)

        output = ""
        for map_name, event_displays in subsections.items():
            subheader = f"- {global_utils.style_text(map_name, 'iu')}:"
            event_displays = " - " + '\n - '.join(event_displays)

            output += f"{subheader}\n{event_displays}\n"

        return f"{header}\n{output}" if header else output

    @app_commands.command(name="schedule", description=global_utils.command_descriptions["schedule"])
    @app_commands.choices(
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        announce="Show the output of the command to everyone (only used in the premier channel)"
    )
    async def schedule(self, interaction: Interaction, announce: int = 0) -> None:
        """[command] Displays the premier schedule from server events

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        announce : int, optional
            Treated as a boolean. Announce the output when used in the premier channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.prem_channel_id or not announce

        await interaction.response.defer(ephemeral=ephem, thinking=True)

        guild = interaction.guild
        events = guild.scheduled_events

        event_header = f"{global_utils.style_text('Upcoming Premier Events:', 'b')}"
        practice_header = f"\n\n{global_utils.style_text('Upcoming Premier Practices:', 'b')}"
        message = []
        practice_message = []

        for event in events:
            map_name = event.description if "playoffs" not in event.name.lower(
            ) else "Playoffs"

            if "premier practice" in event.name.lower():
                practice_message.append(
                    (f"{global_utils.discord_local_time(event.start_time, with_date=True)}", event.start_time, map_name))
            elif "premier" in event.name.lower():
                message.append(
                    (f"{global_utils.discord_local_time(event.start_time, with_date=True)}", event.start_time, map_name))

        if message == []:
            message = f"{global_utils.style_text('No premier events scheduled', 'b')}"
        else:
            message = self.format_schedule(message, event_header)

        if practice_message == []:
            practice_message = f"\n\n{global_utils.style_text('No premier practices scheduled', 'b')}"
        else:
            practice_message = self.format_schedule(
                practice_message, practice_header)

        message += practice_message

        await interaction.followup.send(message, ephemeral=ephem)

    @app_commands.command(name="map-pool", description=global_utils.command_descriptions["map-pool-common"])
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
            app_commands.Choice(
                name="Clear all maps (even if map_name is set)", value="clear"),
        ],

        map_name=[
            # map_pool only has maps that are currently playable, need to get all maps
            app_commands.Choice(name=f"{s.title()}", value=s) for s in global_utils.map_preferences.keys()
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        action="The action to take on the map pool (ADMIN ONLY)",
        map_name="The map to add or remove (ADMIN ONLY)",
        announce="Show the output of the command to everyone (only used in the premier channel)"
    )
    async def mappool(self, interaction: Interaction, action: str = "", map_name: str = "", announce: int = 0) -> None:
        """[command] Adds/removes maps from the map pool or display the map pool

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        action : str, optional
            The action to take on the map pool (ADMIN ONLY), by default ""
        map_name : str, optional
            The map to add or remove (ADMIN ONLY), by default ""
        announce : int, optional
            Treated as a boolean. Announce the output when used in the premier channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.prem_channel_id or not announce

        if action == "" and map_name == "":  # display the map pool
            if len(global_utils.map_pool) == 0:
                output = f'The map pool is empty'
            else:
                output = 'Current map pool\n- ' + \
                    "\n- ".join([m.title() for m in global_utils.map_pool])

            await interaction.response.send_message(output, ephemeral=ephem)
            return

        if not await global_utils.is_admin(interaction):
            return

        def xor(a, b): return bool(a) != bool(b)

        if xor(action, map_name):  # if one is set but not the other
            await interaction.response.send_message(f"Please provide an action {global_utils.style_text('and', 'bu')} a map.", ephemeral=True)
            return

        output = ""
        map_display_name = global_utils.style_text(map_name.title(), 'i')

        if action == "clear":
            global_utils.map_pool.clear()
            output = f'The map pool has been cleared'
            log_message = f'{interaction.user.display_name} has cleared the map pool'
        elif action == "add":
            if map_name not in global_utils.map_pool:
                global_utils.map_pool.append(map_name)
                output = f'{map_display_name} has been added to the map pool'
                log_message = f'{interaction.user.display_name} has added {map_name} to the map pool'
            else:
                await interaction.response.send_message(f'{map_display_name} is already in the map pool', ephemeral=True)
                return
        elif action == "remove":
            if map_name in global_utils.map_pool:
                global_utils.map_pool.remove(map_name)
                output = f'{map_display_name} has been removed from the map pool'
                log_message = f'{interaction.user.display_name} has removed {map_name} from the map pool'
            else:
                await interaction.response.send_message(f'{map_display_name} is not in the map pool', ephemeral=True)
                return

        await interaction.response.send_message(output, ephemeral=ephem)

        global_utils.log(log_message)

        global_utils.save_pool()

    @app_commands.command(name="notes", description=global_utils.command_descriptions["notes"])
    @app_commands.choices(
        map_name=[
            app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_preferences.keys()
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        map_name="The map to display the note for",
        note_number="The note number to display (1-indexed). Leave empty to see options.",
        announce="Return the note so that it is visible to everyone (only in notes channel)"
    )
    async def notes(self, interaction: Interaction, map_name: str, note_number: int = 0, announce: int = 0) -> None:
        """[command] Displays practice notes for a map

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        map_name : str
            The map to display the note for
        note_number : int, optional
            The note number to display (1-indexed). Leaving this empty will show all options, by default 0
        announce : int, optional
            Treated as a boolean. Announce the output when used in the notes channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.notes_channel_id or not announce

        map_display_name = global_utils.style_text(map_display_name, 'i')

        if map_name not in global_utils.practice_notes or len(global_utils.practice_notes[map_name]) == 0:
            await interaction.response.send_message(f'No notes found for {map_display_name}', ephemeral=True)
            return

        if note_number < 0 or note_number > len(global_utils.practice_notes[map_name]):
            await interaction.response.send_message(f'Invalid note number. Leave blank to see all options.', ephemeral=True)
            return

        if note_number == 0:
            notes_list = global_utils.practice_notes[map_name]
            output = global_utils.style_text("Practice notes for ", 'b')
            output += global_utils.style_text(map_display_name, 'b') + ":\n"
            for i, note_id in enumerate(notes_list.keys()):
                note_number = f"Note {i+1}"
                output += f"- {global_utils.style_text(note_number, 'b')}: {global_utils.style_text(notes_list[note_id], 'i')}\n"

            await interaction.response.send_message(output, ephemeral=True)
            return

        note_id = list(global_utils.practice_notes[map_name].keys())[
            note_number - 1]
        try:
            note = await interaction.channel.fetch_message(int(note_id))
        except errors.NotFound:
            await interaction.followup.send(f'This note has been deleted by the author. Removing it from the notes list.', ephemeral=True)
            global_utils.practice_notes[map_name].pop(note_id)
            global_utils.save_notes()
            return

        output = f'Practice note for {map_display_name} (created by {note.author.display_name}):\n\n{note.content}'

        await interaction.followup.send(output, ephemeral=ephem)


async def setup(bot: commands.bot) -> None:
    """Adds the InfoCommands cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(InfoCommands(bot), guilds=[Object(global_utils.val_server_id), Object(global_utils.debug_server_id)])
