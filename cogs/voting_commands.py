import discord
from discord import app_commands
from discord.ext import commands

from global_utils import global_utils


class VotingButtons(discord.ui.View):
    def __init__(self, *, timeout: float | None = None, interaction: discord.Interaction, preferences: dict) -> None:
        """Initializes the VotingView class

        Parameters
        ----------
        timeout : float | None, optional
            The number of seconds to listen for an interaction before timing out, by default None (no timeout)
        interaction : discord.Interaction
            The interaction object from the command generating this view
        preferences : dict
            A dictionary containing the backend symbols for each preference type (like, neutral, dislike)
        """
        super().__init__(timeout=timeout)

        self.question_interaction = interaction
        self.map_display_names = None
        self.map_names = None
        self.emojis = {"like": "👍", "neutral": "✊", "dislike": "👎"}
        self.preferences = preferences

    async def start(self) -> None:
        """Starts the voting process by getting the list of maps and asking the first question
        """
        maps = [global_utils.style_text(map_name.title(), 'i')
                for map_name in global_utils.map_preferences.keys()]
        map_name = maps[0]
        await self.question_interaction.followup.send(content=f"What do you think of {map_name}?", view=self, ephemeral=True)
        self.map_display_names = maps
        self.map_names = list(global_utils.map_preferences.keys())

    @discord.ui.button(label="Like", style=discord.ButtonStyle.success, emoji="👍")
    async def like(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """[button] Saves the user's preference for the current map as a like

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object from the button click
        button : discord.ui.Button
            The button object that was clicked
        """
        await self.save_preference(self.preferences["like"])

        reaction_message = f"{self.emojis['like']}"
        await self.respond(interaction, reaction_message)

    @discord.ui.button(label="Neutral", style=discord.ButtonStyle.secondary, emoji="✊")
    async def neutral(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """[button] Saves the user's preference for the current map as neutral

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object from the button click
        button : discord.ui.Button
            The button object that was clicked
        """
        await self.save_preference(self.preferences["neutral"])

        reaction_message = f"{self.emojis['neutral']}"
        await self.respond(interaction, reaction_message)

    @discord.ui.button(label="Dislike", style=discord.ButtonStyle.danger, emoji="👎")
    async def dislike(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """[button] Saves the user's preference for the current map as a dislike

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object from the button click
        button : discord.ui.Button
            The button object that was clicked
        """
        await self.save_preference(self.preferences["dislike"])

        reaction_message = f"{self.emojis['dislike']}"
        await self.respond(interaction, reaction_message)

    async def save_preference(self, preference: str) -> None:
        """Saves the user's preference for the current map from self.map_names

        Parameters
        ----------
        preference : str
            The preference value to save (either "+", "~", or "-")
        """
        map_name = self.map_names.pop(0)
        user_id = self.question_interaction.user.id
        global_utils.map_preferences[map_name][str(user_id)] = preference
        global_utils.save_preferences()

    async def respond(self, button_interaction: discord.Interaction, message: str) -> None:
        """Responds to the user after they click a button by either asking the next question or disabling the buttons

        Parameters
        ----------
        button_interaction : discord.Interaction
            The interaction object from the button click
        message : str
            The message to send to the user
        """
        await button_interaction.response.send_message(message, ephemeral=True, delete_after=1)

        if len(self.map_display_names) > 1:
            self.map_display_names.pop(0)
            map_name = self.map_display_names[0]
            await self.question_interaction.edit_original_response(content=f"What do you think of {map_name}?")
        else:
            await self.disable_buttons()
            await self.question_interaction.edit_original_response(content=f"Preferences saved. Thank you!", view=self)

    async def disable_buttons(self) -> None:
        """Disables all buttons in the view
        """
        for button in self.children:
            button.disabled = True


class VotingCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the VotingCommands cog

        Parameters
        ----------
        bot : discord.ext.commands.Bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot
        self.preferences = {"like": '+', "neutral": '~', "dislike": '-'}

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the VotingCommands cog is ready
        """
        # global_utils.log("Voting cog loaded")
        pass

    @app_commands.command(name="prefer-map", description=global_utils.command_descriptions["prefer-map"])
    async def start_voting(self, interaction: discord.Interaction) -> None:
        """[command] Declares a preference for a map to play in premier playoffs

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        view = VotingButtons(
            timeout=None, interaction=interaction, preferences=self.preferences)
        await view.start()

    @app_commands.command(name="map-votes", description=global_utils.command_descriptions["map-votes"])
    @app_commands.choices(
        announce=[
            discord.app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        announce="Show the output of the command to everyone when used in the premier channel"
    )
    async def mapvotes(self, interaction: discord.Interaction, announce: int = 0) -> None:
        """[command] Displays each user's preferences for each map in the map pool

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        announce : int, optional
            Treated as a boolean. Announce the output when used in the premier channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.prem_channel_id or not announce

        role_name = global_utils.prem_role_name if interaction.guild.id == global_utils.val_server_id else global_utils.debug_role_name
        premier_team = discord.utils.get(
            interaction.guild.roles, name=role_name).members

        output = ""

        for map_name in global_utils.map_pool:
            header = f"- {global_utils.style_text(map_name.title(), 'i')} ({global_utils.style_text(global_utils.map_weights[map_name], 'b')}):\n"
            body = ""
            for user in premier_team:
                if str(user.id) in global_utils.map_preferences[map_name]:
                    encoded_weight = global_utils.map_preferences[map_name][str(
                        user.id)]

                    like = self.preferences["like"]
                    neutral = self.preferences["neutral"]
                    dislike = self.preferences["dislike"]

                    weight = "Like" if encoded_weight == like else "Neutral" if encoded_weight == neutral else "Dislike" if encoded_weight == dislike else "Error"

                    body += f" - {user.mention}: {global_utils.style_text(weight, 'c')}\n"

            if body == "":
                body = " - No votes for this map.\n"

            output += header + body

        if output == "":
            output = "No votes for any maps in the map pool."

        await interaction.response.send_message(output, ephemeral=ephem, silent=True)

    @app_commands.command(name="map-weights", description=global_utils.command_descriptions["map-weights"])
    @app_commands.choices(
        announce=[
            discord.app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        announce="Show the output of the command to everyone (only in the premier channel)"
    )
    async def mapweights(self, interaction: discord.Interaction, announce: int = 0) -> None:
        """[command] Displays the weights of each map in the map pool based on user preferences

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        announce : int, optional
            Treated as a boolean. Announce the output when used in the premier channel, by default 0
        """
        ephem = interaction.channel.id != global_utils.prem_channel_id or not announce

        output = ""

        global_utils.map_weights = dict(sorted(global_utils.map_weights.items(
        ), key=lambda item: item[1], reverse=True))  # sort the weights in descending order

        for map_name in global_utils.map_weights.keys():
            if map_name not in global_utils.map_pool:
                continue

            output += f'{map_name.title()}: {global_utils.map_weights[map_name]}\n'

        if output == "":
            output = "No weights to show for maps in the map pool."

        await interaction.response.send_message(output, ephemeral=ephem)


async def setup(bot: commands.bot) -> None:
    """Adds the VotingCommands cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(VotingCommands(bot), guilds=[discord.Object(global_utils.val_server_id), discord.Object(global_utils.debug_server_id)])
