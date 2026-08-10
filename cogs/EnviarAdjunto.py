import discord
from discord import app_commands
from discord.ext import commands

class EnviarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot_owner_id: int | None = None  # cache del dueño

    async def get_owner_id(self):
        """Obtiene el ID del dueño (usa caché para evitar lag)."""
        if self.bot_owner_id is None:
            info = await self.bot.application_info()
            self.bot_owner_id = info.owner.id
        return self.bot_owner_id

    # -------- AUTOCOMPLETADOS --------
    async def autocomplete_servidores(
        self, interaction: discord.Interaction, current: str
    ):
        """Autocompleta servidores donde está el bot."""
        opciones = [
            app_commands.Choice(name=g.name, value=str(g.id))
            for g in self.bot.guilds
            if current.lower() in g.name.lower()
        ]
        return opciones[:25]

    async def autocomplete_canales(
        self, interaction: discord.Interaction, current: str
    ):
        """Autocompleta canales del servidor elegido."""
        servidor_id = interaction.namespace.servidor
        if not servidor_id:
            return []
        guild = self.bot.get_guild(int(servidor_id))
        if not guild:
            return []
        opciones = [
            app_commands.Choice(name=f"#{c.name}", value=str(c.id))
            for c in guild.text_channels
            if c.permissions_for(guild.me).send_messages and current.lower() in c.name.lower()
        ]
        return opciones[:25]

    # -------- COMANDO PRINCIPAL --------
    @app_commands.command(
        name="enviar",
        description="Envía un mensaje y/o archivo a un servidor donde esté el bot (solo dueño)."
    )
    @app_commands.describe(
        archivo="Adjunta una imagen o archivo para enviar",
        texto="Texto a enviar junto al archivo",
        servidor="Servidor de destino",
        canal="Canal del servidor donde enviar el mensaje"
    )
    @app_commands.autocomplete(
        servidor=autocomplete_servidores,
        canal=autocomplete_canales
    )
    async def enviar(
        self,
        interaction: discord.Interaction,
        archivo: discord.Attachment | None,
        texto: str,
        servidor: str,
        canal: str | None = None
    ):
        # --- Verificación de dueño ---
        owner_id = await self.get_owner_id()
        if interaction.user.id != owner_id:
            await interaction.response.send_message(
                "🚫 Solo el **dueño del bot** puede usar este comando.",
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        # Obtener servidor
        guild = self.bot.get_guild(int(servidor))
        if not guild:
            await interaction.followup.send("❌ No se encontró el servidor indicado.")
            return

        # Obtener canal
        if canal:
            channel = guild.get_channel(int(canal))
        else:
            # Si no se especifica, usa el primer canal escribible
            channel = discord.utils.find(
                lambda c: isinstance(c, discord.TextChannel)
                and c.permissions_for(guild.me).send_messages,
                guild.text_channels
            )

        if not channel:
            await interaction.followup.send("⚠️ No se encontró un canal válido en ese servidor.")
            return

        # Procesar archivo si hay
        files = []
        if archivo is not None:
            import io
            data = await archivo.read()
            files.append(discord.File(io.BytesIO(data), filename=archivo.filename))

        # Enviar mensaje
        await channel.send(content=texto or None, files=files)

        await interaction.followup.send(
            f"✅ Mensaje enviado a **{guild.name}** en **#{channel.name}**.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(EnviarCog(bot))
