import discord
from discord.ext import commands
from google import genai
from GEMINI_API_KEY import GEMINI_API_KEY
import json
import asyncio

# API Key en variable de entorno
client_genai = genai.Client(api_key=GEMINI_API_KEY)

# Cargar triggers desde JSON
with open("keywords.json", "r", encoding="utf-8") as f:
    TRIGGERS = json.load(f)

# Cargar configuración de servidores y canales
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

class GeminiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Comando manual de texto ---
    @commands.command(name="ia")
    async def ia(self, ctx, *, prompt: str):
        """Genera texto con Gemini 2.5 Flash"""
        try:
            response = client_genai.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            clean_text = " ".join(response.text.split())
            await ctx.send(clean_text)
        except Exception as e:
            await ctx.send(f"⚠️ Error: {e}")

    # --- Escuchar mensajes para triggers automáticos ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        guild_id = str(message.guild.id) if message.guild else None
        channel_id = str(message.channel.id) if message.channel else None

        # Revisar si guild y canal están permitidos
        if not guild_id or not channel_id:
            return
        if guild_id not in CONFIG["enabled_guilds"]:
            return
        if channel_id not in CONFIG["enabled_guilds"][guild_id]:
            return

        msg_lower = message.content.lower()
        trigger_found = None
        for trigger, prompt_template in TRIGGERS.items():
            # Palabras clave parciales: detecta variantes
            trigger_words = trigger.lower().split()
            if all(word in msg_lower for word in trigger_words):
                trigger_found = trigger
                break

        if not trigger_found:
            return

        # --- Preparar prompt final con conciencia ligera y contextual ---
        full_prompt = TRIGGERS[trigger_found] + f" : '{message.content}'"

        # Conciencia contextual ligera sobre Abi
        if "abi" in msg_lower:
            full_prompt += (
                " Mantén tu estilo y personalidad, pero puedes integrar brevemente comentarios cortos "
                "positivos sobre Abi cuando sea relevante al contexto del mensaje. "
                "No fuerces la mención, solo cuando tenga sentido con la conversación y sé muy breve."
                "Abi es como una segunda hermana lejana tuya, se llevan muy bien, le gusta dibujar."
            )

        try:
            # Generar respuesta directamente en reply
            def generate_sync_call():
                return client_genai.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt
                )

            response = await asyncio.to_thread(generate_sync_call)

            if not hasattr(response, 'text') or not response.text:
                raise Exception("La IA no devolvió texto.")

            clean_text = " ".join(response.text.split())

            # Enviar la respuesta como reply directo
            await message.reply(clean_text)

        except Exception as e:
            await message.channel.send(f"⚠️ Error generando respuesta automática: {e}")

async def setup(bot):
    await bot.add_cog(GeminiCog(bot))
