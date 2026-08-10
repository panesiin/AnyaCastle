from __future__ import annotations
"""
tiktok_live_detector.py – Multi-streamer detector con config JSON
=================================================================
• Lee un archivo JSON y crea un monitor por cada streamer.
• Cada monitor usa TikTokLiveClient.is_live() y mantiene su propio loop.
"""

import asyncio, json, pathlib
from datetime import datetime
from typing import Optional, Dict, Any

import discord
from discord.ext import commands, tasks
from TikTokLive import TikTokLiveClient

__all__ = ["setup"]

# ---------- Ruta del archivo de configuración ----------
CONFIG_PATH = pathlib.Path(__file__).with_name("tiktok_live_config.json")


# --------- Clase que monitoriza 1 streamer ---------
class StreamerMonitor:
    def __init__(self, cog: commands.Cog, name: str, cfg: Dict[str, Any]):
        self.cog = cog
        self.name = name

        # Parámetros con defaults
        self.username: str = cfg.get("USERNAME", "").lstrip("@")
        self.interval: int = int(cfg.get("CHECK_INTERVAL_SEC", 60))
        self.timeout: int = int(cfg.get("REQUEST_TIMEOUT_SEC", 8))
        self.channel_id: int = int(cfg.get("DISCORD_CHANNEL_ID"))
        self.mention_role_id: Optional[int] = cfg.get("MENTION_ROLE_ID")

        # Textos embed
        self.title_on = cfg.get("TITLE_ON", "🔴 ¡EN VIVO en TikTok!")
        self.desc_on = cfg.get(
            "DESCRIPTION_ON",
            "La cuenta @{USERNAME} acaba de iniciar un directo."
        )
        self.title_off = cfg.get("TITLE_OFF", "⏹️ Fin del directo")
        self.desc_off = cfg.get(
            "DESCRIPTION_OFF",
            "@{USERNAME} ha terminado su live."
        )

        # Estado
        self.client = TikTokLiveClient(unique_id=self.username)
        self.is_live_prev: Optional[bool] = None
        self.first_run = True

        # Arranca loop
        self.task = tasks.loop(seconds=self.interval)(self._loop_task)
        self.task.start()

    # --------------- LOOP ---------------
    async def _loop_task(self):
        try:
            is_live = await asyncio.wait_for(
                self.client.is_live(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            print(f"[{self.username}] Timeout en is_live()")
            return
        except Exception as exc:
            print(f"[{self.username}] Error is_live(): {exc}")
            return

        # Primer ciclo solo memoriza
        if self.first_run:
            self.is_live_prev = is_live
            self.first_run = False
            print(f"[{self.username}] Estado inicial: {'LIVE' if is_live else 'OFF'}")
            return

        if is_live and not self.is_live_prev:
            await self._announce(start=True)
        elif not is_live and self.is_live_prev:
            await self._announce(start=False)

        self.is_live_prev = is_live

    # --------------- EMBED ---------------
    async def _announce(self, *, start: bool):
        channel = self.cog.bot.get_channel(self.channel_id)
        if channel is None:
            print(f"[{self.username}] Canal {self.channel_id} no encontrado")
            return

        # Personaliza texto con username
        if start:
            title = self.title_on
            desc = self.desc_on
            color = discord.Color.red()
        else:
            title = self.title_off
            desc = self.desc_off
            color = discord.Color.greyple()

        title = title.replace("{USERNAME}", self.username)
        desc = desc.replace("{USERNAME}", self.username)

        embed = discord.Embed(
            title=title,
            url=f"https://www.tiktok.com/@{self.username}/live",
            description=desc,
            timestamp=datetime.utcnow(),
            color=color,
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3046/3046123.png")
        embed.set_footer(text="TikTok Live Detector")

        mention = f"<@&{self.mention_role_id}> " if self.mention_role_id else ""

        try:
            await channel.send(content=mention, embed=embed,
                               allowed_mentions=discord.AllowedMentions(roles=True))
        except discord.HTTPException as exc:
            print(f"[{self.username}] Error enviando embed: {exc}")

    # --------------- Limpieza ---------------
    def stop(self):
        self.task.cancel()


# --------- Cog principal (carga config) ---------
class TikTokLiveManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.monitors: Dict[str, StreamerMonitor] = {}

        cfg = self._load_config()
        for name, data in cfg.items():
            try:
                mon = StreamerMonitor(self, name, data)
                self.monitors[name] = mon
            except Exception as exc:
                print(f"[Config] No se pudo crear monitor {name}: {exc}")

    # ---------- JSON loader ----------
    @staticmethod
    def _load_config() -> Dict[str, Any]:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"No se encontró {CONFIG_PATH}")
        with CONFIG_PATH.open(encoding="utf-8") as fp:
            data = json.load(fp)

        # Soporta objeto {"STREAMER1": {...}} o {"streamers":[...]}
        if isinstance(data, list):  # viejo formato array
            return {f"Streamer{i+1}": v for i, v in enumerate(data)}
        elif isinstance(data, dict):
            return data
        else:
            raise ValueError("Formato JSON no reconocido")

    # ---------- Owner command ----------
    @commands.is_owner()
    @commands.command(name="tklivecheck", help="Fuerza check de un streamer")
    async def tklivecheck(self, ctx: commands.Context, streamer_key: str):
        """
        Uso: !tklivecheck STREAMER1
        Lanza revisión manual (ON u OFF) para ese streamer.
        """
        mon = self.monitors.get(streamer_key)
        if not mon:
            await ctx.reply("Streamer no encontrado en la configuración.")
            return

        try:
            is_live = await asyncio.wait_for(
                mon.client.is_live(), mon.timeout
            )
        except asyncio.TimeoutError:
            await ctx.reply("⏱️ Timeout al consultar TikTok.")
            return
        except Exception as exc:
            await ctx.reply(f"Error al comprobar: {exc}")
            return

        if is_live:
            await mon._announce(start=True)
            mon.is_live_prev = True
            await ctx.reply("✅ Live detectado y notificado.")
        else:
            await mon._announce(start=False)
            mon.is_live_prev = False
            await ctx.reply("❌ El streamer NO está en vivo.")

    def cog_unload(self):
        for mon in self.monitors.values():
            mon.stop()


# -------- setup --------
async def setup(bot: commands.Bot):
    await bot.add_cog(TikTokLiveManager(bot))
