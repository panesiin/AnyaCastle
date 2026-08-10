import random, json, asyncio
from pathlib import Path
import discord
from discord.ext import commands

DATA_FILE = Path(__file__).with_name("secso_count.json")

# ──────── helpers de estadísticas ──────────────────────────────────────
def cargar_stats():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {}

def guardar_stats(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))

# ──────── frases ───────────────────────────────────────────────────────
FRASES_AMOR = FRASES_AMOR = [
    "de forma intensa, telepática y ligeramente ilegal en 9 países <:surprise6:1320810691321532560>",
    "con tanto entusiasmo que me tuve que tapar los ojos <:sleep2:1320810528796315700>",
    "rompiendo las leyes de la física y del buen gusto <:spy2:1320810637714133063>",
    "como si fuera la última escena de un hentai prohibido <:surprise5:1320810683125993504>",
    "donde las miradas hablaban más que las palabras... y las nalgadas <:surprise:1320810649743392809>",
    "hasta que el suelo pidió clemencia y la cama firmó renuncia <:sospechoso:1320810594584100885>",
    "con tanto movimiento que el WiFi se cayó de la vergüenza <:sospechoso2:1320810605648805950>",
    "a un ritmo que hizo temblar todo LATAM <:fall:1320810176504139806>",
    "entre gemidos cósmicos y risas nerviosas del universo <:serius:1320810446835679283>",
    "con pasión, jadeos... y dos calzones que no aparecieron más <:feliz2:1320810225388880005>",
    "tan intensamente que Google pidió confirmación de identidad <:inspect3:1320810259698286687>",
    "con una técnica que haría llorar de orgullo a un maestro Pokémon <:inspect:1320810245181935657>",
    "como si tuvieran la guía secreta de Kamasutra versión Anya <:feliz1:1320810209597456536>",
    "hasta que el colchón emitió un bug report con stack overflow <:face:1320810146959724546>",
    "invocando posiciones que ni ChatGPT puede describir claramente <:horror:1320810235195166730>",
    "a gritos de *“más lento”* y *“más fuerte”* al mismo tiempo <:serius3:1320810480608083978>", 
    "con susurros que los ángeles enmudecieron y los demonios tomaron nota <:spy2:1320810637714133063>",
    "hasta donde las paredes escucharon, aprendieron… y también se mojaron <:surprise2:1320810658228338748>",
    "con ritmo, sabor y un colapso existencial incluido <:sad4:1320810436001792001>",
    "hasta que el alma salió del cuerpo y dijo: 'yo vuelvo cuando terminen' <:serius3:1320810480608083978>",
    "tan intensamente que Discord los mandó al canal NSFW automáticamente <:surprise3:1320810666239590461>",
    "con pausas dramáticas, mordidas estratégicas y 404 gemidos encontrados <:angel:1320810068035375104>",
    "desatando una tormenta hormonal que llegó a los servidores de Tokio <:surprise4:1320810674363826239>",
    "hasta que los vecinos se suscribieron en silencio a los sonidos del deseo <:sport:1320810616067199097>",
    "a tal nivel que los moderadores recibieron un ticket automático <:peace:1320808504323477504>",
    "al punto de invocar accidentalmente a un succubus <:curiosa:1320810123819749556>",
]

FRASES_SPICY = [
    "como dos conejos entrenados por un demonio del hentai <:poke:1320810361414483968>",
    "a tal nivel que el colchón pidió asilo político <:perv:1320810348504285274>",
    "sin piedad, sin ropa... y sin arrepentimientos <:mide:1320810288660090960>",
    "como si estuvieran en modo PvP... pero sin ropa <:horror:1320810235195166730>",
    "tan frutidelicioso que este mensaje solo aparece con un 5%, de probabilidad <:pensar:1320810337825587271>",
]

