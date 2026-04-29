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
    print(f'{ds_bot.user} online')

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
    
    text = soup.get_text(separator="\n")
    text = text.replace('\xa0', ' ').replace('*', '').replace('#dailyrun', '')
    
    text = re.sub(r'(\d+)\s*🚪', r'\1 кнобсов', text)
    text = re.sub(r'(\d+)\s*⭐️', r'\1 стардаста', text)
    text = re.sub(r'(\d+)\s*❤️', r'\1 ревайв', text)

    bad_emojis = ['🔥', '🚪', '💩', '🏮', '🛑', '👀', '🫨', '😃', '🦇', '⚫️', '🏆', '✅', '🌟']
    for em in bad_emojis:
        text = text.replace(em, '')

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    final_msg = []
    entities = []
    reward_block = ""
    tomorrow_block = ""
    
    for line in lines:
        if "ДЕНЬ" in line.upper():
            day_match = re.search(r'\d+', line)
            if day_match:
                final_msg.append(f"**ДЕНЬ {day_match.group()}:**")
                final_msg.append("⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯")
        
        elif "Дверей" in line:
            parts = line.split('—')
            final_msg.append(f"***{parts[0].strip()}***")
            if len(parts) > 1:
                locs = [loc.strip() for loc in parts[1].split(',') if loc.strip()]
                final_msg.append(f"`{chr(10).join(locs)}`")

        elif "Проходится за" in line:
            clean_time = line.lstrip('— ').strip()
            final_msg.append(f"*— {clean_time}*")

        elif "Награда:" in line:
            val = line.replace("Награда:", "").strip()
            formatted_val = val.replace('+', '\n+')
            reward_block = f"**Награда:** **`{formatted_val}`**"

        elif "Завтра:" in line:
            val = line.replace("Завтра:", "").strip()
            formatted_val = val.replace('+', '\n+')
            tomorrow_block = f"**Завтра:** **`{formatted_val}`**"

        else:
            entities.append(f"**- {line}**")

    if entities:
        final_msg.append("\n".join(entities))
    if reward_block:
        final_msg.append(reward_block)
    if tomorrow_block:
        final_msg.append(tomorrow_block)

    result_text = "\n".join(final_msg)

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
    except: pass

async def handle(r): return web.Response(text="OK")
async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()

async def main():
    asyncio.create_task(web_server())
    await tg_bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(dp.start_polling(tg_bot), ds_bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
