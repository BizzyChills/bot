import sys
import asyncio
from os import getenv

from discord import Interaction, Intents, app_commands
from discord.ext import commands
from discord.ext.commands import Context

from global_utils import global_utils

bot = commands.Bot(command_prefix='!',
                   intents=Intents.all(), help_command=None)

bot_token = getenv("DISCORD_BOT_TOKEN")

if not bot_token:
    raise ValueError(
        "DISCORD_BOT_TOKEN is not set in the environment variables")


@bot.event
async def on_ready() -> None:
    """[event] Executes when the bot is ready
    """
    sys.stderr = open(f'./logs/{global_utils.last_log_date}_stderr.log', 'a')

    global_utils.log(
        f'Bot "{bot.user.name}" has connected to Discord. Starting log')


@bot.tree.error
async def on_app_command_error(interaction: Interaction, error: app_commands.AppCommandError) -> None:
    """[error] Handles slash command errors

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object that initiated the command
    error : discord.app_commands.AppCommandError
        The error that occurred

    Raises
    ------
    error
        If the interaction is expired and cannot be responded to, simply raise the error
    """
    global_utils.debug_log(str(error))

    if interaction.is_expired():
        raise error

    if interaction.user.id == global_utils.my_id:
        await interaction.response.send_message(f"{error}", ephemeral=True)
    else:
        m = await interaction.response.send_message("An unexpected error occurred. Please notify Bizzy.", ephemeral=True)
        await m.delete(delay=5)
        await interaction.message.delete(delay=5)


@bot.event
async def on_command_error(ctx: Context, error: commands.CommandError) -> None:
    """[error] Handles text command errors

    Parameters
    ----------
    ctx : discord.ext.commands.Context
        The context object that initiated the command
    error : discord.ext.commands.CommandError
        The error that occurred
    """
    global_utils.debug_log(str(error))

    if ctx.author.id == global_utils.my_id:
        await ctx.send(f"{error}")
    else:
        m = await ctx.send("An unexpected error occurred. Please notify Bizzy.")
        await m.delete(delay=5)
        await ctx.message.delete(delay=5)


async def main() -> None:
    """Loads all cogs and starts the bot
    """
    await global_utils.load_cogs(bot)
    await bot.start(bot_token)

if __name__ == '__main__':
    asyncio.run(main())
    # bot.run(bot_token)
else:
    print("This script is not meant to be imported. Please run it directly.")
    sys.exit(1)