# ⬇️ Cambia estas URLs por las que obtengas al subir tus GIFs
GIFS_AMOR = [
    "https://media.discordapp.net/attachments/1386190643725860916/1386191171293941770/1.gif?ex=6858cea1&is=68577d21&hm=8ff7d2b018217005e953501aafba1e44927c5bbc3960b8b06e807be7403d1043&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191171700920330/3.gif?ex=6858cea1&is=68577d21&hm=88cd039faa607856949b6a97224764bf4adf89835e1a365b77a723f3d09b6050&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191172548034641/4.gif?ex=6858cea1&is=68577d21&hm=be288afa935e695503f57bf22e2698ca24a068a6362e9e40a263880391354a63&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191172992503825/5.gif?ex=6858cea1&is=68577d21&hm=40b5b3f7382f8067a9a76490ce2a2c07f7ab081eb52ee6379d1fdcccc86045a3&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191173567385721/6.gif?ex=6858cea1&is=68577d21&hm=b2e7290e452e558670cdfe5371f72799c9bd792f40b85aab9e387cb32642d7ad&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191173982355476/8.gif?ex=6858cea2&is=68577d22&hm=ddf38e0e65df74fa171a86d5c8430981e56743d0d74645e386d80857dff339a9&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191174339137536/9.gif?ex=6858cea2&is=68577d22&hm=08d247d2e0f027317941551215f55e00b16aab057e5b723420b850523b8cad9e&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191174661837000/10.gif?ex=6858cea2&is=68577d22&hm=08b286aac5292377ec6e96cd91ab3a1037564c9fd11f3a9d55a45eabba56e76c&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191174972346419/11.gif?ex=6858cea2&is=68577d22&hm=46186e101bad20c8fff076e051f70caca600acaed771f34c8e6f3f56573cd898&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191175370801252/12.gif?ex=6858cea2&is=68577d22&hm=421bdf0c5e3fce45a9fb66e23f41eb9b621f14ff49c18841410b186b3cda307f&=", #10
    "https://media.discordapp.net/attachments/1386190643725860916/1386191238151278602/13.gif?ex=6858ceb1&is=68577d31&hm=acf14aad96b79dbc80a46a59b74d49d2588fba41382b64159e6abc298aee2159&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191238868242473/14.gif?ex=6858ceb1&is=68577d31&hm=9131ae29022bf6827196208998a4a531959254ac47051f4839ccbfb8e6235a38&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191239300517940/15.gif?ex=6858ceb1&is=68577d31&hm=9b7fd1d55da57a2d180b2571f016ded8bbd726e0894be0707267d2ea5b560450&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191239711555717/16.gif?ex=6858ceb1&is=68577d31&hm=3239c9f671a095dfd73e0f700760c359ab1850cf7ddd93da1ba866a583c0abda&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191240130990080/17.gif?ex=6858ceb1&is=68577d31&hm=62dd595f97ac455a01489c9a37c9414ace4eaa564e53ecb4adcd5636f01318fd&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191240529186827/18.gif?ex=6858ceb1&is=68577d31&hm=e86f64f7e522b70e8084753cc6472b240dfc9ae36b17302484b90544599c9c82&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191240999075860/19.gif?ex=6858ceb2&is=68577d32&hm=1dd8e4ab6ef43e2322b7de28bcb3190a2a74966bb1364497ec015b0c03ba0ea5&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191241347338280/20.gif?ex=6858ceb2&is=68577d32&hm=54731f24538169e662d6d93d65e4fcc40956dc42dd26fc34eda9619079f87d75&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191241686814873/21.gif?ex=6858ceb2&is=68577d32&hm=a51f5eef7029f32b5794b358a3cbd3fe08d57adde53439bdfda215aa082cbe22&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191242051715152/22.gif?ex=6858ceb2&is=68577d32&hm=c45b7df4304cf268b448f8b70201d1ef7eb5449cc070c2aec9ff4cc8f0cc126b&=", #10
    "https://media.discordapp.net/attachments/1386190643725860916/1386191280018686074/23.gif?ex=6858cebb&is=68577d3b&hm=a6f3de00956629caa4f57114ac0dd6af5ead43a4ea597f38e3a9b8b12747d856&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191280396177569/24.gif?ex=6858cebb&is=68577d3b&hm=a79b488a542a94e41d0823eb998a1473842ed5a6339855d2577d36dc9da3162e&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191280811409458/25.gif?ex=6858cebb&is=68577d3b&hm=3e1c78db65fe63cd015fbe907f5fe269db5f35dcda072100c5212b7ebf1cfb57&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191281188900965/26.gif?ex=6858cebb&is=68577d3b&hm=08da68ba8115d9f5c6c203617fa279eb4dda33d33be1fae56083773232f288fa&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191281511989352/27.gif?ex=6858cebb&is=68577d3b&hm=d1cd203c167e4cb7123b586149a733b96ad596d497e82df685daf683a81fa7f7&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191281822105630/28.gif?ex=6858cebb&is=68577d3b&hm=77fd1aa678685d447e62c5dfa6b0ccfe87aab96fc0c226fd679db7886686a011&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191282157785259/29.gif?ex=6858cebb&is=68577d3b&hm=732a34135c66d3dda39fcda1b2a5664b9ed4d179a0dbf6b3351ea1f974eb6c10&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191282501845032/30.gif?ex=6858cebb&is=68577d3b&hm=55b26eb6fab2ee03ee28bf0a9e58779f015f1c0dbce088f7c81cca244101d34b&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191282824544407/32.gif?ex=6858cebc&is=68577d3c&hm=cf3c7e88216c1fd0a84ed8d01ad9b2e8c74c224cacec569e7cba2d54dc9c5206&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191283155898469/33.gif?ex=6858cebc&is=68577d3c&hm=c085423418cce1ac2e4246f95f3e5bdd71a5be09d1d16fe900614b60ed440ea2&=", #10
    "https://media.discordapp.net/attachments/1386190643725860916/1386191321781244016/34.gif?ex=6858cec5&is=68577d45&hm=04301330e0f43f37ddfa58cc71731fc5d08823872e448ad6dd488bc052635353&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191322091749437/35.gif?ex=6858cec5&is=68577d45&hm=9eab50ff9b3a696da55aea86cd170366b3ced2b65a87e4f5d5c07c30ddf565b1&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191322423230575/36.gif?ex=6858cec5&is=68577d45&hm=939a550ae5ec92ffce5b62213bdccc005be4ab1fb290102d8787813b30634fbc&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191322750390292/37.gif?ex=6858cec5&is=68577d45&hm=925b5ef68082f3a6e4de0568900fb1e224aeab932674ab8b739fcddd8824ab38&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191323140325417/38.gif?ex=6858cec5&is=68577d45&hm=938429a217241f0168aa23b015e24626da1c06a3d2df15dd72ba538b686ad7f2&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191323576664094/39.gif?ex=6858cec5&is=68577d45&hm=1c80e51774abf3e3ccb383a726d43314ef26f66338ceb8f4e290a0f24db402fb&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191323903824014/40.gif?ex=6858cec5&is=68577d45&hm=6b2b58c68fc7eda33e39db4fb6ef97b3fc50e891a17f70ee0dd3f7c6bbb111c5&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191324293759127/42.gif?ex=6858cec5&is=68577d45&hm=c25c96e2667c30615aba12a8f7c029baa39ecab9a72a0eaa2d923f45421a4adc&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191324633628833/43.gif?ex=6858cec5&is=68577d45&hm=832b3cd90d6fb07092a2abc8cd22acdee27eccb47a1153a774a90bfb9275c5d8&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191324944011324/44.gif?ex=6858cec6&is=68577d46&hm=efe804159df9d66a4c7c8d75b13341e59ec77c02b9c4b4820bb3b922bf1b2c66&=", #10
    "https://media.discordapp.net/attachments/1386190643725860916/1386191349891600424/46.gif?ex=6858cecc&is=68577d4c&hm=d5cab141c4dd7a7cf681473c91ba84b12c03363814c81420d07fe063f3ae64cd&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191350436986910/47.gif?ex=6858cecc&is=68577d4c&hm=7573807eb3c13249d334ae4e0c35f0e6e6f813c8fdb2e855ea0d3c9f430dbf1f&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191350780788807/48.gif?ex=6858cecc&is=68577d4c&hm=58221c5bbe07cd4b60e9db515e1235ed93352cdfdbdee27f2306bec039c80830&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191351129047120/49.gif?ex=6858cecc&is=68577d4c&hm=35ee078a025d9d8d9bc150e80cc22cc70573c7f809790d185ae3f69fb2a7a85f&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191351820976139/50.gif?ex=6858cecc&is=68577d4c&hm=21ff1864b9d7051b65b2e07508038cea01a4da0c01ed539d91c0ad5a9a4bb187&=",
    "https://media.discordapp.net/attachments/1386190643725860916/1386191352299258037/51.gif?ex=6858cecc&is=68577d4c&hm=e43c7f161a3f4c4ce76a16c3aa358364eb3f831e4add18d4546c29d2a78d7df7&=", #6
    
]

