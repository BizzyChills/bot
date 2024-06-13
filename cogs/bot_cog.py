from discord import Object, Interaction, app_commands
from discord.ext import commands

from global_utils import global_utils


class BotCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the BotCog cog

        Parameters
        ----------
        bot : discord.ext.commands.Bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the BotCog cog is ready
        """
        # global_utils.log("Bot cog loaded")
        pass

    @app_commands.command(name="commands", description=global_utils.command_descriptions["commands"])
    @app_commands.choices(
        list_type=[
            app_commands.Choice(name="only the bare minimum", value="basic"),
            app_commands.Choice(name="all non-admin commands", value="user"),
            app_commands.Choice(
                name="bare minimum + admin commands", value="basic_admin"),
            app_commands.Choice(name="only admin commands", value="admin"),
            app_commands.Choice(
                name="all commands except Bizzy's", value="user_admin"),
            app_commands.Choice(name="every command available", value="all"),
        ],
        announce=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        list_type="The type of command list to display",
        announce="Allow others to see the returned command list in the channel (only in bot channel)"
    )
    async def commands(self, interaction: Interaction, list_type: str = "all", announce: int = 0) -> None:
        """[command] Displays all bot commands

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        list_type : str, optional
            The type of command list to display, by default "user"
        announce : int, optional
            Treated as a boolean. Announce the output when used in the bot channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.bot_channel_id or not announce

        await interaction.response.defer(ephemeral=ephem, thinking=True)

        basic_commands = [f"{global_utils.style_text('Commands', 'b')} (start typing the command to see its description):",

                          f"- {global_utils.style_text('HELP', 'b')}:",
                          f" - {global_utils.style_text('/commands', 'c')}",
                          f" - {global_utils.style_text('/source-code', 'c')}",

                          f"- {global_utils.style_text('INFO', 'b')}:",
                          f" - {global_utils.style_text('/schedule', 'c')}",
                          f" - {global_utils.style_text('/map-pool', 'c')}",
                          f" - {global_utils.style_text('/notes', 'c')}",

                          f"- {global_utils.style_text('VOTING', 'b')}:",
                          f" - {global_utils.style_text('/prefer-map', 'c')}",
                          f" - {global_utils.style_text('/map-votes', 'c')}",
                          f" - {global_utils.style_text('/map-weights', 'c')}",]

        admin_commands = [f"- {global_utils.style_text('ADMIN ONLY', 'b')}:",
                          f" - {global_utils.style_text('/map-pool', 'c')}",
                          f" - {global_utils.style_text('/add-map', 'c')}",
                          f" - {global_utils.style_text('/remove-map', 'c')}",
                          f" - {global_utils.style_text('/add-events', 'c')}",
                          f" - {global_utils.style_text('/cancel-event', 'c')}",
                          f" - {global_utils.style_text('/add-practices', 'c')}",
                          f" - {global_utils.style_text('/cancel-practice', 'c')}",
                          f" - {global_utils.style_text('/clear-schedule', 'c')}",
                          f" - {global_utils.style_text('/add-note', 'c')}",
                          f" - {global_utils.style_text('/remove-note', 'c')}",
                          f" - {global_utils.style_text('/remind', 'c')}",
                          f" - {global_utils.style_text('/pin', 'c')}",
                          f" - {global_utils.style_text('/unpin', 'c')}",
                          f" - {global_utils.style_text('/delete-message', 'c')}",
                          f" - {global_utils.style_text('(! | /)kill', 'c')}",]

        my_commands = [f"- {global_utils.style_text('BIZZY ONLY', 'b')}:",
                       f" - {global_utils.style_text('(! | /)reload', 'c')}",
                       f" - {global_utils.style_text('/clear', 'c')}",
                       f" - {global_utils.style_text('/feature', 'c')}",]

        misc_commands = [f"- {global_utils.style_text('MISC', 'b')}:",
                         f" - {global_utils.style_text('/hello', 'c')}",
                         f" - {global_utils.style_text('/trivia', 'c')}",
                         f" - {global_utils.style_text('/feed', 'c')}",
                         f" - {global_utils.style_text('/unfeed', 'c')}",]

        music_commands = [f"- {global_utils.style_text('MUSIC', 'b')}:",
                          f" - {global_utils.style_text('/join-voice', 'c')}",
                          f" - {global_utils.style_text('/leave-voice', 'c')}",
                          f" - {global_utils.style_text('/add-song', 'c')}",
                          f" - {global_utils.style_text('/playlist', 'c')}",
                          f" - {global_utils.style_text('/play-song', 'c')}",
                          f" - {global_utils.style_text('/pause-song', 'c')}",
                          f" - {global_utils.style_text('/resume-song', 'c')}",
                          f" - {global_utils.style_text('/stop-song', 'c')}",
                          f" - {global_utils.style_text('/skip-song', 'c')}",
                          f" - {global_utils.style_text('/loop-song', 'c')}",]

        user_commands = basic_commands + music_commands + misc_commands
        basic_admin_commands = basic_commands + admin_commands
        user_admin_commands = user_commands + admin_commands
        all_commands = user_admin_commands + my_commands

        match list_type:
            case "basic":
                output = basic_commands
            case "user":
                output = user_commands
            case "basic_admin":
                output = basic_admin_commands
            case "admin":
                output = admin_commands
                if interaction.user.id == global_utils.my_id:
                    output += my_commands
            case "user_admin":
                output = user_admin_commands
            case "all":
                output = all_commands
            case _:
                output = all_commands

        await interaction.followup.send('\n'.join(output), ephemeral=ephem, silent=True)

    @app_commands.command(name="source-code", description=global_utils.command_descriptions["source-code"])
    async def source(self, interaction: Interaction) -> None:
        """[command] Links the repo containing the source code for the bot

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await interaction.response.send_message(f"Here is my source code: {global_utils.style_text(global_utils.source_code, 'c')}", ephemeral=True)


async def setup(bot: commands.bot) -> None:
    """Adds the BotCog cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(BotCog(bot), guilds=[Object(global_utils.val_server_id), Object(global_utils.debug_server_id)])
