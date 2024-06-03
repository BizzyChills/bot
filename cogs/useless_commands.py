from discord import app_commands, Interaction, Object
from discord.ext import commands
from random import choice

from global_utils import global_utils


class UselessCommands(commands.Cog):
    def __init__(self, bot: commands.bot) -> None:
        """Initializes the UselessCommands cog

        Parameters
        ----------
        bot : discord.ext.commands.bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method

        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the UselessCommands cog is ready
        """
        # print("Useless cog loaded")
        pass

    @app_commands.command(name="hello", description=global_utils.command_descriptions["hello"])
    async def hello(self, interaction: Interaction) -> None:
        """[command] Says hello to the bot

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """

        await interaction.response.send_message(f'Hello {interaction.user.mention}!', ephemeral=True)

    @app_commands.command(name="feed", description=global_utils.command_descriptions["feed"])
    async def feed(self, interaction: Interaction) -> None:
        """[command] Feeds the bot

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """

        await interaction.response.send_message("Yum yum! Thanks for the food!", ephemeral=True)

    @app_commands.command(name="unfeed", description=global_utils.command_descriptions["unfeed"])
    async def unfeed(self, interaction: Interaction) -> None:
        """[command] Unfeeds the bot

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """

        options = ["pukes", "poops", "performs own liposuction"]

        option = choice(options)

        await interaction.response.send_message(f'\*looks at you with a deadpan expression\* ... \*{option}\*', ephemeral=True)


async def setup(bot: commands.bot) -> None:
    """Adds the UselessCommands cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(UselessCommands(bot), guilds=[Object(global_utils.val_server), Object(global_utils.debug_server)])
