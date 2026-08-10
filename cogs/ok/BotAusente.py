from __future__ import annotations

"""buzon_ausente.py – Cog de Discord con buzón de ausencias **persistente y refinado**.

(Modificado el 2025‑06‑21 según indicaciones de Panesiin)

Cambios clave:
1. ✅ Ya **no se envía** el reply burlón cuando el destinatario no responde; sólo se almacena la mención.
2. ✅ En modo **chat** se intenta mandar la notificación como **ephemeral** (sólo visible para el usuario) siempre que el contexto sea una interacción. Si no se puede (por ejemplo, comandos de prefijo), se mantiene el fallback clásico.

La lógica de guardado, recordatorios y botones permanece sin cambios.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands, tasks

__all__ = ["setup"]

# ---- Personaliza imágenes ----
AUTHOR_NAME = "Buzón de Menciones"
AUTHOR_ICON_URL = "https://media.discordapp.net/attachments/966755203787407370/1383855712270024754/4cef9e8a8ecba07212109351e8d6e92e.jpg?ex=68504f90&is=684efe10&hm=8ea065cf77989a6a64d6e12ac00a290d6a65853c8567a5cec55b5f85dcea25e1&=&format=webp"
THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/966755203787407370/1321130060618666169/sad3.png?ex=6850313f&is=684edfbf&hm=a74b888df74bffec38640b65f0873c2f7796c143a8579e1bc3bd6930edcb4629"
FOOTER_TEXT = "Sistema de ausencias • {time}"

# ---- Archivos ----
BASE_PATH = Path(__file__).parent
CONFIG_FILE = BASE_PATH / "buzon_user_configs.json"
PENDING_FILE = BASE_PATH / "buzon_pending.json"


# ---- Helpers JSON ----
def _save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[BuzonAusente] ⚠️ Archivo corrupto: {path.name}. Se reinicia.")
    return default


# ---- Vista con botones ----
class ReminderView(discord.ui.View):
    def __init__(self, cog: "BuzonAusente", member: discord.abc.User, msgs: List[dict]):
        super().__init__(timeout=20)
        self.cog = cog
        self.member = member
        self.msgs = msgs
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, i: discord.Interaction) -> bool:
        if i.user.id != self.member.id:
            await i.response.send_message("⛔ No puedes usar esto.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Ver", style=discord.ButtonStyle.primary)
    async def _ver(self, i: discord.Interaction, _):
        emb = self.cog._build_details_embed(self.msgs)
        await i.response.edit_message(embed=emb, view=None, content=None)
        await self.cog._remove_pending(self.member.id)

    @discord.ui.button(label="Borrar", style=discord.ButtonStyle.danger)
    async def _borrar(self, i: discord.Interaction, _):
        await i.response.edit_message(
            content="🗑️ Mensajes descartados.", embed=None, view=None
        )
        await self.cog._remove_pending(self.member.id)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(
                    content="📨 Menciones guardadas. Usa `!bz` para ver tu recordatorio.",
                    embed=None,
                    view=None,
                )
            except discord.HTTPException:
                pass


# ---- Cog ----
class BuzonAusente(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_configs: Dict[int, dict] = {
            int(k): v for k, v in _load_json(CONFIG_FILE, {}).items()
        }
        self.pending: List[dict] = _load_json(PENDING_FILE, [])
        self.last_reminder: Dict[int, float] = {}
        self.cleaner.start()

    # ---- Persistencia ----
    def _save_configs(self):
        _save_json(CONFIG_FILE, {str(k): v for k, v in self.user_configs.items()})

    def _save_pending(self):
        _save_json(PENDING_FILE, self.pending)

    # ---- Slash commands ----
    ausente = app_commands.Group(name="ausente", description="Configura tu buzón")

    @ausente.command(name="on")
    @app_commands.choices(
        modo=[
            app_commands.Choice(name="dm", value="dm"),
            app_commands.Choice(name="chat", value="chat"),
        ]
    )
    async def _on(self, inter: discord.Interaction, modo: app_commands.Choice[str]):
        self.user_configs[inter.user.id] = {"active": True, "mode": modo.value}
        self._save_configs()
        await inter.response.send_message(
            f"✅ Buzón activado en **{modo.value.upper()}**.", ephemeral=True
        )

    @ausente.command(name="off")
    async def _off(self, inter: discord.Interaction):
        self.user_configs[inter.user.id] = {"active": False, "mode": "dm"}
        self._save_configs()
        await inter.response.send_message("🚫 Buzón desactivado.", ephemeral=True)

    # ---- Prefix !bz ----
    @commands.command(name="bz")
    async def _bz(self, ctx: commands.Context):
        cfg = self.user_configs.get(ctx.author.id)
        if not (cfg and cfg.get("active")):
            return await ctx.reply("❌ No tienes activo el buzón.", mention_author=False)
        if not self._has_pending_for(ctx.author.id):
            return await ctx.reply(
                "<:sad3:1320810423909613598> No hay menciones pendientes.", mention_author=False
            )
        await self._deliver_pending(ctx.author, ctx.channel, cfg["mode"], force=True)

    # ---- Listener ----
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if m.author.bot:
            return
        cfg = self.user_configs.get(m.author.id)
        if cfg and cfg.get("active") and self._has_pending_for(m.author.id):
            if time.time() - self.last_reminder.get(m.author.id, 0) >= 300:
                await self._deliver_pending(m.author, m.channel, cfg["mode"])

        for u in m.mentions:
            ucfg = self.user_configs.get(u.id)
            if ucfg and ucfg.get("active"):
                # Dispara la espera sin responder públicamente
                self.bot.loop.create_task(self._await_response_or_store(u, m))

    # ---- Ausencia ----
    async def _await_response_or_store(
        self, target: discord.abc.User, origin: discord.Message
    ):
        """Espera 60 s a que la persona mencionada responda.
        Si no lo hace, se almacena la mención *sin* enviar reply público."""

        def check(msg: discord.Message):
            return msg.author.id == target.id and msg.channel == origin.channel

        try:
            await self.bot.wait_for("message", timeout=60, check=check)
        except asyncio.TimeoutError:
            # ⏸️ Ya no respondemos en el canal; solo guardamos la mención
            self.pending.append(
                {
                    "target": target.id,
                    "author": origin.author.id,
                    "channel": origin.channel.id,
                    "content": origin.clean_content,
                    "timestamp": time.time(),
                }
            )
            self._save_pending()

    # ---- Entrega ----
    def _has_pending_for(self, uid: int) -> bool:
        return any(p["target"] == uid for p in self.pending)

    async def _deliver_pending(
        self,
        member: discord.abc.User,
        fallback: Union[discord.abc.Messageable, discord.Interaction],
        mode: str,
        *,
        force=False,
    ):
        msgs = [p for p in self.pending if p["target"] == member.id]
        if not msgs:
            return

        embed = discord.Embed(
            title="📬 Tienes menciones guardadas",
            description="Se guardaron **{0}** mencion(es). "
            "Usa los botones para ver o borrar, se cerrará tras 20 s.".format(len(msgs)),
            color=discord.Color.orange(),
        )
        self._decorate(embed)

        view = ReminderView(self, member, msgs)
        sent = False

        # 1) DM directo
        if mode == "dm":
            try:
                view.message = await member.send(embed=embed, view=view)
                sent = True
            except discord.Forbidden:
                sent = False

        # 2) Chat – preferimos ephemerals si el "fallback" es una interacción
        if not sent and mode == "chat":
            if isinstance(fallback, discord.Interaction):
                # Slash‑command o botón → podemos usar ephemeral
                view.message = await fallback.followup.send(
                    embed=embed,
                    view=view,
                    ephemeral=True,
                )
                sent = True

        # 3) Fallback clásico (visible para todos)
        if not sent:
            view.message = await fallback.send(
                member.mention,
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(users=[member]),
            )

        if not force:
            self.last_reminder[member.id] = time.time()

    # ---- Embeds helpers ----
    def _decorate(self, embed: discord.Embed):
        embed.set_author(name=AUTHOR_NAME, icon_url=AUTHOR_ICON_URL or discord.Embed.Empty)
        if THUMBNAIL_URL:
            embed.set_thumbnail(url=THUMBNAIL_URL)
        embed.set_footer(text=FOOTER_TEXT.format(time=datetime.now().strftime("%Y-%m-%d")))

    def _build_details_embed(self, msgs: List[dict]) -> discord.Embed:
        lines = []
        for p in msgs:
            author_obj = self.bot.get_user(p["author"])
            author = author_obj.mention if author_obj else f"<@{p['author']}>"

            channel_obj = self.bot.get_channel(p["channel"])
            channel = channel_obj.mention if channel_obj else f"<#{p['channel']}>"

            t = datetime.fromtimestamp(p["timestamp"], tz=timezone.utc).astimezone()
            lines.append(
                f"• **{author}** en {channel} — {t:%Y-%m-%d %H:%M}:\n> {p['content']}"
            )

        emb = discord.Embed(
            title="📨 Menciones",
            description="\n\n".join(lines),
            color=discord.Color.green(),
        )
        self._decorate(emb)
        return emb

    async def _remove_pending(self, uid: int):
        before = len(self.pending)
        self.pending = [p for p in self.pending if p["target"] != uid]
        if len(self.pending) != before:
            self._save_pending()

    # ---- Limpieza ----
    @tasks.loop(hours=1)
    async def cleaner(self):
        cutoff = time.time() - 86_400  # 24 h
        before = len(self.pending)
        self.pending = [p for p in self.pending if p["timestamp"] > cutoff]
        if len(self.pending) != before:
            self._save_pending()

    def cog_unload(self):
        self.cleaner.cancel()


# ---- Setup ----
async def setup(bot: commands.Bot):
    await bot.add_cog(BuzonAusente(bot))
