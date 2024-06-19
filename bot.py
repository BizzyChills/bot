import sys
import asyncio
from os import getenv, listdir, remove

from discord import Interaction, Intents, app_commands, Message
from discord.ext import commands
from discord.ext.commands import Context

from global_utils import global_utils
from cogs.persist_commands import PersistentButtons, PersistCommands


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
    sys.stderr = open(f'./logs/{global_utils.log_date}_stderr.log', 'a')

    global_utils.log(
        f'Bot "{bot.user.name}" has connected to Discord. Starting log')


async def setup_hook() -> None:
    """Re-links/syncs the bot's persistent buttons"""
    cog = PersistCommands(bot)
    bot.add_view(PersistentButtons(cog=cog))


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


@bot.event
async def on_message(message: Message) -> None:
    """[event] Executes when a message is sent

    Parameters
    ----------
    message : discord.Message
        The message object that was sent
    """
    if message.author == bot.user or message.channel.id != global_utils.bot_channel_id:
        return

    if message.content == "!kill" or message.content == "!reload":
        await bot.process_commands(message)

    # if message is in bot channel, and not an approved text command, delete it
    # note: this does not affect slash commands
    await message.delete()


async def main() -> None:
    """Loads all cogs and starts the bot
    """
    sys.stdout = open(global_utils.log_filepath, 'a')
    bot.setup_hook = setup_hook
    await global_utils.load_cogs(bot)
    await bot.start(bot_token)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # honestly, needs to be taken care of better. maybe later :p
        for file in listdir('./local_storage/temp_music'):
            remove(f'./local_storage/temp_music/{file}')
        asyncio.run(bot.close())
    # bot.run(bot_token)
else:
    print("This script is not meant to be imported. Please run it directly.")
    sys.exit(1)
