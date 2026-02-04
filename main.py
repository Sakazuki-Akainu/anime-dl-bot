import os
import asyncio
import glob
import shutil
import time
import re
import requests
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# --- 1. CONFIGURATION ---
try:
    API_ID = int(os.environ.get('API_ID', 0))
    API_HASH = os.environ.get('API_HASH', '')
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
    
    # Optional Channels
    CHANNEL_1 = int(os.environ.get('CHANNEL_1')) if os.environ.get('CHANNEL_1') else None
    CHANNEL_2 = int(os.environ.get('CHANNEL_2')) if os.environ.get('CHANNEL_2') else None
    CHANNEL_3 = int(os.environ.get('CHANNEL_3')) if os.environ.get('CHANNEL_3') else None
except Exception as e:
    print(f"❌ Config Error: {e}")
    raise SystemExit

DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
ACTIVE_TASKS = {}
SETTINGS = {"ch1": False, "ch2": False, "ch3": True}

app = Client(
    "anime_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=4
)

# --- 2. JIKAN API (For Info) ---
def get_anime_details(query):
    try:
        url = f"https://api.jikan.moe/v4/anime?q={query}&limit=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data['data']:
            anime = data['data'][0]
            image_url = anime['images']['jpg']['large_image_url']
            duration_raw = anime.get('duration', '24 min').replace(" per ep", "")
            return {
                "title": anime['title'],
                "native": anime.get('title_japanese', ''),
                "duration": duration_raw,
                "url": anime['url'],
                "image": image_url
            }
    except: pass
    return None

# --- 3. HELPERS ---
async def consume_stream(process):
    while True:
        line = await process.stdout.readline()
        if not line: break
        # Print logs to Railway console
        print(f"[SHELL] {line.decode().strip()}")

# --- 4. COMMANDS ---
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply("🤖 **360p Anime Downloader**\nUsage: `/dl -a \"Anime Name\" -e 1`")

@app.on_message(filters.command("dl"))
async def dl_cmd(client, message):
    chat_id = message.chat.id
    if chat_id in ACTIVE_TASKS: return await message.reply("⚠️ A task is already running.")

    cmd_text = message.text[4:]
    if not cmd_text: return await message.reply("❌ Usage: `/dl -a \"Title\" -e 1`")

    # Extract info
    ep_match = re.search(r'-e\s+([\d,-]+)', cmd_text)
    name_match = re.search(r'-a\s+["\']([^"\']+)["\']', cmd_text)
    
    if not ep_match: return await message.reply("❌ Missing Episode Number (-e)")
    
    anime_query = name_match.group(1) if name_match else "anime"
    ep_num = ep_match.group(1)
    
    status_msg = await message.reply("⏳ **Searching & Initializing (360p)...**")
    
    # Get Info
    anime_info = get_anime_details(anime_query)
    if not anime_info:
        anime_info = {"title": anime_query, "native": "", "duration": "Unknown", "image": None}

    caption_template = (
        f"**{anime_info['title']}**\n"
        f"Quality: 360p (Forced)\n"
        f"Duration: {anime_info['duration']}\n"
    )

    ACTIVE_TASKS[chat_id] = {"status": "running"}
    
    # Send Thumbnail if enabled
    try:
        if anime_info['image']: 
            await client.send_photo(chat_id, photo=anime_info['image'], caption=caption_template)
    except: pass

    # --- EXECUTE SCRIPT (Forced 360p) ---
    # We pass -r 360 explicitly to the shell script
    current_cmd = f"./animepahe-dl.sh -a \"{anime_query}\" -e {ep_num} -r 360 2>&1"

    process = await asyncio.create_subprocess_shell(
        current_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=os.setsid
    )
    
    await consume_stream(process)
    await process.wait()

    # Find the File
    mp4s = glob.glob("**/*.mp4", recursive=True)
    
    if not mp4s:
        await status_msg.edit_text("❌ **Download Failed.** File not found.")
        if chat_id in ACTIVE_TASKS: del ACTIVE_TASKS[chat_id]
        return

    file_to_up = max(mp4s, key=os.path.getctime)
    await status_msg.edit_text("🚀 **Uploading 360p Video...**")

    try:
        sent = await client.send_document(
            chat_id, 
            file_to_up, 
            caption=f"✅ **{anime_info['title']} - Ep {ep_num}** [360p]"
        )
        
        # Forward to channels if configured
        for ch_id in [CHANNEL_1, CHANNEL_2, CHANNEL_3]:
            if ch_id:
                try: await sent.copy(ch_id)
                except: pass

    except Exception as e:
        await message.reply(f"Upload Error: {e}")

    # Cleanup
    try: 
        os.remove(file_to_up)
        shutil.rmtree(os.path.dirname(file_to_up))
    except: pass
    
    if chat_id in ACTIVE_TASKS: del ACTIVE_TASKS[chat_id]
    await status_msg.delete()

async def main():
    print("🤖 Bot Starting on Railway...")
    await app.start()
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
