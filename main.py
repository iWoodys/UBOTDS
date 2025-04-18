import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import requests
import asyncio
import json  

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN no está definido en las variables de entorno.")

bot = commands.Bot(command_prefix="!", intents=intents)

CANAL_TEXTO_ID = 1354580489964359900  
CANAL_DOLAR_ID = 123456789012345678  

CONFIG_FILE = "config.json"

# Intentamos cargar la configuración guardada del canal
def load_config():
    global CANAL_DOLAR_ID
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
            CANAL_DOLAR_ID = config.get("canal_dolar_id", CANAL_DOLAR_ID)

# Guardamos la nueva configuración del canal
def save_config():
    config = {"canal_dolar_id": CANAL_DOLAR_ID}
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

# Cargar la configuración cuando se inicia el bot
load_config()

usuarios_config = {
    "472312737381482507": {
        "color": 0xFF0000,
        "titulo": "⚠️ ¡JUGADOR DEFECTUOSO SE HA UNIDO AL CANAL DE VOZ!",
        "descripcion": "Les recordamos que TxSala, único jugador que erra balas con Aim Assist, se ha unido al chat de voz.",
        "imagen": "https://i.imgur.com/hsKFqwU.png"
    },
    "740806534878986322": {
        "color": 0xFF0000,
        "titulo": "🔥 ¡LEYENDA PRESENTE!",
        "descripcion": "<@740806534878986322> ha entrado a **la sala**. Prepárense para las ratajugadas.",
        "imagen": "https://i.imgur.com/YpIyd9g.png"
    },
    "754077218124333088": {
        "color": 0xFF0000,
        "titulo": "🔥 ¡EL HACKER!",
        "descripcion": "<@1350338284508942346> ha entrado a **la sala**.",
        "imagen": "https://i.imgur.com/5iSLo19.png"
    },
    "1350338284508942346": {
        "color": 0xFF0000,
        "titulo": "🔥 ¡LA MÁQUINA DE FPS!",
        "descripcion": "<@1350338284508942346> ha entrado a **la sala**, los carreados se callan ante el mejor.",
        "imagen": "https://i.imgur.com/UZau7T5.png"
    },
    "1100168924978499595": {
        "color": 0xFF0000,
        "titulo": "🔥 ¡EL BAITERO!",
        "descripcion": "<@1100168924978499595> ha entrado a **la sala**, que no se te escape la kill.",
        "imagen": "https://i.imgur.com/UZau7T5.png"
    }
}

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Twitch | udevzone.gg"))

    try:
        synced = await bot.tree.sync()
        print(f"🔁 Slash commands sincronizados ({len(synced)} comandos)")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

    bot.loop.create_task(actualizar_dolar())  # Inicia la actualización cada 15 minutos


@bot.event
async def on_voice_state_update(member, before, after):
    se_unio = before.channel is None and after.channel is not None
    user_id = str(member.id)
    config = usuarios_config.get(user_id)

    if se_unio and config:
        canal_texto = member.guild.get_channel(CANAL_TEXTO_ID)
        if not canal_texto:
            return

        embed = discord.Embed(
            title=config["titulo"],
            description=config["descripcion"].replace("**la sala**", f"**{after.channel.name}**"),
            color=config["color"]
        )
        embed.set_image(url=config["imagen"])
        embed.set_footer(text="Administración UDevZone")
        embed.timestamp = discord.utils.utcnow()

        await canal_texto.send(content="@everyone", embed=embed)


@bot.tree.command(name="texto", description="Envía un mensaje embed personalizado a un canal (solo admins).")
@app_commands.describe(titulo="Título del embed", canal="Canal donde se enviará", mensaje="Contenido del mensaje")
async def texto(interaction: discord.Interaction, titulo: str, canal: discord.TextChannel, mensaje: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⛔ No tenés permiso para usar este comando.", ephemeral=True)
        return

    embed = discord.Embed(
        title=titulo,
        description=mensaje,
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Enviado por: {interaction.user.display_name}")
    embed.timestamp = discord.utils.utcnow()

    await canal.send(embed=embed)
    await interaction.response.send_message(f"✅ Mensaje enviado a {canal.mention}", ephemeral=True)


@bot.tree.command(name="dolar", description="Muestra la cotización actual del dólar blue y oficial.")
@app_commands.describe(tipo="Tipo de dólar")
async def dolar(interaction: discord.Interaction, tipo: str):
    try:
        if tipo == "blue":
            response = requests.get("https://dolarapi.com/v1/dolares/blue")
        elif tipo == "oficial":
            response = requests.get("https://dolarapi.com/v1/dolares/oficial")
        else:
            await interaction.response.send_message("⛔ Tipo de dólar no reconocido. Usa `blue` o `oficial`.", ephemeral=True)
            return

        data = response.json()
        embed = discord.Embed(
            title=f"💵 Cotización del Dólar {tipo.capitalize()}",
            description=f"**Compra:** ${data.get('compra')}\n**Venta:** ${data.get('venta')}",
            color=0x3498db  # Azul
        )
        embed.set_footer(text="Fuente: dolarapi.com")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print(f"Error al obtener la cotización del dólar: {e}")
        await interaction.response.send_message("❌ Hubo un error al obtener la cotización. Inténtalo más tarde.", ephemeral=True)


@bot.tree.command(name="configurarcanal", description="Configura el canal para las actualizaciones del dólar (solo admins).")
async def configurarcanal(interaction: discord.Interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⛔ No tenés permiso para usar este comando.", ephemeral=True)
        return

    global CANAL_DOLAR_ID
    CANAL_DOLAR_ID = canal.id
    save_config()

    await interaction.response.send_message(f"✅ Canal de actualizaciones del dólar configurado a {canal.mention}.", ephemeral=True)


async def actualizar_dolar():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            canal = bot.get_channel(CANAL_DOLAR_ID)
            if canal:
                # Obtener los valores de los dólares blue y oficial
                response_blue = requests.get("https://dolarapi.com/v1/dolares/blue")
                response_oficial = requests.get("https://dolarapi.com/v1/dolares/oficial")

                data_blue = response_blue.json()
                data_oficial = response_oficial.json()

                # Crear embed con los dos tipos de dólar, incluyendo compra y venta
                embed = discord.Embed(
                    title="💵 Cotización Dólar (Automático)",
                    description=f"**Dólar Blue:**\n"
                                f"Compra: ${data_blue.get('compra')}\n"
                                f"Venta: ${data_blue.get('venta')}\n\n"
                                f"**Dólar Oficial:**\n"
                                f"Compra: ${data_oficial.get('compra')}\n"
                                f"Venta: ${data_oficial.get('venta')}",
                    color=0x3498db  # Azul
                )
                embed.set_footer(text="Fuente: dolarapi.com")
                embed.timestamp = discord.utils.utcnow()

                await canal.send(embed=embed)
        except Exception as e:
            print(f"Error en actualización automática: {e}")
        await asyncio.sleep(1800)  # 30 minutos


# --- Flask trick for Render to detect an open port ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

Thread(target=run).start()
# --- End Flask trick ---

bot.run(TOKEN)