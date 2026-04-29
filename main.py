import discord
from discord.ext import commands
from aiogram import Bot as TgBot, Dispatcher, types
import asyncio
import io
import os
from aiohttp import web
# Подключаем библиотеку для очистки HTML
from bs4 import BeautifulSoup

# Данные бота берутся из настроек Render (безопасный способ)
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DISCORD_CHANNEL_ID = 1343517491241943082 # Это ID твоего канала в ДС

intents = discord.Intents.default()
intents.message_content = True
ds_bot = commands.Bot(command_prefix='!', intents=intents)

@ds_bot.event
async def on_ready():
    print(f'Discord Bot {ds_bot.user} is online!')

tg_bot = TgBot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- Главная функция обработки поста из ТГ ---
@dp.channel_post()
async def handle_channel_post(message: types.Message):
    ds_channel = ds_bot.get_channel(DISCORD_CHANNEL_ID)
    if not ds_channel:
        print("Ошибка: Канал Дискорда не найден!")
        return

    # Берем HTML текст поста
    raw_html_text = message.html_text or "" 
    
    # --- СУПЕР-ОЧИСТКА ОТ ЕБАНЫХ АЙДИШНИКОВ СМАЙЛОВ ---
    # Мы используем BeautifulSoup, чтобы "прочитать" HTML как структуру
    soup = BeautifulSoup(raw_html_text, 'html.parser')
    
    # Находим все теги <tg-emoji>
    for emoji_tag in soup.find_all('tg-emoji'):
        # Заменяем весь этот ебаный тег с айдишниками на ТОЛЬКО его внутренний текст (сам смайл)
        emoji_tag.replace_with(emoji_tag.text)
        
    # Превращаем очищенную структуру обратно в строку
    text_to_send = str(soup)
    # ----------------------------------------------------

    # Подготовка медиафайлов
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
            print(f"Error downloading media: {e}")
            text_to_send += f"\n\n*(Ошибка загрузки файла)*"

    # Финальная конвертация оставшейся HTML-разметки под формат Дискорда
    text_to_send = text_to_send.replace('<b>', '**').replace('</b>', '**') # Жирный
    text_to_send = text_to_send.replace('<i>', '*').replace('</i>', '*') # Курсив
    
    # Удаляем пустые теги <blockquote>, которые иногда оставляет BeautifulSoup после очистки
    text_to_send = text_to_send.replace('<blockquote>', '').replace('</blockquote>', '')

    # Отправка в Дискорд
    try:
        # Отправляем только если есть что отправлять
        if discord_file:
            # У Дискорда есть лимит в 2000 символов, но посты в ТГ обычно меньше
            await ds_channel.send(content=text_to_send if text_to_send else None, file=discord_file)
        elif text_to_send.strip():
            await ds_channel.send(content=text_to_send)
        
        print("Пост успешно переслан в Discord!")
    except Exception as e:
         print(f"Error sending to Discord: {e}")

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
    # Запускаем обоих ботов параллельно
    print("Запускаю Telegram polling и Discord бота...")
    await asyncio.gather(dp.start_polling(tg_bot), ds_bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
