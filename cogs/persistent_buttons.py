from typing import Any, Coroutine
import discord
from discord import app_commands
from discord.ext import commands

from datetime import datetime

from global_utils import global_utils

class SelectMenu(discord.ui.Select):
    def __init__(self, buttons_view):
        options = [discord.SelectOption(label="The basic commands", value="basic"),
                   discord.SelectOption(label="All user commands", value="user"),
                   discord.SelectOption(label="Admin commands", value="admin"),
                   discord.SelectOption(label="Basic + Admin", value="basic_admin"),
                   discord.SelectOption(label="User + Admin", value="user_admin"),
                   discord.SelectOption(label="All commands", value="all"),]
        placeholder = "Command list to display (default: user commands)"
        custom_id = "commands_list_type"
        self.buttons_view = buttons_view
        super().__init__(options=options, placeholder=placeholder, custom_id=custom_id)
    
    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0] if self.values else "user"
        self.buttons_view.list_type = selected
        await interaction.response.edit_message(view=self.view)


class PersistentButtons(discord.ui.View):
    def __init__(self, *, timeout: float | None = None) -> None:
        """Initializes the PersistentButton class

        Parameters
        ----------
        timeout : float | None, optional
            The number of seconds to listen for an interaction before timing out, by default None (no timeout)
        """
        super().__init__(timeout=timeout)
        self.menu = SelectMenu(self)
        self.add_item(self.menu)
        self.list_type = "user"

    @discord.ui.button(label="Commands", style=discord.ButtonStyle.primary, custom_id="commands_button", emoji="❔")
    async def commands_button(self, interaction: discord.Object, button: discord.ui.Button) -> None:
        """[button] Sends a list of all bot commands (that a general user can use)

        Parameters
        ----------
        button : discord.ui.Button
            The button object that was clicked
        interaction : discord.Interaction
            The interaction object from the button click
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
                          f" - {global_utils.style_text('/music (WIP)', 'c')}",
                        #   f" - {global_utils.style_text('/playlist', 'c')}",
                        #   f" - {global_utils.style_text('/play-song', 'c')}",
                        #   f" - {global_utils.style_text('/pause-song', 'c')}",
                        #   #   f" - {global_utils.style_text('/resume-song', 'c')}", # deprecated. just use /play-song
                        #   f" - {global_utils.style_text('/stop-song', 'c')}",
                        #   f" - {global_utils.style_text('/skip-song', 'c')}",
                        #   f" - {global_utils.style_text('/loop-song', 'c')}",
                          ]

        user_commands = basic_commands + music_commands + misc_commands
        basic_admin_commands = basic_commands + admin_commands
        user_admin_commands = user_commands + admin_commands
        all_commands = user_admin_commands + my_commands

        match self.list_type:
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
            case _:
                output = all_commands

        await interaction.followup.send('\n'.join(output), ephemeral=ephem, silent=True)

    @discord.ui.button(label="Schedule", style=discord.ButtonStyle.primary, custom_id="schedule_button", emoji="📅")
    async def schedule_button(self, interaction: discord.Object, button: discord.ui.Button) -> None:
        """[button] Sends the schedule for the val server

        Parameters
        ----------
        interaction : discord.Object
            The interaction object from the button click
        button : discord.ui.Button
            The button object that was clicked
        """
        # ephem = interaction.channel.id != global_utils.prem_channel_id or not announce
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

    def format_schedule(self, schedule: list[tuple[str, datetime, str]], header: str = None) -> str:
        """Formats the schedule for display in Discord

        Parameters
        ----------
        schedule : list[tuple[str, datetime, str]]
            The schedule to format. This should be a list of tuples with the following structure: [(event_display_string, event_datetime, event_map), ...]
        header : str, optional
            The header to display at the top of the schedule, by default None

        Returns
        -------
        str
            The formatted schedule as a string to display in Discord
        """
        schedule = sorted(schedule, key=lambda x: x[1])

        subsections = {entry[2]: [] for entry in schedule}

        for m in schedule:
            map_name = m[2]
            event_display = m[0]  # just use variables for readability

            subsections[map_name].append(event_display)

        output = ""
        for map_name, event_displays in subsections.items():
            subheader = f"- {global_utils.style_text(map_name, 'iu')}:"
            event_displays = " - " + '\n - '.join(event_displays)

            output += f"{subheader}\n{event_displays}\n"

        return f"{header}\n{output}" if header else output


class PersistentCommands(commands.Cog):
    def __init__(self) -> None:
        """Initializes the PersistentCommands class"""
        pass

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[listener] Executes when the PersistentCommands cog is ready
        """
        # global_utils.log("PersistentCommands cog loaded")
        pass

    @app_commands.command(name="persist", description=global_utils.command_descriptions["persist"])
    async def persist(self, interaction: discord.Interaction) -> None:
        """[command] Adds the persistent buttons to the bot

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        view = PersistentButtons()
        source_code_button = discord.ui.Button(label="Source Code", style=discord.ButtonStyle.link, url=global_utils.source_code)
        view.add_item(source_code_button)
        await interaction.response.send_message("Help:", view=view)



async def setup(bot: commands.Bot) -> None:
    """Adds the PersistentCommands cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.Bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(PersistentCommands(), guilds=[discord.Object(global_utils.val_server_id), discord.Object(global_utils.debug_server_id)])
