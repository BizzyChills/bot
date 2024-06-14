import os
import sys
import json

from datetime import datetime, time, timedelta
import pytz

# reduce bloat, only for type hints
from discord import Interaction, Guild, ScheduledEvent
from discord.ext import commands


class Utils:
    def __init__(self) -> None:
        """Initializes the global utility class, which contains various utility functions and global variables for the bot
        """
        os.chdir(os.path.dirname(os.path.abspath(__file__))
                 )  # ensure the working directory is the same as the script
        if not os.path.exists('logs'):
            os.makedirs('logs')

        self.source_code = "https://github.com/BizzyChills/bot/"

        self.log_date = datetime.now().strftime("%Y-%m-%d")
        self.log_filepath = f'./logs/{self.log_date}_stdout.log'

        self.debug_server_id = 1217649405759324232
        self.debug_role_name = "southern"
        self.debug_channel_id = 1217649405759324235

        self.val_server_id = 1100632842528096330
        self.prem_role_name = "The Valorats"
        self.bot_channel_id = 1218420817394925668
        self.prem_channel_id = 1193661647752003614
        self.notes_channel_id = 1237971459461218376

        self.my_id = 461265370813038633
        sam_id = 180107711806046208
        self.admin_ids = [self.my_id, sam_id]

        self.tz = pytz.timezone("US/Eastern")

        right_now = (datetime.now().replace(
            microsecond=0) + timedelta(seconds=5)).time()
        self.premier_reminder_times = [  # add 2 seconds to each time to ensure time_remaining logic works
            right_now,  # debug,
            time(hour=19, second=2),  # 3 hours before for thur and sun
            time(hour=20, second=2),  # 3 hours before for sat

            # 30 mins before for thur and sun
            time(hour=21, minute=30, second=2),

            # right on time for thur and sun
            time(hour=22, second=2),
            time(hour=22, minute=30, second=2),  # 30 minutes before for sat

            time(hour=23, second=2)  # right on time for sat
        ]

        self.premier_reminder_times = [self.est_to_utc(
            t) for t in self.premier_reminder_times]

        self.map_pool = self.get_pool()
        self.map_preferences = self.get_preferences()
        self.map_weights = self.get_weights()
        self.reminders = self.get_reminders()
        self.practice_notes = self.get_notes()

        self.positive_preference = "+"
        self.neutral_preference = "~"
        self.negative_preference = "-"

        self.command_descriptions = {
            # persist
            "commands": "Display all bot commands",
            "schedule": "Display the premier event and practice schedules",
            "source-code": "Link the repo containing the source code for the bot",
            "persist": "Display the persistent buttons",

            # info
            "map-pool-common": "Display the current competitive map pool",
            "notes": "Display a practice note from the notes channel. Leave note_id blank to display all options",

            # voting
            "prefer-map": "Declare your preference for a map to play for premier playoffs",
            "map-votes": "Display each member's map preferences",
            "map-weights": "Display the total weights for each map in the map pool",

            # music
            "join-voice": "Join your voice channel",
            "leave-voice": "Leave your voice channel",
            "add-song": "Add a song (or any video really) to the playlist via YouTube URL (can take a while!)",
            "music": "Display the music controls",
            # "play-song": "Begin/resume playback of current song (or next song if current is None)",
            # "pause-song": "Pause playback of current song",
            # # "resume-song": "Resume playback of current song", # deprecated, just use play-song
            # "stop-song": "Stop playback of current song (cannot resume)",
            # "skip-song": "Skip current song and play next song in playlist (if any)",
            # "loop-song": "Toggle looping of the current song",
            # "playlist": "Display the current song as well as the songs in the playlist",


            # admin
            "map-pool-admin": "Modify the map pool",
            "add-map": "Add a map to the list of all maps in the game",
            "remove-map": "Remove a map from the list of all maps in the game",
            "add-events": "Add all premier events to the schedule",
            "cancel-event": "Cancel a premier map for today/all days",
            "add-practices": "Add all premier practices to the schedule (a map must still have a Thursday event to add practices)",
            "cancel-practice": "Cancel a premier practice for today/all days",
            "clear-schedule": "Clear the schedule of all premier events AND practices",
            "add-note": "Add a reference/link to a practice note in the notes channel",
            "remove-note": "Remove a reference/link to practice note in the notes channel (this does not delete the note itself)",
            "remind": "Set a reminder for the premier role",
            "pin": "Pin a message",
            "unpin": "Unpin a message",
            "delete-message": "Delete a message by ID",
            "kill": "Kill the bot",

            # bizzy
            "clear": "(debug only) clear the debug channel",
            "feature": "Promote a new feature in the current channel",
            "reload": "Reload the bot's cogs",

            # misc
            "hello": "Say hello",
            "feed": "Feed the bot",
            "unfeed": "Unfeed the bot",
            "trivia": "Play a game of trivia with the bot to earn a prize!",
        }

    def get_pool(self) -> list[str]:
        """Extracts the map pool from the map_pool.txt file

        Returns
        -------
        list
            A list of strings containing the maps in the current map pool
        """
        with open("./local_storage/map_pool.txt", "r") as file:
            return file.read().splitlines()

    def save_pool(self) -> None:
        """Saves any changes to the map pool during runtime to the map_pool.txt file
        """
        self.map_pool.sort()
        with open("./local_storage/map_pool.txt", "w") as file:
            file.write("\n".join(self.map_pool))

    def get_preferences(self) -> dict:
        """Extracts the map preferences from the map_preferences.json file

        Returns
        -------
        dict
            A 2D dictionary containing with the following structure: {map: {user_id: weight}}
        """
        with open("./local_storage/map_preferences.json", "r") as file:
            return json.load(file)

    def save_preferences(self) -> None:
        """Saves any changes to the map preferences during runtime to the map_preferences.json file and also saves the map weights
        """
        self.map_preferences = {
            k: self.map_preferences[k] for k in sorted(self.map_preferences)}
        with open("./local_storage/map_preferences.json", "w") as file:
            json.dump(self.map_preferences, file)

        self.save_weights()

    def get_weights(self) -> dict:
        """Extracts the map weights from the map_weights.json file

        Returns
        -------
        dict
            A dictionary containing the weights for each map in the current map pool
        """
        with open("./local_storage/map_weights.json", "r") as file:
            return json.load(file)

    def save_weights(self) -> None:
        """Saves any changes to the map weights during runtime to the map_weights.json file
        """
        for map_name, user_weights in self.map_preferences.items():
            self.map_weights[map_name] = sum(
                [1 if user_weights.get(str(user_id)) == "+" else -1 if user_weights.get(str(user_id)) == "-" else 0 for user_id in user_weights])

        self.map_weights = {k: self.map_weights[k]
                            for k in sorted(self.map_weights)}

        with open("./local_storage/map_weights.json", "w") as file:
            json.dump(self.map_weights, file)

    def get_reminders(self) -> dict:
        """Extracts the reminders from the reminders.json file

        Returns
        -------
        dict
            A 2D dictionary containing with the following structure: {guild_id: {reminder_time: reminder_message}}
        """
        with open("./local_storage/reminders.json", "r") as file:
            return json.load(file)

    def save_reminders(self) -> None:
        """Saves any changes to the reminders during runtime to the reminders.json file
        """
        with open("./local_storage/reminders.json", "w") as file:
            json.dump(self.reminders, file)

    def get_notes(self) -> dict:
        """Extracts the practice notes from the notes.json file. This file does not actually contain the notes, but rather the message IDs of the notes in the notes channel.

        Returns
        -------
        dict
            A 2D dictionary containing with the following structure: {map: {note_message_id: note_description}}
        """
        with open("./local_storage/notes.json", "r") as file:
            return json.load(file)

    def save_notes(self) -> None:
        """Saves any changes to the practice notes during runtime to the notes.json file
        """
        with open("./local_storage/notes.json", "w") as file:
            json.dump(self.notes, file)

    def log(self, message: str) -> None:
        """Logs a message to the current stdout log file

        Parameters
        ----------
        message : str
            The message to log
        """
        with open(self.log_filepath, 'a+') as file:
            if ("connected to Discord" in message):
                prefix = "\n" if file.readline() != "" else ""
                file.write(f"{prefix}{'-' * 50}\n")

            file.write(
                f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')

    def debug_log(self, message: str) -> None:
        """Logs a message to the debug log file

        Parameters
        ----------
        message : str
            The debug message to log
        """
        with open("./local_storage/debug_log.txt", 'a') as file:
            file.write(
                f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')

    def est_to_utc(self, t: time) -> time:
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

    def discord_local_time(self, date_time: datetime, with_date=False) -> str:
        """Converts a datetime object to a Discord-formatted local time string (shows the time in the user's local time zone)

        Parameters
        ----------
        date_time : datetime
            The datetime object to convert
        with_date : bool, optional
            Include the date in the formatted string, by default False

        Returns
        -------
        str
            The Discord-formatted local time string
        """
        epoch_time = date_time.timestamp()
        style = "F" if with_date else "t"  # F for full date and time
        formatted = f"<t:{str(int(epoch_time))}:{style}>"
        return formatted

    def style_text(self, text: str, style: str) -> str:
        """Formats text to a specified style in Discord

        Parameters
        ----------
        text : str
            The text to format
        style : str
            The style string to apply to the text. Options are "(i)talics", "(u)nderline", "(b)old", or "(c)ode". 

            Just use the first letter of the desired style (case-insensitive and spaces are ignored). 
            If a style character is not recognized, it will be ignored.

        Example:
        ```python
        style_text("Hello, World!", 'ib')  # returns "_**Hello, World!**_"
        ```

        Returns
        -------
        str
            The formatted text
        """
        style = style.replace(" ", "").lower()  # easier to parse the style
        style = set(style)

        output = text

        all_styles = {'i': '_', 'u': '__', 'b': '**', 'c': '`'}

        for s in style:
            if s not in all_styles:
                continue

            s = all_styles[s]
            output = f"{s}{output}{s}"

        return output

    async def load_cogs(self, bot: commands.Bot) -> None:
        """Load/reload all cogs in the cogs directory

        Parameters
        ----------
        bot : discord.ext.commands.Bot
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

    def already_logged(self, log_message: str) -> bool:
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

        with open(self.log_filepath, "r") as file:
            log_contents = file.read()

        return log_message in log_contents if log_contents != "" else False

    async def is_admin(self, ctx: commands.Context | Interaction, respond: bool = True) -> bool:
        """Determines if the user is either Sam or Bizzy for use in admin commands

        Parameters
        ----------
        ctx : discord.ext.commands.Context | discord.Interaction
            The context object that initiated the command. Can be either a text command or a slash command
        respond : bool, optional
            Respond to the user with a invalid permissions message, by default True

        Returns
        -------
        bool
            Whether the user has permission to use the command
        """
        message = "You do not have permission to use this command"

        if type(ctx) == commands.Context:
            responder = ctx.send
            command = ctx.invoked_with
            user_id = ctx.author.id
        else:
            responder = ctx.response.send_message
            command = ctx.command.name
            user_id = ctx.user.id

        if user_id in self.admin_ids:
            return True

        if respond:
            await responder(message, ephemeral=True)

        # commands uses this function just to display extra commands if admin. User is not trying to use an admin command
        if command != "commands":
            self.log(
                f"User with id {user_id} attempted to use the admin command '{command}'")
        return False


global_utils = Utils()
