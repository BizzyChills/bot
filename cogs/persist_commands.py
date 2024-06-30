import discord
from discord import app_commands
from discord.ext import commands

from datetime import datetime

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

        self.basic_commands = [f"{global_utils.style_text('Commands', 'b')} (start typing the command to see its description):",

                               f"- {global_utils.style_text('INFO', 'b')}:",
                               f" - {global_utils.style_text('/notes', 'c')}",

                               f"- {global_utils.style_text('VOTING', 'b')}:",
                               f" - {global_utils.style_text('/prefer-maps', 'c')}",
                               f" - {global_utils.style_text('/map-votes', 'c')}",
                               f" - {global_utils.style_text('/map-weights', 'c')}",]

        self.admin_commands = [f"- {global_utils.style_text('ADMIN ONLY', 'b')}:",
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

        self.bizzy_commands = [f"- {global_utils.style_text('BIZZY ONLY', 'b')}:",
                               f" - {global_utils.style_text('(! | /)reload', 'c')}",
                               f" - {global_utils.style_text('/clear', 'c')}",
                               f" - {global_utils.style_text('/feature', 'c')}",]

        self.misc_commands = [f"- {global_utils.style_text('MISC', 'b')}:",
                              f" - {global_utils.style_text('/hello', 'c')}",
                              f" - {global_utils.style_text('/trivia', 'c')}",
                              f" - {global_utils.style_text('/feed', 'c')}",
                              f" - {global_utils.style_text('/unfeed', 'c')}",]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the BotCog cog is ready
        """
        # global_utils.log("Bot cog loaded")
        pass

    async def commands(self, interaction: discord.Interaction, list_type: str = "all") -> discord.WebhookMessage:
        """Displays all bot commands

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        list_type : str, optional
            The type of command list to display, by default "user"

        Returns
        -------
        discord.WebhookMessage
            The message object that was sent
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        user_commands = self.basic_commands + self.misc_commands
        basic_admin_commands = self.basic_commands + self.admin_commands
        user_admin_commands = user_commands + self.admin_commands
        all_commands = user_admin_commands + self.bizzy_commands

        match list_type:
            case "basic":
                output = self.basic_commands
            case "user":
                output = user_commands
            case "basic_admin":
                output = basic_admin_commands
            case "admin":
                output = self.admin_commands
                if interaction.user.id == global_utils.my_id:
                    output += self.bizzy_commands
            case "user_admin":
                output = user_admin_commands
            case "all":
                output = all_commands
            case _:
                output = all_commands

        return await interaction.followup.send('\n'.join(output), ephemeral=True, silent=True)

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

    async def schedule(self, interaction: discord.Interaction) -> discord.WebhookMessage:
        """[command] Displays the premier schedule from server events

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild
        events = guild.scheduled_events

        event_header = f"{global_utils.style_text('Upcoming Premier Events:', 'b')}"
        practice_header = f"\n\n{global_utils.style_text('Upcoming Premier Practices:', 'b')}"
        event_message = []
        practice_message = []

        for event in events:
            map_name = event.description if "playoffs" not in event.name.lower(
            ) else "Playoffs"

            if "premier practice" in event.name.lower():
                practice_message.append(
                    (f"{global_utils.discord_local_time(event.start_time, with_date=True)}", event.start_time, map_name))
            elif "premier" in event.name.lower():
                event_message.append(
                    (f"{global_utils.discord_local_time(event.start_time, with_date=True)}", event.start_time, map_name))

        if event_message == []:
            event_message = f"{global_utils.style_text('No premier events scheduled', 'b')}"
        else:
            event_message = self.format_schedule(event_message, event_header)

        if practice_message == []:
            practice_message = f"\n\n{global_utils.style_text('No premier practices scheduled', 'b')}"
        else:
            practice_message = self.format_schedule(
                practice_message, practice_header)

        message = event_message + practice_message

        return await interaction.followup.send(message, ephemeral=True)

    async def map_pool(self, interaction: discord.Interaction) -> discord.WebhookMessage:
        """[command] Displays the current map pool for the server

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        map_list = ', '.join([global_utils.style_text(
            m.title(), 'i') for m in global_utils.map_pool])
        embed = discord.Embed(
            title="Map Pool", description=f"{map_list}", color=discord.Color.blurple())
        return await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="persist", description=global_utils.command_descriptions["persist"])
    async def persist(self, interaction: discord.Interaction) -> None:
        """[command] Sends the persistent buttons view

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        view = PersistentView(cog=self)
        await interaction.response.send_message(global_utils.style_text("HELP:", 'b'), view=view)


class PersistentView(discord.ui.View):
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
        source_button = discord.ui.Button(
            style=discord.ButtonStyle.link, label="Source code", url=global_utils.source_code, row=1)
        self.add_item(source_button)
        self.callbacks = {"commands": cog.commands,
                          "schedule": cog.schedule,
                          "map_pool": cog.map_pool}
        self.output_message = None

    async def remove_old(self) -> None:
        """Removes the old output message
        """
        if self.output_message is not None:
            try:
                await self.output_message.delete()
            except discord.NotFound:
                pass

    @discord.ui.select(placeholder="Commands List", min_values=0, custom_id="commands_list_type",
                       options=[discord.SelectOption(label="Minimum commands", value="basic"),
                                discord.SelectOption(
                                    label="User commands", value="user"),
                                discord.SelectOption(
                                    label="Admin commands", value="admin"),
                                discord.SelectOption(
                                    label="Minimum + Admin", value="basic_admin"),
                                discord.SelectOption(
                                    label="User + Admin", value="user_admin"),
                                discord.SelectOption(label="All commands", value="all")])
    async def commands_list_button(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        """[select menu] Sends the selected list of commands

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object from the select menu
        select : discord.ui.Select
            The select menu object that was used
        """
        await self.remove_old()

        if len(select.values) == 0:
            await interaction.response.defer()
            return

        selected = select.values[0]
        self.output_message = await self.callbacks["commands"](interaction, list_type=selected)

    @discord.ui.button(label="Schedule", style=discord.ButtonStyle.primary, custom_id="schedule_button", emoji="📅", row=1)
    async def schedule_button(self, interaction: discord.Object, button: discord.ui.Button) -> None:
        """[button] Sends the premier schedule for the current server

        Parameters
        ----------
        interaction : discord.Object
            The interaction object from the button click
        button : discord.ui.Button
            The button object that was clicked
        """
        await self.remove_old()

        self.output_message = await self.callbacks["schedule"](interaction)

    @discord.ui.button(label="Map Pool", style=discord.ButtonStyle.primary, custom_id="map_pool_button", emoji="🗺️", row=1)
    async def map_pool_button(self, interaction: discord.Object, button: discord.ui.Button) -> None:
        """[button] Sends the current map pool for the server

        Parameters
        ----------
        interaction : discord.Object
            The interaction object from the button click
        button : discord.ui.Button
            The button object that was clicked
        """
        await self.remove_old()

        self.output_message = await self.callbacks["map_pool"](interaction)


async def setup(bot: commands.bot) -> None:
    """Adds the BotCog cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(PersistCommands(bot), guilds=[discord.Object(global_utils.val_server_id), discord.Object(global_utils.debug_server_id)])
