import os
import asyncio
import glob
import shutil
import time
import re
import requests
from pyrogram import Client, filters, idle
from aiohttp import web

# --- CONFIGURATION ---
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_1 = int(os.environ.get('CHANNEL_1')) if os.environ.get('CHANNEL_1') else None
CHANNEL_2 = int(os.environ.get('CHANNEL_2')) if os.environ.get('CHANNEL_2') else None

DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
ACTIVE_TASKS = {}

app = Client("anime_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=4)

# --- HEALTH CHECK (Required for Koyeb) ---
async def health_check(request):
    return web.Response(text="OK")

async def start_web_server():
    server = web.Application()
    server.router.add_get("/", health_check)
    runner = web.AppRunner(server)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    print("🌍 Health Check running on 8080")

# --- JIKAN API ---
def get_anime_details(query):
    try:
        url = f"https://api.jikan.moe/v4/anime?q={query}&limit=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data['data']:
            anime = data['data'][0]
            return {
                "title": anime['title'],
                "native": anime.get('title_japanese', ''),
                "duration": anime.get('duration', '24 min').replace(" per ep", ""),
                "image": anime['images']['jpg']['large_image_url']
            }
    except: pass
    return None

async def consume_stream(process):
    while True:
        line = await process.stdout.readline()
        if not line: break
        print(f"[SHELL] {line.decode().strip()}")

@app.on_message(filters.command("dl"))
async def dl_cmd(client, message):
    chat_id = message.chat.id
    if chat_id in ACTIVE_TASKS: return await message.reply("⚠️ Busy.")
    
    cmd_text = message.text[4:]
    ep_match = re.search(r'-e\s+([\d,-]+)', cmd_text)
    name_match = re.search(r'-a\s+["\']([^"\']+)["\']', cmd_text)
    
    if not ep_match or not name_match: return await message.reply("Usage: `/dl -a \"Title\" -e 1`")
    
    anime_query = name_match.group(1)
    ep_num = ep_match.group(1)
    
    ACTIVE_TASKS[chat_id] = True
    status_msg = await message.reply("⏳ **Starting...**")
    
    anime_info = get_anime_details(anime_query)
    title = anime_info['title'] if anime_info else anime_query
    
    # Post Image
    try:
        if anime_info and anime_info['image']:
            sent = await client.send_photo(chat_id, photo=anime_info['image'], caption=f"**{title}**\nDuration: {anime_info['duration']}")
            for ch in [CHANNEL_1, CHANNEL_2]:
                if ch: await sent.copy(ch)
    except: pass

    # Download (We let the script choose resolution)
    cmd = f"./animepahe-dl.sh -a \"{anime_query}\" -e {ep_num} 2>&1"
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, preexec_fn=os.setsid)
    await consume_stream(process)
    await process.wait()
    
    # Upload
    mp4s = glob.glob("**/*.mp4", recursive=True)
    if not mp4s:
        await status_msg.edit_text("❌ Failed to download.")
    else:
        file_path = max(mp4s, key=os.path.getctime)
        await status_msg.edit_text("🚀 Uploading...")
        sent_vid = await client.send_document(chat_id, file_path, caption=f"**{title} - Ep {ep_num}**")
        
        for ch in [CHANNEL_1, CHANNEL_2]:
            if ch: await sent_vid.copy(ch)
            
        try: os.remove(file_path); shutil.rmtree(os.path.dirname(file_path))
        except: pass

    del ACTIVE_TASKS[chat_id]
    await status_msg.delete()

async def main():
    await start_web_server()
    await app.start()
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
