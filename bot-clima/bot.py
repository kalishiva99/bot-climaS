"""
Bot de Discord que dice el clima actual y pronóstico de CUALQUIER ciudad del mundo.
Usa las APIs gratuitas de Open-Meteo (no necesitan registro ni API key).
"""

import discord
from discord.ext import commands, tasks
import requests
import json
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Servidor web mínimo para engañar el escaneo de puertos de Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot activo 24/7")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Iniciar el servidor web en un hilo secundario antes de arrancar el bot
threading.Thread(target=run_web_server, daemon=True).start()

# --- Ciudades guardadas por defecto / accesos rápidos ---
CIUDADES = {
    "santiago": {
        "lat": -33.4489,
        "lon": -70.6693,
        "nombre": "Santiago, Chile",
        "timezone": "America/Santiago"
    },
    "temuco": {
        "lat": -38.7397,
        "lon": -72.5901,
        "nombre": "Temuco, Chile",
        "timezone": "America/Santiago"
    },
    "concepcion": {
        "lat": -36.827,
        "lon": -73.0498,
        "nombre": "Concepción, Chile",
        "timezone": "America/Santiago"
    }


CIUDAD_POR_DEFECTO = "temuco"
ARCHIVO_CONFIG = "config.json"


def cargar_configuracion():
    if not os.path.exists(ARCHIVO_CONFIG):
        return {}
    with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_configuracion(configuracion):
    with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as archivo:
        json.dump(configuracion, archivo, indent=2)


def config_del_servidor(configuracion, id_servidor):
    valor = configuracion.get(id_servidor, {})
    if isinstance(valor, str):
        valor = {"ciudad": valor}
    return valor


def ciudad_por_defecto_del_servidor(ctx):
    configuracion = cargar_configuracion()
    config_servidor = config_del_servidor(configuracion, str(ctx.guild.id))
    return config_servidor.get("ciudad", CIUDAD_POR_DEFECTO)


# --- Configuración del bot ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


CODIGOS_CLIMA = {
    0: "Despejado ☀️",
    1: "Mayormente despejado 🌤️",
    2: "Parcialmente nublado ⛅",
    3: "Nublado ☁️",
    45: "Niebla 🌫️",
    48: "Niebla con escarcha 🌫️",
    51: "Llovizna ligera 🌦️",
    53: "Llovizna moderada 🌦️",
    55: "Llovizna intensa 🌧️",
    56: "Llovizna helada ligera 🌧️❄️",
    57: "Llovizna helada intensa 🌧️❄️",
    61: "Lluvia ligera 🌧️",
    63: "Lluvia moderada 🌧️",
    65: "Lluvia intensa 🌧️",
    66: "Lluvia helada ligera 🌧️❄️",
    67: "Lluvia helada intensa 🌧️❄️",
    71: "Nieve ligera 🌨️",
    73: "Nieve moderada 🌨️",
    75: "Nieve intensa ❄️",
    77: "Granos de nieve 🌨️",
    80: "Chubascos ligeros 🌦️",
    81: "Chubascos moderados 🌧️",
    82: "Chubascos violentos ⛈️",
    85: "Chubascos de nieve ligeros 🌨️",
    86: "Chubascos de nieve intensos ❄️",
    95: "Tormenta eléctrica ⛈️",
    96: "Tormenta con granizo ligero ⛈️🧊",
    99: "Tormenta con granizo intenso ⛈️🧊",
}


def buscar_ciudad(nombre_ciudad):
    """
    Busca las coordenadas de cualquier ciudad del mundo usando la API de Geocodificación de Open-Meteo.
    Si la ciudad está en el diccionario local (CIUDADES), la usa directamente.
    """
    clave = nombre_ciudad.lower().strip()
    if clave in CIUDADES:
        return CIUDADES[clave]

    url = "https://geocoding-api.open-meteo.com/v1/search"
    parametros = {
        "name": nombre_ciudad,
        "count": 1,
        "language": "es",
        "format": "json"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        respuesta = requests.get(url, params=parametros, headers=headers, timeout=10)
        respuesta.raise_for_status()
        
        # Verificar si Cloudflare devolvió HTML en lugar de JSON
        content_type = respuesta.headers.get("content-type", "")
        if "application/json" not in content_type:
            print("Error: Cloudflare está bloqueando la IP del servidor con un desafío HTML.")
            return None
            
        datos = respuesta.json()
        
        if "results" in datos and len(datos["results"]) > 0:
            resultado = datos["results"][0]
            nombre = resultado.get("name")
            pais = resultado.get("country", "")
            nombre_completo = f"{nombre}, {pais}" if pais else nombre

            return {
                "lat": resultado["latitude"],
                "lon": resultado["longitude"],
                "nombre": nombre_completo,
                "timezone": resultado.get("timezone", "auto")
            }
    except Exception as e:
        print(f"Error buscando ciudad: {e}")
    
    return None


def obtener_clima(ciudad_info):
    url = "https://api.open-meteo.com/v1/forecast"
    zona_horaria = ciudad_info.get("timezone", "America/Santiago")

    parametros = {
        "latitude": ciudad_info["lat"],
        "longitude": ciudad_info["lon"],
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "timezone": zona_horaria,
    }

    respuesta = requests.get(url, params=parametros, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()

    actual = datos["current"]
    temperatura = actual["temperature_2m"]
    humedad = actual["relative_humidity_2m"]
    viento = actual["wind_speed_10m"]
    codigo = actual["weather_code"]

    descripcion = CODIGOS_CLIMA.get(codigo, "Condición desconocida")

    mensaje = (
        f"**Clima actual en {ciudad_info['nombre']}** 🌡️\n"
        f"{descripcion}\n"
        f"Temperatura: {temperatura}°C\n"
        f"Humedad: {humedad}%\n"
        f"Viento: {viento} km/h"
    )
    return mensaje


DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def obtener_pronostico(ciudad_info, dias=5):
    url = "https://api.open-meteo.com/v1/forecast"
    zona_horaria = ciudad_info.get("timezone", "America/Santiago")

    parametros = {
        "latitude": ciudad_info["lat"],
        "longitude": ciudad_info["lon"],
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": zona_horaria,
        "forecast_days": dias,
    }

    respuesta = requests.get(url, params=parametros, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()

    diario = datos["daily"]
    fechas = diario["time"]
    codigos = diario["weather_code"]
    maximas = diario["temperature_2m_max"]
    minimas = diario["temperature_2m_min"]
    prob_lluvia = diario["precipitation_probability_max"]

    lineas = [f"**Pronóstico para {ciudad_info['nombre']}** 📅\n"]

    for fecha_texto, codigo, maxima, minima, lluvia in zip(
        fechas, codigos, maximas, minimas, prob_lluvia
    ):
        fecha = datetime.strptime(fecha_texto, "%Y-%m-%d")
        dia_semana = DIAS_SEMANA[fecha.weekday()]
        descripcion = CODIGOS_CLIMA.get(codigo, "Condición desconocida")

        lineas.append(
            f"**{dia_semana} {fecha.day}/{fecha.month}** — {descripcion}\n"
            f"Máx: {maxima}°C | Mín: {minima}°C | Prob. lluvia: {lluvia}%"
        )

    return "\n\n".join(lineas)


# --- Aviso automático diario ---
HORA_AVISO = time(hour=9, minute=0, tzinfo=ZoneInfo("America/Santiago"))


@tasks.loop(time=HORA_AVISO)
async def aviso_diario():
    configuracion = cargar_configuracion()

    for id_servidor, valor in configuracion.items():
        config_servidor = config_del_servidor(configuracion, id_servidor)
        id_canal = config_servidor.get("canal_aviso")

        if id_canal is None:
            continue

        canal = bot.get_channel(id_canal)
        if canal is None:
            continue

        clave_ciudad = config_servidor.get("ciudad", CIUDAD_POR_DEFECTO)
        ciudad_info = buscar_ciudad(clave_ciudad)
        
        if ciudad_info:
            try:
                mensaje = obtener_clima(ciudad_info)
                await canal.send(f"☀️ **Buenos días!** Así amanece hoy:\n\n{mensaje}")
            except Exception as error:
                print(f"Error mandando aviso diario a servidor {id_servidor}: {error}")


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    if not aviso_diario.is_running():
        aviso_diario.start()


@bot.command(name="clima")
async def clima(ctx, *, ciudad: str = None):
    if ciudad is None:
        ciudad = ciudad_por_defecto_del_servidor(ctx)

    ciudad_info = buscar_ciudad(ciudad)

    if not ciudad_info:
        await ctx.send(f"😅 No encontré la ciudad **'{ciudad}'**. Intenta escribir el nombre completo.")
        return

    try:
        mensaje = obtener_clima(ciudad_info)
        await ctx.send(mensaje)
    except Exception as error:
        await ctx.send("No pude obtener el clima ahora mismo. Intenta de nuevo en un rato.")
        print(f"Error al obtener clima: {error}")


@bot.command(name="pronostico")
async def pronostico(ctx, *, ciudad: str = None):
    if ciudad is None:
        ciudad = ciudad_por_defecto_del_servidor(ctx)

    ciudad_info = buscar_ciudad(ciudad)

    if not ciudad_info:
        await ctx.send(f"😅 No encontré la ciudad **'{ciudad}'**. Intenta escribir el nombre completo.")
        return

    try:
        mensaje = obtener_pronostico(ciudad_info)
        await ctx.send(mensaje)
    except Exception as error:
        await ctx.send("No pude obtener el pronóstico ahora mismo. Intenta de nuevo en un rato.")
        print(f"Error al obtener pronóstico: {error}")


@bot.command(name="setciudad")
@commands.has_permissions(manage_guild=True)
async def setciudad(ctx, *, ciudad: str):
    ciudad_info = buscar_ciudad(ciudad)

    if not ciudad_info:
        await ctx.send(f"😅 No encontré la ciudad **'{ciudad}'**. Intenta de nuevo.")
        return

    id_servidor = str(ctx.guild.id)
    configuracion = cargar_configuracion()
    config_servidor = config_del_servidor(configuracion, id_servidor)
    config_servidor["ciudad"] = ciudad
    configuracion[id_servidor] = config_servidor
    guardar_configuracion(configuracion)

    await ctx.send(f"✅ Listo, ahora la ciudad por defecto de este servidor es **{ciudad_info['nombre']}**.")


@setciudad.error
async def setciudad_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Necesitas el permiso de \"Gestionar servidor\" para usar este comando.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Tienes que decirme qué ciudad. Ej: `!setciudad santiago`")
    else:
        await ctx.send("Ocurrió un error al cambiar la ciudad.")
        print(f"Error en !setciudad: {error}")


@bot.command(name="setcanal")
@commands.has_permissions(manage_guild=True)
async def setcanal(ctx):
    id_servidor = str(ctx.guild.id)
    configuracion = cargar_configuracion()
    config_servidor = config_del_servidor(configuracion, id_servidor)
    config_servidor["canal_aviso"] = ctx.channel.id
    configuracion[id_servidor] = config_servidor
    guardar_configuracion(configuracion)

    await ctx.send("✅ Listo, desde ahora voy a mandar el clima acá todos los días a las 9:00.")


@setcanal.error
async def setcanal_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Necesitas el permiso de \"Gestionar servidor\" para usar este comando.")
    else:
        await ctx.send("Ocurrió un error al configurar el canal.")
        print(f"Error en !setcanal: {error}")


@bot.command(name="ayuda")
async def ayuda(ctx):
    embed = discord.Embed(
        title="📖 Comandos disponibles",
        description="Esto es lo que sé hacer por ahora:",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="!clima [ciudad]",
        value=(
            "Muestra el clima actual de cualquier ciudad del mundo.\n"
            "Ej: `!clima Pucon`, `!clima Madrid`, `!clima Tokio`"
        ),
        inline=False,
    )
    embed.add_field(
        name="!pronostico [ciudad]",
        value=(
            "Muestra el pronóstico de los próximos 5 días de cualquier ciudad.\n"
            "Ej: `!pronostico Buenos Aires`"
        ),
        inline=False,
    )
    embed.add_field(
        name="!setciudad <ciudad>",
        value=(
            "Define la ciudad por defecto de este servidor "
            "(requiere permiso de Gestionar servidor).\n"
            "Ej: `!setciudad Osorno`"
        ),
        inline=False,
    )
    embed.add_field(
        name="!setcanal",
        value=(
            "Hace que este canal reciba el clima automático todos los "
            "días a las 9:00 (requiere permiso de Gestionar servidor)."
        ),
        inline=False,
    )
    embed.add_field(
        name="!ping",
        value="Revisa si el bot está vivo y qué tan rápido responde.",
        inline=False,
    )
    embed.add_field(
        name="!ayuda",
        value="Muestra este mensaje.",
        inline=False,
    )

    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx):
    latencia_ms = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! ({latencia_ms}ms)")


# --- Conectar el bot ---
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN and os.path.exists("token.txt"):
    with open("token.txt", "r") as archivo:
        TOKEN = archivo.read().strip()

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: No se encontró el token de Discord.")
