from __future__ import annotations
"""help_cog.py help mejorado con menú desplegable

Comandos:
* **!anya**  → versión prefijo (mensaje público)
* **/anya**  → slash (ephemeral)

`help_data.json` define **todo** el contenido.  campo extra
`"thumbrl"` (opcional) para asignar un thumbnail distinto por categoría.
Si falta se usa la URL global por defectoo

Ejemplo de bloque:
```
{
  "title": "MÚSICA",
  "emoji": "🎵",
  "thumbrl": "https://cdn.example.com/music.png",
  "commands": [
    {"cmd": "!join", "desc": "Me uno al canal de voz."},
    ...
  ]
}

-------------------COMANDOS OCULTOS LISTENER:------------------------
-Lesbianas →    gif
-holi →         holi muchachos como tamos?
-mimir →        Zzz
-deadpool →     Hora de hacer las ptas chimichangas
-abi →          Abi ta' chambeando dormida chavales
-anya →         Si diga?
-versh →        salud?

{
  "exact_replies.json"
}
----------------------------------------------------------------------
```
"""

import json
from pathlib import Path
from typing import List, Dict

import discord
from discord import app_commands
from discord.ext import commands

__all__ = ["setup"]

# ----- Archivos y paths -----
BASE_PATH = Path(__file__).parent
HELP_FILE = BASE_PATH / "help_data.json"
DEFAULT_THUMB = (
    "https://cdn.discordapp.com/attachments/966755203787407370/1321130060618666169/sad3.png"
)

# ---------- Helper de datos ----------

def _load_help_data() -> List[Dict]:
    """Carga y valida el JSON con las categorías y comandos."""
    try:
        with HELP_FILE.open(encoding="utf-8") as fp:
            data = json.load(fp)
            assert isinstance(data, list), "La raíz debe ser lista"
            return data
    except FileNotFoundError:
        print("[HelpCog] ❌ help_data.json no encontrado. Crea el archivo con tus comandos.")
    except (json.JSONDecodeError, AssertionError) as exc:
        print(f"[HelpCog] ❌ help_data.json corrupto: {exc}")
    return []


# ---------- Vista menú ----------
class HelpMenuView(discord.ui.View):
    """Select dinámico para navegar categorías."""

    def __init__(self, data: List[Dict]):
        super().__init__(timeout=300)
        self.data = data

        options = [
            discord.SelectOption(
                label=block.get("title", "Sin título"),
                description=f"{len(block.get('commands', []))} comando(s)",
                emoji=block.get("emoji"),
            )
            for block in data
        ]
        self.add_item(_HelpSelect(options, data))


class _HelpSelect(discord.ui.Select):
    def __init__(self, options, data):
        super().__init__(
            placeholder="Selecciona una categoría…",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.data = data

    async def callback(self, interaction: discord.Interaction):
        block = next((b for b in self.data if b.get("title") == self.values[0]), None)
        embed = build_category_embed(block) if block else build_empty_embed()
        await interaction.response.edit_message(embed=embed, view=self.view)


# ---------- Embeds ----------

def build_category_embed(block: Dict) -> discord.Embed:
    lines = [f"**`{c['cmd']}`** → {c['desc']}" for c in block.get("commands", [])]
    embed = discord.Embed(
        title=f"{block.get('emoji', '')} {block.get('title', 'Sin título')}",
        description="\n".join(lines) or "*(sin comandos)*",
        color=discord.Color.green(),
    )
    thumb = block.get("thumbrl", DEFAULT_THUMB)
    if thumb:
        embed.set_thumbnail(url=thumb)
    embed.set_footer(text="Usa el menú para cambiar de categoría •")
    return embed


def build_empty_embed() -> discord.Embed:
    return discord.Embed(
        title="🚫 Ayuda no disponible",
        description="`help_data.json` no se encontró o está dañado. Consulta la consola.",
        color=discord.Color.red(),
    )


# ---------- Cog ----------
class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = _load_help_data()

    # --- Comando prefijo ---
    @commands.command(name="anya")
    async def _anya_prefix(self, ctx: commands.Context):
        """Envía la ayuda con menú (mensaje público)."""
        if not self.data:
            await ctx.send(embed=build_empty_embed())
            return
        embed = build_category_embed(self.data[0])
        view = HelpMenuView(self.data)
        await ctx.send(embed=embed, view=view)

    # --- Comando slash ---
    @app_commands.command(name="anya", description="Muestra la ayuda del bot (menú)")
    async def _anya_slash(self, inter: discord.Interaction):
        """Slash‑command: respuesta *ephemeral*."""
        if not self.data:
            await inter.response.send_message(embed=build_empty_embed(), ephemeral=True)
            return
        embed = build_category_embed(self.data[0])
        view = HelpMenuView(self.data)
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)


# ---------- Setup ----------
async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))