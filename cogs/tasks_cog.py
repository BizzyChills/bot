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
    def __init__(self, bot: commands.bot) -> None:
        """Initializes the TasksCog cog and stores the type names for premier reminders

        Parameters
        ----------
        bot : discord.ext.commands.bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method

        """
        self.bot = bot

        self.premier_reminder_types = ["start", "prestart", "day"]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the TasksCog cog is ready to start the tasks
        """
        # global_utils.log("Tasks cog loaded")
        self.eventreminders.add_exception_type(asyncpg.PostgresConnectionError)
        self.eventreminders.start()
        self.clear_old_reminders.start()
        self.syncreminders.start()
        self.latest_log.start()

    async def get_reminder(self, event: discord.ScheduledEvent) -> tuple[str, str]:
        """Given an event, returns the type of reminder to send and the message to send

        Parameters
        ----------
        event : discord.Event
            The event to determine the reminder type for

        Returns
        -------
        tuple | None
            A tuple with the structure (reminder_type, message). If there is no reminder to send, each value is empty string

        """
        current_time = datetime.now(pytz.utc)
        start_time = event.start_time

        time_remaining = (start_time - current_time).total_seconds()

        reminder_type = ""
        if time_remaining <= 0:  # allow this reminder until 10 minutes after the event has already started
            if time_remaining >= -60 * 10:
                reminder_type = self.premier_reminder_types[0]
                if event.status == discord.EventStatus.scheduled:
                    await event.start()
            elif time_remaining <= -3600:  # remove the event
                if event.status == discord.EventStatus.active:
                    await event.end()
                elif event.status == discord.EventStatus.scheduled:
                    await event.cancel()
        elif time_remaining <= 60 * 30:
            reminder_type = self.premier_reminder_types[1]
        elif time_remaining <= 3600 * 3:
            reminder_type = self.premier_reminder_types[2]

        if reminder_type == "":
            return "", ""

        g = event.guild
        role_name = global_utils.prem_role_name if g.id == global_utils.val_server_id else global_utils.debug_role_name
        role = discord.utils.get(g.roles, name=role_name)

        if reminder_type == self.premier_reminder_types[0]:
            message = f"has started (at {global_utils.discord_local_time(start_time)}). JOIN THE VC!"
        elif reminder_type == self.premier_reminder_types[1]:
            message = f"is starting in 30 minutes (at {global_utils.discord_local_time(start_time)})!"
        elif reminder_type == self.premier_reminder_types[2]:
            message = f"is today at {global_utils.discord_local_time(start_time)}! Make sure you have RSVP'ed if you're joining!"

        message = f"(reminder) {event.name} on {global_utils.style_text(event.description, 'i')} {message}"

        if reminder_type != self.premier_reminder_types[2]:
            message = message.split()
            # need "(reminder)" to be the first word, ping the role after it
            message.insert(1, f"{role.mention}")
            message = " ".join(message)

        return reminder_type, message

    @tasks.loop(time=global_utils.premier_reminder_times)
    async def eventreminders(self) -> None:
        """[task] Sends reminders for upcoming events near starting times of West Coast premier events"""

        global_utils.log("Checking for event reminders")

        events = []

        for g_id in [global_utils.val_server_id, global_utils.debug_server_id]:
            guild = self.bot.get_guild(g_id)
            # the more urgent the reminder, the later it should be sent (since it will be closer to the bottom of the chat)
            events += sorted(guild.scheduled_events, key=lambda x: x.start_time, reverse=True)

        for event in events:
            if "premier" not in event.name.lower():
                continue

            start_time = event.start_time

            reminder_type, message = await self.get_reminder(event)
            if reminder_type == "":  # there is no event reminder to send
                continue

            log_message = f"Posted '{reminder_type}' reminder for event: {event.name} on {event.description} starting at {start_time.astimezone(global_utils.tz).strftime('%Y-%m-%d %H:%M:%S')} EST"

            # if the reminder has already been posted, skip it
            if global_utils.already_logged(log_message):
                continue

            subbed_users = []
            async for user in event.users():
                subbed_users.append(user)

            channel = self.bot.get_channel(
                global_utils.prem_channel_id) if event.guild.id == global_utils.val_server_id else self.bot.get_channel(global_utils.debug_channel_id)

            await self.send_reminder(channel, message, reminder_type, len(subbed_users))

            # mark the reminder as posted
            global_utils.log(log_message)

            # don't show RSVP list for the day reminder
            if reminder_type == self.premier_reminder_types[2]:
                continue

            # loud ping individual users only for the start reminder
            is_silent = reminder_type != self.premier_reminder_types[0]

            await self.send_rsvp(channel, is_silent, subbed_users)

    async def send_reminder(self, channel: discord.TextChannel, message: str, reminder_type: str = "", rsvp_len: int = 0) -> None:
        """Sends a reminder message to a channel

        Parameters
        ----------
        channel : discord.TextChannel
            The channel to send the reminder message to (not the channel ID)
        message : str
            The message to send
        reminder_type : str
            The class of the reminder message
        rsvp_len : int
            The number of users who have RSVP'ed to the event
        """
        # who to ping when
        pings = {"subbed": self.premier_reminder_types[0],
                 "role": self.premier_reminder_types[1],
                 "none": self.premier_reminder_types[2]}

        is_silent = reminder_type != pings["role"]

        if reminder_type == pings["role"] and rsvp_len < 5:
            message += f"\nWe don't have enough people RSVP'ed yet!"
            message += " Please RSVP before it's too late!"

        if is_silent:
            message += "\n\n(This message was sent silently)"

        await channel.send(message, silent=is_silent)

    async def send_rsvp(self, channel: discord.TextChannel, is_silent: bool, subbed_users: list[discord.User] = []) -> None:
        """Sends the list of users who have RSVP'ed to an event (to accompany the reminder message)

        Parameters
        ----------
        channel : discord.TextChannel
            The channel to send the list of users to
        subbed_users : list[discord.User]
            The list of users who have RSVP'ed to the event
        """
        if len(subbed_users) > 0:
            message = ("RSVP'ed users: \n" +
                       "- " +
                       "\n- ".join([user.mention for user in subbed_users]))
        else:
            message = "No one has RSVP'ed."

        message = "(reminder) " + message

        message += "\n\n(This message was sent silently)" if is_silent else ""

        await channel.send(message, silent=is_silent)

    @tasks.loop(hours=1)
    async def clear_old_reminders(self) -> None:
        """[task] Clears old reminder messages from the premier and debug channels"""
        channels = global_utils.prem_channel_id, global_utils.debug_channel_id

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
    async def syncreminders(self) -> None:
        """[task] Resyncs reminder timers in case the bot went offline with reminders still in the queue"""
        iterable = deepcopy(global_utils.reminders)

        for server in iterable.keys():
            for time, message in iterable[server].items():
                channel = self.bot.get_channel(
                    global_utils.prem_channel_id) if server == str(global_utils.val_server_id) else self.bot.get_channel(global_utils.debug_channel_id)

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
    async def latest_log(self) -> None:
        """[task] Creates a new log file at midnight and updates the logger to write to the new file"""
        new_date = datetime.now().strftime("%Y-%m-%d")

        if new_date != global_utils.last_log_date:
            global_utils.log("Starting new log file")
            global_utils.last_log_date = new_date
            global_utils.last_log = f"./logs/{global_utils.last_log_date}_stdout.log"
            sys.stdout.close()
            sys.stdout = open(global_utils.last_log, 'a')

    @tasks.loop(minutes=5)
    async def update_cache(self) -> None:
        """[task] Updates the cache of the bot with whatever this function has been made to update (like scheduled_events)"""
        guild_ids = [global_utils.val_server_id, global_utils.debug_server_id]

        for g_id in guild_ids:
            guild = self.bot.get_guild(g_id)
            guild.scheduled_events = await guild.fetch_scheduled_events()

async def setup(bot: commands.bot) -> None:
    """Adds the TasksCog cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(TasksCog(bot), guilds=[discord.Object(global_utils.val_server_id), discord.Object(global_utils.debug_server_id)])
