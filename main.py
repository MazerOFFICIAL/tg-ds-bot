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

KNOWN_SECTIONS = [
    "Отель", "Оранжерея", "Румс", "Бэкдор", "Ретро-комнаты", 
    "Шахты", "Rooms", "The Backdoor", "Hotel", "Greenhouse", "Mines"
]

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
    sections = []
    entities = []
    rewards = []
    tomorrow = []
    
    day_info = ""
    doors_info = ""
    time_info = ""
    
    mode = None

    for line in lines:
        if "ДЕНЬ" in line.upper():
            day_m = re.search(r'\d+', line)
            if day_m:
                day_info = f"**ДЕНЬ {day_m.group()}:**\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"
            continue

        if "Дверей" in line:
            p = re.split(r'[—–-]', line, 1)
            doors_info = f"***{p[0].strip()}***"
            if len(p) > 1:
                sub_locs = [s.strip().lstrip('—–- ').strip() for s in p[1].split(',') if s.strip().lstrip('—–- ').strip()]
                sections.extend(sub_locs)
            mode = "LOCS"
            continue

        if "Проходится за" in line:
            time_info = f"*— {line.lstrip('—–- ').strip()}*"
            mode = "MONS"
            continue

        if "Награда:" in line:
            mode = "REW"
            val = line.replace("Награда:", "").strip().lstrip('—–- ').strip()
            if val: rewards.append(val)
            continue
        
        if "Завтра:" in line:
            mode = "TOM"
            val = line.replace("Завтра:", "").strip().lstrip('—–- ').strip()
            if val: tomorrow.append(val)
            continue

        clean_line = line.lstrip('—–- ').strip()
        if not clean_line: continue

        if mode == "LOCS":
            sub_locs = [s.strip().lstrip('—–- ').strip() for s in line.split(',') if s.strip().lstrip('—–- ').strip()]
            sections.extend(sub_locs)
        elif mode == "MONS":
            if any(word in clean_line for word in KNOWN_SECTIONS):
                sections.append(clean_line)
            else:
                entities.append(clean_line)
        elif mode == "REW":
            rewards.append(clean_line)
        elif mode == "TOM":
            tomorrow.append(clean_line)

    if day_info: final_msg.append(day_info)
    if doors_info: final_msg.append(doors_info)
    
    if sections:
        final_msg.append("`Секции:`")
        for s in sections: 
            if s and s not in ["—", "–", "-"]:
                final_msg.append(f"***{s}***")
    
    if time_info: final_msg.append(time_info)
    
    if entities:
        final_msg.append("` Монстры:`")
        for e in entities: final_msg.append(f"** {e}**")
    
    if rewards:
        r_text = "\n+".join([r.lstrip('+ ').strip() for r in rewards if r.strip()])
        final_msg.append(f"**Награда:** **`{r_text}`**")
    
    if tomorrow:
        t_text = "\n+".join([t.lstrip('+ ').strip() for t in tomorrow if t.strip()])
        final_msg.append(f"**Завтра:** **`{t_text}`**")

    res = "\n".join(final_msg)

    f_id = None
    if message.photo: f_id = message.photo[-1].file_id
    elif message.video: f_id = message.video.file_id

    d_file = None
    if f_id:
        try:
            f_info = await tg_bot.get_file(f_id)
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
