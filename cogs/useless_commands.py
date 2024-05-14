from discord import app_commands, Interaction, Object
from discord.ext import commands
import random

from my_utils import command_descriptions, val_server, debug_server


class UselessCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
        # print("Useless cog loaded")
        pass

    @app_commands.command(name="hello", description=command_descriptions["hello"])
    async def hello(self, interaction: Interaction):
        """Says hello"""

        await interaction.response.send_message(f'Hello {interaction.user.mention}!', ephemeral=True)

    @app_commands.command(name="feed", description=command_descriptions["feed"])
    async def feed(self, interaction: Interaction):
        """Feed the bot"""

        await interaction.response.send_message("Yum yum! Thanks for the food!", ephemeral=True)

    @app_commands.command(name="unfeed", description=command_descriptions["unfeed"])
    async def unfeed(self, interaction: Interaction):
        """Unfeed the bot"""

        options = ["pukes", "poops", "performs own liposuction"]

        option = options[random.randint(0, len(options) - 1)]

        await interaction.response.send_message(f'\*looks at you with a deadpan expression\* ... \*{option}\*', ephemeral=True)


async def setup(bot):
    await bot.add_cog(UselessCommands(bot), guilds=[Object(val_server), Object(debug_server)])