import discord
from discord import app_commands
from discord.ext import commands

from global_utils import global_utils


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
    @app_commands.choices(
        map_name=[
            discord.app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_preferences.keys()
        ],

        preference=[
            discord.app_commands.Choice(name="Like/Will Play", value=global_utils.positive_preference),
            discord.app_commands.Choice(name="Neutral/Don't Care", value=global_utils.neutral_preference),
            discord.app_commands.Choice(name="Dislike/Won't Play", value=global_utils.negative_preference),
        ]

    )
    @discord.app_commands.describe(
        map_name="The map to vote for",
        preference="Your preference for the map"
    )
    async def prefermap(self, interaction: discord.Interaction, map_name: str, preference: str) -> None:
        """[command] Declares a preference for a map to play in premier playoffs

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        map_name : str
            The map to mark with a preference
        preference : str
            The preference value for the map
        """
        output = ""
        like = global_utils.positive_preference
        neutral = global_utils.neutral_preference
        dislike = global_utils.negative_preference
        preference_decoder = {like: "Like", neutral: "Neutral", dislike: "Dislike"}

        old_preference = ""
        uuid = str(interaction.user.id)

        map_display = global_utils.style_text(map_name.title(), 'i')
        preference_display = global_utils.style_text(
            preference_decoder[preference], 'c')

        # if you've voted for this map before, need to remove the old weight
        if uuid in global_utils.map_preferences[map_name]:
            old_preference = global_utils.map_preferences[map_name][uuid]

            # no change in preference, return
            if old_preference == preference:
                mention = interaction.user.mention
                message = f"{mention} you have already marked {map_display} with a preference of {preference_display}"
                await interaction.response.send_message(message, ephemeral=True)
                return

            old_preference_display = global_utils.style_text(
                preference_decoder[old_preference], 'c')

            output = f"Your preference for {map_display} has been changed from {old_preference_display} to {preference_display}"

        else:
            output = f"You marked {map_display} with a preference of {preference_display}"

        global_utils.map_preferences[map_name][uuid] = preference


        global_utils.save_preferences()

        await interaction.response.send_message(output, ephemeral=True)

        global_utils.log(
            f'{interaction.user.name} marked {map_name.title()} with a preference of "{preference_decoder[preference]}"')

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
