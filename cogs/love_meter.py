import os
import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import discord
from discord.ext import commands


# Ruta raíz del bot (sale desde /cogs hasta /Bot)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Archivos dentro de assets
BASE_IMG = os.path.join(BASE_DIR, "assets", "love.png")
FONT_PATH = os.path.join(BASE_DIR, "assets", "impact.ttf")


class LoveMeter(commands.Cog):
    """Comando para medir el amor entre dos usuarios"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Dibujar texto centrado horizontalmente
    def draw_centered_text(self, draw, text, position, font, fill):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        x = position[0] - text_width // 2
        y = position[1]

        draw.text((x, y), text, font=font, fill=fill)

    @commands.command(name='amor', help='Mide el nivel de amor entre dos usuarios.')
    async def amor(self, ctx: commands.Context, member: discord.Member | None = None):

        if member is None:
            await ctx.send('💞 Debes mencionar a alguien.')
            return

        # Verificar plantilla
        if not os.path.exists(BASE_IMG):
            print(f"❌ No existe la imagen: {BASE_IMG}")
            await ctx.send('❌ No se encontró la plantilla love.png')
            return

        # Verificar fuente
        if not os.path.exists(FONT_PATH):
            print(f"❌ No existe la fuente: {FONT_PATH}")
            await ctx.send('❌ No se encontró la fuente impact.ttf')
            return


        love_percentage = random.randint(0, 100)

        base_img = Image.open(BASE_IMG).convert("RGBA")
        draw = ImageDraw.Draw(base_img)


        font = ImageFont.truetype(FONT_PATH, 18)
        name_font = ImageFont.truetype(FONT_PATH, 20)


        # Nombres
        self.draw_centered_text(
            draw,
            ctx.author.display_name,
            (100, 190),
            name_font,
            "white"
        )

        self.draw_centered_text(
            draw,
            member.display_name,
            (495, 190),
            name_font,
            "white"
        )


        # Barra de amor
        filled_length = int(20 * love_percentage // 100)

        bar = "█" * filled_length + " " * (20 - filled_length)

        bar_width = 20 * 10

        x_bar = (545 - bar_width) // 2
        y_bar = 90

        draw.text(
            (x_bar, y_bar),
            bar,
            font=font,
            fill="red"
        )


        # Porcentaje
        self.draw_centered_text(
            draw,
            f"{love_percentage}%",
            (275, 120),
            name_font,
            "white"
        )


        # Avatares
        avatar_a = BytesIO(await ctx.author.display_avatar.read())
        avatar_b = BytesIO(await member.display_avatar.read())


        avatar_a_img = (
            Image.open(avatar_a)
            .convert("RGBA")
            .resize((100, 100))
        )

        avatar_b_img = (
            Image.open(avatar_b)
            .convert("RGBA")
            .resize((100, 100))
        )


        base_img.paste(
            avatar_a_img,
            (50, 70),
            avatar_a_img
        )

        base_img.paste(
            avatar_b_img,
            (450, 70),
            avatar_b_img
        )


        # Guardar memoria temporal
        buffer = BytesIO()

        base_img.save(
            buffer,
            format="PNG"
        )

        buffer.seek(0)


        await ctx.send(
            file=discord.File(
                buffer,
                filename="love.png"
            ),
            content=(
                f'💞 El amor de {ctx.author.mention} '
                f'y {member.mention} es de **{love_percentage}%**'
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(LoveMeter(bot))