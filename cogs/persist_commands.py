import discord
from discord import app_commands
from discord.ext import commands

from global_utils import global_utils


class PersistCommands(commands.Cog):
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

    async def commands(self, interaction: discord.Interaction, list_type: str = "all") -> None:
        """[command] Displays all bot commands

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        list_type : str, optional
            The type of command list to display, by default "user"
        """
        ephem = True

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
                          f" - {global_utils.style_text('/prefer-maps', 'c')}",
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
                          f" - {global_utils.style_text('/music (WIP)', 'c')}",
                          ]

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

    async def schedule(self, interaction: discord.Interaction) -> None:
        """[command] Displays the premier schedule from server events

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        ephem = True

        await interaction.response.defer(ephemeral=ephem, thinking=True)

        guild = interaction.guild
        events = guild.scheduled_events

        event_header = f"{global_utils.style_text('Upcoming Premier Events:', 'b')}"
        practice_header = f"\n\n{global_utils.style_text('Upcoming Premier Practices:', 'b')}"
        message = []
        practice_message = []

        for event in events:
            map_name = event.description if "playoffs" not in event.name.lower(
            ) else "Playoffs"

            if "premier practice" in event.name.lower():
                practice_message.append(
                    (f"{global_utils.discord_local_time(event.start_time, with_date=True)}", event.start_time, map_name))
            elif "premier" in event.name.lower():
                message.append(
                    (f"{global_utils.discord_local_time(event.start_time, with_date=True)}", event.start_time, map_name))

        if message == []:
            message = f"{global_utils.style_text('No premier events scheduled', 'b')}"
        else:
            message = self.format_schedule(message, event_header)

        if practice_message == []:
            practice_message = f"\n\n{global_utils.style_text('No premier practices scheduled', 'b')}"
        else:
            practice_message = self.format_schedule(
                practice_message, practice_header)

        message += practice_message

        await interaction.followup.send(message, ephemeral=ephem)

    @app_commands.command(name="persist", description=global_utils.command_descriptions["persist"])
    async def persist(self, interaction: discord.Interaction) -> None:
        """[command] Sends the persistent buttons view

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        view = PersistentButtons(cog=self)
        source_button = discord.ui.Button(
            style=discord.ButtonStyle.link, label="Source code", url=global_utils.source_code, row=1)
        view.add_item(source_button)
        await interaction.response.send_message("Help:", view=view)


class SelectMenu(discord.ui.Select):
    def __init__(self, buttons_view):
        options = [discord.SelectOption(label="Minimum commands", value="basic"),
                   discord.SelectOption(
                       label="User commands", value="user"),
                   discord.SelectOption(label="Admin commands", value="admin"),
                   discord.SelectOption(
                       label="Minimum + Admin", value="basic_admin"),
                   discord.SelectOption(
                       label="User + Admin", value="user_admin"),
                   discord.SelectOption(label="All commands", value="all"),]
        placeholder = "Commands"
        custom_id = "commands_list_type"
        self.buttons_view = buttons_view
        super().__init__(options=options, placeholder=placeholder, custom_id=custom_id, )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0] if self.values else "user"
        await self.buttons_view.cog.commands(interaction, list_type=selected)
        return


# this will get merged with bot_cog.py eventually to avoid all of this redundancy
class PersistentButtons(discord.ui.View):
    def __init__(self, *, timeout: float | None = None, cog: PersistCommands) -> None:
        """Initializes the PersistentButton class

        Parameters
        ----------
        timeout : float | None, optional
            The number of seconds to listen for an interaction before timing out, by default None (no timeout)
        cog : BotCog
            The BotCog instance that is using the buttons
        """
        super().__init__(timeout=timeout)
        self.cog = cog
        self.menu = SelectMenu(self)
        self.menu.row = 0
        self.add_item(self.menu)
        self.list_type = "user"

    # @discord.ui.button(label="Commands", style=discord.ButtonStyle.primary, custom_id="commands_button", emoji="❔")
    # async def commands_button(self, interaction: discord.Object, button: discord.ui.Button) -> None:
    #     """[button] Sends a list of all bot commands (that a general user can use)

    #     Parameters
    #     ----------
    #     button : discord.ui.Button
    #         The button object that was clicked
    #     interaction : discord.Interaction
    #         The interaction object from the button click
    #     """
    #     await self.cog.commands(interaction, list_type=self.list_type)

    @discord.ui.button(label="Schedule", style=discord.ButtonStyle.primary, custom_id="schedule_button", emoji="📅", row=1)
    async def schedule_button(self, interaction: discord.Object, button: discord.ui.Button) -> None:
        """[button] Sends the schedule for the val server

        Parameters
        ----------
        interaction : discord.Object
            The interaction object from the button click
        button : discord.ui.Button
            The button object that was clicked
        """
        await self.cog.schedule(interaction)


async def setup(bot: commands.bot) -> None:
    """Adds the BotCog cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(PersistCommands(bot), guilds=[discord.Object(global_utils.val_server_id), discord.Object(global_utils.debug_server_id)])