class Detonar(commands.Cog):
    """Comando !detonar con typing y gifs CDN."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stats = cargar_stats()

    def _key(self, uid1: int, uid2: int) -> str:
        return "_".join(str(i) for i in sorted((uid1, uid2)))

    @commands.command(name="detonar", help="Ten 'sepso' con alguien…")
    async def detonar(self, ctx: commands.Context, target: discord.Member | None = None):
        author = ctx.author

        # ── validaciones ────────────────────────────────────────────────
        if target is None:
            await ctx.reply("Debes mencionar a alguien: `!detonar @fulanito` <:inspect2:1320810253532659773>", mention_author=False); return
        if target.bot:
            await ctx.reply("Los bots no tenemos cuca, respeta. <:spy:1320810627513716858>", mention_author=False); return
        if target == author:
            await ctx.reply("Autodetonarse a uno mismo no esta mal... pero no funciona así <:sleep5:1320810560073367645>", mention_author=False); return

        # ── elegir frase & gif ──────────────────────────────────────────
        frase = random.choice(FRASES_SPICY) if random.random() < 0.05 else random.choice(FRASES_AMOR)
        gif   = random.choice(GIFS_AMOR)

        # ── actualizar stats ────────────────────────────────────────────
        key   = self._key(author.id, target.id)
        veces = self.stats.get(key, 0) + 1
        self.stats[key] = veces
        guardar_stats(self.stats)

        # ── efecto typing (1 s) ─────────────────────────────────────────
        async with ctx.typing():
            await asyncio.sleep(1)

        # ── crear embed ────────────────────────────────────────────────
        embed = discord.Embed(
            description=f"{author.mention} & {target.mention} **se detonaron,** _{frase}_",
            color=0xFF69B4,
        )
        embed.set_image(url=gif)
        embed.set_footer(text=f"Estos puercos se han detonado {veces} veces. 🙀 | ''consulta tus detonadas con !pr''")

        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Detonar(bot))
