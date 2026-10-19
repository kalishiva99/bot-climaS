# Bot de Discord - Clima en Temuco 🌤️

Bot simple que responde con el clima actual de Temuco cuando escribes `!clima`
en cualquier canal donde esté el bot.

## Paso 1: Crear el bot en Discord

1. Ve a https://discord.com/developers/applications
2. Click en "New Application", ponle un nombre (ej: "ClimaTemucoBot")
3. En el menú izquierdo, click en "Bot"
4. Click en "Reset Token" (o "Add Bot" si es la primera vez) y copia el token
   que te muestra. **Es como una contraseña, no lo compartas con nadie.**
5. Más abajo en esa misma página, activa el switch de **"Message Content Intent"**
   (el bot necesita esto para leer el comando `!clima`)

## Paso 2: Invitar el bot a tu servidor

1. En el menú izquierdo, click en "OAuth2" -> "URL Generator"
2. En "Scopes" marca: `bot`
3. En "Bot Permissions" marca: `Send Messages` y `Read Message History`
4. Copia la URL que se genera abajo, pégala en tu navegador, y elige el
   servidor de Discord donde quieres agregar el bot

## Paso 3: Instalar lo necesario en tu PC

Abre una terminal (CMD o PowerShell en Windows) en esta carpeta y corre:

```
pip install -r requirements.txt
```

## Paso 4: Poner tu token

1. En esta misma carpeta, crea un archivo nuevo llamado `token.txt`
2. Pega adentro el token que copiaste en el Paso 1 (solo el token, nada más)
3. Guarda el archivo

**Nunca subas `token.txt` a GitHub ni lo compartas con nadie** — cualquiera
con ese token puede controlar tu bot.

## Paso 5: Correr el bot

En la terminal, en esta carpeta:

```
python bot.py
```

Si todo funciona, vas a ver en la terminal:
```
✅ Bot conectado como ClimaTemucoBot#1234
```

Y en Discord, escribe `!clima` en cualquier canal donde esté el bot. Te va
a responder con la temperatura, humedad, viento y condición actual de Temuco.

## Cómo funciona por dentro

- Usa la librería `discord.py` para conectarse a Discord y escuchar comandos
- Usa `requests` para pedirle los datos del clima a **Open-Meteo**
  (https://open-meteo.com), una API gratuita que no pide registro
- Las coordenadas de Temuco ya están puestas en el código (`LATITUD`, `LONGITUD`)

## Próximos pasos (si quieres mejorarlo)

- Agregar más ciudades: `!clima santiago`, `!clima temuco`, etc.
- Agregar el pronóstico de los próximos días, no solo el clima actual
- Hacer que el bot avise automáticamente si va a llover (notificación diaria)
- Subir el bot a un servidor gratuito (como Railway u Oracle Cloud Free Tier)
  para que funcione 24/7 sin depender de que tu PC esté prendido

Si quieres, podemos seguir agregando cualquiera de estas funciones.
