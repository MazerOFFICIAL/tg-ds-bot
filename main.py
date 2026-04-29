import discord
from discord.ext import commands
from aiogram import Bot as TgBot, Dispatcher, types
import asyncio
import io
import os
import re
from aiohttp import web
from bs4 import BeautifulSoup

# Данные из окружения Render
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DISCORD_CHANNEL_ID = 1343517491241943082

intents = discord.Intents.default()
intents.message_content = True
ds_bot = commands.Bot(command_prefix='!', intents=intents)

@ds_bot.event
async def on_ready():
    print(f'Бот {ds_bot.user} запущен и готов к работе!')

tg_bot = TgBot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.channel_post()
async def handle_channel_post(message: types.Message):
    ds_channel = ds_bot.get_channel(DISCORD_CHANNEL_ID)
    if not ds_channel: return

    # 1. Вытаскиваем чистый текст без скрытых ссылок и спецсимволов
    raw_html = message.html_text or ""
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Вычищаем кастомные эмодзи ТГ (те самые айдишники)
    for tg_emoji in soup.find_all('tg-emoji'):
        tg_emoji.replace_with(tg_emoji.text)
    
    clean_text = soup.get_text(separator="\n")

    # 2. Обработка наград (кнобсы, стардаст, ревайвы)
    clean_text = re.sub(r'(\d+)\s*🚪', r'\1 кнобсов', clean_text)
    clean_text = re.sub(r'(\d+)\s*⭐️', r'\1 стардаста', clean_text)
    clean_text = re.sub(r'(\d+)\s*❤️', r'\1 ревайв', clean_text)

    # 3. Чистка мусора: хэштеги, лишние звезды, смайлы
    clean_text = clean_text.replace('#dailyrun', '')
    clean_text = clean_text.replace('*', '') # Убираем старые звезды полностью
    
    bad_emojis = ['🔥', '🚪', '💩', '🏮', '🛑', '👀', '🫨', '😃', '🦇', '⚫️', '🏆', '✅', '🌟']
    for emoji in bad_emojis:
        clean_text = clean_text.replace(emoji, '')

    # 4. Форматирование под "Прекрасный вид"
    lines = clean_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Делаем заголовок ДЕНЬ XXX жирным и добавляем разделитель
        if "ДЕНЬ" in line.upper():
            day_num = re.search(r'\d+', line)
            if day_num:
                formatted_lines.append(f"**ДЕНЬ {day_num.group()}:**")
                formatted_lines.append("⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯")
                continue
        
        # Форматируем ключевые строки
        if "Награда:" in line:
            formatted_lines.append(f"**Награда:** {line.replace('Награда:', '').strip()}")
        elif "Завтра:" in line:
            formatted_lines.append(f"**Завтра:** {line.replace('Завтра:', '').strip()}")
        elif "Проходится за" in line:
            formatted_lines.append(f"*{line.strip()}*")
        else:
            # Обычные строки (монстры, комнаты)
            formatted_lines.append(line)

    final_text = "\n".join(formatted_lines)

    # 5. Работа с фото/видео
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

    # 6. Отправка
    try:
        await ds_channel.send(content=final_text if final_text else None, file=discord_file)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# Web-сервер для Render (Uptime)
async def handle(request): return web.Response(text="OK")
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
