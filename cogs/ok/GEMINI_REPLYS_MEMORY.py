import discord
from discord.ext import commands

from google import genai
from GEMINI_API_KEY import GEMINI_API_KEY

import json
import asyncio
import os
import time
import random
import re
from datetime import datetime


# ==================================================
# CONFIGURACIÓN
# ==================================================

MODEL = "gemini-2.5-flash"


MAX_REPLIES = 4

# Tiempo sin respuesta antes de guardar memoria
MEMORY_DELAY = 180

# Tiempo que un usuario queda sin poder volver a activar aprendizaje
USER_COOLDOWN = 7200

# Bloqueo global después de guardar memoria
GLOBAL_COOLDOWN = 60


TIRED_MESSAGES = [
    "Waaa... Anya está cansada ehehe~",
    "Anya necesita dormir un poquito... zzz",
    "Misión descanso activada... Anya vuelve después.",
    "Waku waku terminó por hoy... Anya necesita energía."
]


# ==================================================
# GEMINI
# ==================================================

client_genai = genai.Client(
    api_key=GEMINI_API_KEY
)



# ==================================================
# ARCHIVOS
# ==================================================

MEMORY_FOLDER = "memory/users"


def ensure_memory_folder():

    if not os.path.exists(MEMORY_FOLDER):
        os.makedirs(MEMORY_FOLDER)



def get_memory_path(user_id):

    ensure_memory_folder()

    return os.path.join(
        MEMORY_FOLDER,
        f"{user_id}.json"
    )



def load_memory(user_id):

    path = get_memory_path(user_id)


    if not os.path.exists(path):

        return {

            "user_id": user_id,
            "username": "",
            "display_name": "",
            "context": "",
            "updated": ""

        }


    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)


    except Exception:

        return {

            "user_id": user_id,
            "username": "",
            "display_name": "",
            "context": "",
            "updated": ""

        }



def save_memory(data):

    path = get_memory_path(
        data["user_id"]
    )


    data["updated"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )



# ==================================================
# PROMPTS
# ==================================================

PERSONALITY = """

Responde como Anya Forger de Spy x Family.

Reglas:

- Responde brevemente.
- Sé adorable, inocente y graciosa.
- Usa expresiones tipo Anya.
- Sigue el juego del usuario.
- No seas formal.
- No expliques demasiado.

"""


MEMORY_PROMPT = """

Eres el sistema de memoria de un bot.

Analiza una conversación entre un usuario y Anya.

Actualiza el contexto permanente del usuario.

Reglas:

- Guarda solamente información útil a futuro.
- No guardes saludos.
- No guardes bromas pasajeras.
- No guardes emociones temporales.
- No guardes preguntas.
- Resume información repetida.
- Mantén frases cortas.
- Máximo 6 frases.

Devuelve únicamente el contexto final.
Sin explicaciones.

"""



# ==================================================
# GEMINI REQUEST
# ==================================================

async def ask_gemini(prompt):

    def request():

        return client_genai.models.generate_content(

            model=MODEL,

            contents=prompt

        )


    response = await asyncio.to_thread(
        request
    )


    if not hasattr(response, "text"):

        return ""


    return response.text.strip()



# ==================================================
# DETECCIÓN DE PERSONAS
# ==================================================

def extract_names(text):

    """
    Busca posibles nombres mencionados.
    """

    words = re.findall(
        r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b",
        text
    )

    return words



def find_user_context(bot, message):

    """
    Busca usuarios mencionados por:
    - Mention Discord
    - Nombre visible
    """

    found = []


    # Menciones reales

    for member in message.mentions:

        found.append(member)



    # Buscar nombres escritos

    names = extract_names(
        message.content
    )


    if names:

        for member in message.guild.members:

            if member.bot:
                continue


            if (
                member.display_name in names
                or member.name in names
            ):

                if member not in found:

                    found.append(member)



    return found

# ==================================================
# COG PRINCIPAL
# ==================================================

