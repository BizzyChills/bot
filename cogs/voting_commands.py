import discord
from discord import app_commands
from discord.ext import commands
from my_utils import *


class VotingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # print("Voting cog loaded")
        pass

    @app_commands.command(name="prefermap", description=command_descriptions["prefermap"])
    @app_commands.choices(
        _map=[
            discord.app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
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

        global map_preferences
        global map_weights
        if interaction.channel.id not in [bot_channel, debug_channel]:
            await interaction.response.send_message(f'You cannot vote in this channel', ephemeral=True)
            return

        output = ""
        preferences = {"+": "like", "~": "neutral", "-": "dislike"}

        _map = _map.lower()

        old_preferences = ""
        # if you've voted for this map before
        if str(interaction.user.id) in map_preferences[_map]:
            old_preferences = map_preferences[_map][str(interaction.user.id)]
            if old_preferences == preference:
                await interaction.response.send_message(f'{interaction.user.mention} you have already marked {_map.title()} with a weight of {preferences[preference]}', ephemeral=True)
                return

            output = f'{interaction.user.mention}\'s vote for {_map.title()} has been changed from {preferences[old_preferences]} to {preferences[preference]}'
            old_preferences = 1 if old_preferences == "+" else 0 if old_preferences == "~" else -1
            map_weights[_map] -= old_preferences

        map_preferences[_map][str(interaction.user.id)] = preference
        if old_preferences == "":
            output = f'{interaction.user.mention} voted for {_map.title()} with a weight of {preference}'
        preference = 1 if preference == "+" else 0 if preference == "~" else -1
        map_weights[_map] += preference

        await interaction.response.send_message(output, ephemeral=True)

        log(output)

        save_prefrences(map_preferences)
        save_weights(map_weights)

    @app_commands.command(name="mapvotes", description=command_descriptions["mapvotes"])
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
        
        global map_preferences
        if interaction.channel.id not in all_channels:
            await wrong_channel(interaction)
            return

        role = prem_role if interaction.guild.id == val_server else debug_role
        all_users = discord.utils.get(interaction.guild.roles, name=role).members

        output = ""

        for _map in map_pool:
            header = f'- {_map.title()} ({map_weights[_map]}):\n'
            body = ""
            for user in all_users:
                if str(user.id) in map_preferences[_map]:
                    encoded_weight = map_preferences[_map][str(user.id)]
                    weight = {"+": "like", "~": "neutral", "-": "dislike"}[encoded_weight]

                    body += f' - {user.mention}: {weight}\n'

            if body == "":
                body = "No votes for this map."


            output += header + body

        if output == "":
            output = "No votes for any maps in the map pool."

        ephem = False if announce and interaction.channel.id == prem_channel else True

        await interaction.response.send_message(output, ephemeral=ephem, silent=True)

    @app_commands.command(name="mapweights", description=command_descriptions["mapweights"])
    @app_commands.choices(
        announce=[
            discord.app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        announce="Show the output of the command to everyone when used in the premier channel"
    )
    async def mapweights(self, interaction: discord.Interaction, announce: int = 0):
        """Display the sorted map weights"""

        global map_weights
        if interaction.channel.id not in all_channels:
            await wrong_channel(interaction)
            return

        output = ""

        map_weights = dict(sorted(map_weights.items(
        ), key=lambda item: item[1], reverse=True))  # sort the weights in descending order

        for _map in map_weights.keys():
            if _map not in map_pool:
                continue

            output += f'{_map.title()}: {map_weights[_map]}\n'

        if output == "":
            output = "No weights to show for maps in the map pool."

        ephem = False if announce and interaction.channel.id == prem_channel else True

        await interaction.response.send_message(output, ephemeral=ephem)

async def setup(bot):
    await bot.add_cog(VotingCommands(bot), guilds=[discord.Object(val_server), discord.Object(debug_server)])
