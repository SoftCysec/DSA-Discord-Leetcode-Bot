import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import requests
import random

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!problem'
LT_API_URL = 'https://leetcode.com/api/problems/all/'
PROBLEM_URL_BASE = 'https://leetcode.com/problems/'

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

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


@bot.command(name='random')
async def random_problem(ctx, type: str = '', difficulty: str = ''):
    """Get a random problem. Optional arguments: free, paid, easy, medium, hard."""
    problems = all_problems
    if type.lower() == 'free':
        problems = free_problems
    elif type.lower() == 'paid':
        problems = paid_problems

    if difficulty:
        problems = [problem for problem in problems if problem.difficulty.lower() == difficulty.lower()]

    if not problems:
        await ctx.send(f"No problems found with given criteria.")
        return

    selected_problem = random.choice(problems)
    await ctx.send(f"**{selected_problem.title}**\nDifficulty: {selected_problem.difficulty}\n{selected_problem.url}")


@bot.command()
async def info(ctx):
    """Display information about the number of problems."""
    await ctx.send(f"LeetCode has {len(all_problems)} problems. {len(free_problems)} are free, {len(paid_problems)} are paid.")


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    fetch_problems_from_api()


bot.run(TOKEN)
