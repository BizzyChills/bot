from discord import Object, Interaction, app_commands
from discord.ext import commands

from global_utils import global_utils


class BotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # global_utils.log("Bot cog loaded")
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
            global_utils.debug_channel, global_utils.bot_channel] or not announce

        await interaction.response.defer(ephemeral=ephem, thinking=True)

        common_commands = [f"{global_utils.bold('Commands')} (start typing the command to see its description):",

                           f"- {global_utils.bold('HELP')}:",
                           f" - {global_utils.inline_code('/commands')}",

                           f"- {global_utils.bold('INFO')}:",
                           f" - {global_utils.inline_code('/schedule')}",
                           f" - {global_utils.inline_code('/mappool')}",
                           f" - {global_utils.inline_code('/notes')}",

                           f"- {global_utils.bold('VOTING')}:",
                           f" - {global_utils.inline_code('/prefermap')}",
                           f" - {global_utils.inline_code('/mapvotes')}",
                           f" - {global_utils.inline_code('/mapweights')}",]

        admin_commands = [f"- {global_utils.bold('ADMIN ONLY')}:",
                          f" - {global_utils.inline_code('/mappool')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/addevents')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/cancelevent')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/addpractices')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/cancelpractice')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/clearschedule')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/addnote')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/removenote')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/remind')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/pin')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/unpin')} ({global_utils.bold('admin')})",
                          f" - {global_utils.inline_code('/deletemessage')} ({global_utils.bold('admin')})",]

        my_commands = [f"- {global_utils.bold('BIZZY ONLY')}:",
                       f" - {global_utils.inline_code('(! | /)reload')} ({global_utils.bold('Bizzy')})",
                       f" - {global_utils.inline_code('(! | /)sync')} ({global_utils.bold('Bizzy')})",
                       f" - {global_utils.inline_code('/clear')} ({global_utils.bold('Bizzy')})",
                       f" - {global_utils.inline_code('/clearslash')} ({global_utils.bold('Bizzy')})",
                       f" - {global_utils.inline_code('(! | /)kill')} ({global_utils.bold('Bizzy')})",]

        useless_commands = [f"- {global_utils.bold('MISC')}:",
                            f" - {global_utils.inline_code('/hello')}",
                            f" - {global_utils.inline_code('/feed')}",
                            f" - {global_utils.inline_code('/unfeed')}",]

        output = common_commands

        if not shorten:
            if interaction.user.id in global_utils.admin_ids:
                output += admin_commands

            if interaction.user.id == global_utils.my_id:
                output += my_commands

        output += useless_commands

        await interaction.followup.send('\n'.join(output), ephemeral=ephem, silent=True)


async def setup(bot):
    await bot.add_cog(BotCog(bot), guilds=[Object(global_utils.val_server), Object(global_utils.debug_server)])
