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
        self.premier_reminder_types = ["start", "prestart"]

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the TasksCog cog is ready to start the tasks
        """
        # global_utils.log("Tasks cog loaded")
        self.eventreminders.add_exception_type(asyncpg.PostgresConnectionError)
        self.eventreminders.start()
        self.clear_old_reminders.start()
        self.remember_reminders.start()
        self.latest_log.start()

    async def get_reminder_type(self, event: discord.ScheduledEvent) -> str:
        """Given an event, returns the type of reminder that needs to be sent
        Parameters
        ----------
        event : discord.Event
            The event to determine the reminder type for

        Returns
        -------
        str
            The type of reminder to send (from the list of premier reminder types in self.premier_reminder_types) or an empty string if no reminder is needed

        """

        time_remaining = (event.start_time -
                          datetime.now(pytz.utc)).total_seconds()

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
        elif time_remaining <= 3600:
            reminder_type = self.premier_reminder_types[1]

        return reminder_type

    @tasks.loop(time=global_utils.premier_reminder_times)
    async def eventreminders(self) -> None:
        """[task] Sends reminders for upcoming events near starting times of West Coast premier events"""
        global_utils.log("Checking for event reminders")

        events = []

        for g_id in [global_utils.val_server_id, global_utils.debug_server_id]:
            guild = self.bot.get_guild(g_id)
            # the more urgent the reminder, the later it should be sent (since it will be closer to the bottom of the chat)
            new_events = [
                e for e in guild.scheduled_events if "premier" in e.name.lower()]
            events += sorted(new_events,
                             key=lambda x: x.start_time, reverse=True)

        for event in events:
            reminder_type = await self.get_reminder_type(event)
            if reminder_type == "":  # there is no event reminder to send
                continue

            log_message = f"Posted '{reminder_type}' reminder for event: {event.name} on {event.description} starting at {event.start_time.astimezone(global_utils.tz).strftime('%Y-%m-%d %H:%M:%S')} EST"

            # if the reminder has already been posted, skip it
            if global_utils.already_logged(log_message):
                continue

            subbed_users = []
            async for user in event.users():
                subbed_users.append(user)

            if event.guild.id == global_utils.val_server_id:
                channel = self.bot.get_channel(global_utils.prem_channel_id)
                role = discord.utils.get(
                    event.guild.roles, name=global_utils.prem_role_name)
            elif event.guild.id == global_utils.debug_server_id:
                channel = self.bot.get_channel(global_utils.debug_channel_id)
                role = discord.utils.get(
                    event.guild.roles, name=global_utils.debug_role_name)

            if reminder_type == self.premier_reminder_types[-1]:
                message = f"(reminder) {role.mention}"
            else:
                message = f"(reminder) RSVP'ed Users:\n- " + \
                    '\n- '.join([user.mention for user in subbed_users])

            embed = await self.gen_embed(event, reminder_type, len(subbed_users))

            button = discord.ui.Button(
                style=discord.ButtonStyle.link, label="RSVP", url=event.url)
            view = discord.ui.View()

            if reminder_type == self.premier_reminder_types[-1]:
                view.add_item(button)

            await channel.send(message, embed=embed, view=view)

            # mark the reminder as posted
            global_utils.log(log_message)

    async def gen_embed(self, event: discord.ScheduledEvent, reminder_type: str, rsvp_len: int) -> discord.Embed:
        """Generates an embed for a reminder message

        Parameters
        ----------
        event : discord.ScheduledEvent
            The event that the reminder is for
        reminder_type : str
            The class of the reminder message
        rsvp_len : int
            The number of users who have RSVP'ed to the event

        Returns
        -------
        discord.Embed
            The embed to send
        """
        urls = {m: "" for m in global_utils.map_preferences.keys()}
        urls["abyss"] = "https://static.wikia.nocookie.net/valorant/images/6/61/Loading_Screen_Abyss.png/revision/latest/scale-to-width-down/1000?cb=20240621121057"
        urls["ascent"] = "https://static.wikia.nocookie.net/valorant/images/e/e7/Loading_Screen_Ascent.png/revision/latest/scale-to-width-down/1000?cb=20200607180020"
        urls["bind"] = "https://static.wikia.nocookie.net/valorant/images/2/23/Loading_Screen_Bind.png/revision/latest/scale-to-width-down/1000?cb=20200620202316"
        urls["breeze"] = "https://static.wikia.nocookie.net/valorant/images/1/10/Loading_Screen_Breeze.png/revision/latest/scale-to-width-down/1000?cb=20210427160616"
        urls["fracture"] = "https://static.wikia.nocookie.net/valorant/images/f/fc/Loading_Screen_Fracture.png/revision/latest/scale-to-width-down/1000?cb=20210908143656"
        urls["haven"] = "https://static.wikia.nocookie.net/valorant/images/7/70/Loading_Screen_Haven.png/revision/latest/scale-to-width-down/1000?cb=20200620202335"
        urls["icebox"] = "https://static.wikia.nocookie.net/valorant/images/1/13/Loading_Screen_Icebox.png/revision/latest/scale-to-width-down/1000?cb=20201015084446"
        urls["lotus"] = "https://static.wikia.nocookie.net/valorant/images/d/d0/Loading_Screen_Lotus.png/revision/latest/scale-to-width-down/1000?cb=20230106163526"
        urls["pearl"] = "https://static.wikia.nocookie.net/valorant/images/a/af/Loading_Screen_Pearl.png/revision/latest/scale-to-width-down/1000?cb=20220622132842"
        urls["split"] = "https://static.wikia.nocookie.net/valorant/images/d/d6/Loading_Screen_Split.png/revision/latest/scale-to-width-down/1000?cb=20230411161807"
        urls["sunset"] = "https://static.wikia.nocookie.net/valorant/images/5/5c/Loading_Screen_Sunset.png/revision/latest/scale-to-width-down/1000?cb=20230829125442"

        map_name = event.description.lower()
        map_url = urls.get(map_name, "")
        map_display_name = global_utils.style_text(
            event.description.title(), 'i')

        title = f"Premier match on {map_display_name}"
        rsvp_hint = f"Please RSVP by clicking the button below and then clicking {global_utils.style_text('interested', 'c')} (if you haven't already)."
        desc = f"There is a premier match on {map_display_name} in 1 hour (at {global_utils.discord_local_time(event.start_time)})! {rsvp_hint}" if reminder_type == "prestart" else f"The premier match on {map_display_name} has started! JOIN THE VC!"
        author = self.bot.user

        the_little_things = "user" if rsvp_len == 1 else "users"

        embed = discord.Embed(title=title, description=desc,
                              color=discord.Color.blurple())
        (
            embed.set_author(name=author.display_name,
                             icon_url=author.avatar.url)
            .set_image(url=map_url)
            .add_field(name="RSVP'ed", value=f"{rsvp_len} {the_little_things}", inline=True)
            .add_field(name="Map Weight", value=f"{global_utils.map_weights[map_name]}", inline=True)
        )

        return embed

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
    async def remember_reminders(self) -> None:
        """[task] Remembers reminder timers (made via /remind) in case the bot went offline with reminders still in the queue"""
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

        if new_date != global_utils.log_date:
            global_utils.log("Starting new log file")
            global_utils.log_date = new_date
            global_utils.log_filepath = f"./logs/{global_utils.log_date}_stdout.log"
            sys.stdout.close()
            sys.stdout = open(global_utils.log_filepath, 'a')

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
