import discord
from discord.ext import commands

from google import genai
from GEMINI_API_KEY import GEMINI_API_KEY

import asyncio
import json
import random
from datetime import datetime, timedelta


# ==================================================
# GEMINI CONFIG - ANTES: MODEL = "gemini-2.5-flash"
# ==================================================

MODEL = "gemini-2.5-flash"

client_genai = genai.Client(api_key=GEMINI_API_KEY)


# ==================================================
# CARGA DE ARCHIVOS DE CONFIGURACIÓN
# ==================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_json("config.json")
PERSONALITY = load_json("personality.json")

BASE_PERSONALITY = PERSONALITY["base_personality"]
FALLBACK_MESSAGE = PERSONALITY["fallback_message"]
TIRED_MESSAGES = PERSONALITY["tired_messages"]
LIMIT_MESSAGES = PERSONALITY["limit_messages"]
KEYWORDS = PERSONALITY["keywords"]


# ==================================================
# PARÁMETROS DE SESIÓN
# ==================================================

MAX_REPLIES = 4
COOLDOWN = timedelta(hours=2)


# ==================================================
# COG
# ==================================================

class GeminiListenerBase(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # sessions[user_id] = {
        #   "channel_id": int,
        #   "personality_prompt": str,
        #   "history": [ {"user": str, "anya": str}, ... ],
        #   "reply_count": int,
        #   "last_bot_message_id": int,
        #   "tired_sent": bool,
        #   "cooldown_until": datetime | None
        # }
        self.sessions: dict[int, dict] = {}

    # ==================================================
    # HELPERS DE CONFIG
    # ==================================================

    def is_channel_allowed(self, guild_id: str, channel_id: str) -> bool:
        if guild_id not in CONFIG["enabled_guilds"]:
            return False

        if channel_id not in CONFIG["enabled_guilds"][guild_id]:
            return False

        return True

    def find_keyword(self, content: str):
        content = content.lower()

        for keyword, prompt in KEYWORDS.items():
            if keyword.lower() in content:
                return keyword, prompt

        return None, None

    # ==================================================
    # HELPERS DE SESIÓN
    # ==================================================

    def get_active_session(self, user_id: int):
        """Regresa la sesión solo si sigue vigente (no está en cooldown/cerrada)."""

        session = self.sessions.get(user_id)

        if session is None:
            return None

        if session["tired_sent"]:
            return None

        return session

    def is_in_cooldown(self, user_id: int) -> bool:
        session = self.sessions.get(user_id)

        if session is None:
            return False

        cooldown_until = session.get("cooldown_until")

        if cooldown_until is None:
            return False

        return datetime.utcnow() < cooldown_until

    def start_session(self, user_id: int, channel_id: str, personality_prompt: str):
        self.sessions[user_id] = {
            "channel_id": channel_id,
            "personality_prompt": personality_prompt,
            "history": [],
            "reply_count": 0,
            "last_bot_message_id": None,
            "tired_sent": False,
            "cooldown_until": None
        }

        return self.sessions[user_id]

    def close_session(self, user_id: int):
        session = self.sessions.get(user_id)

        if session is None:
            return

        session["tired_sent"] = True
        session["cooldown_until"] = datetime.utcnow() + COOLDOWN

    # ==================================================
    # PROMPT BUILDING
    # ==================================================

    def build_prompt(self, personality: str, history: list, user_message: str) -> str:
        history_text = ""

        for turn in history:
            history_text += f"\nUsuario: {turn['user']}\nAnya: {turn['anya']}\n"

        return f"""{BASE_PERSONALITY}

Situación especial:
{personality}

Historial de la conversación:
{history_text if history_text else "(sin mensajes previos)"}

Mensaje del usuario:
{user_message}

Responde ahora:
"""

    async def ask_gemini(self, prompt: str) -> str:

        def request():

            return client_genai.models.generate_content(
                model=MODEL,
                contents=prompt
            )


        try:

            response = await asyncio.to_thread(request)


            if not response.text:

                return FALLBACK_MESSAGE


            return response.text.strip()



        except Exception as e:


            error_text = str(e)


            # Límite gratuito Gemini
            if (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "quota" in error_text.lower()
            ):

                return random.choice(
                    LIMIT_MESSAGES
                )


            print(
                "Error Gemini:",
                e
            )


            return FALLBACK_MESSAGE

    # ==================================================
    # LISTENER
    # ==================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not message.guild:
            return

        guild_id = str(message.guild.id)
        channel_id = str(message.channel.id)
        user_id = message.author.id

        # ----------------------------------------
        # CASO 1: es un reply dirigido al bot
        # ----------------------------------------

        if message.reference is not None:
            await self.handle_reply(message, user_id, channel_id)
            return

        # ----------------------------------------
        # CASO 2: posible nueva llamada con keyword
        # ----------------------------------------

        if not self.is_channel_allowed(guild_id, channel_id):
            return

        keyword, personality = self.find_keyword(message.content)

        if not keyword:
            return

        await self.handle_new_call(message, user_id, channel_id, personality)

    # ==================================================
    # MANEJO: NUEVA LLAMADA (KEYWORD)
    # ==================================================

    async def handle_new_call(self, message, user_id, channel_id, personality):
        # Si está en cooldown (ya se le dijo que está cansada), la ignora
        if self.is_in_cooldown(user_id):
            return

        session = self.start_session(user_id, channel_id, personality)

        prompt = self.build_prompt(personality, session["history"], message.content)

        try:
            answer = await self.ask_gemini(prompt)
            bot_message = await message.reply(answer)

            session["last_bot_message_id"] = bot_message.id
            session["history"].append({
                "user": message.content,
                "anya": answer
            })

        except Exception as e:
            await message.channel.send(f"⚠️ Error Gemini: {e}")

    # ==================================================
    # MANEJO: REPLY A UN MENSAJE DEL BOT
    # ==================================================

    async def handle_reply(self, message, user_id, channel_id):
        session = self.get_active_session(user_id)

        if session is None:
            return

        # El reply debe ser al ÚLTIMO mensaje que Anya le mandó a ESTE usuario
        if session["channel_id"] != channel_id:
            return

        if message.reference.message_id != session["last_bot_message_id"]:
            return

        # Ya agotó sus 4 replies -> este intento (el 5to) dispara el mensaje de cansancio
        if session["reply_count"] >= MAX_REPLIES:
            tired_message = random.choice(TIRED_MESSAGES)

            try:
                await message.reply(tired_message)
            except Exception as e:
                await message.channel.send(f"⚠️ Error Gemini: {e}")

            self.close_session(user_id)
            return

        # Responder normalmente, usando el historial como contexto
        prompt = self.build_prompt(
            session["personality_prompt"],
            session["history"],
            message.content
        )

        try:
            answer = await self.ask_gemini(prompt)
            bot_message = await message.reply(answer)

            session["last_bot_message_id"] = bot_message.id
            session["reply_count"] += 1
            session["history"].append({
                "user": message.content,
                "anya": answer
            })

        except Exception as e:
            await message.channel.send(f"⚠️ Error Gemini: {e}")


# ==================================================
# LOAD COG
# ==================================================

async def setup(bot):
    await bot.add_cog(GeminiListenerBase(bot))