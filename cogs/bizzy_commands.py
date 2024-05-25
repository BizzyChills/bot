from discord import Interaction, Object, app_commands
from discord.ext import commands
from discord.ext.commands import Context
from asyncio import sleep

from datetime import datetime, timedelta

from global_utils import global_utils


class BizzyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
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
    async def clear(self, interaction: Interaction):
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

    # /clearslash has been deprecated; I couldn't think of a use case for it that couldn't be done by removing the bot from the server.
    # @app_commands.command(name="clearslash", description=global_utils.command_descriptions["clearslash"])
    # async def clearslash(self, interaction: Interaction):
    #     """[command] Clears all of the bot's slash commands in the calling server

    #     Parameters
    #     ----------
    #     interaction : discord.Interaction
    #         The interaction object that initiated the command
    #     """
    #     if interaction.user.id != global_utils.my_id:
    #         await interaction.response.send_message(f'You do not have permission to use this command', ephemeral=True)
    #         return

    #     g = Object(id=interaction.guild.id)

    #     await interaction.response.defer(ephemeral=True, thinking=True)
    #     self.bot.tree.clear_commands(guild=g)
    #     await self.sync_commands(interaction.guild.id)

    #     global_utils.log(f"Bot's slash commands cleared in server: {interaction.guild.name}")

    #     await interaction.followup.send(f'Cleared all of {self.bot.user.name}\'s slash commands', ephemeral=True)

    # /sync has been deprecated; use /reload sync=1 instead. There is negligible cost in running /reload, so just sync there when needed
    # @commands.hybrid_command(name="sync", description=global_utils.command_descriptions["sync"])
    # @app_commands.guilds(Object(id=global_utils.val_server), Object(global_utils.debug_server))
    # async def sync(self, ctx: Context):
    #     """[command] Syncs the bot's app commands in the calling server

    #     Parameters
    #     ----------
    #     ctx : discord.Context
    #         The context object that initiated the command
    #     """
    #     if ctx.author.id != global_utils.my_id:
    #         await ctx.send(f'You do not have permission to use this command', ephemeral=True)

    #     async with ctx.typing(ephemeral=True):

    #         synced = await self.sync_commands(ctx.guild.id)

    #     m = await ctx.send(f'Commands synced: {len(synced)}', ephemeral=True)

    #     await ctx.message.delete(delay=3)
    #     await m.delete(delay=3)

    #     global_utils.log(f"Bot commands synced for {ctx.guild.name}")

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
    async def reload(self, ctx: Context, sync: int = 0):
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

            global_utils.premier_reminder_times[0] = global_utils.est_to_utc(right_now)

            await global_utils.load_cogs(self.bot, reload=True)

            message = "All cogs reloaded"

            if sync:
                synced = await self.sync_commands(ctx.guild.id)
                message += f" and {len(synced)} commands synced in {ctx.guild.name}"

        m = await ctx.send(message, ephemeral=True)

        await ctx.message.delete(delay=3)
        await m.delete(delay=3)

    @commands.hybrid_command(name="kill", description=global_utils.command_descriptions["kill"])
    @app_commands.guilds(Object(id=global_utils.val_server), Object(global_utils.debug_server))
    async def kill(self, ctx: Context, *, reason: str = "no reason given"):
        """[command] Kills the bot (shutdown)

        Parameters
        ----------
        ctx : discord.Context
            The context object that initiated the command
        reason : str, optional
            The reason for killing the bot, by default "no reason given"
        """
        if not await global_utils.has_permission(ctx.author.id, ctx):
            return

        m = await ctx.send(f'Goodbye cruel world!', ephemeral=True)

        await ctx.message.delete(delay=3)
        await m.delete(delay=3)

        global_utils.log(f"Bot killed. reason: {reason}")

        await self.bot.close()


async def setup(bot):
    await bot.add_cog(BizzyCommands(bot), guilds=[Object(global_utils.val_server), Object(global_utils.debug_server)])
