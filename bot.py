import os
import asyncio
import aiohttp
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.errors import FloodWait
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION ---
# Pulling secrets from Environment Variables
API_ID = os.environ.get("API_ID", "YOUR_API_ID") 
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGO_URI") # Added MongoDB URI
# MUST BE AN INTEGER: e.g., 123456789
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0")) 

# --- MONGODB DATABASE SETUP ---
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["clario_bot"]
users_collection = db["users"]

# In-memory toggle for maintenance mode
bot_live = True

# Helper function to add users to database
async def add_user_to_db(user_id: int):
    user = await users_collection.find_one({"_id": user_id})
    if not user:
        await users_collection.insert_one({"_id": user_id})

# Initialize Pyrogram Client
app = Client(
    "ClarioBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- DUMMY WEB SERVER FOR RENDER ---
async def handle(request):
    return web.Response(text="💀 Clario Terminal is Online and Locked Down!")

async def web_server():
    web_app = web.Application()
    web_app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"💀 Web server bound to port {port}")

# --- ADMIN PANEL ---
@app.on_message(filters.command(["admin"]) & filters.private)
async def admin_panel(client: Client, message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    total_users = await users_collection.count_documents({})
    status_text = "🟢 ONLINE" if bot_live else "🔴 OFFLINE"
    text = f"💀 **Clario Admin Terminal**\n\n**System Status:** {status_text}\n**Total Users:** {total_users}"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton(f"Toggle Bot ({'OFF' if bot_live else 'ON'})", callback_data="admin_toggle")]
    ])
    
    await message.reply_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)

@app.on_callback_query(filters.regex(r"^admin_"))
async def admin_callback(client: Client, callback_query: CallbackQuery):
    global bot_live
    
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("Access Denied.", show_alert=True)
        return

    data = callback_query.data

    if data == "admin_toggle":
        bot_live = not bot_live
        status_text = "🟢 ONLINE" if bot_live else "🔴 OFFLINE"
        total_users = await users_collection.count_documents({})
        
        # Re-build buttons
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton(f"Toggle Bot ({'OFF' if bot_live else 'ON'})", callback_data="admin_toggle")]
        ])
        
        text = f"💀 **Clario Admin Terminal**\n\n**System Status:** {status_text}\n**Total Users:** {total_users}"
        await callback_query.message.edit_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)
        await callback_query.answer(f"Bot is now {'LIVE' if bot_live else 'OFFLINE'}")

    elif data == "admin_stats":
        total_users = await users_collection.count_documents({})
        await callback_query.answer(f"Total Users: {total_users}", show_alert=True)

    elif data == "admin_broadcast":
        # Ask admin for the broadcast message
        await callback_query.message.reply_text("Please send the message you want to broadcast.\nReply to this message.", reply_markup=pyrogram.types.ForceReply(selective=True))
        await callback_query.answer()

# Listen for the admin's broadcast reply
@app.on_message(filters.private & filters.reply & filters.user(ADMIN_ID))
async def handle_broadcast(client: Client, message: Message):
    # Check if the message being replied to is the broadcast prompt
    if message.reply_to_message.text and "Please send the message you want to broadcast." in message.reply_to_message.text:
        total_users = await users_collection.count_documents({})
        if total_users == 0:
            await message.reply_text("❌ No users in the database to broadcast to.")
            return

        broadcast_msg = message.text
        if not broadcast_msg:
             # If they sent a photo/video, Pyrogram requires different handling. Sticking to text for simplicity here.
             await message.reply_text("❌ Please send a text message for the broadcast.")
             return
            
        success = 0
        failed = 0
        
        status_msg = await message.reply_text("<i>Initiating broadcast...</i>", parse_mode=ParseMode.HTML)
        
        cursor = users_collection.find({})
        async for document in cursor:
            user_id = document["_id"]
            try:
                await client.send_message(user_id, f"{broadcast_msg}")
                success += 1
                await asyncio.sleep(0.1) # Prevent FloodWait
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await client.send_message(user_id, f"{broadcast_msg}")
                success += 1
            except Exception:
                failed += 1
                
        await status_msg.edit_text(f"✅ **Broadcast Complete**\n\nSent: {success}\nFailed: {failed}", parse_mode=ParseMode.MARKDOWN)


# --- BOT COMMANDS & LOGIC ---
@app.on_message(filters.command(["start", "help"]) & filters.private)
async def start(client, message: Message):
    await add_user_to_db(message.from_user.id) # Add user to DB
    
    if not bot_live and message.from_user.id != ADMIN_ID:
        await message.reply_text("🔧 <b>Maintenance Mode</b>\n\n⚠️ The bot is currently under maintenance.\nPlease wait while we improve our services.\n\nJoin for Updates: @techbittu69\n⏰ We'll be back soon!")
        return

    welcome_text = (
        "👋 <b>Welcome To Clario</b>\n\n"
        "A Premium Way To Discover Who’s Behind The Number.\n\n"
        "Fast, Refined And Intelligent — Clario Helps You Identify Callers With Ease And Confidence.\n\n"
        "Just Send Me A Phone Number. Ex- <code>9876543210</code>"
    )
    await message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

