import discord
from discord.ext import commands
from discord.ui import View
import asyncio
import random

class QuizCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quizzes = {}
        self.cooldowns = {}
        self.global_cooldown = 30
        self.load_quizzes()

    def load_quizzes(self):
        try:
            with open('quizzes.txt', 'r', encoding='utf-8') as file:
                for line in file:
                    topic, question, hint = line.strip().split(':')
                    if topic not in self.quizzes:
                        self.quizzes[topic] = {}
                    self.quizzes[topic][question] = hint
        except FileNotFoundError:
            print("Error: No se pudo encontrar el archivo de quizzes.")

    async def timer(self, duration, message, base_embed):
        for remaining in range(duration, 0, -1):
            embed = base_embed.copy()
            embed.set_footer(text=f"\u23f3 Tiempo restante: {remaining} segundos")
            try:
                await message.edit(embed=embed)
                await asyncio.sleep(1)
            except discord.NotFound:
                break

    @commands.command(name="quiz", help="Inicia un juego de quiz con subtemas.")
    async def quiz(self, ctx):
        user_id = ctx.author.id
        channel_id = ctx.channel.id

        if self.cooldowns.get(channel_id, 0) > 0:
            await ctx.send("> ❌ Este canal está en cooldown. Espera un momento.")
            return

        view = self.TopicSelectionView(ctx, self.bot, self.quizzes, self.timer)
        embed = discord.Embed(
            title="Selecciona un tema para el quiz",
            description="**Pulsa uno de los botones de abajo para elegir un tema**\n\n ⚠️ _Solo el autor puede elegir el tema_",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/966755203787407370/1321130197944242228/feliz2.png")
        await ctx.send(embed=embed, view=view)

        self.cooldowns[channel_id] = self.global_cooldown
        await asyncio.sleep(self.global_cooldown)
        self.cooldowns[channel_id] = 0

    class TopicSelectionView(View):
        def __init__(self, ctx, bot, quizzes, timer_func):
            super().__init__(timeout=30)
            self.ctx = ctx
            self.bot = bot
            self.quizzes = quizzes
            self.timer_func = timer_func

        async def interaction_check(self, interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message(
                    "⚠️ Solo el autor del comando puede interactuar con este quiz.", ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="Festivo", style=discord.ButtonStyle.secondary)
        async def festivo_button(self, interaction, button):
            await self.send_question("festivo", interaction)

        @discord.ui.button(label="Música", style=discord.ButtonStyle.secondary)
        async def musica_button(self, interaction, button):
            await self.send_question("musica", interaction)

        @discord.ui.button(label="Películas", style=discord.ButtonStyle.secondary)
        async def peliculas_button(self, interaction, button):
            await self.send_question("peliculas", interaction)

        @discord.ui.button(label="Otros", style=discord.ButtonStyle.secondary)
        async def otros_button(self, interaction, button):
            await self.send_question("otros", interaction)

        async def send_question(self, topic, interaction):
            await interaction.response.defer()
            await interaction.message.delete()

            if len(self.quizzes[topic]) < 4:
                await self.ctx.send(f"❌ No hay suficientes preguntas en el tema '{topic}'.")
                return

            question, hint = random.choice(list(self.quizzes[topic].items()))
            options = random.sample(list(self.quizzes[topic].keys()), 4)
            if question not in options:
                options[0] = question
            random.shuffle(options)

            description = f"🎵 **Pista:** {hint}\n\n"
            description += f"**{options[0]}\u2800\u2800\u2800\u2800\u2800\u2800{options[1]}**\n"
            description += f"**{options[2]}\u2800\u2800\u2800\u2800\u2800\u2800{options[3]}**\n"

            embed = discord.Embed(
                title=f"¡Adivina el quizz... _Tema elegido: **{topic.capitalize()}**_",
                description=description,
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/966755203787407370/1321129971628118039/pensar.png")
            embed.set_footer(text="⏳ Tiempo restante: 30 segundos")

            message = await self.ctx.send(embed=embed)

            def check(m):
                return m.channel == self.ctx.channel and m.content.strip().lower() in [opt.lower() for opt in options]

            try:
                timer_task = asyncio.create_task(self.timer_func(30, message, embed))
                response_task = asyncio.create_task(self.bot.wait_for('message', check=check, timeout=30))
                done, pending = await asyncio.wait([timer_task, response_task], return_when=asyncio.FIRST_COMPLETED)

                for task in pending:
                    task.cancel()

                if response_task in done:
                    msg = response_task.result()
                    selected_option = msg.content.strip()
                    if selected_option.lower() == question.lower():
                        result_embed = discord.Embed(
                            title="🎉 ¡Correcto!",
                            description=f"¡Era **{question}**! Respondido correctamente por {msg.author.mention}.",
                            color=discord.Color.green()
                        )
                        result_embed.set_thumbnail(url="https://media.discordapp.net/attachments/966755203787407370/1321129997829804092/ok.png")
                        await message.edit(embed=result_embed)
                    else:
                        result_embed = discord.Embed(
                            title="🤏 La respuesta era:",
                            description=f"**{question}**.",
                            color=discord.Color.red()
                        )
                        result_embed.set_thumbnail(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_ksC-_7qUN_geMkRS3SvxGNPs6sWrb8iQYw&s")
                        await message.edit(embed=result_embed)
                else:
                    await message.delete()
                    await self.ctx.send("⏳ Tiempo agotado. ¡Más rápido para la próxima!")
            except asyncio.TimeoutError:
                await message.delete()
                await self.ctx.send("⏳ Tiempo agotado. ¡Más rápido para la próxima!")

async def setup(bot):
    await bot.add_cog(QuizCog(bot))