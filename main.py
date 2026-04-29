import discord
from discord.ext import commands
from aiogram import Bot as TgBot, Dispatcher, types
import asyncio
import io
import os
import re
from aiohttp import web
from bs4 import BeautifulSoup

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DISCORD_CHANNEL_ID = 1343517491241943082

intents = discord.Intents.default()
intents.message_content = True
ds_bot = commands.Bot(command_prefix='!', intents=intents)

@ds_bot.event
async def on_ready():
    print(f'{ds_bot.user} is online')

tg_bot = TgBot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.channel_post()
async def handle_channel_post(message: types.Message):
    ds_channel = ds_bot.get_channel(DISCORD_CHANNEL_ID)
    if not ds_channel:
        return

    raw_html_text = message.html_text or "" 
    
    soup = BeautifulSoup(raw_html_text, 'html.parser')
    for emoji_tag in soup.find_all('tg-emoji'):
        emoji_tag.replace_with(emoji_tag.text)
        
    text_to_send = str(soup)

    text_to_send = text_to_send.replace('\xa0', ' ')

    text_to_send = re.sub(r'(\d+)\s*🚪', r'\1 кнобсов', text_to_send)
    text_to_send = re.sub(r'(\d+)\s*⭐️', r'\1 стардаста', text_to_send)
    text_to_send = re.sub(r'(\d+)\s*❤️', r'\1 ревайв', text_to_send)

    text_to_send = text_to_send.replace('#dailyrun', '')
    text_to_send = re.sub(r'(ДЕНЬ\s*\d+)', r'\1:', text_to_send)
    text_to_send = re.sub(r'—\s*Проходится', 'Проходится', text_to_send)

    emojis_to_remove = [
        '🔥', '🚪', '💩', '🏮', '🛑', '👀', '🫨', 
        '😃', '🦇', '⚫️', '🏆', '✅', '⭐️', '❤️', '🌟'
    ]
    for emoji in emojis_to_remove:
        text_to_send = text_to_send.replace(emoji, '')

    text_to_send = text_to_send.replace('<b>', '').replace('</b>', '')
    text_to_send = text_to_send.replace('<i>', '').replace('</i>', '')
    text_to_send = text_to_send.replace('<blockquote>', '').replace('</blockquote>', '')
    text_to_send = text_to_send.replace('*', '')

    text_to_send = re.sub(r' +', ' ', text_to_send)
    text_to_send = re.sub(r' ,', ',', text_to_send)
    text_to_send = re.sub(r',\s+', ', ', text_to_send)

    lines = [line.strip() for line in text_to_send.split('\n')]
    lines = [line for line in lines if line]
    text_to_send = '\n'.join(lines)

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
        except Exception as e:
            pass

    try:
        if discord_file:
            await ds_channel.send(content=text_to_send if text_to_send else None, file=discord_file)
        elif text_to_send.strip():
            await ds_channel.send(content=text_to_send)
    except Exception as e:
         pass

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
