import os
import requests
import random
import discord
from discord.ext import commands
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!'
LT_API_URL = 'https://leetcode.com/api/problems/all/'
PROBLEM_URL_BASE = 'https://leetcode.com/problems/'

all_problems = []
free_problems = []
paid_problems = []

intents = discord.Intents.all()  # This will enable all intents, including member-related ones
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

class Problem:
    def __init__(self, problem_data):
        self.id = problem_data['stat']['question_id']
        self.title = problem_data['stat']['question__title']
        self.title_slug = problem_data['stat']['question__title_slug']
        self.difficulty = ['Easy', 'Medium', 'Hard'][problem_data['difficulty']['level'] - 1]
        self.paid_only = problem_data['paid_only']
        self.url = PROBLEM_URL_BASE + self.title_slug + '/'

def fetch_problems_from_api():
    global all_problems, free_problems, paid_problems
    response = requests.get(LT_API_URL)
    if response.status_code == 200:
        data = response.json()
        for problem_data in data['stat_status_pairs']:
            problem = Problem(problem_data)
            all_problems.append(problem)
            if not problem.paid_only:
                free_problems.append(problem)
            else:
                paid_problems.append(problem)

@bot.command(name='challenge')
async def fetch_challenge(ctx, payment_type: str = 'free', difficulty: str = 'easy'):
    # Normalize the parameters
    payment_type = payment_type.lower()
    difficulty = difficulty.capitalize()

    # Filter problems based on payment type and difficulty
    problems_to_consider = free_problems if payment_type == 'free' else paid_problems
    problems_of_difficulty = [problem for problem in problems_to_consider if problem.difficulty == difficulty]

    if not problems_of_difficulty:
        await ctx.send(f"No {difficulty} problems available for {payment_type}.")
        return

    selected_problem = random.choice(problems_of_difficulty)

    # Check if the user already has a private channel
    channel_name = f"{ctx.author.name.lower()}-private"
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)

    # If not, create one
    if not channel:
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True)
        }
        channel = await ctx.guild.create_text_channel(channel_name, overwrites=overwrites)

    await channel.send(f"**{selected_problem.title}**\nDifficulty: {selected_problem.difficulty}\n{selected_problem.url}")

@bot.command(name='scheduled_challenge')
async def scheduled_challenge(ctx):
    current_hour = datetime.now().hour

    # Schedule based on hours
    schedule = {
        6: 'Easy',
        12: 'Medium',
        18: 'Hard'
    }

    if current_hour in schedule:
        difficulty = schedule[current_hour]
        problems_of_difficulty = [problem for problem in free_problems if problem.difficulty == difficulty]
        if not problems_of_difficulty:
            await ctx.send(f"No {difficulty} problems available.")
            return

        selected_problem = random.choice(problems_of_difficulty)

        # Find the "code-challenges" channel
        channel = discord.utils.get(ctx.guild.channels, name="code-challenges")
        if not channel:
            await ctx.send("Couldn't find the 'code-challenges' channel.")
            return

        await channel.send(f"**{selected_problem.title}**\nDifficulty: {selected_problem.difficulty}\n{selected_problem.url}")
    else:
        await ctx.send("It's not the scheduled time for a challenge.")

@bot.event
async def on_member_join(member):
    # Create a private channel for the member
    channel_name = f"{member.name.lower()}-private"
    overwrites = {
        member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True)
    }
    await member.guild.create_text_channel(channel_name, overwrites=overwrites)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    fetch_problems_from_api()
    

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while processing your command: {error.original}")
    else:
        await ctx.send(f"An error occurred: {error}")


bot.run(TOKEN)
