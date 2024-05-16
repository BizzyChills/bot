import os
import sys
import asyncio

from discord import Interaction, Intents, app_commands
from discord.ext import commands

from my_utils import *


sys.stdout = open(last_log, 'a')
# redirect stderr after connecting to discord to avoid spamming the error log with connection messages

bot = commands.Bot(command_prefix='!',
                   intents=Intents.all(), help_command=None)


async def load():
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            await bot.load_extension(f'cogs.{file[:-3]}')


@bot.event
async def on_ready():
    global last_log_date
    sys.stderr = open(f'./logs/{last_log_date}_stderr.log', 'a')

    log(f'Bot "{bot.user.name}" has connected to Discord. Starting log')

@bot.event
async def on_tree_error(interaction: Interaction, error: app_commands.AppCommandError):
    log(f"Error: {error}")
    if interaction.is_expired():
        return
    
    if interaction.user.id == my_id:
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred. Please notify Bizzy.", ephemeral=True)
bot.tree.on_error = on_tree_error

async def main():
    await load()
    # await bot.start(bot_token)

asyncio.run(main())
bot.run(bot_token)
