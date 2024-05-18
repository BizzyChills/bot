from discord import Interaction, Object, app_commands
from discord.ext import commands
from discord.ext.commands import Context
from asyncio import sleep

from my_utils import *


class BizzyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # print("Bizzy cog loaded")
        pass

    async def sync_commands(self, guild_id: int = debug_server):
        """Sync the commands with the discord API"""
        synced = await self.bot.tree.sync(guild=Object(id=guild_id))
        return synced

    # only available in the debug server
    @app_commands.command(name="clear", description=command_descriptions["clear"])
    async def clear(self, interaction: Interaction):
        """clear the debug channel"""
        if interaction.guild.id != debug_server:
            await interaction.response.send_message(
                "This command is not available in this server", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.channel.purge(limit=None, bulk=True)
        await interaction.followup.send("Cleared the entire channel", ephemeral=True)

    # /clearslash has been deprecated; I couldn't think of a use case for it that couldn't be done by removing the bot from the server.
    # @app_commands.command(name="clearslash", description=command_descriptions["clearslash"])
    # async def clearslash(self, interaction: Interaction):
    #     """Clear all slash commands in the calling server"""
    #     if interaction.user.id != my_id:
    #         await interaction.response.send_message(f'You do not have permission to use this command', ephemeral=True)
    #         return

    #     g = Object(id=interaction.guild.id)

    #     await interaction.response.defer(ephemeral=True, thinking=True)
    #     self.bot.tree.clear_commands(guild=g)
    #     await self.sync_commands(interaction.guild.id)

    #     log(f"Bot's slash commands cleared in server: {interaction.guild.name}")

    #     await interaction.followup.send(f'Cleared all of {self.bot.user.name}\'s slash commands', ephemeral=True)

    # /sync has been deprecated; use /reload sync=1 instead. There is negligible cost in running /reload, so just sync there when needed
    # @commands.hybrid_command(name="sync", description=command_descriptions["sync"])
    # @app_commands.guilds(Object(id=val_server), Object(debug_server))
    # async def sync(self, ctx: Context):
    #     """Add slash commands specific to this server. Only run this when commands are updated"""
    #     if ctx.author.id != my_id:
    #         await ctx.send(f'You do not have permission to use this command', ephemeral=True)

    #     async with ctx.typing(ephemeral=True):

    #         synced = await self.sync_commands(ctx.guild.id)

    #     m = await ctx.send(f'Commands synced: {len(synced)}', ephemeral=True)

    #     await ctx.message.delete(delay=3)
    #     await m.delete(delay=3)

    #     log(f"Bot commands synced for {ctx.guild.name}")

    @commands.hybrid_command(name="reload", description=command_descriptions["reload"])
    @app_commands.guilds(Object(id=val_server), Object(debug_server))
    @app_commands.choices(
        sync=[
            app_commands.Choice(name="Sync", value=1),
        ]
    )
    @app_commands.describe(
        sync="Sync commands after reloading"
    )
    async def reload(self, ctx: Context, sync: int = 0):
        """Reload all cogs."""
        if ctx.author.id != my_id:
            content = f'{ctx.author.mention}You do not have permission to use this command'
            await ctx.response.send_message(content, ephemeral=True)
            return

        async with ctx.typing(ephemeral=True):

            right_now = (datetime.now().replace(
                microsecond=0) + timedelta(seconds=5)).time()

            premier_reminder_times[0] = est_to_utc(right_now)

            await load_cogs(self.bot, reload=True)

            message = "All cogs reloaded"

            if sync:
                synced = await self.sync_commands(ctx.guild.id)
                message += f" and {len(synced)} commands synced in {ctx.guild.name}"

        m = await ctx.send(message, ephemeral=True)

        await ctx.message.delete(delay=3)
        await m.delete(delay=3)

    @commands.hybrid_command(name="kill", description=command_descriptions["kill"])
    @app_commands.guilds(Object(id=val_server), Object(debug_server))
    async def kill(self, ctx: Context, *, reason: str = "no reason given"):
        """Kill the bot."""
        if not await has_permission(ctx.author.id, ctx):
            return

        m = await ctx.send(f'Goodbye cruel world!', ephemeral=True)

        await ctx.message.delete(delay=3)
        await m.delete(delay=3)

        log(f"Bot killed. reason: {reason}")

        await self.bot.close()


async def setup(bot):
    await bot.add_cog(BizzyCommands(bot), guilds=[Object(val_server), Object(debug_server)])
