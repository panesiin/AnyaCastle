import json
import unicodedata
from pathlib import Path
import time
import discord
from discord.ext import commands

# -------------------------------------------------------------------
#                🔎 RESPUESTAS EXACTAS (reply sin ping)
# -------------------------------------------------------------------

def _strip_accents(text: str) -> str:
    """Convierte 'Canción' → 'cancion' (insensible a tildes y a 'ñ')."""
    return ''.join(
        ch for ch in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(ch) != "Mn"
    )

# --- cargamos y normalizamos una vez ---
REPLIES_FILE = Path(__file__).with_name("exact_replies.json")
with REPLIES_FILE.open(encoding="utf-8") as f:
    _raw_replies: dict[str, str] = json.load(f)

EXACT_REPLIES: dict[str, str] = {
    _strip_accents(k.strip()): v for k, v in _raw_replies.items()
}
# -------------------------------------------------------------------

class FrasesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns: dict[str, float] = {}

    # --- SIN CAMBIAR LA LÓGICA DE COOLDOWN ---
    def _exact_on_cd(self, phrase: str, user_id: int) -> bool:
        return self.cooldowns.get(f"ex_{phrase}_{user_id}", 0) > time.time()

    @commands.Cog.listener("on_message")
    async def on_message_exact(self, message: discord.Message):
        if message.author.bot:
            return

        # ① normalizamos minúsculas + sin tildes + strip espacios
        normalized = _strip_accents(message.content.strip())

        # ② comprobamos en el dict cargado de JSON (ya normalizado)
        if normalized in EXACT_REPLIES:
            if self._exact_on_cd(normalized, message.author.id):
                return

            await message.reply(EXACT_REPLIES[normalized], mention_author=False)
            # ③ cooldown usa la misma key normalizada (no afecta lógica)
            self.cooldowns[f"ex_{normalized}_{message.author.id}"] = time.time() + 120

async def setup(bot: commands.Bot):
    await bot.add_cog(FrasesCog(bot))