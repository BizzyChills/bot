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
        short=[
            app_commands.Choice(name="(Optional) Shorten", value=1),
        ],
        announce=[
            app_commands.Choice(name="(Optional) Announce", value=1),
        ]
    )
    @app_commands.describe(
        short="Whether to display the full list of commands or a shortened list",
        announce="Whether to allow others to see the returned command list in the channel"
    )
    async def commands(self, interaction: Interaction, short: int = 0, announce: int = 0):
        """Displays all bot commands."""
        if interaction.channel.id not in [debug_channel, bot_channel]:
            wrong_channel(interaction)
            return

        ephem = False if announce else True

        await interaction.response.defer(ephemeral=ephem, thinking=True)

        common_commands = [ "**Commands** (start typing the command to see its description):",

                            "- **HELP**:",
                            f" - _/commands_",

                            f"- **INFO**:",
                            f" - _/schedule_",
                            f" - _/mappool_",
                            f" - _/notes_",

                            "- **VOTING**:",
                            f" - _/prefermap_",
                            f" - _/mapvotes_",
                            f" - _/mapweights_",]

        admin_commands = [  "- **ADMIN ONLY**:",
                            f" - _/mappool_ (**admin**)",
                            f" - _/addevents_ (**admin**)",
                            f" - _/cancelevent_ (**admin**)",
                            f" - _/addpractices_ (**admin**)",
                            f" - _/cancelpractice_ (**admin**)",
                            f" - _/clearschedule_ (**admin**)",
                            f" - _/addnote_ (**admin**)",
                            f" - _/removenote_ (**admin**)",
                            f" - _/remind_ (**admin**)",
                            f" - _/pin_ (**admin**)",
                            f" - _/unpin_ (**admin**)",
                            f" - _/deletemessage_ (**admin**)",]

        my_commands = [     "- **BIZZY ONLY**:",
                            f" - _/reload_ (**Bizzy**)",
                            f" - **!sync** (**Bizzy**)",
                            f" - _/sync_ (**Bizzy**)",
                            f" - _/clear_ (**Bizzy**)",
                            f" - **!clearslash** (**Bizzy**)",
                            f" - _/clearlogs_ (**Bizzy**)",
                            f" - _/kill_ (**Bizzy**)",]

        useless_commands = ["- **MISC**:",
                            f" - _/hello_",
                            f" - _/feed_",
                            f" - _/unfeed_",]

        output = common_commands

        if not short:
            if interaction.user.id in admin_ids:
                output += admin_commands

            if interaction.user.id == my_id:
                output += my_commands

        output += useless_commands

        # await interaction.response.send_message('\n'.join(output), ephemeral=ephem, silent=True)
        await interaction.followup.send('\n'.join(output), ephemeral=ephem, silent=True)


async def setup(bot):
    await bot.add_cog(BotCog(bot), guilds=[Object(val_server), Object(debug_server)])