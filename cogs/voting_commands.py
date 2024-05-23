import discord
from discord import app_commands
from discord.ext import commands

from global_utils import global_utils


class VotingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # print("Voting cog loaded")
        pass

    @app_commands.command(name="prefermap", description=global_utils.command_descriptions["prefermap"])
    @app_commands.choices(
        _map=[
            discord.app_commands.Choice(name=s.title(), value=s) for s in global_utils.map_preferences.keys()
        ],

        preference=[
            discord.app_commands.Choice(name="Like/Will Play", value="+"),
            discord.app_commands.Choice(name="Neutral/Don't Care", value="~"),
            discord.app_commands.Choice(name="Dislike/Won't Play", value="-"),
        ]

    )
    @discord.app_commands.describe(
        _map="The map to vote for",
        preference="Your preference for the map"
    )
    async def prefermap(self, interaction: discord.Interaction, _map: str, preference: str):
        """Declare a preference for a map to play for premier playoffs"""

        output = ""
        preference_decoder = {"+": "Like", "~": "Neutral", "-": "Dislike"}
        preference_weights = {"+": 1, "~": 0, "-": -1}

        old_preference = ""
        uuid = str(interaction.user.id)

        # if you've voted for this map before, need to remove the old weight
        if uuid in global_utils.map_preferences[_map]:
            old_preference = global_utils.map_preferences[_map][uuid]

            # no change in preference, return
            if old_preference == preference:
                await interaction.response.send_message(f"{interaction.user.mention} you have already marked {global_utils.italics(_map.title())} with a preference of {global_utils.inline_code(preference_decoder[preference])}", ephemeral=True)
                return

            output = f"Your preference for {global_utils.italics(_map.title())} has been changed from {global_utils.inline_code(preference_decoder[old_preference])} to {global_utils.inline_code(preference_decoder[preference])}"

            global_utils.map_weights[_map] -= preference_weights[old_preference]
        else:
            output = f"You marked {global_utils.italics(_map.title())} with a preference of {global_utils.inline_code(preference_decoder[preference])}"

        global_utils.map_preferences[_map][uuid] = preference

        global_utils.map_weights[_map] += preference_weights[preference]

        await interaction.response.send_message(output, ephemeral=True)

        global_utils.log(f'{interaction.user.name} marked {_map.title()} with a preference of "{preference_decoder[preference]}"')

        global_utils.save_preferences()
        global_utils.save_weights()

    @app_commands.command(name="mapvotes", description=global_utils.command_descriptions["mapvotes"])
    @app_commands.choices(
        announce=[
            discord.app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        announce="Show the output of the command to everyone when used in the premier channel"
    )
    async def mapvotes(self, interaction: discord.Interaction, announce: int = 0):
        """Display the map votes for each user"""
        ephem = interaction.channel.id != global_utils.prem_channel or not announce

        role = global_utils.prem_role if interaction.guild.id == global_utils.val_server else global_utils.debug_role
        all_users = discord.utils.get(
            interaction.guild.roles, name=role).members

        output = ""

        for _map in global_utils.map_pool:
            header = f'- {global_utils.italics(_map.title())} ({global_utils.bold(global_utils.map_weights[_map])}):\n'
            body = ""
            for user in all_users:
                if str(user.id) in global_utils.map_preferences[_map]:
                    encoded_weight = global_utils.map_preferences[_map][str(user.id)]
                    weight = {"+": "Like", "~": "Neutral",
                              "-": "Dislike"}[encoded_weight]

                    body += f' - {user.mention}: {global_utils.inline_code(weight)}\n'

            if body == "":
                body = "No votes for this map."

            output += header + body

        if output == "":
            output = "No votes for any maps in the map pool."

        await interaction.response.send_message(output, ephemeral=ephem, silent=True)

    @app_commands.command(name="mapweights", description=global_utils.command_descriptions["mapweights"])
    @app_commands.choices(
        announce=[
            discord.app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        announce="Show the output of the command to everyone (only in the premier channel)"
    )
    async def mapweights(self, interaction: discord.Interaction, announce: int = 0):
        """Display the sorted map weights"""
        ephem = interaction.channel.id != global_utils.prem_channel or not announce

        output = ""

        global_utils.map_weights = dict(sorted(global_utils.map_weights.items(
        ), key=lambda item: item[1], reverse=True))  # sort the weights in descending order

        for _map in global_utils.map_weights.keys():
            if _map not in global_utils.map_pool:
                continue

            output += f'{_map.title()}: {global_utils.map_weights[_map]}\n'

        if output == "":
            output = "No weights to show for maps in the map pool."

        await interaction.response.send_message(output, ephemeral=ephem)


async def setup(bot):
    await bot.add_cog(VotingCommands(bot), guilds=[discord.Object(global_utils.val_server), discord.Object(global_utils.debug_server)])
