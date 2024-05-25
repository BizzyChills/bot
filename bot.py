import os
import sys
import asyncio

from discord import Interaction, Intents, app_commands
from discord.ext import commands

from global_utils import global_utils

bot = commands.Bot(command_prefix='!',
                   intents=Intents.all(), help_command=None)

@bot.event
async def on_ready():
    sys.stderr = open(f'./logs/{global_utils.last_log_date}_stderr.log', 'a')

    global_utils.log(f'Bot "{bot.user.name}" has connected to Discord. Starting log')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.guild is None: # don't use bot commands in DMs
        await message.reply("I can't respond to messages in DMs. Please use my slash commands in the server.")
        return


@bot.tree.error
async def on_app_command_error(interaction, error):
    global_utils.debug_log(str(error))

    if interaction.is_expired():
        raise error

    if interaction.user.id == global_utils.my_id:
        await interaction.response.send_message(f"{error}", ephemeral=True)
    else:
        await interaction.response.send_message("An unexpected error occurred. Please notify Bizzy.", ephemeral=True)


@bot.event
async def on_command_error(ctx, error):
    global_utils.debug_log(str(error))

    if ctx.author.id == global_utils.my_id:
        await ctx.send(f"{error}")
    else:
        await ctx.send("An unexpected error occurred. Please notify Bizzy.")


async def main():
    await global_utils.load_cogs(bot)
    # await bot.start(global_utils.bot_token)

asyncio.run(main())
bot.run(global_utils.bot_token)
