from discord.ext import commands
from discord import Interaction, errors, Object
from discord import app_commands

from global_utils import global_utils


class InfoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # print("Info cog loaded")
        pass

    @app_commands.command(name="schedule", description=global_utils.command_descriptions["schedule"])
    @app_commands.choices(
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        announce="Show the output of the command to everyone (only used in the premier channel)"
    )
    async def schedule(self, interaction: Interaction, announce: int = 0):
        """[command] Displays the premier schedule from server events

        Parameters
        ----------
        interaction : Interaction
            The interaction object that initiated the command
        announce : int, optional
            Treated as a boolean, determines whether to announce the output when used in the premier channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.prem_channel or not announce

        events = interaction.guild.scheduled_events

        event_header = "**Upcoming Premier Events:**"
        practice_header = "\n\n**Upcoming Premier Practices:**"
        message = []
        practice_message = []

        await interaction.response.defer(ephemeral=ephem, thinking=True)

        for event in events:
            if "premier practice" in event.name.lower():
                practice_message.append(
                    (f" - {global_utils.discord_local_time(event.start_time, _datetime=True)}", event.start_time, event.description))
            elif "premier" in event.name.lower():
                desc = "Playoffs" if "playoffs" in event.name.lower() else event.description
                message.append(
                    (f" - {global_utils.discord_local_time(event.start_time, _datetime=True)}", event.start_time, desc))

        if message == []:
            message = "**No premier events scheduled**"
        else:
            message = global_utils.format_schedule(message, event_header)

        if practice_message == []:
            practice_message = "\n\n**No premier practices scheduled**"
        else:
            practice_message = global_utils.format_schedule(
                practice_message, practice_header)

        message += practice_message

        await interaction.followup.send(message, ephemeral=ephem)

    @app_commands.command(name="mappool", description=global_utils.command_descriptions["mappool_common"])
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
            app_commands.Choice(
                name="Clear all maps (even if _map is set)", value="clear"),
        ],

        _map=[
            # mappool only has maps that are currently playable, need to get all maps
            app_commands.Choice(name=f"{s.title()}", value=s) for s in global_utils.map_preferences.keys()
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        action="The action to take on the map pool (ADMIN ONLY)",
        _map="The map to add or remove (ADMIN ONLY)",
        announce="Show the output of the command to everyone (only used in the premier channel)"
    )
    async def mappool(self, interaction: Interaction, action: str = "", _map: str = "", announce: int = 0):
        """[command] Adds/removes maps from the map pool or display the map pool

        Parameters
        ----------
        interaction : Interaction
            The interaction object that initiated the command
        action : str, optional
            The action to take on the map pool (ADMIN ONLY), by default ""
        _map : str, optional
            The map to add or remove (ADMIN ONLY), by default ""
        announce : int, optional
            Treated as a boolean, determines whether to announce the output when used in the premier channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.prem_channel or not announce

        if action == "" and _map == "":  # display the map pool
            if len(global_utils.map_pool) == 0:
                output = f'The map pool is empty'
            else:
                output = 'Current map pool\n- ' + \
                    "\n- ".join([m.title() for m in global_utils.map_pool])

            await interaction.response.send_message(output, ephemeral=ephem)
            return

        if not await global_utils.has_permission(interaction.user.id, interaction):
            return

        if _map ^ action:  # both parameters must be set to perform an action
            await interaction.response.send_message(f'Please provide an action and a map.', ephemeral=True)
            return

        output = ""

        if action == "clear":
            global_utils.map_pool.clear()
            output = f'The map pool has been cleared'
            log_message = f'{interaction.user.display_name} has cleared the map pool'
        elif action == "add":
            if _map not in global_utils.map_pool:
                global_utils.map_pool.append(_map)
                output = f'{_map} has been added to the map pool'
                log_message = f'{interaction.user.display_name} has added {_map} to the map pool'
            else:
                await interaction.response.send_message(f'{_map} is already in the map pool', ephemeral=True)
                return
        elif action == "remove":
            if _map in global_utils.map_pool:
                global_utils.map_pool.remove(_map)
                output = f'{_map.title()} has been removed from the map pool'
                log_message = f'{interaction.user.display_name} has removed {_map.title()} from the map pool'
            else:
                await interaction.response.send_message(f'{_map} is not in the map pool', ephemeral=True)
                return

        await interaction.response.send_message(output, ephemeral=ephem)

        global_utils.log(log_message)

        global_utils.save_pool()

    @app_commands.command(name="notes", description=global_utils.command_descriptions["notes"])
    @app_commands.choices(
        _map=[
            app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_preferences.keys()
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        _map="The map to display the note for",
        note_number="The note number to display (1-indexed). Leave empty to see options.",
        announce="Return the note so that it is visible to everyone (only in notes channel)"
    )
    async def notes(self, interaction: Interaction, _map: str, note_number: int = 0, announce: int = 0):
        """[command] Displays practice notes for a map

        Parameters
        ----------
        interaction : Interaction
            The interaction object that initiated the command
        _map : str
            The map to display the note for
        note_number : int, optional
            The note number to display (1-indexed). Leaving this empty will show all options, by default 0
        announce : int, optional
            Treated as a boolean, determines whether to announce the output when used in the premier channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.prem_channel or not announce

        # user gave a valid map, but there are no notes for it
        if _map not in global_utils.practice_notes or len(global_utils.practice_notes[_map]) == 0:
            await interaction.response.send_message(f'There are no notes for {_map.title()}', ephemeral=True)
            return

        if note_number < 0 or note_number > len(global_utils.practice_notes[_map]):
            await interaction.response.send_message(f'Invalid note number. Leave blank to see all options.', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=ephem, thinking=True)

        if note_number == 0:
            notes_list = global_utils.practice_notes[_map]
            output = f'**Practice notes for _{_map.title()}_:**\n'
            for i, note_id in enumerate(notes_list.keys()):
                output += f'- **Note {i+1}**: _{notes_list[note_id]}_\n'

            await interaction.followup.send(output, ephemeral=True)
            return

        note_id = list(global_utils.practice_notes[_map].keys())[note_number - 1]
        try:
            note = await interaction.channel.fetch_message(int(note_id))
        except errors.NotFound:
            await interaction.followup.send(f'This note has been deleted by the author. Removing it from the notes list.', ephemeral=True)
            global_utils.practice_notes[_map].pop(note_id)
            global_utils.save_notes()
            return

        output = f'Practice note for {_map.title()} (created by {note.author.display_name}):\n\n{note.content}'

        await interaction.followup.send(output, ephemeral=ephem)


async def setup(bot):
    await bot.add_cog(InfoCommands(bot), guilds=[Object(global_utils.val_server), Object(global_utils.debug_server)])
