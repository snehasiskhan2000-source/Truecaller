import os
import asyncio
import aiohttp
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from aiohttp import web

# --- CONFIGURATION (Pulls from Render Environment Variables) ---
API_ID = os.environ.get("API_ID", "YOUR_API_ID_HERE") 
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH_HERE")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Initialize Pyrogram Client
app = Client(
    "AdvanceLookupBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- DUMMY WEB SERVER FOR RENDER ---
async def handle(request):
    return web.Response(text="💀 Premium Bot is Online!")

async def web_server():
    web_app = web.Application()
    web_app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- BOT COMMANDS & LOGIC ---
@app.on_message(filters.command(["start", "help"]))
async def start(client, message: Message):
    welcome_text = (
        "👋 <b>Welcome to the Advance Lookup Bot!</b>\n\n"
        "Send me a 10-digit number (e.g., 8436829060) and I'll fetch the target's details."
    )
    await message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

@app.on_message(filters.text & filters.private)
async def handle_lookup(client, message: Message):
    target_number = message.text.strip()
    
    # Clean the number (remove +91 or spaces if the user adds them)
    clean_number = "".join(filter(str.isdigit, target_number))
    if len(clean_number) > 10 and clean_number.startswith("91"):
        clean_number = clean_number[2:]

    # 1. Start Initial Animation
    loading_text = "<b>[■□□□□□□□□□] 10%</b>\n<i>⚡ Initializing secure connection...</i>"
    msg = await message.reply_text(loading_text, parse_mode=ParseMode.HTML)
    
    # 2. High-End Editing Animation Sequence
    anim_stages = [
        "<b>[■■■■□□□□□□] 40%</b>\n<i>🔍 Scanning Truecaller database...</i>",
        "<b>[■■■■■■■□□□] 70%</b>\n<i>🧬 Extracting target identity & Aadhaar...</i>",
        "<b>[■■■■■■■■■■] 100%</b>\n<i>✅ Decrypting payload...</i>"
    ]
    
    for stage in anim_stages:
        await asyncio.sleep(0.8) # Wait slightly to avoid Telegram Flood limits
        try:
            await msg.edit_text(stage, parse_mode=ParseMode.HTML)
        except:
            pass # Ignore if telegram blocks a rapid edit

    # 3. Fetch Data via aiohttp (Fast Async)
    url = f"https://true-call-check.vercel.app/api/truecaller?num={clean_number}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    await msg.edit_text("❌ <b>Error:</b> API offline or unreachable.", parse_mode=ParseMode.HTML)
                    return
                data = await response.json()
                
        records = data.get("data", [])
        
        if not records:
            await msg.edit_text("❌ <b>Target Ghosted:</b> No records found.", parse_mode=ParseMode.HTML)
            return

        # 4. Format the final output
        output_msg = ""
        for i, record in enumerate(records, start=1):
            name = record.get("name", "N/A")
            father = record.get("father_name", "N/A")
            mobile = record.get("mobile", target_number)
            alt_mobile = record.get("alt_mobile", "N/A")
            aadhaar_id = record.get("id", "N/A")
            circle = record.get("circle", "N/A")
            
            # Clean up that messy address string (!Fingagachi!...)
            raw_address = record.get("address", "N/A")
            clean_address = raw_address.replace("!", ", ").strip(", ")

            output_msg += f"🗂 <b>Record {i}</b>\n"
            output_msg += f"👤 <b>Name:</b> {name}\n"
            output_msg += f"👨 <b>Father:</b> {father}\n"
            output_msg += f"📞 <b>Mobile:</b> <code>{mobile}</code>\n"
            output_msg += f"📞 <b>Alt Mobile:</b> <code>{alt_mobile}</code>\n"
            # Pyrogram HTML tag for spoilers
            output_msg += f"🪪 <b>Aadhaar:</b> <tg-spoiler>{aadhaar_id}</tg-spoiler>\n"
            output_msg += f"🏠 <b>Address:</b> {clean_address}\n"
            output_msg += f"🆔 <b>Circle:</b> {circle}\n"
            output_msg += "━━━━━━━━━━━━━━━━━━━\n"
        
        bot_info = await client.get_me()
        output_msg += f"\n👨‍💻 Checked by: @{bot_info.username}\n"
        output_msg += "👑 Powered by: @TheAdvanceBots"
        
        # 5. Send final payload
        await msg.edit_text(output_msg, parse_mode=ParseMode.HTML)

    except Exception as e:
        await msg.edit_text(f"❌ <b>System Failure:</b> {str(e)}", parse_mode=ParseMode.HTML)

# --- RUN THE APP ---
async def main():
    await web_server() # Starts the Render health-check server
    await app.start()  # Starts the bot
    print("💀 Premium Bot is running...")
    await pyrogram.idle() # Keeps it running
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    
