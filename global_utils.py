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

        self.bot_token = os.getenv("DISCORD_BOT_TOKEN")

        if not self.bot_token:
            raise ValueError(
                "DISCORD_BOT_TOKEN is not set in the environment variables")

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
        self.all_channels = [self.debug_channel,
                             self.bot_channel, self.prem_channel]

        self.my_id = 461265370813038633
        self.sam_id = 180107711806046208
        self.admin_ids = [self.my_id, self.sam_id]

        self.tz = pytz.timezone("US/Eastern")

        right_now = (datetime.now().replace(
            microsecond=0) + timedelta(seconds=5)).time()
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

        self.premier_reminder_times = [self.est_to_utc(
            t) for t in self.premier_reminder_times]

        self.premier_reminder_classes = ["start", "prestart", "day"]

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
            "clear": "(debug only) clear the debug channel",
            "deletemessage": "Delete a message by ID",
            "reload": "Reload the bot's cogs",
            "kill": "Kill the bot",
        }

    def get_pool(self):
        """Extracts the map pool from the map_pool.txt file

        Returns
        -------
        list
            A list of strings containing the maps in the current map pool
        """
        with open("./local_storage/map_pool.txt", "r") as file:
            return file.read().splitlines()

    def save_pool(self):
        """Saves any changes to the map pool during runtime to the map_pool.txt file
        """
        with open("./local_storage/map_pool.txt", "w") as file:
            file.write("\n".join(self.map_pool))

    def get_preferences(self):
        """Extracts the map preferences from the map_preferences.json file

        Returns
        -------
        dict
            A 2D dictionary containing with the following structure: {map: {user_id: weight}}
        """
        with open("./local_storage/map_preferences.json", "r") as file:
            return json.load(file)

    def save_preferences(self):
        """Saves any changes to the map preferences during runtime to the map_preferences.json file
        """
        with open("./local_storage/map_preferences.json", "w") as file:
            json.dump(self.map_preferences, file)

    def get_weights(self):
        """Extracts the map weights from the map_weights.json file

        Returns
        -------
        dict
            A dictionary containing the weights for each map in the current map pool
        """
        with open("./local_storage/map_weights.json", "r") as file:
            return json.load(file)

    def save_weights(self):
        """Saves any changes to the map weights during runtime to the map_weights.json file
        """
        with open("./local_storage/map_weights.json", "w") as file:
            json.dump(self.map_weights, file)

    def get_reminders(self):
        """Extracts the reminders from the reminders.json file

        Returns
        -------
        dict
            A 2D dictionary containing with the following structure: {guild_id: {reminder_time: reminder_message}}
        """
        with open("./local_storage/reminders.json", "r") as file:
            return json.load(file)

    def save_reminders(self):
        """Saves any changes to the reminders during runtime to the reminders.json file
        """
        with open("./local_storage/reminders.json", "w") as file:
            json.dump(self.reminders, file)

    def get_notes(self):
        """Extracts the practice notes from the notes.json file. This file does not actually contain the notes, but rather the message IDs of the notes in the notes channel.

        Returns
        -------
        dict
            A 2D dictionary containing with the following structure: {map: {note_message_id: note_description}}
        """
        with open("./local_storage/notes.json", "r") as file:
            return json.load(file)

    def save_notes(self):
        """Saves any changes to the practice notes during runtime to the notes.json file
        """
        with open("./local_storage/notes.json", "w") as file:
            json.dump(self.notes, file)

    def est_to_utc(self, t: time):
        """Converts an EST time to a UTC time

        Parameters
        ----------
        t : time
            The EST time to convert

        Returns
        -------
        datetime.time
            The converted, UTC time
        """
        d = datetime.combine(datetime.today(), t)
        return self.tz.localize(d).astimezone(pytz.utc).time()

    def discord_local_time(self, time: datetime, _datetime=False):
        """Converts a datetime object to a Discord-formatted local time string (shows the time in the user's local time zone)

        Parameters
        ----------
        time : datetime
            The datetime object to convert
        _datetime : bool, optional
            Whether to include the date in the formatted string, by default False

        Returns
        -------
        str
            The Discord-formatted local time string
        """
        epoch_time = time.timestamp()
        style = "F" if _datetime else "t"  # F for full date and time
        formatted = f"<t:{str(int(epoch_time))}:{style}>"
        return formatted

    def log(self, message: str):
        """Logs a message to the current stdout log file

        Parameters
        ----------
        message : str
            The message to log
        """
        with open(self.last_log, 'a+') as file:
            if ("connected to Discord" in message):
                prefix = "\n" if file.readline() != "" else ""
                file.write(f"{prefix}{'-' * 50}\n")

            file.write(
                f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')

    def debug_log(self, message: str):
        """Logs a message to the debug log file

        Parameters
        ----------
        message : str
            The debug message to log
        """
        with open("./local_storage/debug_log.txt", 'a') as file:
            file.write(
                f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')

    def italics(self, text: str):
        """Formats text to be italicized in Discord

        Parameters
        ----------
        text : str
            The text to format

        Returns
        -------
        str
            The formatted text
        """
        return f"_{text}_"

    def underline(self, text: str):
        """Formats text to be underlined in Discord

        Parameters
        ----------
        text : str
            The text to format

        Returns
        -------
        str
            The formatted text
        """
        return f"__{text}__"

    def bold(self, text: str):
        """Formats text to be bold in Discord

        Parameters
        ----------
        text : str
            The text to format

        Returns
        -------
        str
            The formatted text
        """
        return f"**{text}**"

    def inline_code(self, text: str):
        """Formats text to be in an inline code block in Discord

        Parameters
        ----------
        text : str
            The text to format

        Returns
        -------
        str
            The formatted text
        """
        return f"`{text}`"

    def style_text(self, text: str, style: str):
        """Formats text to a specified style in Discord

        Parameters
        ----------
        text : str
            The text to format
        style : str
            The style to apply to the text. Options are "(i)talics", "(u)nderline", "(b)old", or "(c)ode". 

            Just use the first letter of the style (case-insensitive and spaces are ignored). 
            If a style character is not recognized, it will be ignored.

        Returns
        -------
        str
            The formatted text
        """
        style = style.replace(" ", "").lower()  # easier to parse the style
        style = set(style)

        output = text

        all_styles = {'i': self.italics, 'u': self.underline,
                      'b': self.bold, 'c': self.inline_code}

        for s in style:
            if s not in all_styles:
                continue

            output = all_styles[s](output)

        return output

    async def load_cogs(self, bot: commands.Bot):
        """Load/reload all cogs in the cogs directory

        Parameters
        ----------
        bot : commands.Bot
            The bot object that the cogs will be loaded into
        """
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                f = f'cogs.{file[:-3]}'
                try:
                    # reload them if they're already loaded
                    await bot.reload_extension(f)
                except commands.ExtensionNotLoaded:  # otherwise
                    await bot.load_extension(f)  # load them
    
    async def already_logged(self, log_message: str):
        """Checks if a log message has already been logged in the current stdout log file

        Parameters
        ----------
        log_message : str
            The message to check for in the log file

        Returns
        -------
        bool
            Whether the message has already been logged
        """
        if log_message == "":
            return False

        with open(self.last_log, "r") as file:
            log_contents = file.read()
        
        return log_message in log_contents if log_contents != "" else False
    

    async def has_permission(self, id: int, ctx: commands.Context | Interaction):
        """Determines if the user is either Sam or Bizzy for use in admin commands

        Parameters
        ----------
        id : int
            The user ID to check
        ctx : commands.Context | Interaction
            The context object that initiated the command. Used to notify the user that they don't have permission (and log the attempt).

        Returns
        -------
        bool
            Whether the user has permission to use the command
        """
        message = "You do not have permission to use this command"

        if id in self.admin_ids:
            return True

        if type(ctx) == commands.Context:
            await ctx.send(message, ephemeral=True)
            command = ctx.invoked_with
        else:
            await ctx.response.send_message(message, ephemeral=True)
            command = ctx.command.name

        self.log(
            f"User {id} attempted to use the admin command '{ctx.prefix}{command}'")
        return False


global_utils = Utils()