class GeminiMemoryTest(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


        # Conversaciones activas en RAM
        self.conversations = {}


        # Usuarios que ya aprendieron y están descansando
        self.user_cooldowns = {}


        # Bloqueo global temporal
        self.global_cooldown_until = 0



        # Cargar configuración
        with open(
            "keywords.json",
            "r",
            encoding="utf-8"
        ) as f:

            self.triggers = json.load(f)



        with open(
            "config.json",
            "r",
            encoding="utf-8"
        ) as f:

            self.config = json.load(f)



    # ==================================================
    # CREAR CONVERSACIÓN
    # ==================================================

    def start_conversation(self, user_id):

        self.conversations[user_id] = {

            "history": [],

            "reply_count": 0,

            "last_activity": time.time(),

            "ready": False

        }



    def add_history(self, user_id, role, text):

        if user_id not in self.conversations:

            self.start_conversation(user_id)


        self.conversations[user_id]["history"].append({

            "role": role,

            "text": text

        })


        self.conversations[user_id]["last_activity"] = time.time()



    # ==================================================
    # GENERAR RESPUESTA NORMAL
    # ==================================================

    async def generate_answer(self, message):


        context = ""


        # Buscar personas mencionadas

        users = find_user_context(
            self.bot,
            message
        )


        if users:

            context += "\nInformación conocida:\n"


            for user in users:

                memory = load_memory(
                    user.id
                )


                if memory["context"]:

                    context += (
                        f"\n{user.display_name}: "
                        f"{memory['context']}"
                    )



        # Memoria propia del usuario

        own_memory = load_memory(
            message.author.id
        )


        if own_memory["context"]:

            context += (
                "\nInformación del usuario:\n"
                + own_memory["context"]
            )



        prompt = (

            PERSONALITY

            + context

            + "\n\nMensaje:\n"

            + message.content

        )


        return await ask_gemini(prompt)



    # ==================================================
    # GUARDAR MEMORIA
    # ==================================================

    async def save_conversation_memory(self, user_id):


        conversation = self.conversations.get(
            user_id
        )


        if not conversation:

            return



        old_memory = load_memory(
            user_id
        )


        history = "\n".join(

            [

                f"{x['role']}: {x['text']}"

                for x in conversation["history"]

            ]

        )



        prompt = (

            MEMORY_PROMPT

            + "\n\nContexto actual:\n"

            + old_memory["context"]

            + "\n\nConversación:\n"

            + history

        )


        try:

            new_context = await ask_gemini(
                prompt
            )


            old_memory["context"] = new_context

            save_memory(
                old_memory
            )


        except Exception as e:

            print(
                "Error guardando memoria:",
                e
            )


        finally:

            if user_id in self.conversations:

                del self.conversations[user_id]


            self.user_cooldowns[user_id] = (
                time.time()
                + USER_COOLDOWN
            )



            self.global_cooldown_until = (
                time.time()
                + GLOBAL_COOLDOWN
            )



    # ==================================================
    # ESPERA DE MEMORIA
    # ==================================================

    async def memory_wait(self, user_id):

        await asyncio.sleep(
            MEMORY_DELAY
        )


        conversation = self.conversations.get(
            user_id
        )


        if not conversation:

            return



        elapsed = (
            time.time()
            -
            conversation["last_activity"]
        )


        if elapsed >= MEMORY_DELAY:

            await self.save_conversation_memory(
                user_id
            )



        else:

            # Reinicia espera si hubo actividad

            asyncio.create_task(
                self.memory_wait(user_id)
            )



    # ==================================================
    # LISTENER PRINCIPAL
    # ==================================================

    @commands.Cog.listener()
    async def on_message(self, message):


        if message.author.bot:

            return



        if not message.guild:

            return



        guild_id = str(
            message.guild.id
        )

        channel_id = str(
            message.channel.id
        )


        if guild_id not in self.config["enabled_guilds"]:

            return



        if channel_id not in self.config["enabled_guilds"][guild_id]:

            return



        user_id = message.author.id



        # =============================================
        # REPLY A ANYA
        # =============================================

        if message.reference:


            try:

                replied = await message.channel.fetch_message(
                    message.reference.message_id
                )


                if replied.author.id == self.bot.user.id:


                    if user_id in self.conversations:


                        cooldown = self.user_cooldowns.get(
                            user_id,
                            0
                        )


                        if time.time() < cooldown:

                            await message.reply(
                                random.choice(
                                    TIRED_MESSAGES
                                )
                            )

                            return



                        conversation = self.conversations[user_id]


                        if conversation["reply_count"] >= MAX_REPLIES:


                            await message.reply(
                                random.choice(
                                    TIRED_MESSAGES
                                )
                            )

                            return



                        answer = await self.generate_answer(
                            message
                        )


                        await message.reply(
                            answer
                        )


                        self.add_history(
                            user_id,
                            "Usuario",
                            message.content
                        )


                        self.add_history(
                            user_id,
                            "Anya",
                            answer
                        )


                        conversation["reply_count"] += 1



                        if conversation["reply_count"] >= 3:

                            conversation["ready"] = True



                        if conversation["ready"]:

                            asyncio.create_task(
                                self.memory_wait(
                                    user_id
                                )
                            )



                        return



            except Exception as e:

                print(
                    "Reply error:",
                    e
                )



        # =============================================
        # KEYWORDS
        # =============================================


        text = message.content.lower()


        trigger_found = None


        for trigger in self.triggers:

            words = trigger.lower().split()


            if all(
                word in text
                for word in words
            ):

                trigger_found = trigger

                break



        if not trigger_found:

            return



        # Crear conversación

        self.start_conversation(
            user_id
        )



        answer = await self.generate_answer(
            message
        )


        await message.reply(
            answer
        )



        self.add_history(
            user_id,
            "Usuario",
            message.content
        )


        self.add_history(
            user_id,
            "Anya",
            answer
        )


        self.conversations[user_id]["reply_count"] = 1




# ==================================================
# CARGA DEL COG
# ==================================================

async def setup(bot):

    await bot.add_cog(
        GeminiMemoryTest(bot)
    )