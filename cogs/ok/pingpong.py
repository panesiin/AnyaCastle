import time
import asyncio
import random
import discord
from discord import app_commands
from discord.ext import commands

class General(commands.Cog):
    """Comandos generales y utilidades rápidas"""

    GLOBAL_COOLDOWN = 30

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns: dict[str, float] = {}  # «usuario_comando» : timestamp_fin

    def _on_cooldown(self, key: str) -> bool:
        """Devuelve True si la key sigue en cooldown"""
        return self.cooldowns.get(key, 0) > time.time()

    def _set_cooldown(self, key: str, seconds: int):
        self.cooldowns[key] = time.time() + seconds

    # --------------------------------------------------------------
    # /ping
    # --------------------------------------------------------------
    @app_commands.command(name='ping', description='El bot responde con Pong!')
    async def ping(self, interaction: discord.Interaction):
        key = f'ping_{interaction.user.id}'
        if self._on_cooldown(key):
            await interaction.response.send_message('❌ Estás en cooldown, espera un momento.', ephemeral=True)
            return

        await interaction.response.send_message('🏓 Pong!')
        self._set_cooldown(key, self.GLOBAL_COOLDOWN)

    # --------------------------------------------------------------
    #

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
