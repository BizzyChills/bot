from discord import Object, Interaction, app_commands
from discord.ext import commands

from my_utils import *


class BotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # log("Bot cog loaded")
        pass

    @app_commands.command(name="commands", description="Display all bot commands")
    @app_commands.choices(
        shorten=[
            app_commands.Choice(name="(Optional) Yes", value=1),
        ],
        announce=[
            app_commands.Choice(name="(Optional) Yes", value=1),
        ]
    )
    @app_commands.describe(
        shorten="Whether to display the full list of commands or a shortened list",
        announce="Whether to allow others to see the returned command list in the channel (only in bot channel)"
    )
    async def commands(self, interaction: Interaction, shorten: int = 0, announce: int = 0):
        """Displays all bot commands."""
        ephem = interaction.channel.id not in [
            debug_channel, bot_channel] or not announce

        await interaction.response.defer(ephemeral=ephem, thinking=True)

        common_commands = [f"{bold('Commands')} (start typing the command to see its description):",

                           f"- {bold('HELP')}:",
                           f" - {inline_code('/commands')}",

                           f"- {bold('INFO')}:",
                           f" - {inline_code('/schedule')}",
                           f" - {inline_code('/mappool')}",
                           f" - {inline_code('/notes')}",

                           f"- {bold('VOTING')}:",
                           f" - {inline_code('/prefermap')}",
                           f" - {inline_code('/mapvotes')}",
                           f" - {inline_code('/mapweights')}",]

        admin_commands = [f"- {bold('ADMIN ONLY')}:",
                          f" - {inline_code('/mappool')} ({bold('admin')})",
                          f" - {inline_code('/addevents')} ({bold('admin')})",
                          f" - {inline_code('/cancelevent')} ({bold('admin')})",
                          f" - {inline_code('/addpractices')} ({bold('admin')})",
                          f" - {inline_code('/cancelpractice')} ({bold('admin')})",
                          f" - {inline_code('/clearschedule')} ({bold('admin')})",
                          f" - {inline_code('/addnote')} ({bold('admin')})",
                          f" - {inline_code('/removenote')} ({bold('admin')})",
                          f" - {inline_code('/remind')} ({bold('admin')})",
                          f" - {inline_code('/pin')} ({bold('admin')})",
                          f" - {inline_code('/unpin')} ({bold('admin')})",
                          f" - {inline_code('/deletemessage')} ({bold('admin')})",]

        my_commands = [f"- {bold('BIZZY ONLY')}:",
                       f" - {inline_code('(! | /)reload')} ({bold('Bizzy')})",
                       f" - {inline_code('(! | /)sync')} ({bold('Bizzy')})",
                       f" - {inline_code('/clear')} ({bold('Bizzy')})",
                       f" - {inline_code('/clearslash')} ({bold('Bizzy')})",
                       f" - {inline_code('(! | /)kill')} ({bold('Bizzy')})",]

        useless_commands = [f"- {bold('MISC')}:",
                            f" - {inline_code('/hello')}",
                            f" - {inline_code('/feed')}",
                            f" - {inline_code('/unfeed')}",]

        output = common_commands

        if not shorten:
            if interaction.user.id in admin_ids:
                output += admin_commands

            if interaction.user.id == my_id:
                output += my_commands

        output += useless_commands

        await interaction.followup.send('\n'.join(output), ephemeral=ephem, silent=True)


async def setup(bot):
    await bot.add_cog(BotCog(bot), guilds=[Object(val_server), Object(debug_server)])
