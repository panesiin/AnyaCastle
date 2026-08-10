import random
import asyncio
import time
import json
import unicodedata
import discord
from discord.ext import commands
from pathlib import Path

FRASES_FILE = Path(__file__).with_name("frases_bot.json")   # mismo folder
CHISTES_FILE = 'chistes.txt'
DESEOS_FILE = 'deseos_navidad.txt'
GIF_LESB = (
    'https://media.discordapp.net/attachments/966755203787407370/1321778098793873428/pevert.gif'
    '?ex=676e7948&is=676d27c8&hm=046111d2dfd25a4bcb79d5cb64dd65145e6299267b65e4f9c288218a4fc5c94b&='
)

class ExtraFun(commands.Cog):
    """Comandos divertidos: chistes, deseos, nalgadas, etc."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.chistes = self._load(CHISTES_FILE)
        self.deseos = self._load(DESEOS_FILE)
        self.cooldowns: dict[str, float] = {}

    # -------------------------------------------------------------------
    #                          UTILIDADES
    # -------------------------------------------------------------------
    def _load(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return [l.strip() for l in f if l.strip()]
        except FileNotFoundError:
            print(f'Archivo no encontrado: {path}')
            return []

    def _on_cd(self, key: str) -> bool:
        return self.cooldowns.get(key, 0) > time.time()

    # -------------------------------------------------------------------
    #                     📸  LESBIANAS (GIF)  📸
    # -------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.content.lower() == 'lesbianas':
            key = f'lesb_{message.author.id}'
            if self._on_cd(key):
                return

            embed = discord.Embed(title='¡Vivan las lesbianas!', color=discord.Color.blue())
            embed.set_image(url=GIF_LESB)
            await message.channel.send(embed=embed)
            self.cooldowns[key] = time.time() + 120

    # -------------------------------------------------------------------
    #                             🎄  DESEOS
    # -------------------------------------------------------------------
    @commands.command(name='deseo', help='Genera un deseo navideño aleatorio')
    async def deseo(self, ctx: commands.Context):
        key = f'deseo_{ctx.author.id}'
        if self._on_cd(key):
            await ctx.send('Comando en cooldown.')
            return

        deseo = random.choice(self.deseos) if self.deseos else 'Paz y amor 🎄'
        await ctx.send(f'🎁 **Tu deseo es:**\n {deseo}')
        self.cooldowns[key] = time.time() + 5

    # -------------------------------------------------------------------
    #                             🤣  CHISTES
    # -------------------------------------------------------------------
    @commands.command(name='chiste', help='Cuenta un chiste')
    async def chiste(self, ctx: commands.Context):
        key = f'chiste_{ctx.author.id}'
        if self._on_cd(key):
            await ctx.send('En cooldown.')
            return

        chiste = random.choice(self.chistes) if self.chistes else 'Sin chistes disponibles.'
        await ctx.send(chiste)
        self.cooldowns[key] = time.time() + 10

    # -------------------------------------------------------------------
    #                            👋  NALGADA
    # -------------------------------------------------------------------
    @commands.command(
        name='nalgada',
        help='Dale una nalgada a alguien al azar o menciona a alguien con @.'
    )
    async def nalgada(self, ctx: commands.Context, member: discord.Member | None = None):
        key = f"nalgada_{ctx.author.id}"
        if self._on_cd(key):
            await ctx.send('> ❌ Estás en cooldown, espera un momento.')
            return

        if member is None:
            member = random.choice([m for m in ctx.guild.members if not m.bot])

        embed = discord.Embed(
            title="👋🏼",
            description=f"¡{ctx.author.mention} se nalgueó a {member.mention} 😳",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url="https://i.imgur.com/5kJLPOp.jpeg")
        embed.set_footer(
            text="⚠️ El botón solo puede ser presionado por el destinatario dentro de 60 segundos.",
            icon_url=(ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        )

        class NalgadaView(discord.ui.View):
            def __init__(self, author: discord.Member, target: discord.Member, embed_orig: discord.Embed):
                super().__init__(timeout=60)
                self.author = author
                self.target = target
                self.embed_orig = embed_orig
                self.message: discord.Message | None = None

            @discord.ui.button(label="Putear😾", style=discord.ButtonStyle.primary)
            async def correspond(self, interaction: discord.Interaction, _: discord.ui.Button):
                if interaction.user.id == self.target.id:
                    emb_resp = discord.Embed(
                        title="¡Se vienen madrazos 👊🏼!",
                        description=(
                            f"{interaction.user.mention} se puteó a "
                            f"{self.author.mention}!\n"
                            "A las damas se les invita un cafecito primero 😾"
                        ),
                        color=discord.Color.green()
                    )
                    emb_resp.set_thumbnail(url="https://i.imgur.com/MvVTcSi.png")
                    await interaction.response.send_message(embed=emb_resp)

                    self.clear_items()
                    await self.message.edit(
                        content="El botón ha sido desactivado.",
                        embed=self.embed_orig,
                        view=None
                    )
                    self.stop()
                else:
                    emb_err = discord.Embed(
                        title="❌ Error",
                        description="Solo el destinatario puede presionar el botón.",
                        color=discord.Color.red()
                    )
                    emb_err.set_thumbnail(url="https://i.imgur.com/DlkgcV3.png")
                    await interaction.response.send_message(embed=emb_err, ephemeral=True)

            async def on_timeout(self):
                if self.message:
                    await self.message.edit(
                        content="El botón ha sido desactivado.",
                        embed=self.embed_orig,
                        view=None
                    )

        view = NalgadaView(ctx.author, member, embed)
        sent_msg = await ctx.send(embed=embed, view=view)
        view.message = sent_msg
        self.cooldowns[key] = time.time() + 10

    # -------------------------------------------------------------------
    #                  👀 RESPUESTAS PALABRA CLAVE (texto)
    # -------------------------------------------------------------------
    KEYWORD_REPLIES: dict[str, str] = {
        "holi": "holi muchachos como tamos?",
        "mimir": "<:snorl:1320810582684860516> Zzz",
        "deadpool": "Hora de hacer las p*tas chimichangas",
        "abi": "Abi ta' chambeando dormida chavales <:sleep5:1320810560073367645>",
        "anya": "Si diga? <:spy2:1320810637714133063>",
        "verga": "Provecho! :o",
    }

    def _kw_on_cd(self, word: str, user_id: int) -> bool:
        return self.cooldowns.get(f"kw_{word}_{user_id}", 0) > time.time()

    @commands.Cog.listener("on_message")
    async def on_message_keywords(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content.lower().strip()
        if content in self.KEYWORD_REPLIES:
            if self._kw_on_cd(content, message.author.id):
                return

            await message.channel.send(self.KEYWORD_REPLIES[content])
            self.cooldowns[f"kw_{content}_{message.author.id}"] = time.time() + 120  

async def setup(bot: commands.Bot):
    await bot.add_cog(ExtraFun(bot))