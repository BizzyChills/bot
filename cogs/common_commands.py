import discord
from discord import app_commands
from discord.ext import commands
from my_utils import *
import random

class CommonCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Common cog loaded")

    @app_commands.command(name="hello", description=command_descriptions["hello"])
    async def hello(self, interaction: discord.Interaction):
        """Says hello"""

        await interaction.response.send_message(f'Hello {interaction.user.mention}!', ephemeral=True)

    @app_commands.command(name="feed", description=command_descriptions["feed"])
    async def feed(self, interaction: discord.Interaction):
        """Feed the bot"""

        await interaction.response.send_message("Yum yum! Thanks for the food!", ephemeral=True)
    
    @app_commands.command(name="unfeed", description=command_descriptions["unfeed"])
    async def unfeed(self, interaction: discord.Interaction):
        """Unfeed the bot"""

        options = ["pukes", "poops", "performs own liposuction"]

        option = options[random.randint(0, len(options) - 1)]

        await interaction.response.send_message(f'\*looks at you with a deadpan expression\* ... \*{option}\*', ephemeral=True)

    @app_commands.command(name="schedule", description=command_descriptions["schedule"])
    async def schedule(self, interaction: discord.Interaction):
        """Display the premier schedule"""
        if interaction.channel.id not in all_channels:
            await wrong_channel(interaction)
            return

        guild = self.bot.get_guild(
            val_server) if interaction.guild.id == val_server else self.bot.get_guild(debug_server)
        events = guild.scheduled_events

        event_header = "**Upcoming Premier Events:**"
        practice_header = "\n\n**Upcoming Premier Practices:**"
        message = []
        practice_message = []

        await interaction.response.defer(ephemeral=True, thinking=True)

        for event in events:
            if "premier practice" in event.name.lower():
                practice_message.append(
                    (f" - {discord_local_time(event.start_time, _datetime=True)}", event.start_time, event.description))
            elif "premier" in event.name.lower():
                desc = "Playoffs" if "playoffs" in event.name.lower() else event.description
                message.append(
                    (f" - {discord_local_time(event.start_time, _datetime=True)}", event.start_time, desc))

        ephem = True if interaction.channel.id == bot_channel else False

        if message == []:
            message = "**No premier events scheduled**"
        else:
            message = format_schedule(message, event_header)

        if practice_message == []:
            practice_message = "\n\n**No premier practices scheduled**"
        else:
            practice_message = format_schedule(practice_message, practice_header)

        message += practice_message

        await interaction.followup.send(message, ephemeral=ephem)

    @app_commands.command(name="mappool", description=command_descriptions["mappool_common"])
    @app_commands.choices(
        action=[
            discord.app_commands.Choice(name="Add", value="add"),
            discord.app_commands.Choice(name="Remove", value="remove"),
            discord.app_commands.Choice(name="Clear all maps (even if _map is set)", value="clear"),
        ],

        _map=[
            # mappool only has maps that are currently playable, need to get all maps
            discord.app_commands.Choice(name=f"{s.title()}", value=s) for s in map_preferences.keys()
        ],
        announce=[
            discord.app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        action="The action to take on the map pool (ADMIN ONLY)",
        _map="The map to add or remove (ADMIN ONLY)",
        announce="Show the output of the command to everyone when used in the premier channel"
    )
    async def mappool(self, interaction: discord.Interaction, action: str = "", _map: str = "", announce: int = 0):
        """Add or remove maps from the map pool"""
        if interaction.channel.id not in all_channels:
            await wrong_channel(interaction)
            return
        
        if interaction.channel.id != prem_channel:
            announce = 0 # don't announce in non-premier channels

        if action == "" and _map == "":
            ephem = False if announce else True

            if len(map_pool) == 0:
                output = f'The map pool is empty'
            else:
                output = f'Current map pool: {", ".join(map_pool)}'

            await interaction.response.send_message(output, ephemeral=ephem)
            return

        if not await has_permission(interaction.user.id, interaction):
            return

        if action == "" or (_map == "" and action != "clear"):  # clear doesn't need a map
            await interaction.response.send_message(f'Please provide an action and a map.', ephemeral=True)
            return

        output = ""

        if action == "clear":
            map_pool.clear()
            output = f'The map pool has been cleared'
            log_message = f'{interaction.user.display_name} has cleared the map pool'
        elif action == "add":
            if _map not in map_pool:
                map_pool.append(_map)
                output = f'{_map} has been added to the map pool'
                log_message = f'{interaction.user.display_name} has added {_map} to the map pool'
            else:
                await interaction.response.send_message(f'{_map} is already in the map pool', ephemeral=True)
                return
        elif action == "remove":
            if _map in map_pool:
                map_pool.remove(_map)
                output = f'{_map} has been removed from the map pool'
                log_message = f'{interaction.user.display_name} has removed {_map} from the map pool'
            else:
                await interaction.response.send_message(f'{_map} is not in the map pool', ephemeral=True)
                return

        ephem = False if announce else True

        await interaction.response.send_message(output, ephemeral=ephem)

        log(log_message)

        save_pool(map_pool)

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
        """Declare your preference for a map to play for premier playoffs"""

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

    @app_commands.command(name="notes", description=command_descriptions["notes"])
    @app_commands.choices(
        _map=[
            discord.app_commands.Choice(name=s.title(), value=s) for s in map_preferences.keys()
        ],
        announce=[
            discord.app_commands.Choice(name="Yes", value="yes"),
        ]
    )
    @app_commands.describe(
        _map="The map to display the note for",
        note_number="The note number to display (1-indexed). Leave empty to see options.",
        announce="Return the note so that it is visible to everyone (default is visible only to you)"
    )
    async def notes(self, interaction: discord.Interaction, _map: str, note_number: int = 0, announce: str = ""):
        """Display a practice note for a map"""
        if interaction.channel.id != notes_channel:
            await wrong_channel(interaction)
            return

        _map = _map.lower()

        if _map not in practice_notes:  # user gave a valid map, but there are no notes for it
            await interaction.response.send_message(f'There are no notes for {_map.title()}', ephemeral=True)
            return

        if note_number < 0 or note_number > len(practice_notes[_map]):
            await interaction.response.send_message(f'Invalid note number. Leave blank to see all options.', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        if note_number == 0:
            notes_list = practice_notes[_map]
            output = f'Practice notes for {_map.title()}:\n'
            for i, note_id in enumerate(notes_list.keys()):
                output += f' - Note {i+1}: {notes_list[note_id]}\n'

            await interaction.followup.send(output, ephemeral=True)
            return

        note_id = list(practice_notes[_map].keys())[note_number - 1]
        try:
            note = await interaction.channel.fetch_message(int(note_id))
        except discord.errors.NotFound:
            await interaction.followup.send(f'This note has been deleted by the author. Removing it from the notes list.', ephemeral=True)
            practice_notes[_map].pop(note_id)
            save_notes(practice_notes)
            return

        output = f'Practice note for {_map.title()} (created by {note.author.display_name}):\n\n{note.content}'

        if announce == "yes":
            await interaction.followup.send(output, ephemeral=False)
        else:
            await interaction.followup.send(output, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CommonCommands(bot), guilds=[discord.Object(val_server), discord.Object(debug_server)])
