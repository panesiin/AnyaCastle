# amor_perfil.py (versión bonita ✨)
import json, discord
from pathlib import Path
from discord.ext import commands

DATA_FILE = Path(__file__).with_name("secso_count.json")

def cargar_stats():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {}

class AmorPerfil(commands.Cog):
    """Comando !pr — Estadísticas románticas."""

    def __init__(self, bot):
        self.bot = bot

    def _resumen_usuario(self, uid: int, stats: dict):
        total = 0
        parejas = {}
        for key, veces in stats.items():
            id1, id2 = map(int, key.split("_"))
            if uid in (id1, id2):
                otro = id2 if uid == id1 else id1
                total += veces
                parejas[otro] = parejas.get(otro, 0) + veces
        return total, parejas

    @commands.command(name="pr", help="Muestra tus estadísticas de detonadas.")
    async def pr(self, ctx: commands.Context, miembro: discord.Member | None = None):
        stats = cargar_stats()
        user = miembro or ctx.author

        total, parejas = self._resumen_usuario(user.id, stats)

        # Crear embed bonito
        embed = discord.Embed(
            title=f"💘 Perfil Romántico de {user.display_name}",
            color=0xFFC0CB,
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="💞 Total de detonadas", value=f"> **{total} veces**", inline=False)
        embed.add_field(name="👥 Parejas distintas", value=f"> **{len(parejas)} personas**", inline=False)

        if parejas:
            fav_id = max(parejas, key=parejas.get)
            fav_count = parejas[fav_id]
            fav_member = ctx.guild.get_member(fav_id)
            nombre_fav = fav_member.display_name if fav_member else f"ID {fav_id}"
            embed.add_field(
                name="💘 Pareja favorita",
                value=f"> **{nombre_fav}** con **{fav_count} detonadas**",
                inline=False,
            )
        else:
            embed.add_field(name="✨ Estado", value="> *Aún sin detonar... 😳*", inline=False)

        embed.set_footer(text="Anya observa con fines estadísticos 👀")
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AmorPerfil(bot))
