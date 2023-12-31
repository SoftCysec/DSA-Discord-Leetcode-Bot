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
LT_API_URL = os.getenv('LT_API_URL')
PROBLEM_URL_BASE = os.getenv('PROBLEM_URL_BASE')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None, reconnect=True)

all_problems = []
free_problems = []
paid_problems = []
user_query_count = {}

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

@tasks.loop(hours=1)
async def post_scheduled_challenge():
    if not bot.guilds:  # Check if the bot is connected to any guilds
        return

    guild = bot.guilds[0]
    channel = discord.utils.get(guild.text_channels, name='code-challenges')
    if not channel:
        if guild.me.guild_permissions.manage_channels:
            channel = await guild.create_text_channel('code-challenges')
        else:
            print("Missing permissions to create the 'code-challenges' channel.")
            return
    
    current_hour = datetime.utcnow().hour
    
    # Check for the 6am window (4am to 8am)
    if 4 <= current_hour <= 8:
        difficulty = 'Easy'
    # Check for the 12pm window (10am to 2pm)
    elif 10 <= current_hour <= 14:
        difficulty = 'Medium'
    # Check for the 6pm window (4pm to 8pm)
    elif 16 <= current_hour <= 20:
        difficulty = 'Hard'
    else:
        return  # Exit the function if it's not within one of the specified windows
    
    problems = [problem for problem in free_problems if problem.difficulty == difficulty]
    if problems:
        selected_problem = random.choice(problems)
        await channel.send(f"**{selected_problem.title}**\nDifficulty: {selected_problem.difficulty}\n{selected_problem.url}")

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="Coding Challenges DSA Bot Help", description="List of available commands", color=0x00ff00)
    embed.add_field(name="!problem challenge [type] [difficulty]", value="Fetches a random problem. Type can be 'free' or 'paid'. Difficulty can be 'easy', 'medium', or 'hard'.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='challenge')
async def fetch_challenge(ctx, type: str = 'free', difficulty: str = 'easy'):
    user_id = ctx.author.id
    if user_id in user_query_count:
        if user_query_count[user_id] >= 3:
            await ctx.send("You've reached the maximum number of challenges for today.")
            return
    else:
        user_query_count[user_id] = 0
    
    if type not in ['free', 'paid']:
        await ctx.send("Type must be 'free' or 'paid'.")
        return
    
    if difficulty not in ['easy', 'medium', 'hard']:
        await ctx.send("Difficulty must be 'easy', 'medium', or 'hard'.")
        return
    
    problems = free_problems if type == 'free' else paid_problems
    problems = [problem for problem in problems if problem.difficulty.lower() == difficulty]
    
    if not problems:
        await ctx.send(f"No {type} problems found for {difficulty} difficulty.")
        return
    
    selected_problem = random.choice(problems)
    
    channel_name = f"{ctx.author.name}-challenges"
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    if not channel:
        if ctx.guild.me.guild_permissions.manage_channels:
            channel = await ctx.guild.create_text_channel(channel_name, overwrites=overwrites)
        else:
            await ctx.send("I don't have permission to create channels. Please grant the 'Manage Channels' permission.")
            return
    
    user_query_count[user_id] += 1
    await channel.send(f"**{selected_problem.title}**\nDifficulty: {selected_problem.difficulty}\n{selected_problem.url}")

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    fetch_problems_from_api()
    post_scheduled_challenge.start()

@bot.event
async def on_member_join(member):
    channel_name = f"{member.name}-challenges"
    if not discord.utils.get(member.guild.text_channels, name=channel_name):
        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True)
        }
        await member.guild.create_text_channel(channel_name, overwrites=overwrites)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while processing your command: {error.original}")
    else:
        await ctx.send(f"An error occurred: {error}")

@bot.event
async def on_resumed():
    print("Bot reconnected.")

bot.run(TOKEN)
