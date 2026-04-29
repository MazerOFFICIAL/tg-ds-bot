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
    locs_found = []
    monsters = []
    rewards = []
    tomorrow = []
    current_sec = None
    
    for line in lines:
        if "ДЕНЬ" in line.upper():
            day = re.search(r'\d+', line)
            if day:
                final_msg.append(f"**ДЕНЬ {day.group()}:**")
                final_msg.append("⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯")
            continue

        if "Дверей" in line:
            parts = re.split(r'[—–-]', line, 1)
            final_msg.append(f"***{parts[0].strip()}***")
            if len(parts) > 1:
                l_list = [loc.strip() for loc in parts[1].split(',') if loc.strip()]
                locs_found.extend(l_list)
            continue

        if locs_found and not monsters and "Проходится за" not in line and "Награда" not in line:
            l_list = [loc.strip() for loc in line.split(',') if loc.strip()]
            locs_found.extend(l_list)
            continue

        if "Проходится за" in line:
            if locs_found:
                final_msg.append(f"`{chr(10).join(locs_found)}`")
                locs_found = []
            final_msg.append(f"*— {line.lstrip('—–- ').strip()}*")
            current_sec = "MONS"
            continue

        if "Награда:" in line:
            current_sec = "REW"
            v = line.replace("Награда:", "").strip()
            if v: rewards.append(v)
            continue

        if "Завтра:" in line:
            current_sec = "TOM"
            v = line.replace("Завтра:", "").strip()
            if v: tomorrow.append(v)
            continue

        if current_sec == "MONS":
            monsters.append(line.lstrip('—–- ').strip())
        elif current_sec == "REW":
            rewards.append(line)
        elif current_sec == "TOM":
            tomorrow.append(line)

    if monsters:
        m_block = "\n".join([f"- {m}" for m in monsters])
        final_msg.append(f"**{m_block}**")

    if rewards:
        r_str = "\n+".join([r.lstrip('+').strip() for r in rewards if r.strip()])
        final_msg.append(f"**Награда:** **`{r_str}`**")

    if tomorrow:
        t_str = "\n+".join([t.lstrip('+').strip() for t in tomorrow if t.strip()])
        final_msg.append(f"**Завтра:** **`{t_str}`**")

    res = "\n".join(final_msg)

    file_id = None
    if message.photo: file_id = message.photo[-1].file_id
    elif message.video: file_id = message.video.file_id

    d_file = None
    if file_id:
        try:
            f_info = await tg_bot.get_file(file_id)
            down = await tg_bot.download_file(f_info.file_path)
            d_file = discord.File(fp=io.BytesIO(down.read()), filename="daily.jpg")
        except: pass

    try:
        await ds_channel.send(content=res, file=d_file)
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
