# kick_scrap_notifier.py
"""
Cog de Discord que monitoriza un canal de Kick mediante scraping y envía notificaciones
con un embed estilizado (autor, campos, thumbnail…) cuando el stream se enciende o apaga.

DEPENDENCIAS:
    pip install -U discord.py aiohttp
"""

import json
import aiohttp
import discord
from discord.ext import commands, tasks

# ───── CONFIGURACIÓN BÁSICA ─────
KICK_CHANNEL        = "tablita-play"            # slug del canal en Kick
DISCORD_CHANNEL_ID  = 952419779673735250        # canal de texto en Discord
CHECK_INTERVAL      = 30                        # segundos entre chequeos
DEBUG               = False                      # mensajes por consola
MESSAGE_CONTENT     = "Chavalines ya esta Abi en **Stream por KICK**, gei el último!"  # mensaje opcional
# ─────────────────────────────────

SEARCH_STRING = '"is_live":true'
KICK_ICON     = "https://cdn.kick.com/favicon.ico"
AUTHOR_NAME   = "Anya Castle"
AUTHOR_ICON   = "https://media.discordapp.net/attachments/966755203787407370/1320702855405109268/AnyaXmas.png"
PLACEHOLDER   = "https://via.placeholder.com/320x180.png?text=En+Vivo"

def dbg(msg: str):
    if DEBUG:
        print(f"[KICK DEBUG] {msg}")

class KickNotifier(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.was_live = False
        self.check_kick_status.start()

    def cog_unload(self):
        self.check_kick_status.cancel()

    # ──────────────────────────────
    # LOOP PRINCIPAL
    # ──────────────────────────────
    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_kick_status(self):
        dbg("🔄 Haciendo comprobación…")

        url = f"https://kick.com/api/v2/channels/{KICK_CHANNEL}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        }

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as resp:
                    dbg(f"HTTP STATUS: {resp.status}")
                    if resp.status != 200:
                        return
                    raw = await resp.text()
        except Exception as e:
            dbg(f"❌ Error al hacer la solicitud: {e}")
            return

        is_live = SEARCH_STRING in raw
        dbg(f"is_live = {is_live} | was_live = {self.was_live}")

        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
        if channel is None:
            dbg("❌ No se encontró el canal de Discord.")
            return

        # ——— STREAM ON ———
        if is_live and not self.was_live:
            self.was_live = True
            dbg("✅ ¡El canal ha comenzado en vivo!")

            title, category, thumb_url = self.extract_stream_info(raw)
            embed = self.build_embed_on(title, category, thumb_url)

            await channel.send(content=MESSAGE_CONTENT, embed=embed)

        # ——— STREAM OFF ———
        elif not is_live and self.was_live:
            self.was_live = False
            dbg("⛔ El canal se apagó.")
            await channel.send(embed=self.build_embed_off())

        else:
            dbg(f"➖ Sin cambios. Próxima revisión en {CHECK_INTERVAL}s")

    # ──────────────────────────────
    # UTILIDADES
    # ──────────────────────────────
    def extract_stream_info(self, raw: str):
        """Devuelve título, categoría y thumbnail (valida URL)."""
        try:
            data = json.loads(raw)
            live = data.get("livestream") or {}
            title = live.get("session_title") or "En directo ahora"
            category = (
                live.get("categories", [{}])[0].get("name")
                if live.get("categories") else "Sin categoría"
            )
            thumb = live.get("thumbnail", {}).get("url") or PLACEHOLDER
        except Exception as e:
            dbg(f"⚠️ Error parseando JSON: {e}")
            title, category, thumb = "En directo ahora", "Sin categoría", PLACEHOLDER

        # Asegura tamaño 320×180 si el link soporta placeholders
        thumb = thumb.replace("{width}", "320").replace("{height}", "180")
        return title, category, thumb

    # ──────────────────────────────
    # EMBEDS
    # ──────────────────────────────
    def build_embed_on(self, title: str, category: str, thumb_url: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"🥕{KICK_CHANNEL.upper()} está fumando de la verde en LIVE",
            color=discord.Color.red()
        )
        embed.set_author(name=AUTHOR_NAME, icon_url=AUTHOR_ICON)
        embed.set_thumbnail(url=thumb_url)
        embed.add_field(
            name="Título del Stream",
            value=f"**{title}**\n[Ver ahora en Kick](https://kick.com/{KICK_CHANNEL})",
            inline=True
        )
        embed.add_field(
            name="Categoría",
            value=f"**{category}**",
            inline=True
        )
        embed.set_footer(
            text="Notificación automática por AnyaCastle • Stream Iniciando • KICK",
            icon_url= "https://media.discordapp.net/attachments/966755203787407370/1384110998138654740/feliz1.png?ex=68513d51&is=684febd1&hm=b62b19d72484c1c525d66b21127c10712bed8e6cccb1b204c138b6baff966c5c&=&format=webp&quality=lossless"
        )
        return embed

    def build_embed_off(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🛑 {KICK_CHANNEL.upper()} ha finalizado el stream, gracias por pasarse <:sleep6:1320810569401372744>",
            color=0x9b111e  # rojo más oscuro
        )
        embed.set_author(name=AUTHOR_NAME, icon_url=AUTHOR_ICON)
        embed.set_footer(
            text="Notificación automática por AnyaCastle • Stream Finalizado • KICK",
            icon_url= "https://media.discordapp.net/attachments/966755203787407370/1321130060618666169/sad3.png?ex=6850d9ff&is=684f887f&hm=8cad0167bc5b9a3e87d8f9b2c438bd8d3080849c5f69040d3caab5693898c702&=&format=webp&quality=lossless"
        )
        return embed

    # ──────────────────────────────
    # COMANDO MANUAL
    # ──────────────────────────────
    @commands.command()
    async def kickcheck(self, ctx: commands.Context):
        """Fuerza una comprobación manual."""
        await ctx.send("🔍 Verificando Kick…")
        await self.check_kick_status()

# ─── SETUP ───
async def setup(bot: commands.Bot):
    await bot.add_cog(KickNotifier(bot))
