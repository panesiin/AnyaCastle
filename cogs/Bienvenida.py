# welcome_image_cog.py
import discord
from discord.ext import commands
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import aiohttp, io

# ───── CONFIGURACIÓN ─────
WELCOME_CHANNEL_ID = 960072304212209695 #952429462346154004 ← ABI

# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Assets
BANNER_PATH = BASE_DIR / "assets" / "banner.png"
FONT_PATH = BASE_DIR / "assets" / "impact.ttf"
# ─────────────────────────

class WelcomeImageCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ╭─ EVENTO: nuevo miembro ─╮
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.send_welcome(member)

    # ╭─ COMANDO TEST (solo dueño) ─╮
    @commands.is_owner()
    @commands.command(name="welcometest")
    async def welcometest(
        self,
        ctx: commands.Context,
        target: discord.Member | None = None
    ):
        target = target or ctx.author
        await self.send_welcome(target)
        await ctx.reply(
            "✅ Tarjeta de bienvenida enviada (modo test).",
            ephemeral=True
        )

    # ╭─ ENVÍO DE MENSAJE + IMAGEN ─╮
    async def send_welcome(self, member: discord.Member):
        if not BANNER_PATH.exists():
            print("❌ No encontré banner.png.")
            return

        buf = await self.build_welcome_card(member)

        # Mensaje secreto
        agent_number = member.guild.member_count

        msg = (
            f"🚓 **APROBADO..** {member.mention} 🕵🏼‍♀️ ||AGNT-{agent_number}|| 🔍\n"
            "> Anya ha aprobado tu ingreso a la academia secreta de Abi<:inspect2:1320810253532659773>"
        )

        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)

        if channel:
            await channel.send(
                content=msg,
                file=discord.File(buf, filename="welcome.png")
            )

    # ╭─ GENERAR TARJETA ─╮
    async def build_welcome_card(self, member: discord.Member) -> io.BytesIO:

        base = Image.open(BANNER_PATH).convert("RGBA")
        width, _ = base.size

        draw = ImageDraw.Draw(base)

        # ---------- Avatar ----------

        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

        avatar = (
            Image.open(io.BytesIO(avatar_bytes))
            .convert("RGBA")
            .resize((200, 200), Image.LANCZOS)
        )

        mask = Image.new("L", avatar.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)

        avatar.putalpha(mask)

        # ─── Alineación ───

        right_center_x = (width * 3) // 4

        OFFSET_X = -50

        # -------------------

        avatar_x = right_center_x - 100 + OFFSET_X

        base.paste(avatar, (avatar_x, 70), avatar)

        # ---------- Fuentes ----------

        if FONT_PATH.exists():

            font_title = ImageFont.truetype(str(FONT_PATH), 70)
            font_name = ImageFont.truetype(str(FONT_PATH), 60)
            font_msg = ImageFont.truetype(str(FONT_PATH), 40)

        else:

            font_title = font_name = font_msg = ImageFont.load_default()

        # ---------- Función centrado ----------

        def center_right(text, y, font, color=(255, 255, 255)):

            bbox = draw.textbbox((0, 0), text, font=font)

            x = right_center_x - (bbox[2] - bbox[0]) // 2 + OFFSET_X

            draw.text(
                (x, y),
                text,
                font=font,
                fill=color
            )

        # ---------- Dibujar textos ----------

        center_right("¡Weeeelcome!", 280, font_title)

        center_right(
            member.name,
            350,
            font_name,
            (180, 255, 180)
        )

        center_right(
            "Fin del mensaje ultra secreto",
            420,
            font_msg,
            (200, 200, 255)
        )

        # ---------- Guardar ----------

        buf = io.BytesIO()

        base.save(buf, "PNG")

        buf.seek(0)

        return buf

# ╭─ SETUP ─╮

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeImageCog(bot))