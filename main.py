import os
import asyncio
import glob
import time
import re
from pyrogram import Client, filters, idle

# --- 1. CONFIGURATION ---
# Railway uses Environment Variables for these
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

app = Client("anime_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

ACTIVE_TASKS = {}

# --- 2. HELPERS ---
async def consume_stream(process):
    """Prints the output of the bash script to the Railway logs"""
    while True:
        line = await process.stdout.readline()
        if not line: break
        print(f"[SHELL] {line.decode().strip()}")

# --- 3. COMMANDS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("🤖 **Anime 360p Downloader Ready!**\nUsage: `/dl -a \"Anime Name\" -e 1`")

@app.on_message(filters.command("dl"))
async def dl_cmd(client, message):
    chat_id = message.chat.id
    if chat_id in ACTIVE_TASKS: 
        return await message.reply("⚠️ A task is already running. Please wait.")

    # Extract anime name and episode from command
    cmd_text = message.text[4:]
    name_match = re.search(r'-a\s+["\']([^"\']+)["\']', cmd_text)
    ep_match = re.search(r'-e\s+([\d,-]+)', cmd_text)

    if not name_match or not ep_match:
        return await message.reply("❌ **Invalid Format!**\nUse: `/dl -a \"One Piece\" -e 1000`")

    anime_name = name_match.group(1)
    ep_num = ep_match.group(1)

    status_msg = await message.reply(f"📥 **Downloading:** {anime_name} - Ep {ep_num} (360p)")
    ACTIVE_TASKS[chat_id] = True

    try:
        # Run your .sh script. Forced to 360p (-r 360)
        command = f"bash animepahe-dl.sh -a \"{anime_name}\" -e {ep_num} -r 360"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await consume_stream(process)
        await process.wait()

        # Check for the downloaded .mp4 file
        mp4_files = glob.glob("**/*.mp4", recursive=True)
        if not mp4_files:
            await status_msg.edit_text("❌ **Download failed.** Could not find the file.")
            return

        file_to_send = max(mp4_files, key=os.path.getctime)
        
        await status_msg.edit_text("🚀 **Uploading to Telegram...**")
        await client.send_document(
            chat_id, 
            file_to_send, 
            caption=f"✅ **{anime_name} - Episode {ep_num}**\nQuality: 360p"
        )
        
        # Cleanup file to save disk space
        os.remove(file_to_send)
        await status_msg.delete()

    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")
    finally:
        if chat_id in ACTIVE_TASKS:
            del ACTIVE_TASKS[chat_id]

async def main():
    print("🤖 Bot is starting on Railway...")
    await app.start()
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
