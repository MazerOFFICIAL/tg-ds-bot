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
    rewards = []
    tomorrow = []
    
    current_section = None

    for line in lines:
        if "ДЕНЬ" in line.upper():
            day_match = re.search(r'\d+', line)
            if day_match:
                final_msg.append(f"**ДЕНЬ {day_match.group()}:**")
                final_msg.append("⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯")
            continue

        if "Дверей" in line:
            parts = re.split(r'[—–-]', line, 1)
            final_msg.append(f"***{parts[0].strip()}***")
            if len(parts) > 1:
                locs = [loc.strip() for loc in parts[1].split(',') if loc.strip()]
                final_msg.append(f"`{chr(10).join(locs)}`")
            continue

        if "Проходится за" in line:
            final_msg.append(f"*— {line.lstrip('—–- ').strip()}*")
            continue

        if "Награда:" in line:
            current_section = "REWARD"
            rewards.append(line.replace("Награда:", "").strip())
            continue
        
        if "Завтра:" in line:
            current_section = "TOMORROW"
            tomorrow.append(line.replace("Завтра:", "").strip())
            continue

        if current_section == "REWARD" and (line.startswith('+') or any(x in line for x in ['кнобсов', 'стардаста', 'ревайв'])):
            rewards.append(line)
            continue
        
        if current_section == "TOMORROW" and (line.startswith('+') or any(x in line for x in ['кнобсов', 'стардаста', 'ревайв'])):
            tomorrow.append(line)
            continue

        if line and line not in ["—", "–", "-"]:
            entities.append(f"**- {line.lstrip('—–- ').strip()}**")

    if entities:
        final_msg.append("\n".join(entities))

    if rewards:
        rew_text = "\n".join(rewards).replace('+', '\n+')
        final_msg.append(f"**Награда:** **`{rew_text}`**")

    if tomorrow:
        tom_text = "\n".join(tomorrow).replace('+', '\n+')
        final_msg.append(f"**Завтра:** **`{tom_text}`**")

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
