from discord import Interaction, Object, app_commands
from discord.ext import commands

from my_utils import *


class BizzyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # print("Bizzy cog loaded")
        pass

    async def sync_commands(self):
        """Sync the commands with the discord API"""
        synced = await self.bot.tree.sync(guild=Object(id=debug_server))
        synced = await self.bot.tree.sync(guild=Object(id=val_server))
        return synced


    @app_commands.command(name="clearlogs", description=command_descriptions["clearlogs"])
    @app_commands.choices(
        all_logs=[
            app_commands.Choice(name="All Logs", value="all"),
        ]
    )
    @app_commands.describe(
        all_logs="Clear all logs"
    )
    async def clearlogs(self, interaction: Interaction, all_logs: str = ""):
        """Clear the stdout log for today, or all logs"""
        global last_log

        if interaction.user.id != my_id:
            await interaction.response.send_message(f'You do not have permission to use this command', ephemeral=True)
            return

        if interaction.channel.id not in [debug_channel, bot_channel]:
            return

        message = "Log cleared"

        if all_logs:  # empty string is false and we already checked for "all" if it's not empty
            for file in os.listdir('./logs'):
                if not file.endswith("stdout.log"):
                    continue
                with open(f'./logs/{file}', 'w') as file:
                    file.write(
                        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

        message = "All stdout logs cleared"

        log(f"{message}")

        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="clearslash", description=command_descriptions["clearslash"])
    async def clearslash(self, interaction: Interaction):
        """Clear all slash commands."""
        if interaction.user.id != my_id or interaction.channel.id not in [debug_channel, bot_channel]:
            await interaction.response.send_message(f'You do not have permission to use this command', ephemeral=True)
            return

        g = Object(id=interaction.guild.id)

        self.bot.tree.clear_commands(guild=g)
        await self.bot.tree.sync(guild=g)

        log(f"All Bot commands cleared in the {interaction.guild.name}")

        await interaction.response.send_message(f'Cleared all slash commands', ephemeral=True)

    @commands.hybrid_command(name="sync", description=command_descriptions["sync"])
    @app_commands.guilds(Object(id=val_server), Object(debug_server))
    async def sync(self, ctx):
        """Add slash commands specific to this server. Only run this when commands are updated"""
        if ctx.channel.id not in [debug_channel, bot_channel] or ctx.author.id != my_id:
            return

        synced = await self.sync_commands()
        await ctx.send(f'Commands synced: {len(synced)}', ephemeral=True)

        log(f"Bot commands synced for {ctx.guild.name}")

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
    async def reload(self, ctx, sync: int = 0):
        """Reload all cogs."""
        if ctx.author.id != my_id:
            await ctx.send(f'You do not have permission to use this command', ephemeral=True)
            return

        # if ctx.channel.id not in [debug_channel, bot_channel]:
        #     wrong_channel(ctx)
        #     return

        if type(ctx) == Interaction:
            log(type(ctx))
            await ctx.response.defer(ephemeral=True, thinking=True)

        right_now = (datetime.now().replace(
            microsecond=0) + timedelta(seconds=5)).time()

        premier_reminder_times[0] = est_to_utc(right_now)

        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                await self.bot.reload_extension(f'cogs.{file[:-3]}')

        if sync:
            await self.sync_commands()

        if type(ctx) == Interaction:
            await ctx.followup.send(f'All cogs reloaded', ephemeral=True)
        else:
            await ctx.send(f'All cogs reloaded', ephemeral=True)

    @commands.hybrid_command(name="kill", description=command_descriptions["kill"])
    @app_commands.guilds(Object(id=val_server), Object(debug_server))
    async def kill(self, ctx, *, reason: str = "no reason given"):
        """Kill the bot."""
        if not await has_permission(ctx.author.id, ctx):
            return

        if ctx.channel.id not in [debug_channel, bot_channel]:
            return

        await ctx.send(f'Goodbye cruel world!', ephemeral=True)

        log(
            f"Bot killed for reason: {reason}")

        await self.bot.close()


async def setup(bot):
    await bot.add_cog(BizzyCommands(bot), guilds=[Object(val_server), Object(debug_server)])
