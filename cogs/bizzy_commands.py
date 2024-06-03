from discord import Interaction, Object, app_commands
from discord.ext import commands
from discord.ext.commands import Context
from asyncio import sleep

from datetime import datetime, timedelta

from global_utils import global_utils


class BizzyCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the BizzyCommands cog

        Parameters
        ----------
        bot : discord.ext.commands.Bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the BizzyCommands cog is ready
        """
        # print("Bizzy cog loaded")
        pass

    async def sync_commands(self, guild_id: int = global_utils.debug_server) -> int:
        """Syncs the bot's app commands within the given guild

        Parameters
        ----------
        guild_id : int, optional
            The guild ID to sync the commands in, by default debug_server

        Returns
        -------
        int
            The number of commands synced
        """
        synced = await self.bot.tree.sync(guild=Object(id=guild_id))
        return synced

    # only available in the debug server
    @app_commands.command(name="clear", description=global_utils.command_descriptions["clear"])
    async def clear(self, interaction: Interaction) -> None:
        """[command] Clears the calling channel in the debug server

        Parameters
        ----------
        interaction : Interaction
            The interaction object that initiated the command
        """
        if interaction.guild.id != global_utils.debug_server:
            await interaction.response.send_message(
                "This command is not available in this server", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.channel.purge(limit=None, bulk=True)
        await interaction.followup.send("Cleared the entire channel", ephemeral=True)

    @commands.hybrid_command(name="reload", description=global_utils.command_descriptions["reload"])
    @app_commands.guilds(Object(id=global_utils.val_server), Object(global_utils.debug_server))
    @app_commands.choices(
        sync=[
            app_commands.Choice(name="Sync", value=1),
        ]
    )
    @app_commands.describe(
        sync="Sync commands after reloading"
    )
    async def reload(self, ctx: Context, sync: int = 0) -> None:
        """[command] Reloads all cogs in the bot

        Parameters
        ----------
        ctx : discord.Context
            The context object that initiated the command
        sync : int, optional
            Treated as a boolean, determines whether to sync the commands after reloading, by default 0
        """
        if ctx.author.id != global_utils.my_id:
            content = f'{ctx.author.mention}You do not have permission to use this command'
            await ctx.response.send_message(content, ephemeral=True)
            return

        async with ctx.typing(ephemeral=True):

            right_now = (datetime.now().replace(
                microsecond=0) + timedelta(seconds=5)).time()

            global_utils.premier_reminder_times[0] = global_utils.est_to_utc(
                right_now)

            await global_utils.load_cogs(self.bot)  # also *re*loads the cogs

            message = "All cogs reloaded"

            if sync:
                synced = await self.sync_commands(ctx.guild.id)
                message += f" and {len(synced)} commands synced in {ctx.guild.name}"

        m = await ctx.send(message, ephemeral=True)

        await ctx.message.delete(delay=3)
        await m.delete(delay=3)


async def setup(bot: commands.bot) -> None:
    """Adds the BizzyCommands cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.Bot
        The bot to add the cog to. Automatically passed in by the bot.load_extension method
    """
    await bot.add_cog(BizzyCommands(bot), guilds=[Object(global_utils.val_server), Object(global_utils.debug_server)])
