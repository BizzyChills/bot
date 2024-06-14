import discord
from discord import app_commands
from discord.ext import commands

from global_utils import global_utils
from .voting_buttons import VotingButtons

class VotingCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the VotingCommands cog

        Parameters
        ----------
        bot : discord.ext.commands.Bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot

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
        view = VotingButtons(timeout=None, interaction=interaction)
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
                    
                    like = global_utils.positive_preference
                    neutral = global_utils.neutral_preference
                    dislike = global_utils.negative_preference

                    weight = {like: "Like", neutral: "Neutral", dislike: "Dislike"}[encoded_weight]

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
