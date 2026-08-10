from __future__ import annotations
"""youtube_rss_notifier.py – Notificador de *Directos & Shorts* (RSS) ⏱️ cada 5 min
para **un solo canal**, evitando spam inicial.

🔔 **Novedad**: al primer arranque **no envía** los shorts/directos anteriores; solo los
marca como vistos. Así no se inunda el canal la primera vez.

Configura aquí:
```py
YT_CHANNEL_ID = "UCxxxxxxxxxxxxxxxx"      # ID del canal YouTube
DISCORD_CHANNEL_ID = 123456789012345678   # Canal Discord para avisos
MENTION_ROLE_ID = None                    # id de rol a mencionar o None
```

Dependencias: `pip install aiohttp python-dateutil`
"""
import asyncio
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional

import aiohttp
import discord
from discord.ext import commands, tasks
from dateutil import parser as dateparser

__all__ = ["setup"]

# ------------- Config -------------
YT_CHANNEL_ID = "UCXPtwo8m4l1PDIyxl9Zf_1w"        # ← UC‑ID de @tablitaplay UCcgIhm5zX17HWmZvu4ujVMg              fanbilimdza UCXPtwo8m4l1PDIyxl9Zf_1w
DISCORD_CHANNEL_ID = 1317332004706189384      # ← id del canal de Discord
MENTION_ROLE_ID: Optional[int] = None        # ← id de rol a pingear o None
FETCH_INTERVAL_MIN = 2                       # cada 5 min

BASE_PATH = Path(__file__).parent
SEEN_FILE = BASE_PATH / "yt_seen.json"

def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[YTNotifier] ⚠️ {path.name} corrupto → reiniciado")
    return default

def _save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

class YTRSSNotifier(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.seen: Set[str] = set(_load_json(SEEN_FILE, []))
        self.session: aiohttp.ClientSession | None = None
        self.task.start()

    async def _prime_seen(self):
        try:
            xml_text = await self._fetch_feed(YT_CHANNEL_ID)
            ids = self._collect_relevant_ids(xml_text)
            if ids:
                self.seen.update(ids)
                _save_json(SEEN_FILE, list(self.seen)[-100:])
                print(f"[YTNotifier] Inicializados {len(ids)} IDs como vistos (no se enviarán).")
        except Exception as exc:
            print(f"[YTNotifier] Prime error: {exc}")

    @tasks.loop(minutes=FETCH_INTERVAL_MIN)
    async def task(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        try:
            xml_text = await self._fetch_feed(YT_CHANNEL_ID)
            new_items = self._parse_feed(xml_text)
            if new_items:
                await self._announce(new_items)
                _save_json(SEEN_FILE, list(self.seen)[-100:])
        except Exception as exc:
            print(f"[YTNotifier] Error: {exc}")

    @task.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        if not self.seen:
            await self._prime_seen()

    async def _fetch_feed(self, channel_id: str) -> str:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=15) as resp:
                resp.raise_for_status()
                return await resp.text()

    def _collect_relevant_ids(self, xml_text: str) -> List[str]:
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }
        root = ET.fromstring(xml_text)
        ids: List[str] = []
        for entry in root.findall("atom:entry", ns):
            video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
            title = entry.findtext("atom:title", default="", namespaces=ns)
            desc = entry.findtext("media:group/media:description", default="", namespaces=ns)
            text = f"{title} {desc}".lower()
            is_short = bool(re.search(r"#?shorts?", text))
            is_live = bool(re.search(r"(live|directo|stream)", text)) or entry.find("yt:liveBroadcastEvent", ns) is not None
            if is_short or is_live:
                ids.append(video_id)
        return ids

    def _parse_feed(self, xml_text: str) -> List[Dict]:
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }
        root = ET.fromstring(xml_text)
        new_items: List[Dict] = []
        for entry in root.findall("atom:entry", ns):
            video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
            if video_id in self.seen:
                continue

            title = entry.findtext("atom:title", default="", namespaces=ns)
            desc = entry.findtext("media:group/media:description", default="", namespaces=ns)
            text = f"{title} {desc}".lower()
            is_short = bool(re.search(r"#?shorts?", text))
            is_live = bool(re.search(r"(live|directo|stream)", text)) or entry.find("yt:liveBroadcastEvent", ns) is not None
            if not (is_short or is_live):
                continue

            published_str = entry.findtext("atom:published", default="", namespaces=ns)
            published = dateparser.parse(published_str) if published_str else datetime.utcnow()
            new_items.append({
                "id": video_id,
                "title": title,
                "published": published,
                "link": f"https://youtu.be/{video_id}",
                "thumb": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "hero": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                "is_live": is_live,
                "is_short": is_short,
            })
            self.seen.add(video_id)

        new_items.sort(key=lambda x: x["published"])
        return new_items

    async def _announce(self, items: List[Dict]):
        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
        if channel is None:
            print(f"[YTNotifier] ⚠️ Canal {DISCORD_CHANNEL_ID} no encontrado")
            return
        mention = f"<@&{MENTION_ROLE_ID}> " if MENTION_ROLE_ID else ""
        for item in items:
            color = discord.Color.red() if item["is_live"] else discord.Color.orange()
            kind = "🔴 En VIVO en Youtube" if item["is_live"] else "🎬 Nuevo SHORT en Youtube chavalitos"

            embed = discord.Embed(
                title=kind,
                url=item["link"],
                description=item["title"],
                timestamp=item["published"],
                color=color,
            )
            embed.set_author(
                name="YouTube",
                icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png",
            )
            embed.set_thumbnail(url=item["thumb"])
            embed.set_footer(
                text="Anya YT-Notify • Directos & Shorts (5 Min/Retraso aprox.)",
                icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png",
            )

            try:
                await channel.send(content=mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
            except discord.HTTPException as exc:
                print(f"[YTNotifier] Error enviando mensaje: {exc}")

    def cog_unload(self):
        self.task.cancel()
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())

async def setup(bot: commands.Bot):
    await bot.add_cog(YTRSSNotifier(bot))
