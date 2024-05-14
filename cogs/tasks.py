import discord
from discord.ext import commands, tasks

from copy import deepcopy
from datetime import datetime, time, timedelta
import pytz
import asyncio
import asyncpg
import sys

from my_utils import *

class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @commands.Cog.listener()
    async def on_ready(self):
        log("Tasks cog loaded")
        self.eventreminders.add_exception_type(asyncpg.PostgresConnectionError)
        self.eventreminders.start()
        self.syncreminders.start()
        self.latest_log.start()


    @tasks.loop(time=premier_reminder_times)
    async def eventreminders(self):
        """Send reminders for upcoming events"""

        log("Checking for event reminders")

        guild = self.bot.get_guild(val_server)
        prem_events = guild.scheduled_events

        debug_guild = self.bot.get_guild(debug_server)
        debug_events = debug_guild.scheduled_events

        current_time = datetime.now(pytz.utc).time()


        # no longer using this, but keeping it here in case we want to use it again
        # current_day = datetime.now().weekday()  # get current day based on my timezone
        # if current_day not in [3,5,6]: # only check for events on thursday, saturday, and sunday
        #     return

        # for event in list(prem_events) + list(debug_events):
        for event in list(debug_events):
            if "premier" not in event.name.lower():
                continue
            
            g = event.guild
            r = prem_role if g.id == val_server else debug_role
            role = discord.utils.get(g.roles, name=r)
            subbed_users = []
            async for user in event.users():
                subbed_users.append(user)

            start_time = event.start_time
            current_time = datetime.now().astimezone(tz)

            time_remaining = (start_time - current_time).total_seconds()

            reminder_messages = {premier_reminder_classes[0]: f"(reminder) {role.mention} {event.name} on _{event.description}_ has started (at {discord_local_time(start_time)}). JOIN THE VC!",
                                premier_reminder_classes[1]: f"(reminder) {role.mention} {event.name} on _{event.description}_ is starting in 10 minutes (at {discord_local_time(start_time)})! JOIN THE VC!",
                                premier_reminder_classes[2]: f"(reminder) {role.mention} {event.name} on _{event.description}_ is starting in 1 hour (at {discord_local_time(start_time)})! Make sure you have RSVP'ed if you're joining!",
                                premier_reminder_classes[3]: f"(reminder) {role.mention} {event.name} on _{event.description}_ is today at {discord_local_time(start_time)}! Make sure you have RSVP'ed if you're joining!"}

            reminder_class = ""
            if time_remaining <= 0:  # allow this reminder until 30 minutes after the event has already started
                if time_remaining >= -3600 * .5:
                    reminder_class = "start"
                elif time_remaining <= -3600 * 1:  # remove the event
                    try:
                        await event.cancel()
                    except ValueError:
                        await event.end()
                        
            elif time_remaining <= 60 * 10:
                reminder_class = "prestart"
            elif time_remaining <= 3600:
                reminder_class = "hour"
            elif time_remaining <= 3600 * 3:
                reminder_class = "day"

            if reminder_class != "":  # there is an event reminder to send
                log_message = f"Posted '{reminder_class}' reminder for event: {event.name} on {event.description} starting at {start_time.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')} EST"

                with open(last_log, "r") as file:
                    log_contents = file.read()

                if log_message in log_contents:  # if the reminder has already been posted, skip it
                    continue

                message = reminder_messages[reminder_class]

                channel = self.bot.get_channel(
                    prem_channel) if g.id == val_server else self.bot.get_channel(debug_channel)

                is_silent = True if len(
                    subbed_users) >= 5 and reminder_class == "hour" else False

                if len(subbed_users) < 5:  # if we don't have enough people, actually ping the role
                    message += f"\nWe don't have enough people for {event.name} on _{event.description}_ yet!"
                    message += " Please RSVP before it's too late!" if reminder_class not in [
                        "start", "prestart"] else " Please join the VC so we can start!"
                    is_silent = False

                if is_silent:
                    message += "\n\n(This message was sent silently)"

                await channel.send(message, silent=is_silent)

                log(log_message)

                if len(subbed_users) > 0:
                    message = " RSVP'ed users: \n" + \
                        "- " + "\n- ".join([user.mention for user in subbed_users])
                else:
                    message = "No one has RSVP'ed yet."

                message += "\n\n(This message was sent silently)"

                await channel.send(message, silent=True)


    @tasks.loop(count=1)
    async def syncreminders(self):
        """Resync reminder timers in case the bot went offline """
        global reminders

        iterable = deepcopy(reminders)

        for server in iterable.keys():
            for time, message in iterable[server].items():
                channel = self.bot.get_channel(
                    prem_channel) if server == str(val_server) else self.bot.get_channel(debug_channel)

                time_dt = datetime.fromisoformat(time)

                if time_dt < datetime.now():
                    await channel.send(message + "\n(bot was offline when this reminder was supposed to go off at " + discord_local_time(time_dt) + ".")
                    log("Bot missed a reminder during its downtime, but sent it now. Message: " + message)
                    reminders[server].pop(time)
                else:
                    await asyncio.sleep((time_dt - datetime.now()).total_seconds())
                    await channel.send(message)
                    log("Posted reminder: " + message)
                    reminders[server].pop(time)

            save_reminders(reminders)

    # wait until 1 minute after midnight to start new log in case of delay


    @tasks.loop(time=est_to_utc(time(hour=0, minute=1, second=0)))
    async def latest_log(self):
        """Create a new log file at midnight"""
        global last_log
        global last_log_date

        log_date = datetime.now().strftime("%Y-%m-%d")

        if log_date != last_log_date:
            log("Starting new log file")
            last_log_date = log_date
            last_log = f"./logs/{last_log_date}_stdout.log"
            sys.stdout.close()
            sys.stdout = open(last_log, 'a')


async def setup(bot):
    await bot.add_cog(Tasks(bot), guilds=[discord.Object(val_server), discord.Object(debug_server)])