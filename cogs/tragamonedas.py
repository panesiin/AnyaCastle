import random
import json
import asyncio
from pathlib import Path
from typing import List, Optional

import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import time, timedelta, timezone

JSON_PATH = Path(__file__).with_name("slot_combinations_extended.json")

OPCIONES = ["nut", "apple", "cake", "heart", "dog"]
COLOR_PASTEL = 0xFADADD
ROL_ESTRELLA = "⭐StellaStars⭐"

# Zona horaria México Central (CDT UTC-5)
CDT = timezone(timedelta(hours=-5))

class SlotGIFView(discord.ui.View):
    def __init__(self, cog: 'SlotGIFCog', ctx: commands.Context):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.message: Optional[discord.Message] = None

        tiros_restantes = 3 - self.cog.usuarios_giros.get(ctx.author.id, 0)
        self.pull_button.disabled = tiros_restantes <= 0
        self.pull_button.label = f"Tirar ({tiros_restantes})" if tiros_restantes > 0 else "Tiros agotados"

    @discord.ui.button(label="Tirar (3)", style=discord.ButtonStyle.green, custom_id="slot_gif_pull")
    async def pull_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Solo quien usó el comando puede activar la palanca.", ephemeral=True)
            return

        user_id = interaction.user.id
        giros = self.cog.usuarios_giros.get(user_id, 0)
        if giros >= 3:
            await interaction.response.send_message("⚠️ Ya usaste tus 3 giros de hoy. Intenta mañana.", ephemeral=True)
            return

        button.disabled = True
        await interaction.response.edit_message(view=self)

        if self.cog.combinacion_forzada:
            resultado = self.cog.combinacion_forzada
            self.cog.combinacion_forzada = None
        else:
            resultado = self.cog.elegir_combinacion_ponderada()

        entry = self.cog.get_entry_by_resultado(resultado)
        if not entry:
            await interaction.response.send_message("❌ No se encontró una entrada para esta combinación.", ephemeral=True)
            return

        gif_url = entry["url"]
        final_url = entry["endframe"]

        embed = discord.Embed(color=COLOR_PASTEL)
        embed.title = "🎲 Girando, Girando... 🎰"
        embed.set_image(url=gif_url)
        embed.set_footer(text="Vamos vamos vamos... 🤞🏼")
        await interaction.edit_original_response(embed=embed, view=self)

        await asyncio.sleep(5)

        gano = self.cog.es_ganadora(resultado)

        if gano:
            embed.title = "🏆 ¡HAS GANADO! 🏆"
            embed.set_footer(text=f"¡Bienvenido Agente, {interaction.user.display_name}!")
            rol = discord.utils.get(interaction.guild.roles, name=ROL_ESTRELLA)
            if rol and rol not in interaction.user.roles:
                try:
                    await interaction.user.add_roles(rol)
                    await interaction.channel.send(f"> 🌟 {interaction.user.mention} ahora formas parte de los **{ROL_ESTRELLA}** super secreto.")
                except discord.Forbidden:
                    await interaction.channel.send(f"> ⚠️ No tengo permisos para asignar el rol {ROL_ESTRELLA}.")
        else:
            embed.title = "😣 ¡HAS PERDIDO! 😣"
            embed.description = "Oh no, más suerte la próxima"
            embed.set_footer(text=f"Reinicios de tiros a las 12am Mx / 12am Pe")

        embed.set_image(url=final_url)
        await interaction.edit_original_response(embed=embed, view=self)

        giros += 1
        self.cog.usuarios_giros[user_id] = giros

        tiros_restantes = 3 - giros
        if tiros_restantes > 0:
            button.disabled = False
            button.label = f"Tirar ({tiros_restantes})"
        else:
            button.disabled = True
            button.label = "Tiros agotados"

        await interaction.edit_original_response(view=self)


class SlotGIFCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.combinations: List[dict] = []
        self.combinacion_forzada: Optional[List[str]] = None
        self.probabilidad_ganar = 0.20
        self.usuarios_giros = {}
        self.reset_giros_tarea.start()

    async def cog_load(self):
        if JSON_PATH.exists():
            with open(JSON_PATH, encoding='utf-8') as f:
                self.combinations = json.load(f)
        else:
            self.combinations = []

    def get_entry_by_resultado(self, resultado: List[str]) -> Optional[dict]:
        for entry in self.combinations:
            if entry.get("resultado") == resultado:
                return entry
        return None

    def es_ganadora(self, resultado: List[str]) -> bool:
        return len(set(resultado)) == 1

    def elegir_combinacion_ponderada(self) -> List[str]:
        pool = []
        peso_ganadoras = round((self.probabilidad_ganar * len(self.combinations)) / 5)
        for entry in self.combinations:
            resultado = entry.get("resultado")
            if len(set(resultado)) == 1:
                pool.extend([resultado] * peso_ganadoras)
            else:
                pool.append(resultado)
        return random.choice(pool)

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=CDT))
    async def reset_giros_tarea(self):
        self.usuarios_giros.clear()

    @reset_giros_tarea.before_loop
    async def before_reset_giros_tarea(self):
        await self.bot.wait_until_ready()

    @commands.command(name="slot", help="Forza la siguiente combinación. Uso: !slot nut_nut_nut")
    async def slots_force(self, ctx: commands.Context, combinacion: str):
        if await self.bot.is_owner(ctx.author) is False:
            await ctx.send("> ❌ Este comando solo puede ser usado por el dueño del bot.")
            return

        partes = combinacion.lower().split('_')
        if len(partes) != 3 or not all(p in OPCIONES for p in partes):
            await ctx.send("> ❌ Formato inválido. Usa: !slot nut_nut_nut con opciones válidas.")
            return

        self.combinacion_forzada = partes
        await ctx.send(f"> ✅ Combinación forzada para el próximo uso: `{'_'.join(partes)}`")

    @commands.command(name="slots", help="Inicia tragamonedas visual con botón")
    async def slotsgif(self, ctx: commands.Context):
        try:
            view = SlotGIFView(self, ctx)
            embed = discord.Embed(color=COLOR_PASTEL)
            embed.title = "Tira del botón para empezar. 🎲"
            embed.set_image(url="https://media.discordapp.net/attachments/1386799627923357766/1389148493037310072/Spy_23.png?ex=68658b19&is=68643999&hm=1d28e4819b1dd098cc4d23fd15064f5f90a28d7b7757e5569249289b33d4e19f&=&format=webp&quality=lossless")
            embed.set_footer(text="Reinicios de tiros a las 12am Mx / 12am Pe")
            view.message = await ctx.send(embed=embed, view=view)
        except commands.MissingPermissions:
            await ctx.send("> ❌ No tienes permiso para usar este comando.")

    @slotsgif.error
    async def slotsgif_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("> ❌ No tienes permiso para usar este comando.")

    @commands.command(name="set_chance", help="Establece la probabilidad de ganar (solo dueño). Uso: !set_chance 0.25")
    async def set_chance(self, ctx: commands.Context, valor: float):
        if await self.bot.is_owner(ctx.author) is False:
            await ctx.send("❌ Solo el dueño del bot puede usar este comando.")
            return

        if not (0 <= valor <= 1):
            await ctx.send("❌ Ingresa un valor entre 0.0 y 1.0 (ej: 0.25 para 25%).")
            return

        self.probabilidad_ganar = valor
        await ctx.send(f"✅ Probabilidad de ganar actualizada a: {valor:.2%}")
            

    @app_commands.command(name="slot_reset", description="Resetea los giros usados por un usuario o todos")
    @app_commands.describe(usuario="Usuario para resetear giros, si no se especifica, resetea todos")
    async def slash_slot_reset(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        es_dueno = await self.bot.is_owner(interaction.user)
        if not es_dueno:
            await interaction.response.send_message("❌ Este comando solo puede usarlo el dueño del bot.", ephemeral=True)
            return

        if usuario:
            self.usuarios_giros.pop(usuario.id, None)
            await interaction.response.send_message(f"🔄 Giros reseteados para {usuario.mention}.", ephemeral=True)
        else:
            self.usuarios_giros.clear()
            await interaction.response.send_message("🔄 Giros reseteados para todos los usuarios.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SlotGIFCog(bot))
