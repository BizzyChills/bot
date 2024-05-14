import os
import sys
import asyncio

import discord
from discord.ext import commands

from my_utils import *


sys.stdout = open(last_log, 'a')
# redirect stderr after connecting to discord to avoid spamming the error log with connection messages

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all(), help_command=None)

async def load():
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            await bot.load_extension(f'cogs.{file[:-3]}')

@bot.event
async def on_ready():
    global last_log_date
    sys.stderr = open(f'./logs/{last_log_date}_stderr.log', 'a')

    log(f'Bot "{bot.user.name}" has connected to Discord. Starting log')


# ---------------------Command List-----------------------------
@bot.tree.command(name="commands", description="Display all bot commands", guilds=[discord.Object(id=val_server)])
@discord.app_commands.choices(
    short=[
        discord.app_commands.Choice(name="(Optional) Shorten", value=1),
    ],
    announce=[
        discord.app_commands.Choice(name="(Optional) Announce", value=1),
    ]
)
@discord.app_commands.describe(
    short="Whether to display the full list of commands or a shortened list",
    announce="Whether to allow others to see the returned command list in the channel"
)
async def commands(interaction: discord.Interaction, short: int = 0, announce: int = 0):
    """Displays all bot commands."""
    if interaction.channel.id not in [debug_channel, bot_channel]:
        wrong_channel(interaction)
        return

    ephem = False if announce else True

    await interaction.response.defer(ephemeral=ephem, thinking=True)

    common_commands = [   "**Commands**:",
                          
                          "- **HELP**:",
                          f" - **/commands** - _{command_descriptions['commands']}_",

                          f"- **INFO**:",
                          f" - **/schedule** - _{command_descriptions['schedule']}_",
                          f" - **/mappool** - _{command_descriptions['mappool_common']}_",
                          f" - **/notes** - _{command_descriptions['notes']}_",

                          "- **VOTING**:",
                          f" - **/prefermap** - _{command_descriptions['prefermap']}_",
                          f" - **/mapvotes** - _{command_descriptions['mapvotes']}_",
                          f" - **/mapweights** - _{command_descriptions['mapweights']}_",]
    
    admin_commands = [    "- **ADMIN ONLY**:",
                        #   f" - **/role** (__admin__) - _Add or remove the '{target_role.mention}' role from a member_", # role has been deprecated
                          f" - **/mappool** (__admin__) - _{command_descriptions['mappool_admin']}_",
                          f" - **/addevents** (__admin__) - _{command_descriptions['addevents']}_",
                          f" - **/cancelevent** (__admin__) - _{command_descriptions['cancelevent']}_",
                          f" - **/addpractices** (__admin__) - _{command_descriptions['addpractices']}_",
                          f" - **/cancelpractice** (__admin__) - _{command_descriptions['cancelpractice']}_",
                          f" - **/clearschedule** (__admin__) - _{command_descriptions['clearschedule']}_",
                          f" - **/addnote** (__admin__) - _{command_descriptions['addnote']}_",
                          f" - **/remind** (__admin__) - _{command_descriptions['remind']}_",
                          f" - **/pin** (__admin__) - _{command_descriptions['pin']}_",
                          f" - **/unpin** (__admin__) - _{command_descriptions['unpin']}_",]

    my_commands = [       "- **BIZZY ONLY**:",
                          f" - **!sync** (__Bizzy__) - _{command_descriptions['sync']}_",
                          f" - **/sync** (__Bizzy__) - _{command_descriptions['sync']}_",
                          f" - **!clearslash** (__Bizzy__) - _{command_descriptions['clearslash']}_",
                          f" - **/clear** (__Bizzy__) - _{command_descriptions['clear']}_",
                          f" - **/clearlogs** (__Bizzy__) - _{command_descriptions['clearlogs']}_",
                          f" - **/kill** (__Bizzy__) - _{command_descriptions['kill']}_",]
    
    useless_commands = ['- **MISC**:',
                        f" - **/hello** - _{command_descriptions['hello']}_",
                        f" - **/feed** - _{command_descriptions['feed']}_",
                        f" - **/unfeed** - _{command_descriptions['unfeed']}_",]


    output = common_commands

    if not short:
        if interaction.user.id in admin_ids:
            output += admin_commands

        if interaction.user.id == my_id:
            output += my_commands

    
    output += useless_commands
    
    # await interaction.response.send_message('\n'.join(output), ephemeral=ephem, silent=True)
    await interaction.followup.send('\n'.join(output), ephemeral=ephem, silent=True)


async def main():
    await load()
    # await bot.start(bot_token)

asyncio.run(main())
bot.run(bot_token)
