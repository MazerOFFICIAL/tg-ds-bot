import discord
from discord.ext import commands
from aiogram import Bot as TgBot, Dispatcher, types
import asyncio
import io
import os
from aiohttp import web

# Эти данные бот возьмет из настроек Render, на GitHub их не будет
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DISCORD_CHANNEL_ID = 1343517491241943082 

intents = discord.Intents.default()
intents.message_content = True
ds_bot = commands.Bot(command_prefix='!', intents=intents)

@ds_bot.event
async def on_ready():
    print(f'Discord Bot {ds_bot.user} is online!')

tg_bot = TgBot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.channel_post()
async def handle_channel_post(message: types.Message):
    ds_channel = ds_bot.get_channel(DISCORD_CHANNEL_ID)
    if not ds_channel:
        return

    text_to_send = message.html_text or "" 
    file_id = None
    file_name = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_name = "photo.jpg"
    elif message.video:
        file_id = message.video.file_id
        file_name = "video.mp4"

    discord_file = None
    if file_id:
        try:
            file_info = await tg_bot.get_file(file_id)
            downloaded_file = await tg_bot.download_file(file_info.file_path)
            discord_file = discord.File(fp=io.BytesIO(downloaded_file.read()), filename=file_name)
        except:
            text_to_send += "\n\n*(Ошибка загрузки файла)*"

    # Форматирование текста под Discord
    text_to_send = text_to_send.replace('<b>', '**').replace('</b>', '**').replace('<i>', '*').replace('</i>', '*')
    
    try:
        if discord_file:
            await ds_channel.send(content=text_to_send if text_to_send else None, file=discord_file)
        elif text_to_send.strip():
            await ds_channel.send(content=text_to_send)
    except Exception as e:
         print(f"Error: {e}")

# Мини-сервер, чтобы Render не выключал бота
async def handle(request):
    return web.Response(text="Bot is alive!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()

async def main():
    asyncio.create_task(web_server())
    await asyncio.gather(dp.start_polling(tg_bot), ds_bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())