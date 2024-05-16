import json
from datetime import datetime, time, timedelta
import pytz
import os
from discord import Interaction as discord_Interaction
# reduce bloat, only for type hints
from discord.ext.commands import Context as commands_Context


def get_pool():
    with open("./local_storage/map_pool.txt", "r") as file:
        return file.read().splitlines()


def save_pool(mp):
    with open("./local_storage/map_pool.txt", "w") as file:
        file.write("\n".join(mp))


def get_prefrences():
    with open("./local_storage/map_preferences.json", "r") as file:
        return json.load(file)


def save_prefrences(mp):
    with open("./local_storage/map_preferences.json", "w") as file:
        json.dump(mp, file)


def get_weights():
    with open("./local_storage/map_weights.json", "r") as file:
        return json.load(file)


def save_weights(mw):
    with open("./local_storage/map_weights.json", "w") as file:
        json.dump(mw, file)


def get_reminders():
    with open("./local_storage/reminders.json", "r") as file:
        return json.load(file)


def save_reminders(reminders):
    with open("./local_storage/reminders.json", "w") as file:
        json.dump(reminders, file)


def get_notes():
    with open("./local_storage/notes.json", "r") as file:
        return json.load(file)


def save_notes(practice_notes):
    with open("./local_storage/notes.json", "w") as file:
        json.dump(practice_notes, file)


def est_to_utc(t: time):
    d = datetime.combine(datetime.today(), t)
    return tz.localize(d).astimezone(pytz.utc).time()


def discord_local_time(time: datetime, _datetime=False):
    epoch_time = time.timestamp()
    style = "F" if _datetime else "t"  # F for full date and time
    formatted = f"<t:{str(int(epoch_time))}:{style}>"
    return formatted


def log(message: str):
    global last_log
    with open(last_log, 'a+') as file:
        if ("connected to Discord" in message):
            prefix = "\n" if file.readline() != "" else ""
            file.write(f"{prefix}{'-' * 50}\n")

        file.write(
            f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')


def debug_log(message: str):
    with open("./local_storage/debug_log.txt", 'a') as file:
        file.write(
            f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')


def wrong_channel(interaction):
    return interaction.response.send_message("This command is not available in this channel.", ephemeral=True)


def format_schedule(schedule: list, header: str = None):
    schedule = sorted(schedule, key=lambda x: x[1])

    subheaders = {m[2]: [] for m in schedule}

    for m in schedule:
        subheaders[m[2]].append(m[0])

    schedule = [f"- ___{k}___:\n" +
                "\n".join(v) for k, v in subheaders.items()]
    schedule = "\n".join(([header] + schedule)
                         ) if header else "\n".join(schedule)

    return schedule


async def has_permission(id: int, ctx: commands_Context | discord_Interaction):
    """Check if caller has perms to use command. Only Sam or Bizzy can use commands that call this function."""
    message = "You do not have permission to use this command"
    if id not in admin_ids:
        if type(ctx) == commands_Context:
            await ctx.send(f'You do not have permission to use this command', ephemeral=True)
        else:
            await ctx.response.send_message(message, ephemeral=True)
        return False

    return True


def convert_to_json():
    with open("./local_storage/map_preferences.txt", "r") as file:
        mp = eval(file.read())
        save_prefrences(mp)

    with open("./local_storage/map_weights.txt", "r") as file:
        mw = eval(file.read())
        save_weights(mw)

    with open("./local_storage/reminders.txt", "r") as file:
        reminders = eval(file.read())
        save_reminders(reminders)


os.chdir(os.path.dirname(os.path.abspath(__file__)))
last_log_date = datetime.now().strftime("%Y-%m-%d")
if not os.path.exists('logs'):
    os.makedirs('logs')

last_log = f"./logs/{last_log_date}_stdout.log"

bot_token = "MTIxNzY0NjU0NDkxNzEwMjcwMw.GaY7e2.Z-YM3oT2Ts_zbZ8hs7N0zoEvhxqCMsSorzYzm8"

val_server = 1100632842528096330
debug_server = 1217649405759324232

debug_channel = 1217649405759324235
bot_channel = 1218420817394925668
prem_channel = 1193661647752003614
notes_channel = 1237971459461218376
voice_channel = 1100632843174031476
# no voice channel, these are the general channels the bot will be in. use specific channel checks for other uses
all_channels = [debug_channel, bot_channel, prem_channel]

my_id = 461265370813038633
sam_id = 180107711806046208
admin_ids = [my_id, sam_id]


debug_role = "southern"
prem_role = "The Valorats"

tz = pytz.timezone("US/Eastern")

# debug, 5 seconds from right now to trigger the eventreminders task on startup
right_now = (datetime.now().replace(
    microsecond=0) + timedelta(seconds=5)).time()

premier_reminder_times = [  # add 2 seconds to each time to ensure time_remaining logic works
    right_now,  # debug,
    time(hour=19, second=2),  # 3 hours before for thur and sun
    time(hour=20, second=2),  # 3 hours before for sat

    time(hour=21, second=2),  # 1 hour before for thur and sun
    time(hour=21, minute=50, second=2),  # 10 minutes before for thur and sun
    # right on time for thur and sun AND 1 hour before for sat
    time(hour=22, second=2),
    time(hour=22, minute=50, second=2),  # 10 minutes before for sat

    time(hour=23, second=2)  # right on time for sat
]


premier_reminder_times = [est_to_utc(t) for t in premier_reminder_times]

premier_reminder_classes = ["start", "prestart", "hour", "day"]

map_pool = get_pool()
map_preferences = get_prefrences()
map_weights = get_weights()
reminders = get_reminders()
practice_notes = get_notes()

command_descriptions = {
    "commands": "Display this message",
    "schedule": "Display the premier event and practice schedules",
    "mappool_common": "Display the current competitive map pool",
    "mappool_admin": "Modify the map pool",
    "notes": "Display a practice note from the notes channel. Leave note_id blank to display all options",
    "prefermap": "Declare your preference for a map to play for premier playoffs",
    "mapvotes": "Display each member's map preferences",
    "mapweights": "Display the total weights for each map",
    "hello": "Say hello",
    "feed": "Feed the bot",
    "unfeed": "Unfeed the bot",
    "remind": "Set a reminder for the premier role",
    "addevents": "Add all premier events to the schedule",
    "addpractices": "Add all premier practices to the schedule (must use /addevents first)",
    "cancelevent": "Cancel a premier map for today/all days",
    "cancelpractice": "Cancel a premier practice for today/all days",
    "clearschedule": "Clear the schedule of all premier events AND practices",
    "addnote": "Add a reference/link to a practice note in the notes channel",
    "removenote": "Remove a reference/link to practice note in the notes channel (this does not delete the note itself)",
    "pin": "Pin a message",
    "unpin": "Unpin a message",
    "sync": "Update the slash commands (ensure that they have been initialized first)",
    "clearslash": "Clear all slash commands",
    "clear": "Clear the last <amount> **commands** from the bot, user, or both (defaults to last command)",
    "deletemessage": "Delete a message by ID",
    "clearlogs": "Clear the stdout log(s)",
    "reload": "Reload the bot's cogs",
    "kill": "Kill the bot",
}
