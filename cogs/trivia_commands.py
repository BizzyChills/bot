import discord
from discord import app_commands
from discord.ext import commands

from random import sample, randint

from asyncio import sleep, TimeoutError

from global_utils import global_utils


class TriviaCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the TriviaCommands cog and creates/stores the trivia questions

        Parameters
        ----------
        bot : discord.ext.commands.Bot
            The bot to add the cog to. Automatically passed with the bot.load_extension method
        """
        self.bot = bot

        self.trivia_questions = self.get_questions()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """[event] Executes when the TriviaCommands cog is ready
        """
        # global_utils.log("Trivia cog loaded")
        pass

    def get_questions(self) -> dict:
        """Sets up the trivia questions for the trivia game

        Returns
        -------
        dict
            a dictionary of trivia questions and answers grouped as lists by easy/medium/hard with the following structure: {difficulty: [{question: answer}, ...]}
        """
        questions = {
            "easy": [
                {
                    "question": "How many agents are currently (05/25/24) in Valorant? (hint: some are hidden)",
                    "answer": "25"
                },
                {
                    "question": "How many multiplayer maps are currently (05/25/24) in Valorant?",
                    "answer": "14"
                },
                {
                    "question": 'What nationality is the agent "Gekko"?',
                    "answer": "American"
                },
                {
                    "question": 'What agent has the ability "Curveball"?',
                    "answer": "Phoenix"
                },
                {
                    "question": "What is Bizzy's cat's name?",
                    "answer": "Luna"
                },
            ],
            "medium": [
                {
                    "question": 'What is the internal codename for the agent "Killjoy"?',
                    "answer": "Killjoy"
                },
                {
                    "question": 'What is the internal codename for Raze\'s ability "Paint Shells"?',
                    "answer": "Default__Clay_4_ClusterGrenade_Gungame_DataAsset_C"
                },
                {
                    "question": "What is the internal codename for the tutorial?",
                    "answer": "Onboarding"
                },
                {
                    "question": "How many ceremonies are there in Valorant?",
                    "answer": "6"
                },
            ],
            "hard": [
                {
                    "question": "What is Bizzy's favorite 2D effect, notably implemented in his Flappy Bird clone? (hint: It gets Bizzy very excited and is related to background elements)",
                    "answer": "Parallax"
                },
                {
                    "question": "What month and year did Bizzy first meet Sam, Fiona, and Dylan (answer in mm/yyyy format)?",
                    "answer": "02/2023"
                },
                {
                    "question": 'What map started "The Adventures of Sam and Bizzy"?',
                    "answer": "Ascent"
                },
                {
                    "question": "What is the food known to give Bizzy a buff?",
                    "answer": "chicken alfredo"
                },
                {
                    "question": "How many non-multiplayer maps are there in Valorant (hint: some are hidden)?",
                    "answer": "2"
                },
            ]
        }

        return questions

    async def delayed_gratification(self, user: discord.User) -> None:
        """[command] Sends the prize message to the user after 5 minutes while taunting them with messages every minute until then

        Parameters
        ----------
        user : discord.User
            The user who has completed the trivia game
        """

        taunts = [
            "Are you mad at me? Good.",
            "You went through all of that just for a pat on the back. How does that make you feel?",
            "You know, I kind of feel bad for you. Just kidding, I don't.",
            "Actually, now I do kind of feel bad for you. I apologize for my rudeness. Give me a minute to think about what I've done and I'll make it up to you."
        ]

        for taunt in taunts:
            await sleep(60)
            await user.send(taunt)

        await user.send("Alright, I thought hard about my actions and I've decided to give you an actual prize. Here it is: \*gives you a pat on the back\* Congratulations!")

        await sleep(5)
        await user.send(f"Just kidding. Here is your actual prize, no foolin: {global_utils.style_text('https://cs.indstate.edu/~cs60901/final/', 'c')}")

    async def clear_dm(self, user: discord.User) -> None:
        """Clears all bot messages in the user's DMs

        Parameters
        ----------
        user : discord.User
            The user to clear the DMs with
        """
        if user.dm_channel is None:
            await user.create_dm()

        async for message in user.dm_channel.history(limit=None):
            if message.author == self.bot.user:
                await message.delete(delay=5)

    async def trivia(self, user: discord.User) -> None:
        """[command] Plays a game of trivia with the user

        Parameters
        ----------
        user : discord.User
            The user to play trivia with
        """

        await user.send((f"Welcome to trivia! You will have {global_utils.style_text('10 seconds', 'c')} to answer each question.\n\n"
                         "Since I'm nice, I'll let you know that almost every answer can be found in the server (or with a simple Google search). Good luck!"
                         ))

        await sleep(10)  # give the user time to read the message

        questions = self.trivia_questions["easy"] + \
            self.trivia_questions["medium"] + self.trivia_questions["hard"]

        if randint(1, 4) == 3:  # The prize for trivia is my name. 25% chance to troll the user by asking them my name lmao
            questions.append({
                "question": "What is Bizzy's name?",
                "answer": "Isaiah"
            })

        questions = sample(questions, len(questions))  # shuffle the questions

        for i in range(len(questions)):
            question_header = global_utils.style_text(
                f"Question {i + 1}:\n", 'b')
            question_body = global_utils.style_text(
                questions[i]['question'], 'i')
            await user.send(f"{question_header}{question_body}")
            try:
                answer = await self.bot.wait_for("message", check=lambda m: m.author == user, timeout=10)
            except TimeoutError as e:
                await user.send("You took too long to answer. Go back to the server and use /trivia to try again")
                return await self.clear_dm(user)

            if answer.content.lower() == questions[i]['answer'].lower():
                await user.send("Correct!")
            else:
                if questions[i]["question"] == "What is Bizzy's name?":
                    await user.send("Awwww, you tried. Go back to the server and use /trivia to try again")
                else:
                    await user.send(f"Incorrect. Go back to the server and use {global_utils.style_text('/trivia', 'c')} to try again (yes this is intentionally tedious)")

                return await self.clear_dm(user)

        await user.send(f"Congratulations, you win! Here is your prize: \*{global_utils.style_text('gives you a pat on the back', 'i')}\*")

        await self.delayed_gratification(user)

    @app_commands.command(name="trivia", description=global_utils.command_descriptions["trivia"])
    async def trivia_help(self, interaction: discord.Interaction) -> None:
        """[command] Starts a game of trivia with the user (in their DMs)

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        user = interaction.user
        await interaction.response.send_message("Please open the DM with the bot to play trivia. It may take a few minutes to start.", ephemeral=True)
        # give the user time to read the message and move to the DMs
        await sleep(2)
        await self.trivia(user)


async def setup(bot: commands.bot) -> None:
    """Adds the TriviaCommands cog to the bot

    Parameters
    ----------
    bot : discord.ext.commands.bot
        The bot to add the cog to. Automatically passed with the bot.load_extension method
    """
    await bot.add_cog(TriviaCommands(bot), guilds=[discord.Object(global_utils.val_server_id), discord.Object(global_utils.debug_server_id)])
