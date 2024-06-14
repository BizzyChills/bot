import discord
from discord import app_commands
from discord.ext import commands, tasks

from datetime import datetime, timedelta
import asyncio
import os


from urllib.parse import urlparse

from global_utils import global_utils

import yt_dlp


class MusicCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the MusicCommands cog

        Parameters
        ----------
        bot : discord.ext.commands.Bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot
        self.vc = None
        self.owner = None
        self.last_activity = None
        # don't dc from vc if downloading a song
        self.downloading = False
        # need to hold the current song since it's removed from the playlist when played. used for looping
        self.current_song = None
        self.loop_song = False
        # holds the actual playlist in the form {(title, author): audio_filepath}
        self.playlist = {}
        # self.playlist.update({("Test Song", "Test Author"): "./local_storage/test.mp3"})
        # simply holds the URLs to avoid downloading the same song multiple times
        self.playlist_urls = {}

        # leave the vc after this many seconds if owner leaves
        self.ownerless_timeout_seconds = 60
        # self.ownerless_timeout_seconds = 3  # for testing
        # leave the vc if not playing music for this many seconds
        self.inactivity_timeout_seconds = 60 * 5
        # self.inactivity_timeout_seconds = 10 # for testing

        self.playlist_limit = 10
        
        self.buttons = MusicButtons(music_cog=self)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the MusicCommands cog is ready
        """
        # global_utils.log("Music commands cog loaded")
        self.timed_checks.start()

        for tmp in os.listdir("./local_storage/temp_music"):
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, self.delete_song,
                                 f"./local_storage/temp_music/{tmp}")

        # pass

    @commands.Cog.listener("on_reload_cogs")
    async def on_reload(self) -> None:
        """[event] Executes when the MusicCommands cog is reloaded
        """
        await self.reset_state()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """[event] Executes when a member's voice state changes

        Parameters
        ----------
        member : discord.Member
            The member whose voice state changed
        before : discord.VoiceState
            The voice state before the change
        after : discord.VoiceState
            The voice state after the change
        """
        if self.vc is None:
            return

        if member != self.owner:
            return

        if self.owner not in self.vc.channel.members:
            await asyncio.sleep(self.ownerless_timeout_seconds)

            if self.owner not in self.vc.channel.members:
                await self.vc.disconnect()
                self.vc = None
                self.owner = None
                self.last_activity = None

    @app_commands.command(name="music", description="button test")
    async def music(self, interaction: discord.Interaction) -> None:
        """[command] Test command for buttons

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if self.vc is None:
            await interaction.response.send_message(f"I am not in a voice channel. Use {global_utils.style_text('/join-voice', 'c')} to add me to a voice channel", ephemeral=True)
            return

        # if len(self.playlist) > 0:
        #     skip_button = view.children[3]
        #     skip_button.disabled = False
        self.buttons.message = interaction
        await interaction.response.send_message("Music Player", view=self.buttons, ephemeral=True)

    @app_commands.command(name="join-voice", description=global_utils.command_descriptions["join-voice"])
    async def join(self, interaction: discord.Interaction) -> None:
        """[command] Joins the user's voice channel

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if interaction.user.voice is None:
            await interaction.response.send_message("You must be in a voice channel to use this command", ephemeral=True)
            return

        if self.vc is not None:
            if interaction.user != self.owner:
                await interaction.response.send_message(f"I am already in a voice channel with {self.owner.display_name}", ephemeral=True)
                return
            if interaction.user.voice.channel == self.vc.channel:
                await interaction.response.send_message("I am already in the voice channel", ephemeral=True)
                return
            await self.vc.move_to(interaction.user.voice.channel)
        else:
            self.vc = await interaction.user.voice.channel.connect()

    
        self.owner = interaction.user
        self.update_activity()

        disconnect_str = global_utils.style_text('/leave-voice', 'c')
        add_str = global_utils.style_text('/add-song', 'c')
        limit_str = global_utils.style_text(
            f'limit: {self.playlist_limit}', 'bu')

        join_message = f"I have joined {self.vc.channel.mention}. Use {disconnect_str} to disconnect me. Use {add_str} to add a song to the playlist ({limit_str})"

        ownerless_timeout_str = global_utils.style_text(
            f'{self.ownerless_timeout_seconds} seconds', 'iu')
        inactive_timeout_str = global_utils.style_text(
            f'{self.inactivity_timeout_seconds} seconds', 'iu')

        extra_message = f"After {inactive_timeout_str} of inactivity (give or take 5 seconds) I will automatically disconnect."
        extra_message += f" Furthermore, if you leave the voice channel, I will automatically disconnect after {ownerless_timeout_str} (give or take 5 seconds)."

        await interaction.response.send_message(f"{join_message}\n\n{extra_message}", ephemeral=True)

    @app_commands.command(name="leave-voice", description=global_utils.command_descriptions["leave-voice"])
    async def leave(self, interaction: discord.Interaction) -> None:
        """[command] Leaves the user's voice channel

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if self.vc is None:
            await interaction.response.send_message("I am not in a voice channel", ephemeral=True)
            return

        if interaction.user != self.owner:
            await interaction.response.send_message("You must be the one who added me to the voice channel to use this command", ephemeral=True)
            return

        if self.current_song is not None:
            audio = self.current_song["audio"]
            audio.cleanup()

        for file in os.listdir("./local_storage/temp_music"):
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, self.delete_song,
                                 f"./local_storage/temp_music/{file}")

        await self.reset_state()
        await interaction.response.send_message("Left the voice channel", ephemeral=True)

    def download_song(self, url: str) -> tuple[str, str]:
        """Downloads a song from a YouTube URL and returns the title and author of the song

        Parameters
        ----------
        url : str
            The YouTube URL of the song to download

        Returns
        -------
        tuple[str, str]
            The title and author of the song
        """
        self.downloading = True

        ydl_opts = {
            'format': 'mp3/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                # 'preferredquality': '192',
            }],
            'outtmpl': './local_storage/temp_music/%(id)s.%(ext)s',
            'noplaylist': 'True',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            title = info['title']
            author = info['uploader']
            video_id = info['id']
            ydl.download([url])

        self.update_activity()
        self.downloading = False
        return title, author, video_id

    def delete_song(self, filepath: str) -> None:
        """Deletes a song file

        Parameters
        ----------
        filepath : str
            The file path of the song to delete
        """
        if os.path.exists(filepath):
            os.remove(filepath)

    @app_commands.command(name="add-song", description=global_utils.command_descriptions["add-song"])
    @app_commands.choices(
        bump=[
            app_commands.Choice(name="Yes", value=1),
        ]
    )
    @app_commands.describe(
        url="The YouTube URL of the song to add",
        bump="Bumps the song to the start of the playlist"
    )
    async def addsong(self, interaction: discord.Interaction, url: str, bump: int = 0) -> None:  # for testing
        """[command] Adds a song (or any video really) to the playlist via YouTube URL (can take a while!)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        url : str
            The YouTube URL of the song to add, by default "https://www.youtube.com/watch?v=jTJvyKZDFsY"
        bump : int, optional
            Treated as a boolean. Bump the song to the top of the playlist, by default 0
        """
        if self.vc is None:
            await interaction.response.send_message("I am not in a voice channel", ephemeral=True)
            return

        if interaction.user != self.owner:
            await interaction.response.send_message("You must be the one who added me to the voice channel to use this command", ephemeral=True)
            return

        self.update_activity()

        if len(self.playlist) == self.playlist_limit:
            await interaction.response.send_message(f"The playlist is currently limited to only {self.playlist_limit} songs. Use {global_utils.style_text('/skip', 'c')} to make space.")
            return

        if url in self.playlist_urls.values():
            await interaction.response.send_message("Song already in playlist. Wait for it to play before adding it again", ephemeral=True)
            return

        domain = urlparse(url).netloc
        if domain != "www.youtube.com" and domain != "youtu.be":
            await interaction.response.send_message("Not a YouTube link", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        loop = asyncio.get_event_loop()
        # this is blocking, so run it in a separate thread
        title, author, video_id = await loop.run_in_executor(None, self.download_song, url)
        info = (title, author)

        self.playlist_urls.update({info: url})
        audio_filepath = f"./local_storage/temp_music/{video_id}.mp3"

        if bump:
            self.playlist = {info: audio_filepath} | self.playlist
        else:
            self.playlist.update({info: audio_filepath})

        await interaction.followup.send("Added to playlist", ephemeral=True)

    # @app_commands.command(name="playlist", description=global_utils.command_descriptions["playlist"])
    async def show_songs(self, interaction: discord.Interaction) -> None:
        """[command] Display the current song as well as the songs in the playlist

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if self.vc is None:
            await interaction.response.send_message("I am not in a voice channel", ephemeral=True)
            return

        if interaction.user == self.owner:
            self.update_activity()

        await interaction.response.defer(ephemeral=True)
        playlist = ""
        for i, info in enumerate(self.playlist, start=1):
            title = info[0]
            author = info[1]
            playlist += f"{i}. {global_utils.style_text(title, 'b')} - {global_utils.style_text(author, 'i')}\n"

        current_str = global_utils.style_text("None", 'b')
        if self.current_song is not None:
            current_title = self.current_song["info"][0]
            current_author = self.current_song["info"][1]

            current_str = f"{global_utils.style_text(current_title, 'b')} - {global_utils.style_text(current_author, 'i')}"

        playlist = f"Currently playing: {current_str}\n\nNext up:\n{playlist if playlist != '' else global_utils.style_text('Playlist Empty', 'i')}"

        await interaction.followup.send(playlist, ephemeral=True)

    async def play(self, interaction: discord.Interaction) -> None:
        """Begins/resumes playback of current song (or next song if current is None)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if self.vc is None:
            return

        if interaction.user != self.owner:
            return

        self.update_activity()

        if self.vc.is_playing():
            return

        if self.vc.is_paused():
            self.vc.resume()
            return

        title, author = self.play_next_song()

        if title is None:
            # await interaction.followup.send(f"Playlist is empty. Use {global_utils.style_text('/add-song', 'c')} to add songs", ephemeral=True)
            return

    async def pause(self, interaction: discord.Interaction) -> None:
        """[command] Pauses playback of current song

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if self.vc is None:
            await interaction.response.send_message("I am not in a voice channel", ephemeral=True)
            return

        if interaction.user != self.owner:
            await interaction.response.send_message("You must be the one who added me to the voice channel to use this command", ephemeral=True)
            return

        self.update_activity()

        if not self.vc.is_playing():
            await interaction.response.send_message("I am not playing audio", ephemeral=True)
            return

        self.vc.pause()
        await interaction.response.send_message("Paused audio", ephemeral=True)

    # deprecated, just use /play-song to resume
    # @app_commands.command(name="resume-song", description=global_utils.command_descriptions["resume-song"])
    # async def resume(self, interaction: discord.Interaction) -> None:
    #     """[command] Resumes playback of current song

    #     Parameters
    #     ----------
    #     interaction : discord.Interaction
    #         The interaction object that initiated the command
    #     """
    #     if self.vc is None:
    #         await interaction.response.send_message("I am not in a voice channel", ephemeral=True)
    #         return

    #     if interaction.user != self.owner:
    #         await interaction.response.send_message("You must be the one who added me to the voice channel to use this command", ephemeral=True)
    #         return

    #     self.update_activity()

    #     if not self.vc.is_paused():
    #         await interaction.response.send_message("I am not paused", ephemeral=True)
    #         return

    #     self.vc.resume()
    #     await interaction.response.send_message("Resumed audio", ephemeral=True)

    async def stop(self, interaction: discord.Interaction) -> None:
        """[command] Stops playback of current song (cannot resume)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if self.vc is None:
            await interaction.response.send_message("I am not in a voice channel", ephemeral=True)
            return

        if interaction.user != self.owner:
            await interaction.response.send_message("You must be the one who added me to the voice channel to use this command", ephemeral=True)
            return

        self.update_activity()

        if not self.vc.is_playing() and not self.vc.is_paused():
            await interaction.response.send_message("I am not playing audio", ephemeral=True)
            return

        self.vc.stop()
        await interaction.response.send_message("Stopped audio", ephemeral=True)

    async def skip(self, interaction: discord.Interaction) -> None:
        """[command] Skips current song and play next song in playlist (if any)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if self.vc is None:
            await interaction.response.send_message("I am not in a voice channel", ephemeral=True)
            return

        if interaction.user != self.owner:
            await interaction.response.send_message("You must be the one who added me to the voice channel to use this command", ephemeral=True)
            return

        self.update_activity()

        if self.vc.is_playing() or self.vc.is_paused():
            self.vc.stop()

        title, author = self.play_next_song()
        message = "Skipped audio.\n"

        if title is None:
            message += "No more audio to play"
        else:
            message += f"Now playing: {title} - {author}"

        await interaction.response.send_message(message, ephemeral=True)

    def play_next_song(self, error: Exception = None) -> str:
        """Plays the next song in the playlist if there is one

        Parameters
        ----------
        error : Exception
            The error that occurred while playing audio, if any

        Returns
        -------
        str
            The playlist info of the song that was played
        """
        # shouldn't be neccessary, since timeout checks for is_playing, but just in case
        self.update_activity(error)
        if self.current_song is not None:
            audio_filepath = self.current_song["audio_filepath"]
            audio = self.current_song["audio"]
            audio.cleanup()

            if self.loop_song:
                if not self.vc.is_playing() and not self.vc.is_paused():
                    info = self.current_song["info"]

                    audio = discord.FFmpegPCMAudio(source=audio_filepath)

                    self.vc.play(audio, after=self.play_next_song)

                    return info
            else:
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, self.delete_song, audio_filepath)

                self.current_song = None

        if len(self.playlist) == 0:
            self.buttons.hit_pause()
            return None, None

        info = next(iter(self.playlist))

        audio_filepath = self.playlist.pop(info)
        audio = discord.FFmpegPCMAudio(source=audio_filepath, stderr=open(
            "./local_storage/debug_log.txt", "w"))
        url = self.playlist_urls.pop(info)

        self.current_song = {"info": info, "audio": audio,
                             "audio_filepath": audio_filepath, "url": url}

        self.vc.play(audio, after=self.play_next_song)

        return info

    async def loop(self, interaction: discord.Interaction) -> None:
        """[command] Toggles looping of the current song

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        if self.vc is None:
            await interaction.response.send_message("I am not in a voice channel", ephemeral=True)
            return

        if interaction.user != self.owner:
            await interaction.response.send_message("You must be the one who added me to the voice channel to use this command", ephemeral=True)
            return

        self.update_activity()

        self.loop_song = not self.loop_song
        message = "Looping" + (" enabled" if self.loop_song else " disabled")
        await interaction.response.send_message(message, ephemeral=True)

    # I don't know the performance impact of this, but it's the only way I can think of to check for inactivity
    @tasks.loop(seconds=5)
    async def timed_checks(self) -> None:
        """[task] Checks for inactivity and leaves the voice channel if inactive
        """
        if self.vc.is_playing() or self.downloading or self.vc is None:
            return

        if (datetime.now() - self.last_activity).seconds >= self.inactivity_timeout_seconds:
            await self.reset_state()

    async def reset_state(self) -> None:
        """Resets the state of the MusicCommands cog (disconnects from voice channel, clears owner, and clears last activity)
        """
        if self.vc is not None:
            await self.vc.disconnect()

        if self.current_song is not None:
            audio = self.current_song["audio"]
            audio.cleanup()

        loop = asyncio.get_event_loop()
        for file in os.listdir("./local_storage/temp_music"):
            loop.run_in_executor(None, self.delete_song,
                                 f"./local_storage/temp_music/{file}")

        self.vc = None
        self.owner = None
        self.last_activity = None
        self.loop_song = False
        self.current_song = None
        self.playlist = {}
        self.playlist_urls = {}

        await self.buttons.disable()
        self.buttons.stop()
        self.buttons = MusicButtons(music_cog=self)


    def update_activity(self, error: Exception = None) -> None:
        """Updates the last activity time of the bot to prevent inactivity timeout

        Parameters
        ----------
        error : Exception
            The error that occurred, if any
        """
        self.last_activity = datetime.now()


class MusicButtons(discord.ui.View):
    def __init__(self, *, timeout: float | None = None, music_cog: MusicCommands) -> None:
        """Initializes the MusicButtons class

        Parameters
        ----------
        timeout : float | None, optional
            The number of seconds to listen for an interaction before timing out, by default None (no timeout)
        music_cog : MusicCommands
            The MusicCommands cog that drives the button functionality
        """
        super().__init__(timeout=timeout)
        self.cog = music_cog
        self.bot = music_cog.bot

    # @discord.ui.button(label="Join Voice", style=discord.ButtonStyle.primary, custom_id="join_voice", emoji="🔊")
    # async def join_voice(self, interaction: discord.Interaction, button: discord.ui.Button,) -> None:
    #     """[button] Joins the user's voice channel

    #     Parameters
    #     ----------
    #     button : discord.ui.Button
    #         The button that was clicked
    #     interaction : discord.Interaction
    #         The interaction object that initiated the command
    #     """
    #     await self.cog.join(interaction)

    # @discord.ui.button(label="Leave Voice", style=discord.ButtonStyle.danger, custom_id="leave_voice", emoji="🔈")
    # async def leave_voice(self, interaction: discord.Interaction, button: discord.ui.Button,) -> None:
    #     """[button] Leaves the user's voice channel

    #     Parameters
    #     ----------
    #     button : discord.ui.Button
    #         The button that was clicked
    #     interaction : discord.Interaction
    #         The interaction object that initiated the command
    #     """
    #     await self.cog.leave(interaction)
    
    async def disable(self) -> None:
        """Disables all buttons
        """
        for child in self.children:
            child.disabled = True
        
        await self.message.edit_original_response(content="Music Player closed", view=self)

    async def generate_embed(self) -> discord.Embed:
        """Generates an embed for the current song

        Returns
        -------
        discord.Embed
            The embed for the current song
        """
        yt_dlp_opts = {
            "playlist_items": "0"
        }
        url = self.cog.current_song["url"]

        with yt_dlp.YoutubeDL({}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info['title'][:150] + "..." if len(info['title']) > 150 else info['title']
            if title.endswith("..."):
                title += " (Read more)"
            desc = info['description'].split("\n")[0]
            desc = desc[:253] + "..." if len(desc) > 256 else desc
            if desc == "":
                desc = "No description"
            elif len(desc) < len(info["description"]) + 1:
                desc += f" [Read more]({url})"
            url = info['webpage_url']
            author = info['uploader']
            author_url = info['uploader_url']
            img_url = info['thumbnail']
            views = info['view_count']
            likes = info['like_count']
            duration = info['duration']
            timestamp = datetime.strptime(info['upload_date'], "%Y%m%d")
        
        with yt_dlp.YoutubeDL(yt_dlp_opts) as ydl:
            info = ydl.extract_info(author_url)
            author_pfp = info['thumbnails'][-1]['url']

        color = discord.Color.red()
        footer_text = f"Added by {self.cog.owner.display_name}"
        footer_url = self.cog.owner.avatar.url

        desc = desc[:101] + "..." if len(desc) > 101 else desc
            
        embed = discord.Embed(title=title, description=desc, url=url,
                                timestamp=datetime.now(), color=color)
        (
            embed.set_author(name=author, url=author_url, icon_url=author_pfp)
            .set_image(url=img_url)
            .add_field(name="Duration", value=str(timedelta(seconds=duration)), inline=True)
            .add_field(name="Uploaded", value=timestamp.strftime("%B %d, %Y"), inline=True)
            .add_field(name="Views", value=f"{views:,}", inline=True)
            .add_field(name="Likes", value=f"{likes:,}", inline=True)
            .set_footer(text=footer_text, icon_url=footer_url)
        )

        return embed
    
    @discord.ui.button(label="Play/Resume", style=discord.ButtonStyle.secondary, custom_id="play_song", emoji="▶️")
    async def play_song(self, interaction: discord.Interaction, button: discord.ui.Button,) -> None:
        """[button] Plays or resumes the current song

        Parameters
        ----------
        button : discord.ui.Button
            The button that was clicked
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await interaction.response.defer(ephemeral=True)
        await self.cog.play(interaction)
        await self.hit_play()
        await interaction.followup.send("Playing audio", ephemeral=True, delete_after=3)

    async def hit_play(self) -> None:
        """Toggles all buttons that need to be toggled when the play button is clicked, and then updates the view
        """
        play_button = self.children[0]
        pause_button = self.children[1]
        stop_button = self.children[2]
        skip_button = self.children[3]

        play_button.disabled = True
        play_button.style = discord.ButtonStyle.success
        pause_button.disabled = False
        pause_button.style = discord.ButtonStyle.secondary
        stop_button.disabled = False
        skip_button.disabled = False

        status = "Resuming" if self.cog.vc.is_paused() else "Playing"
        embed = await self.generate_embed()
        await self.message.edit_original_response(content=status, view=self, embed=embed)

        # await self.message.edit_original_response(content=status, view=self)   

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary, custom_id="pause_song", emoji="⏸️", disabled=True)
    async def pause_song(self, interaction: discord.Interaction, button: discord.ui.Button,) -> None:
        """[button] Pauses the current song

        Parameters
        ----------
        button : discord.ui.Button
            The button that was clicked
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await self.cog.pause(interaction)
        await self.hit_pause()
    
    async def hit_pause(self):
        """Toggles all buttons that need to be toggled when the pause button is clicked
        """
        play_button = self.children[0]
        pause_button = self.children[1]

        play_button.disabled = False
        play_button.style = discord.ButtonStyle.secondary
        pause_button.disabled = True
        pause_button.style = discord.ButtonStyle.success

        await self.message.edit_original_response(view=self)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, custom_id="stop_song", emoji="⏹️", disabled=True)
    async def stop_song(self, interaction: discord.Interaction, button: discord.ui.Button,) -> None:
        """[button] Stops the current song

        Parameters
        ----------
        button : discord.ui.Button
            The button that was clicked
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await self.cog.stop(interaction)
        self.hit_pause()

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, custom_id="skip_song", emoji="⏭️", disabled=True)
    async def skip_song(self, interaction: discord.Interaction, button: discord.ui.Button,) -> None:
        """[button] Skips the current song

        Parameters
        ----------
        button : discord.ui.Button
            The button that was clicked
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await self.cog.skip(interaction)
        await self.hit_play()
    
    @discord.ui.button(label="Loop Song", style=discord.ButtonStyle.secondary, custom_id="loop_song", emoji="🔁")
    async def loop_song(self, interaction: discord.Interaction, button: discord.ui.Button,) -> None:
        """[button] Toggles looping of the current song

        Parameters
        ----------
        button : discord.ui.Button
            The button that was clicked
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await self.cog.loop(interaction)
        loop_button = self.children[4]
        loop_button.style = discord.ButtonStyle.success if loop_button.style == discord.ButtonStyle.secondary else discord.ButtonStyle.secondary
        await self.message.edit_original_response(view=self)
                             
    @discord.ui.button(label="Playlist", style=discord.ButtonStyle.primary, custom_id="playlist", emoji="💿")
    async def show_songs(self, interaction: discord.Interaction, button: discord.ui.Button,) -> None:
        """[button] Displays the current playlist

        Parameters
        ----------
        button : discord.ui.Button
            The button that was clicked
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        await self.cog.show_songs(interaction)


async def setup(bot: commands.Bot) -> None:
    """Adds the MusicCommands cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.Bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(MusicCommands(bot), guilds=[discord.Object(
        global_utils.debug_server_id), discord.Object(global_utils.val_server_id)])
