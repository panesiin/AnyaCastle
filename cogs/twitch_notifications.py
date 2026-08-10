import os
import aiohttp
import requests
import discord
from discord.ext import commands, tasks
import asyncio

TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID', 'ejkfozqmjz368bno5lrbhct75l0k7w')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET', 'npphjjrsju6jiz8kbim0s7xwjlqk3a')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 60))

STREAMERS = {
    'streamer1': {
        'twitch_name': 'tablita_play',
        'channel_id': 952419779673735250,
        'message': 'Chavalitos TablitaHot está en LIVE 🥕'
    },
    'streamer2': {
        'twitch_name': 'telmex_mex',
        'channel_id': 1317332004706189384,
        'message': 'Tu mejor compañía ya está en live @everyone'
    }
}

class TwitchNotifications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.streamer_status = {k: False for k in STREAMERS}
        self.twitch_token: str | None = None
        self.check_live_status.start()

    def cog_unload(self):
        self.check_live_status.cancel()

    def get_twitch_token(self) -> str:
        url = 'https://id.twitch.tv/oauth2/token'
        payload = {
            'client_id': TWITCH_CLIENT_ID,
            'client_secret': TWITCH_CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }
        res = requests.post(url, data=payload, timeout=10)
        res.raise_for_status()
        return res.json()['access_token']

    async def is_live(self, twitch_name: str):
        if not self.twitch_token:
            self.twitch_token = self.get_twitch_token()

        headers = {
            'Client-ID': TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {self.twitch_token}'
        }
        url = f'https://api.twitch.tv/helix/streams?user_login={twitch_name}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 401:
                    # token expirado, renovar
                    self.twitch_token = self.get_twitch_token()
                    headers['Authorization'] = f'Bearer {self.twitch_token}'
                    async with session.get(url, headers=headers) as resp2:
                        data = (await resp2.json())['data']
                else:
                    data = (await resp.json())['data']
        return data[0] if data else None

    async def url_image_is_valid(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return response.status == 200 and response.headers.get("Content-Type", "").startswith("image")
        except Exception:
            return False

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_live_status(self):
        for key, info in STREAMERS.items():
            try:
                live_data = await self.is_live(info['twitch_name'])
                if live_data and not self.streamer_status[key]:
                    self.streamer_status[key] = True
                    channel = self.bot.get_channel(info['channel_id'])
                    if not channel:
                        continue

                    thumbnail_url = live_data["thumbnail_url"].replace("{width}", "320").replace("{height}", "180")

                    # Validar thumbnail (como en original)
                    if "placeholder" in thumbnail_url or not await self.url_image_is_valid(thumbnail_url):
                        thumbnail_url = "https://via.placeholder.com/320x180.png?text=En+Vivo"

                    embed = discord.Embed(
                        title=f"🥕 {live_data['user_name']} está en LIVE",
                        color=discord.Color.red()
                    )
                    embed.set_author(
                        name="Anya Castle",
                        icon_url="https://media.discordapp.net/attachments/966755203787407370/1320702855405109268/AnyaXmas.png"
                    )
                    embed.set_thumbnail(url=thumbnail_url)
                    embed.add_field(
                        name="Título del Stream",
                        value=f"**{live_data['title']}**\n[Ver ahora en Twitch](https://www.twitch.tv/{info['twitch_name']})",
                        inline=True,
                    )
                    embed.add_field(
                        name="Categoría",
                        value=f"**{live_data['game_name'] or 'Sin categoría'}**",
                        inline=True
                    )
                    embed.set_footer(
                        text="Notificación automática de Twitch",
                        icon_url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png"
                    )

                    message_content = info['message'] or "@everyone ¡Alguien está en vivo, no te lo pierdas!"
                    await channel.send(content=message_content, embed=embed)

                elif not live_data and self.streamer_status[key]:
                    self.streamer_status[key] = False

            except Exception as e:
                print(f"Error revisando {info['twitch_name']}: {e}")

    @check_live_status.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(TwitchNotifications(bot))