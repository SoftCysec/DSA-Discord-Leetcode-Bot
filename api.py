import discord
from discord.ext import commands, tasks
from discord.errors import Forbidden
from dotenv import load_dotenv
import os
import requests
import random
from datetime import datetime

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!problem'
LT_API_URL = 'https://leetcode.com/api/problems/all/'
PROBLEM_URL_BASE = 'https://leetcode.com/problems/'

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

all_problems = []
free_problems = []
paid_problems = []

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
            if problem.paid_only:
                paid_problems.append(problem)
            else:
                free_problems.append(problem)

@tasks.loop(hours=6)
async def post_scheduled_challenge():
    channel = discord.utils.get(bot.get_all_channels(), name='code-challenges')
    if not channel:
        return
    
    current_hour = datetime.utcnow().hour
    if 0 <= current_hour < 6:
        difficulty = 'Easy'
    elif 6 <= current_hour < 12:
        difficulty = 'Medium'
    else:
        difficulty = 'Hard'
    
    problems = [problem for problem in free_problems if problem.difficulty == difficulty]
    if problems:
        selected_problem = random.choice(problems)
        await channel.send(f"**{selected_problem.title}**\nDifficulty: {selected_problem.difficulty}\n{selected_problem.url}")

@bot.command(name='help')
async def help_command(ctx):
    """Displays help information."""
    embed = discord.Embed(title="Coding Challenges DSA Bot Help", description="List of available commands", color=0x00ff00)
    embed.add_field(name="!problem random [type] [difficulty]", value="Fetches a random problem. Type can be 'free' or 'paid'. Difficulty can be 'easy', 'medium', or 'hard'.", inline=False)
    embed.add_field(name="!problem info", value="Displays information about the number of problems on LeetCode.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='challenge')
async def fetch_challenge(ctx, type: str = 'free', difficulty: str = 'easy'):
    """Get a challenge based on user's preference."""
    if type not in ['free', 'paid']:
        await ctx.send("Type must be 'free' or 'paid'.")
        return
    
    if difficulty not in ['easy', 'medium', 'hard']:
        await ctx.send("Difficulty must be 'easy', 'medium', or 'hard'.")
        return
    
    channel_name = f"{ctx.author.name}-challenges"
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    if not channel:
        if not ctx.guild.me.guild_permissions.manage_channels:
            await ctx.send("I don't have permission to create channels. Please grant the 'Manage Channels' permission.")
            return
        channel = await ctx.guild.create_text_channel(channel_name, overwrites=overwrites)
    
    problems = free_problems if type == 'free' else paid_problems
    problems = [problem for problem in problems if problem.difficulty.lower() == difficulty]
    
    if not problems:
        await channel.send(f"No {type} problems found for {difficulty} difficulty.")
        return
    
    selected_problem = random.choice(problems)
    await channel.send(f"**{selected_problem.title}**\nDifficulty: {selected_problem.difficulty}\n{selected_problem.url}")

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    fetch_problems_from_api()
    post_scheduled_challenge.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while processing your command: {error.original}")
    else:
        await ctx.send(f"An error occurred: {error}")

bot.run(TOKEN)