@app.on_message(filters.text & filters.private)
async def handle_lookup(client, message: Message):
    # Ignore commands
    if message.text.startswith("/"):
        return
        
    await add_user_to_db(message.from_user.id) # Ensure user is in DB
        
    if not bot_live and message.from_user.id != ADMIN_ID:
        await message.reply_text("🔧 <b>Maintenance Mode</b>\n\n⚠️ The bot is currently under maintenance.\nPlease wait while we improve our services.\n\nJoin for Updates: @techbittu69\n⏰ We'll be back soon!")
        return
        
    target_number = message.text.strip()
    
    clean_number = "".join(filter(str.isdigit, target_number))
    if len(clean_number) > 10 and clean_number.startswith("91"):
        clean_number = clean_number[2:]

    await client.send_chat_action(message.chat.id, ChatAction.TYPING)

    # 1. FASTER FUNNY ANIMATION SEQUENCE
    msg = await message.reply_text("<i>Initializing...</i>", parse_mode=ParseMode.HTML)
    
    anim_stages = [
        "🛸 <i>Connecting To Jadoo...</i>",
        "🚀 <i>Consulting To Elon Mask...</i>",
        "🛰 <i>Contacting To NASA Satellites...</i>",
        "🌌 <i>Calling To Stephen Hawking...</i>",
        "🧬 <i>Running DNA Analysis...</i>",
        "⏳ <i>Decrypting Space-Time...</i>",
        "🔭 <i>Contacting To Hubble Telescope...</i>",
        "☀️ <i>Getting The Info From The Sun...</i>",
        "😶‍🌫️ <i>Collecting Data From NASA Servers...</i>"
    ]
    
    # Ultra-fast edit loop (0.25s)
    for stage in anim_stages:
        try:
            await msg.edit_text(stage, parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.25)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            pass

    # 2. Fetch Data via aiohttp
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

        unique_records = []
        seen = set()
        for r in records:
            sig = f"{r.get('name')}_{r.get('id')}"
            if sig not in seen:
                seen.add(sig)
                unique_records.append(r)

        # 3. Format the final output
        output_msg = ""
        for record in unique_records:
            name = record.get("name", "N/A")
            father = record.get("father_name", "N/A")
            mobile = record.get("mobile", target_number)
            alt_mobile = record.get("alt_mobile", "None")
            email = record.get("email", "None") or "None" 
            aadhaar_id = record.get("id", "N/A")
            circle = record.get("circle", "N/A")
            
            raw_address = record.get("address", "N/A")
            clean_address = raw_address.replace("!", ", ").strip(", ")

            output_msg += f"👤 <b>Name:</b> {name}\n"
            output_msg += f"👨 <b>Father:</b> {father}\n"
            output_msg += f"📞 <b>Mobile:</b> <code>{mobile}</code>\n"
            output_msg += f"📞 <b>Alt Mobile:</b> {alt_mobile}\n"
            output_msg += f"✉️ <b>Email:</b> {email}\n"
            output_msg += f"🪪 <b>Aadhaar:</b> <tg-spoiler>{aadhaar_id}</tg-spoiler>\n"
            output_msg += f"🏠 <b>Address:</b> {clean_address}\n"
            output_msg += f"🆔 <b>Circle:</b> {circle}\n"
            output_msg += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        bot_info = await client.get_me()
        output_msg += f"👨‍💻 Checked by: @{bot_info.username}\n"
        output_msg += "👑 Powered by: @techbittu69"
        
        # 4. SHOW THE FINAL JOKE AND FREEZE 💀
        try:
            await msg.edit_text("<b>Details Fetched Successfully From NASA Servers💀</b>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(1.5)
        except FloodWait as e:
            await asyncio.sleep(e.value)

        # 5. RESTORE ARRIVAL ANIMATION + CONTENT PROTECTION 🔒
        await msg.delete()
        final_msg = await message.reply_text(
            output_msg, 
            parse_mode=ParseMode.HTML, 
            protect_content=True  # <--- THIS LOCKS THE MESSAGE DOWN
        )

        # 6. SILENT CRYSTAL CLEAN PROTOCOL: 60 Second Delete Timer
        await asyncio.sleep(60)
        try:
            await final_msg.delete() 
            await message.delete() 
        except:
            pass

    except Exception as e:
        await msg.edit_text(f"❌ <b>System Failure:</b> {str(e)}", parse_mode=ParseMode.HTML)

# --- RUN THE APP ---
async def main():
    await web_server() 
    await app.start()  
    print("💀 Clario Premium is running securely with MongoDB...")
    await pyrogram.idle() 
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
        
