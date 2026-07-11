import os
import asyncio

import discord
from discord.ext import commands

from config import TOKEN

####################################################
# INTENTS
####################################################

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

####################################################
# BOT
####################################################

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

####################################################
# EVENTOS
####################################################

@bot.event
async def on_ready():

    print("=" * 50)
    print(f"Bot conectado como: {bot.user}")
    print(f"Discord.py {discord.__version__}")
    print("=" * 50)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="la academia secreta 👀"
        )
    )

####################################################
# CARGAR COGS
####################################################

async def load_cogs():

    for filename in os.listdir("./cogs"):

        if filename.endswith(".py"):

            try:

                await bot.load_extension(
                    f"cogs.{filename[:-3]}"
                )

                print(f"✔ {filename}")

            except Exception as e:

                print(f"✖ {filename}")
                print(e)

####################################################
# MAIN
####################################################

async def main():

    async with bot:

        await load_cogs()

        await bot.start(TOKEN)

asyncio.run(main())