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


@bot.event
async def on_ready():
    global last_log_date
    sys.stderr = open(f'./logs/{last_log_date}_stderr.log', 'a')

    log(f'Bot "{bot.user.name}" has connected to Discord. Starting log')


@bot.tree.error
async def on_app_command_error(interaction, error):
    log(str(error))

    if interaction.is_expired():
        raise error

    if interaction.user.id == my_id:
        await interaction.response.send_message(f"{error}", ephemeral=True)
    else:
        await interaction.response.send_message("An unexpected error occurred. Please notify Bizzy.", ephemeral=True)


@bot.event
async def on_command_error(ctx, error):
    log(str(error))

    if ctx.author.id == my_id:
        await ctx.send(f"{error}")
    else:
        await ctx.send("An unexpected error occurred. Please notify Bizzy.")


async def main():
    await load_cogs(bot)
    # await bot.start(bot_token)

asyncio.run(main())
bot.run(bot_token)
