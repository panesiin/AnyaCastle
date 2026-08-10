import discord
from discord.ext import commands
from discord import Embed
from google import genai
from GEMINI_API_KEY import GEMINI_API_KEY
import asyncio
from datetime import datetime, timezone

# --- Configuración ---
try:
    client_genai = genai.Client(api_key=GEMINI_API_KEY)
    client_genai.models.list()
    print("✔  GEN-IA.")
except Exception as e:
    print(f"ADVERTENCIA: Error al inicializar genai.Client: {e}")
    client_genai = None

DELAY_SECONDS = 5

class CelebrityGreetingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = client_genai

    @commands.command(name="saludame")
    async def saludame(self, ctx, *, celebridad: str):
        """
        Pide un saludo a una celebridad.
        Uso: !saludame [Nombre de la celebridad]
        """
        if not self.client:
            await ctx.reply("⚠️ El módulo de IA no se inicializó correctamente. Revisa la consola.")
            return

        # 1️⃣ Mensaje inicial
        try:
            message = await ctx.reply(
                f"📨 **¡Soliciwaku enviada!** <:sleep4:1320810547058573344> "
                f"Anya está contactando mentalmente a **{celebridad}**... ¡Un momento Mmmh <:sleep3:1320810537625325650> !"
            )
        except discord.Forbidden:
            print(f"Error: No se pudo enviar mensaje de confirmación en {ctx.channel.name}")
            return

        # 2️⃣ Simular proceso de generación con 'typing'
        async with ctx.typing():
            await asyncio.sleep(DELAY_SECONDS)

            prompt = (
                f"Actúa exactamente y únicamente como si fueras {celebridad}. "
                f"Un fan tuyo en Discord llamado '{ctx.author.display_name}' te ha pedido que le mandes un saludo tuyo. "
                f"Escríbele un mensaje de un saludo tuyo corto (máximo 2 o 3 frases). "
                f"Captura perfectamente la personalidad de la celebridad, influencer, etc, con su tono de voz y sus vibras. "
                f"No rompas el personaje. No digas 'Soy un modelo de IA' ni nada parecido. Solo actúa."
                f"Si '{celebridad}' no parece ser una persona conocida o no hay suficiente información para imitarla correctamente, "
                f"pide brevemente como si fueras Anya Forger de Spy x Family que el usuario te dé un nombre más completo o que intente con otra persona más reconocida para contactar con su celebridad."
            )

            try:
                def generate_sync_call():
                    return self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                
                response = await asyncio.to_thread(generate_sync_call)

                if not hasattr(response, 'text') or not response.text:
                    raise Exception("La respuesta de la IA no contiene texto.")

                clean_text = " ".join(response.text.split())

            except Exception as e:
                print(f"Error generando respuesta de GenAI: {e}")
                await message.edit(
                    content=f"⚠️ Hubo un problema contactando a **{celebridad}**. "
                            f"Parece que la línea está ocupada o colgó la llamada. (Error: {e})"
                )
                return

        # 3️⃣ Crear Embed final
        embed = Embed(
            title=f"💌 ¡Tienes un wakusaludo especial! ✨",
            description=f"**\"{clean_text}\"**",
            color=discord.Color.random()
        )
        embed.add_field(name="📸 De:", value=f"**{celebridad}**", inline=True)
        embed.add_field(name="👤 Para:", value=f"{ctx.author.mention}", inline=True)
        embed.set_footer(
            text=f"Enviado con cariño por {celebridad} 💫",
            icon_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None
        )
        embed.timestamp = datetime.now(timezone.utc)

        # 4️⃣ Editar el mismo mensaje con el resultado final
        await message.edit(content=None, embed=embed)

# --- Setup del cog ---
async def setup(bot):
    if not client_genai:
        return
        
    await bot.add_cog(CelebrityGreetingCog(bot))
