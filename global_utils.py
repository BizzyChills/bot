import os
import sys
import json

from datetime import datetime, time, timedelta
import pytz

from discord import Interaction  # reduce bloat, only for type hints
from discord.ext import commands

class Utils:
    def __init__(self):
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        if not os.path.exists('logs'):
            os.makedirs('logs')


        self.last_log_date = datetime.now().strftime("%Y-%m-%d")
        self.last_log = f'./logs/{self.last_log_date}_stdout.log'
        sys.stdout = open(self.last_log, 'a')

        self.bot_token = "MTIxNzY0NjU0NDkxNzEwMjcwMw.GaY7e2.Z-YM3oT2Ts_zbZ8hs7N0zoEvhxqCMsSorzYzm8"

        self.debug_server = 1217649405759324232
        self.debug_role = "southern"
        self.debug_channel = 1217649405759324235
        self.debug_voice = 1217649405759324236

        self.val_server = 1100632842528096330
        self.prem_role = "The Valorats"
        self.bot_channel = 1218420817394925668
        self.prem_channel = 1193661647752003614
        self.notes_channel = 1237971459461218376
        self.voice_channel = 1100632843174031476
        # no voice channel, these are the general channels the bot will be in. use specific channel checks for other uses
        self.all_channels = [self.debug_channel, self.bot_channel, self.prem_channel]

        self.my_id = 461265370813038633
        self.sam_id = 180107711806046208
        self.admin_ids = [self.my_id, self.sam_id]

        self.tz = pytz.timezone("US/Eastern")

        right_now = (datetime.now().replace(microsecond=0) + timedelta(seconds=5)).time()
        self.premier_reminder_times = [  # add 2 seconds to each time to ensure time_remaining logic works
            right_now,  # debug,
            time(hour=19, second=2),  # 3 hours before for thur and sun
            time(hour=20, second=2),  # 3 hours before for sat

            time(hour=21, second=2),  # 1 hour before for thur and sun
            # 10 minutes before for thur and sun
            time(hour=21, minute=50, second=2),
            # right on time for thur and sun AND 1 hour before for sat
            time(hour=22, second=2),
            time(hour=22, minute=50, second=2),  # 10 minutes before for sat

            time(hour=23, second=2)  # right on time for sat
        ]

        self.premier_reminder_times = [self.est_to_utc(t) for t in self.premier_reminder_times]

        self.premier_reminder_classes = ["start", "prestart", "hour", "day"]

        self.map_pool = self.get_pool()
        self.map_preferences = self.get_preferences()
        self.map_weights = self.get_weights()
        self.reminders = self.get_reminders()
        self.practice_notes = self.get_notes()

        self.command_descriptions = {
            "commands": "Display this message",
            "schedule": "Display the premier event and practice schedules",
            "mappool_common": "Display the current competitive map pool",
            "mappool_admin": "Modify the map pool",
            "notes": "Display a practice note from the notes channel. Leave note_id blank to display all options",
            "prefermap": "Declare your preference for a map to play for premier playoffs",
            "mapvotes": "Display each member's map preferences",
            "mapweights": "Display the total weights for each map in the map pool",
            "hello": "Say hello",
            "feed": "Feed the bot",
            "unfeed": "Unfeed the bot",
            "trivia": "Play a game of trivia with the bot to earn a prize!",
            "remind": "Set a reminder for the premier role",
            "addevents": "Add all premier events to the schedule",
            "addpractices": "Add all premier practices to the schedule (a map must still have a Thursday event to add practices)",
            "cancelevent": "Cancel a premier map for today/all days",
            "cancelpractice": "Cancel a premier practice for today/all days",
            "clearschedule": "Clear the schedule of all premier events AND practices",
            "addnote": "Add a reference/link to a practice note in the notes channel",
            "removenote": "Remove a reference/link to practice note in the notes channel (this does not delete the note itself)",
            "pin": "Pin a message",
            "unpin": "Unpin a message",
            # "clearslash": "Clear all slash commands", # /clearslash has been deprecated; I couldn't think of a use case for it that couldn't be done by removing the bot from the server.
            "clear": "(debug only) clear the debug channel",
            "deletemessage": "Delete a message by ID",
            # "sync": "Update the slash commands (ensure that they have been initialized first)", # deprecated. use /reload sync=1 instead
            "reload": "Reload the bot's cogs",
            "kill": "Kill the bot",
        }

    
    def get_pool(self):
        with open("./local_storage/map_pool.txt", "r") as file:
            return file.read().splitlines()
    
    def save_pool(self):
        with open("./local_storage/map_pool.txt", "w") as file:
            file.write("\n".join(self.map_pool))
    
    def get_preferences(self):
        with open("./local_storage/map_preferences.json", "r") as file:
            return json.load(file)
        
    def save_preferences(self):
        with open("./local_storage/map_preferences.json", "w") as file:
            json.dump(self.map_preferences, file)
    
    def get_weights(self):
        with open("./local_storage/map_weights.json", "r") as file:
            return json.load(file)

    def save_weights(self):
        with open("./local_storage/map_weights.json", "w") as file:
            json.dump(self.map_weights, file)

    def get_reminders(self):
        with open("./local_storage/reminders.json", "r") as file:
            return json.load(file)

    def save_reminders(self):
        with open("./local_storage/reminders.json", "w") as file:
            json.dump(self.reminders, file)

    def get_notes(self):
        with open("./local_storage/notes.json", "r") as file:
            return json.load(file)

    def save_notes(self):
        with open("./local_storage/notes.json", "w") as file:
            json.dump(self.notes, file)

    def est_to_utc(self, t: time):
        d = datetime.combine(datetime.today(), t)
        return self.tz.localize(d).astimezone(pytz.utc).time()

    def discord_local_time(self, time: datetime, _datetime=False):
        epoch_time = time.timestamp()
        style = "F" if _datetime else "t"  # F for full date and time
        formatted = f"<t:{str(int(epoch_time))}:{style}>"
        return formatted

    def log(self, message: str):
        with open(self.last_log, 'a+') as file:
            if ("connected to Discord" in message):
                prefix = "\n" if file.readline() != "" else ""
                file.write(f"{prefix}{'-' * 50}\n")

            file.write(
                f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')

    def debug_log(self, message: str):
        with open("./local_storage/debug_log.txt", 'a') as file:
            file.write(
                f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')

    def italics(self, text: str):
        return f"_{text}_"

    def bold(self, text: str):
        return f"**{text}**"

    def inline_code(self, text: str):
        return f"`{text}`"

    async def load_cogs(self, bot: commands.Bot, reload=False):
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                f = f'cogs.{file[:-3]}'
                if reload:
                    try:
                        await bot.reload_extension(f)
                    except commands.ExtensionNotLoaded: # reload argument is just to make things faster. if the cog isn't already loaded (new cog), just load it.
                        await bot.load_extension(f)
                else:
                    await bot.load_extension(f)

    def format_schedule(self, schedule: list, header: str = None):
        schedule = sorted(schedule, key=lambda x: x[1])

        subheaders = {m[2]: [] for m in schedule}

        for m in schedule:
            subheaders[m[2]].append(m[0])

        schedule = [f"- ___{k}___:\n" +
                    "\n".join(v) for k, v in subheaders.items()]
        schedule = "\n".join(([header] + schedule)
                            ) if header else "\n".join(schedule)

        return schedule

    async def has_permission(self, id: int, ctx: commands.Context | Interaction):
        """Check if caller has perms to use command. Only Sam or Bizzy can use commands that call this function."""
        message = "You do not have permission to use this command"
        if id not in self.admin_ids:
            if type(ctx) == commands.Context:
                await ctx.send(f'You do not have permission to use this command', ephemeral=True)
            else:
                await ctx.response.send_message(message, ephemeral=True)
            return False

        return True
    

global_utils = Utils()