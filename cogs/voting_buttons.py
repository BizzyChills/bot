import discord
from discord.ext import commands

from global_utils import global_utils

class VotingButtons(discord.ui.View):
    def __init__(self, *, timeout: float | None = None, interaction: discord.Interaction) -> None:
        """Initializes the VotingView class

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object from the command generating this view
        timeout : float | None, optional
            The number of seconds to listen for an interaction before timing out, by default None (no timeout)
        """
        super().__init__(timeout=timeout)

        self.question_interaction = interaction
        self.map_display_names = None
        self.map_names = None
        self.emojis = {"like": "👍", "neutral": "✊", "dislike": "👎"}

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
        await self.save_preference(global_utils.positive_preference)

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
        await self.save_preference(global_utils.neutral_preference)

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
        await self.save_preference(global_utils.negative_preference)

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

async def setup(bot: commands.Bot) -> None:
    """dummy function to satisfy the bot.load_extension() call in bot.py"""
    pass
