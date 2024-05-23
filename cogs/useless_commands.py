from discord import app_commands, Interaction, Object
from discord.ext import commands
import random

from global_utils import global_utils


class UselessCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # print("Useless cog loaded")
        pass

    @app_commands.command(name="hello", description=global_utils.command_descriptions["hello"])
    async def hello(self, interaction: Interaction):
        """Says hello"""

        await interaction.response.send_message(f'Hello {interaction.user.mention}!', ephemeral=True)

    @app_commands.command(name="feed", description=global_utils.command_descriptions["feed"])
    async def feed(self, interaction: Interaction):
        """Feed the bot"""

        await interaction.response.send_message("Yum yum! Thanks for the food!", ephemeral=True)

    @app_commands.command(name="unfeed", description=global_utils.command_descriptions["unfeed"])
    async def unfeed(self, interaction: Interaction):
        """Unfeed the bot"""

        options = ["pukes", "poops", "performs own liposuction"]

        option = options[random.randint(0, len(options) - 1)]

        await interaction.response.send_message(f'\*looks at you with a deadpan expression\* ... \*{option}\*', ephemeral=True)


async def setup(bot):
    await bot.add_cog(UselessCommands(bot), guilds=[Object(global_utils.val_server), Object(global_utils.debug_server)])
