from discord.ext import commands
from discord import Interaction, errors, Object
from discord import app_commands

from my_utils import *


class InfoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # print("Info cog loaded")
        pass

    @app_commands.command(name="schedule", description=command_descriptions["schedule"])
    async def schedule(self, interaction: Interaction):
        """Display the premier schedule"""

        if interaction.channel.id not in all_channels:
            await wrong_channel(interaction)
            return

        guild = self.bot.get_guild(
            val_server) if interaction.guild.id == val_server else self.bot.get_guild(debug_server)
        events = guild.scheduled_events

        event_header = "**Upcoming Premier Events:**"
        practice_header = "\n\n**Upcoming Premier Practices:**"
        message = []
        practice_message = []

        await interaction.response.defer(ephemeral=True, thinking=True)

        for event in events:
            if "premier practice" in event.name.lower():
                practice_message.append(
                    (f" - {discord_local_time(event.start_time, _datetime=True)}", event.start_time, event.description))
            elif "premier" in event.name.lower():
                desc = "Playoffs" if "playoffs" in event.name.lower() else event.description
                message.append(
                    (f" - {discord_local_time(event.start_time, _datetime=True)}", event.start_time, desc))

        ephem = True if interaction.channel.id == bot_channel else False

        if message == []:
            message = "**No premier events scheduled**"
        else:
            message = format_schedule(message, event_header)

        if practice_message == []:
            practice_message = "\n\n**No premier practices scheduled**"
        else:
            practice_message = format_schedule(
                practice_message, practice_header)

        message += practice_message

        await interaction.followup.send(message, ephemeral=ephem)

    @app_commands.command(name="mappool", description=command_descriptions["mappool_common"])
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
            app_commands.Choice(
                name="Clear all maps (even if _map is set)", value="clear"),
        ],

        _map=[
            # mappool only has maps that are currently playable, need to get all maps
            app_commands.Choice(name=f"{s.title()}", value=s) for s in map_preferences.keys()
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        action="The action to take on the map pool (ADMIN ONLY)",
        _map="The map to add or remove (ADMIN ONLY)",
        announce="Show the output of the command to everyone when used in the premier channel"
    )
    async def mappool(self, interaction: Interaction, action: str = "", _map: str = "", announce: int = 0):
        """Add or remove maps from the map pool"""

        if interaction.channel.id not in all_channels:
            await wrong_channel(interaction)
            return

        if interaction.channel.id != prem_channel:
            announce = 0  # don't announce in non-premier channels

        if action == "" and _map == "":
            ephem = False if announce else True

            if len(map_pool) == 0:
                output = f'The map pool is empty'
            else:
                output = f'Current map pool: {", ".join(map_pool)}'

            await interaction.response.send_message(output, ephemeral=ephem)
            return

        if not await has_permission(interaction.user.id, interaction):
            return

        if action == "" or (_map == "" and action != "clear"):  # clear doesn't need a map
            await interaction.response.send_message(f'Please provide an action and a map.', ephemeral=True)
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

        ephem = False if announce else True

        await interaction.response.send_message(output, ephemeral=ephem)

        log(log_message)

        save_pool(map_pool)

    @app_commands.command(name="notes", description=command_descriptions["notes"])
    @app_commands.choices(
        _map=[
            app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        _map="The map to display the note for",
        note_number="The note number to display (1-indexed). Leave empty to see options.",
        announce="Return the note so that it is visible to everyone"
    )
    async def notes(self, interaction: Interaction, _map: str, note_number: int = 0, announce: int = 0):
        """Display a practice note for a map"""

        if interaction.channel.id != notes_channel:
            await wrong_channel(interaction)
            return

        _map = _map.lower()

        if _map not in practice_notes or len(practice_notes[_map]) == 0:  # user gave a valid map, but there are no notes for it
            await interaction.response.send_message(f'There are no notes for {_map.title()}', ephemeral=True)
            return

        if note_number < 0 or note_number > len(practice_notes[_map]):
            await interaction.response.send_message(f'Invalid note number. Leave blank to see all options.', ephemeral=True)
            return

        ephem = False if announce else True # has to explicitly be bool for lib, so can't use announce
        await interaction.response.defer(ephemeral=ephem, thinking=True)

        if note_number == 0:
            notes_list = practice_notes[_map]
            output = f'**Practice notes for _{_map.title()}_:**\n'
            for i, note_id in enumerate(notes_list.keys()):
                output += f'- **Note {i+1}**: _{notes_list[note_id]}_\n'

            await interaction.followup.send(output, ephemeral=True)
            return

        note_id = list(practice_notes[_map].keys())[note_number - 1]
        try:
            note = await interaction.channel.fetch_message(int(note_id))
        except errors.NotFound:
            await interaction.followup.send(f'This note has been deleted by the author. Removing it from the notes list.', ephemeral=True)
            practice_notes[_map].pop(note_id)
            save_notes(practice_notes)
            return

        output = f'Practice note for {_map.title()} (created by {note.author.display_name}):\n\n{note.content}'

        await interaction.followup.send(output, ephemeral=ephem)


async def setup(bot):
    await bot.add_cog(InfoCommands(bot), guilds=[Object(val_server), Object(debug_server)])