import json
from datetime import datetime, time, timedelta
import pytz
import os
import typing

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

def save_notes(notes):
    with open("./local_storage/notes.json", "w") as file:
        json.dump(notes, file)

def est_to_utc(t: time):
    d = datetime.combine(datetime.today(), t)
    return tz.localize(d).astimezone(pytz.utc).time()

def discord_local_time(time: datetime):
    epoch_time = time.timestamp()
    formatted = "<t:" + str(int(epoch_time)) + ":t>"
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
all_channels = [debug_channel, bot_channel, prem_channel] # no voice channel, these are the general channels the bot will be in. use specific channel checks for other uses

my_id = 461265370813038633
sam_id = 180107711806046208
admin_ids = [my_id, sam_id]


debug_role = "southern"
prem_role = "The Valorats"

tz = pytz.timezone("US/Eastern")

# debug, 7 seconds from right now to trigger the eventreminders task on startup
right_now = (datetime.now().replace(
    microsecond=0) + timedelta(seconds=5)).time()

premier_reminder_times = [ # add 2 seconds to each time to ensure time_remaining logic works
    right_now,  # debug,
    time(hour=19, second=2),  # 3 hours before for thur and sun
    time(hour=20, second=2),  # 3 hours before for sat

    time(hour=21, second=2),  # 1 hour before for thur and sun
    time(hour=21, minute=50, second=2),  # 10 minutes before for thur and sun
    time(hour=22, second=2),  # right on time for thur and sun AND 1 hour before for sat
    time(hour=22, minute=50, second=2),  # 10 minutes before for sat

    time(hour=23, second=2)  # right on time for sat
]


premier_reminder_times = [est_to_utc(t) for t in premier_reminder_times]

premier_reminder_classes = ["start", "prestart", "hour", "day"]
p = premier_reminder_times

map_pool = get_pool()
map_preferences = get_prefrences()
map_weights = get_weights()
reminders = get_reminders()
notes = get_notes()
