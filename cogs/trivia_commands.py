import discord
from discord import app_commands
from discord.ext import commands

from random import sample, randint

from asyncio import sleep, TimeoutError

from global_utils import global_utils

class TriviaCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.trivia_questions = self.setup_trivia()

    @commands.Cog.listener()
    async def on_ready(self):
        # print("Trivia cog loaded")
        pass

    def setup_trivia(self) -> dict:
        """Sets up the trivia questions for the trivia game

        Returns
        -------
        dict
            a dictionary of trivia questions and answers grouped as lists by easy/medium/hard with the following structure: {difficulty: [{question: answer}, ...]}
        """
        questions ={
            "easy":[
                {
                    "question": "How many agents are currently (05/25/24) in Valorant?",
                    "answer": "24"
                },
                {
                    "question": "How many multiplayer maps are currently (05/25/24) in Valorant?",
                    "answer": "14"
                },
                {
                    "question": "What nationality is the agent Gekko?",
                    "answer": "American"
                },
                {
                    "question": 'What agent has the ability "Curveball"?',
                    "answer": "Phoenix"
                },
                {
                    "question": "What is Bizzy's cat's name (hint: latin name for a celestial body, sun and moon, sol and ___)?",
                    "answer": "Luna"
                },
            ],
            "medium":[
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
            "hard":[
                {
                    "question": "What is Bizzy's favourite 2D effect, notably implemented in his Flappy Bird clone? (hint: It gets Bizzy very excited and is related to background elements)",
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
                    "question": "What is the food known to give Bizzy a buff (Bizzy's girlfriend usually brings this)?",
                    "answer": "chicken alfredo"
                },
                {
                    "question": "How many TOTAL maps are there in Valorant (hint: some are hidden)?",
                    "answer": "16"
                },
            ]
        }


        return questions
    
    async def clear_dm(self, user: discord.User):
        """Clears the DMs between the bot and the user

        Parameters
        ----------
        user : discord.User
            The user to clear the DMs with
        """
        if user.dm_channel is None:
            await user.create_dm()

        async for message in user.dm_channel.history(limit=None):
            if message.author == self.bot.user:
                await message.delete()
    async def trivia(self, user: discord.User):
        """[command] Plays a game of trivia with the user

        Parameters
        ----------
        message : discord.Message
            The message object that was sent
        """
        await user.send("Welcome to trivia! Please answer the following questions to the best of your ability.\nYou have 10 seconds to answer each question. Good luck!")

        await sleep(3) # give the user time to read the message

        questions = self.trivia_questions["easy"] + self.trivia_questions["medium"] + self.trivia_questions["hard"]
        
        if randint(0,4) == 3:
            questions.append({
                "question": "What is Bizzy's name?",
                "answer": "Isaiah"
            })
        
        questions = sample(questions, len(questions)) # shuffle the questions

            

        for i in range(len(questions)):
            await user.send(global_utils.bold(f'Question {i + 1}') + f":\n{questions[i]['question']}")
            try:
                answer = await self.bot.wait_for("message", check=lambda m: m.author == user, timeout=10)
            except TimeoutError as e:
                await user.send("You took too long to answer. Go back to the server and use /trivia to try again")
                return

            if answer.content.lower() == questions[i]['answer'].lower():
                await user.send("Correct!")
            else:
                if questions[i]["question"] == "What is Bizzy's name?":
                    await user.send("Awwww, you tried. Go back to the server and use /trivia to try again")
                else:
                    await user.send(f"Incorrect. Go back to the server and use {global_utils.inline_code('/trivia')} to try again (yes this is intentionally tedious)")
                
                sleep(3)
                await self.clear_dm(user)
                return
        
        await user.send(f"Congratulations! You have completed the trivia game. Here is your prize: {global_utils.inline_code('a pat on the back')}. Good job!")

        await sleep(60 * 5) # troll the user by making them wait a minute before they recieve the actual prize

        await user.send(f"Just kidding. Here is your prize: {global_utils.inline_code('https://cs.indstate.edu/~cs60901/final/')}")
        
    @app_commands.command(name="trivia", description=global_utils.command_descriptions["trivia"])
    async def trivia_help(self, interaction: discord.Interaction):
        """[command] Simply imforms the user to use the text command !trivia so that the Context object can be used to message multiple times

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object that initiated the command
        """
        user = interaction.user
        await interaction.response.send_message("Please open the DM with the bot to play trivia. It may take a few minutes to start.", ephemeral=True)
        await self.trivia(user)



async def setup(bot):
    await bot.add_cog(TriviaCommands(bot), guilds=[discord.Object(global_utils.val_server), discord.Object(global_utils.debug_server)])
