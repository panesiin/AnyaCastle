# fake_messages.py
import json, discord, random
from pathlib import Path
from discord.ext import commands
from discord import app_commands
from datetime import datetime

CONFIG_FILE = Path(__file__).with_name("fake_config.json")
USAGE_FILE = Path(__file__).with_name("fake_usage.json")

OWNER_ID = 429790043054407680  # Tu ID de Discord

class FakeMessages(commands.Cog):
    """Sistema avanzado de mensajes fake con límite diario y comandos de owner."""

    def __init__(self, bot):
        self.bot = bot
        self.config = self.cargar_config()
        self.usos = self.cargar_usos()

    # ===========================
    # CONFIGURACIÓN
    # ===========================

    def cargar_config(self):
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        base = {"triggers": {}}
        CONFIG_FILE.write_text(json.dumps(base, indent=4, ensure_ascii=False))
        return base

    def cargar_usos(self):
        if USAGE_FILE.exists():
            return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        base = {"fecha": self.fecha_actual(), "usos": {}}
        USAGE_FILE.write_text(json.dumps(base, indent=4))
        return base

    def guardar_usos(self):
        USAGE_FILE.write_text(json.dumps(self.usos, indent=4))

    def fecha_actual(self):
        return datetime.now().strftime("%Y-%m-%d")

    # Reset automático a medianoche
    def revisar_reset_diario(self):
        if self.usos["fecha"] != self.fecha_actual():
            self.usos = {"fecha": self.fecha_actual(), "usos": {}}
            self.guardar_usos()

    # ===========================
    # WEBHOOK
    # ===========================

    async def obtener_webhook(self, channel: discord.TextChannel):
        webhooks = await channel.webhooks()
        for w in webhooks:
            if w.name == "FakeCloner":
                return w
        return await channel.create_webhook(name="FakeCloner")

    # ===========================
    # EVENTO PRINCIPAL
    # ===========================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        self.revisar_reset_diario()

        # Verificar si ya usó su trigger diario
        if str(message.author.id) in self.usos["usos"]:
            return

        contenido = message.content.lower()
        for patron, respuestas in self.config["triggers"].items():
            if "{comer}" in patron:
                base = patron.replace("{comer}", "").strip()
                if contenido.startswith(base):
                    resto = contenido[len(base):].strip()
                    if not resto:
                        return
                    # guardar como usado
                    self.usos["usos"][str(message.author.id)] = True
                    self.guardar_usos()
                    await self.procesar_fake(message, respuestas)
                    return

    # ===========================
    # MENSAJE FAKE
    # ===========================

    async def procesar_fake(self, message: discord.Message, respuestas: list):
        webhook = await self.obtener_webhook(message.channel)
        autor = message.author
        fake_text = random.choice(respuestas)
        try:
            await message.delete()
        except:
            pass
        await webhook.send(
            fake_text,
            username=f"{autor.display_name}",
            avatar_url=autor.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.none()
        )

    # ===========================
    # /ecosimulado — solo owner, con canal
    # ===========================

    @app_commands.command(
        name="ecosimulado",
        description="Envía un mensaje fake usando el nombre de otro usuario en un canal específico."
    )
    @app_commands.describe(
        usuario="Usuario a simular",
        canal="Canal donde se enviará el mensaje",
        texto="Texto falso a enviar"
    )
    async def eco_simulado(self, interaction: discord.Interaction, usuario: discord.Member, canal: discord.TextChannel, texto: str):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        # Validar que el canal pertenece al mismo servidor
        if canal.guild.id != interaction.guild.id:
            return await interaction.response.send_message("❌ Ese canal no pertenece a este servidor.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        webhook = await self.obtener_webhook(canal)
        await webhook.send(
            texto,
            username=f"{usuario.display_name}",
            avatar_url=usuario.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.none()
        )
        await interaction.followup.send(f"✔ Mensaje fake enviado en {canal.mention}.", ephemeral=True)

    # ===========================
    # /fakemensajes_reset — solo owner
    # ===========================

    @app_commands.command(name="fakemensajes_reset", description="Reinicia el contador de usos diarios.")
    async def fakemensajes_reset(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        self.usos = {"fecha": self.fecha_actual(), "usos": {}}
        self.guardar_usos()
        await interaction.response.send_message("🔄 Todos los usos diarios han sido reiniciados.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(FakeMessages(bot))
