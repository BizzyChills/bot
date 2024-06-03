import discord
from discord.ext import commands, tasks

from copy import deepcopy
from datetime import datetime, time, timedelta
import pytz
import asyncio
import asyncpg
import sys

from global_utils import global_utils


class TasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # global_utils.log("Tasks cog loaded")
        self.eventreminders.add_exception_type(asyncpg.PostgresConnectionError)
        self.eventreminders.start()
        self.clear_old_reminders.start()
        self.syncreminders.start()
        self.latest_log.start()

    @tasks.loop(time=global_utils.premier_reminder_times)
    async def eventreminders(self):
        """[task] Sends reminders for upcoming events near starting times of West Coast premier events"""

        global_utils.log("Checking for event reminders")

        guild = self.bot.get_guild(global_utils.val_server)
        prem_events = guild.fetch_scheduled_events() # sometimes, events are cancelled or rescheduled, so we need to fetch the events again

        debug_guild = self.bot.get_guild(global_utils.debug_server)
        debug_events = debug_guild.scheduled_events # don't really care if debug events are cancelled or rescheduled. we can just restart the bot when debugging

        current_time = datetime.now(pytz.utc)

        # no longer using this, but keeping it here in case we want to use it again
        # current_day = datetime.now().weekday()  # get current day based on my timezone
        # if current_day not in [3,5,6]: # only check for events on thursday, saturday, and sunday
        #     return

        for event in list(prem_events) + list(debug_events):
            if "premier" not in event.name.lower():
                continue

            start_time = event.start_time

            time_remaining = (start_time - current_time).total_seconds()

            reminder_class = ""
            if time_remaining <= 0:  # allow this reminder until 10 minutes after the event has already started
                if time_remaining >= -60 * 10:
                    reminder_class = global_utils.premier_reminder_classes[0]
                    if event.status == discord.EventStatus.scheduled:
                        await event.start()
                elif time_remaining <= -3600:  # remove the event
                    if event.status == discord.EventStatus.active:
                        await event.end()
                    elif event.status == discord.EventStatus.scheduled:
                        await event.cancel()
            elif time_remaining <= 60 * 30:
                reminder_class = global_utils.premier_reminder_classes[1]
            elif time_remaining <= 3600 * 3:
                reminder_class = global_utils.premier_reminder_classes[2]

            if reminder_class == "":  # there is no event reminder to send
                continue
            
            g = event.guild
            r = global_utils.prem_role if g.id == global_utils.val_server else global_utils.debug_role
            channel = self.bot.get_channel(
                global_utils.prem_channel) if g.id == global_utils.val_server else self.bot.get_channel(global_utils.debug_channel)
            role = discord.utils.get(g.roles, name=r)

            reminder_messages = {global_utils.premier_reminder_classes[0]: f"has started (at {global_utils.discord_local_time(start_time)}). JOIN THE VC!",
                                 global_utils.premier_reminder_classes[1]: f"is starting in 30 minutes (at {global_utils.discord_local_time(start_time)})!",
                                 global_utils.premier_reminder_classes[2]: f"is today at {global_utils.discord_local_time(start_time)}! Make sure you have RSVP'ed if you're joining!"}


            for k, v in reminder_messages.items():
                reminder = [
                    "(reminder)", f"{event.name} on {global_utils.italics(event.description)}", v]
                if k != global_utils.premier_reminder_classes[2]:
                    reminder.insert(1, f"{role.mention}")

                reminder_messages[k] = " ".join(reminder)
                
            log_message = f"Posted '{reminder_class}' reminder for event: {event.name} on {event.description} starting at {start_time.astimezone(global_utils.tz).strftime('%Y-%m-%d %H:%M:%S')} EST"

            if global_utils.already_logged(log_message):  # if the reminder has already been posted, skip it
                continue

            subbed_users = []
            async for user in event.users():
                subbed_users.append(user)

            await self.send_reminder(channel, reminder_messages[reminder_class], reminder_class, subbed_users)
            global_utils.log(log_message)

    async def send_reminder(self, channel : discord.TextChannel, message : str, reminder_class : str = "", subbed_users : list = []):
        """Sends a reminder message to a channel

        Parameters
        ----------
        channel : discord.TextChannel
            The channel to send the reminder message to (not the channel ID)
        message : str
            The message to send
        reminder_class : str
            The class of the reminder message
        subbed_users : list
            The list of users who have RSVP'ed to the event
        """
        # who to ping when
        pings = {"subbed": global_utils.premier_reminder_classes[0],
                 "message": global_utils.premier_reminder_classes[1],
                 "none": global_utils.premier_reminder_classes[2]}
        
        is_silent = reminder_class != pings["message"] 

        # We're not showing the RSVP list for the "today" reminder
        if reminder_class != pings["none"]:
            if len(subbed_users) < 5 and reminder_class == pings["message"]:
                message += f"\nWe don't have enough people RSVP'ed yet!"
                message += " Please RSVP before it's too late!"

        if is_silent:
            message += "\n\n(This message was sent silently)"

        await channel.send(message, silent=is_silent)

        # don't show the RSVP list for the "today" reminder
        if reminder_class == pings["none"]: 
            return

        if len(subbed_users) > 0:
            message = ("RSVP'ed users: \n" +
                        "- " +
                        "\n- ".join([user.mention for user in subbed_users]))
        else:
            message = "No one has RSVP'ed."

        message = "(reminder) " + message

        # only the start reminder should ping the subbed users
        is_silent = reminder_class != pings["subbed"]

        message += "\n\n(This message was sent silently)" if is_silent else ""

        await channel.send(message, silent=is_silent)

    @tasks.loop(hours=1)
    async def clear_old_reminders(self):
        """[task] Clears old reminder messages from the premier and debug channels"""
        channels = global_utils.prem_channel, global_utils.debug_channel

        for channel_id in channels:
            channel = self.bot.get_channel(channel_id)
            discord.TextChannel.history
            now = datetime.now().astimezone(pytz.utc)
            before_time = now - timedelta(days=1)
            # bulk deletion only works for messages up to 14 days old. If the bot is offline for over 14 days, oh well
            after_time = now - timedelta(days=14)

            messages = [message async for message in channel.history(limit=None, before=before_time, after=after_time) if message.author == self.bot.user
                        # bot prefixes all reminder messages with this
                        and message.content.startswith("(reminder)")
                        and now - message.created_at > timedelta(days=1)]  # only delete reminders that are at least 1 day old

            if len(messages) == 0:
                continue

            await channel.delete_messages(messages)
            global_utils.log(
                f"Deleted {len(messages)} old reminder messages from {channel.name}")

    @tasks.loop(count=1)
    async def syncreminders(self):
        """[task] Resyncs reminder timers in case the bot went offline with reminders still in the queue"""
        iterable = deepcopy(global_utils.reminders)

        for server in iterable.keys():
            for time, message in iterable[server].items():
                channel = self.bot.get_channel(
                    global_utils.prem_channel) if server == str(global_utils.val_server) else self.bot.get_channel(global_utils.debug_channel)

                time_dt = datetime.fromisoformat(time)

                if time_dt < datetime.now():
                    await channel.send(message + "\n(bot was offline when this reminder was supposed to go off at " + global_utils.discord_local_time(time_dt) + ".")
                    global_utils.log(
                        "Bot missed a reminder during its downtime, but sent it now. Message: " + message)
                    global_utils.reminders[server].pop(time)
                else:
                    await asyncio.sleep((time_dt - datetime.now()).total_seconds())
                    await channel.send(message)
                    global_utils.log("Posted reminder: " + message)
                    global_utils.reminders[server].pop(time)

            global_utils.save_reminders()

    # wait until a few seconds after midnight to start new log in case of some delay/desync issue
    @tasks.loop(time=global_utils.est_to_utc(time(hour=0, minute=0, second=5)))
    async def latest_log(self):
        """[task] Creates a new log file at midnight and updates the logger to write to the new file"""
        new_date = datetime.now().strftime("%Y-%m-%d")

        if new_date != global_utils.last_log_date:
            global_utils.log("Starting new log file")
            last_log_date = new_date
            global_utils.last_log = f"./logs/{last_log_date}_stdout.log"
            sys.stdout.close()
            sys.stdout = open(global_utils.last_log, 'a')


async def setup(bot):
    await bot.add_cog(TasksCog(bot), guilds=[discord.Object(global_utils.val_server), discord.Object(global_utils.debug_server)])
