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
    print(f'Бот {ds_bot.user} готов раздавать стиль!')

tg_bot = TgBot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.channel_post()
async def handle_channel_post(message: types.Message):
    ds_channel = ds_bot.get_channel(DISCORD_CHANNEL_ID)
    if not ds_channel: return

    raw_html = message.html_text or ""
    soup = BeautifulSoup(raw_html, 'html.parser')
    for tg_emoji in soup.find_all('tg-emoji'):
        tg_emoji.replace_with(tg_emoji.text)
    
    # Полная очистка от мусора
    text = soup.get_text(separator="\n")
    text = text.replace('\xa0', ' ').replace('*', '').replace('#dailyrun', '')
    
    # Замена игровых валют
    text = re.sub(r'(\d+)\s*🚪', r'\1 кнобсов', text)
    text = re.sub(r'(\d+)\s*⭐️', r'\1 стардаста', text)
    text = re.sub(r'(\d+)\s*❤️', r'\1 ревайв', text)

    bad_emojis = ['🔥', '🚪', '💩', '🏮', '🛑', '👀', '🫨', '😃', '🦇', '⚫️', '🏆', '✅', '🌟']
    for em в bad_emojis: text = text.replace(em, '')

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    final_msg = []
    entities = []
    
    for line in lines:
        # 1. Заголовок дня
        if "ДЕНЬ" in line.upper():
            day_match = re.search(r'\d+', line)
            if day_match:
                final_msg.append(f"**ДЕНЬ {day_match.group()}:**")
                final_msg.append("⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯")
        
        # 2. Локации (25 Дверей — Отель...)
        elif "Дверей" in line:
            parts = line.split('—')
            final_msg.append(f"***{parts[0].strip()}***")
            if len(parts) > 1:
                locs = [loc.strip() for loc in parts[1].split(',') if loc.strip()]
                final_msg.append(f"`{chr(10).join(locs)}`") # Локации в блоке кода

        # 3. Время прохождения
        elif "Проходится за" in line:
            # Убираем лишние тире в начале, если есть
            clean_time = line.lstrip('— ').strip()
            final_msg.append(f"*— {clean_time}*")

        # 4. Награда
        elif "Награда:" in line:
            val = line.replace("Награда:", "").strip()
            # Формат: Награда: **`текст`**
            final_msg.append(f"**Награда:** **`{val.replace('+', chr(10) + '+')}`**")

        # 5. Завтра
        elif "Завтра:" in line:
            val = line.replace("Завтра:", "").strip()
            final_msg.append(f"**Завтра:** **`{val.replace('+', chr(10) + '+')}`**")

        # 6. Всё остальное — это монстры/сущности
        else:
            entities.append(f"**- {line}**")

    # Вставляем монстров после времени прохождения, но перед наградой
    if entities:
        final_msg.insert(-2, "\n".join(entities))

    result_text = "\n".join(final_msg)

    # Фото/Видео
    discord_file = None
    file_id = None
    if message.photo: file_id = message.photo[-1].file_id
    elif message.video: file_id = message.video.file_id

    if file_id:
        try:
            file_info = await tg_bot.get_file(file_id)
            downloaded = await tg_bot.download_file(file_info.file_path)
            discord_file = discord.File(fp=io.BytesIO(downloaded.read()), filename="daily_run.jpg")
        except: pass

    try:
        await ds_channel.send(content=result_text, file=discord_file)
    except Exception as e:
        print(f"Ошибка: {e}")

async def handle(r): return web.Response(text="OK")
async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()

async def main():
    asyncio.create_task(web_server())
    await asyncio.gather(dp.start_polling(tg_bot), ds_bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
