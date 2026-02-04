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
# Sevalla uses Environment Variables for secrets
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

# Channel IDs (Optional)
CHANNEL_1 = os.environ.get('CHANNEL_1')
CHANNEL_2 = os.environ.get('CHANNEL_2')
CHANNEL_3 = os.environ.get('CHANNEL_3')

DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
ACTIVE_TASKS = {}

app = Client(
    "anime_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=8
)

# --- 2. HELPERS ---
async def get_video_resolution(filepath):
    try:
        cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 '{filepath}'"
        process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await process.communicate()
        return f"{stdout.decode().strip()}p"
    except: return "360p"

async def consume_stream(process):
    while True:
        line = await process.stdout.readline()
        if not line: break

# --- 3. COMMANDS ---
@app.on_message(filters.command("dl"))
async def dl_cmd(client, message):
    chat_id = message.chat.id
    if chat_id in ACTIVE_TASKS: return await message.reply("⚠️ A task is already running.")

    cmd_text = message.text[4:]
    
    # Force 360p logic
    ep_match = re.search(r'-e\s+([\d,-]+)', cmd_text)
    name_match = re.search(r'-a\s+["\']([^"\']+)["\']', cmd_text)
    
    if not ep_match or not name_match:
        return await message.reply("Usage: `/dl -a \"Anime Name\" -e 1` (Forced to 360p)")

    anime_query = name_match.group(1)
    ep_num = ep_match.group(1)
    
    status_msg = await message.reply("⏳ **Initializing 360p Download...**")
    ACTIVE_TASKS[chat_id] = {"status": "running"}

    # Run the bash script (Modified for 360p only)
    # We pass '-r 360' explicitly here
    current_cmd = f"bash animepahe-dl.sh -a \"{anime_query}\" -e {ep_num} -r 360"

    process = await asyncio.create_subprocess_shell(
        current_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await consume_stream(process)
    await process.wait()

    # Find the downloaded file
    mp4s = glob.glob(f"**/*.mp4", recursive=True)
    if not mp4s:
        await message.reply("❌ File not found. Check if the anime/episode exists.")
        if chat_id in ACTIVE_TASKS: del ACTIVE_TASKS[chat_id]
        return

    file_to_up = max(mp4s, key=os.path.getctime)
    
    await status_msg.edit_text("🚀 **Uploading 360p quality...**")
    await client.send_document(chat_id, file_to_up, caption=f"✅ {anime_query} - Ep {ep_num} [360p]")
    
    # Cleanup
    os.remove(file_to_up)
    if chat_id in ACTIVE_TASKS: del ACTIVE_TASKS[chat_id]
    await status_msg.delete()

async def start_bot():
    print("🚀 Bot is starting on Sevalla...")
    await app.start()
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
