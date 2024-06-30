import discord
from discord.ext import commands
from discord import errors
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
    async def notes(self, interaction: discord.Interaction, map_name: str, note_number: int = 0, announce: int = 0) -> None:
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

        map_display_name = global_utils.style_text(map_name, 'i').title()

        if map_name not in global_utils.practice_notes or len(global_utils.practice_notes[map_name]) == 0:
            await interaction.response.send_message(f'No notes found for {map_display_name}', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        if note_number < 0 or note_number > len(global_utils.practice_notes[map_name]):
            await interaction.response.send_message(f'Invalid note number. Leave blank to see all options.', ephemeral=True, delete_after=global_utils.delete_after_seconds)
            return

        if note_number == 0:
            notes_list = global_utils.practice_notes[map_name]
            output = f"{global_utils.style_text('Practice notes', 'b')} for {map_display_name}:\n"
            for i, note_id in enumerate(notes_list.keys()):
                note_number = f"Note {i+1}"
                output += f"- {global_utils.style_text(note_number, 'b')}: {global_utils.style_text(notes_list[note_id], 'i')}\n"

            await interaction.response.send_message(output, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=ephem)

        note_id = list(global_utils.practice_notes[map_name].keys())[
            note_number - 1]
        try:
            note = await interaction.channel.fetch_message(int(note_id))
        except errors.NotFound:
            global_utils.practice_notes[map_name].pop(note_id)
            global_utils.save_notes()
            m = await interaction.followup.send(f'This note has been deleted by the author. Removing it from the notes list.', ephemeral=True)
            await m.delete(delay=global_utils.delete_after_seconds)
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
    await bot.add_cog(InfoCommands(bot), guilds=[discord.Object(global_utils.val_server_id), discord.Object(global_utils.debug_server_id)])
