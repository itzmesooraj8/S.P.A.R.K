import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from modules import actions
from fabric import Connection

# You must set TELEGRAM_TOKEN in your .env or export it
TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID") # e.g., '123456789'

# Simple SSH Config for Home PC (Hardcoded for Phase 4 demo, move to DB/Env later)
HOME_PC_HOST = os.getenv("HOME_PC_HOST", "192.168.1.50")
HOME_PC_USER = os.getenv("HOME_PC_USER", "user")
# Assumes SSH Key Auth is set up

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⚡ S.P.A.R.K. Remote Uplink Established.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Unauthorized Access.")
        return

    msg = update.message.text
    print(f"📩 [Telegram] Received: {msg}")
    
    # Simple logic dispatch - In real app, send this to spark_core.think()
    response_text = ""
    
    if "check render" in msg.lower():
        response_text = check_render_status()
    elif "shutdown pc" in msg.lower():
        response_text = "⚠️ Are you sure? Reply 'CONFIRM SHUTDOWN' to execute."
    elif msg == "CONFIRM SHUTDOWN":
        response_text = ssh_shutdown()
    else:
        # For now, just echo. ideally, we pipe this into Ollama here.
        response_text = f"Received: {msg}. (AI processing not linked in this minimal bot script yet)"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response_text)

def check_render_status():
    """Connects to Home PC via SSH and checks a process or file."""
    print("🔌 Connecting to Home PC...")
    try:
        # Using Fabric to run a command remotely
        # Ensure your public key is on the target machine!
        c = Connection(host=HOME_PC_HOST, user=HOME_PC_USER)
        # Example: check if a blender process is running
        result = c.run('pgrep blender', warn=True, hide=True)
        if result.ok:
            return f"✅ Render Active. PID: {result.stdout.strip()}"
        else:
            return "🛑 No render process found."
    except Exception as e:
        return f"❌ Connection Failed: {e}"

def ssh_shutdown():
    try:
        c = Connection(host=HOME_PC_HOST, user=HOME_PC_USER)
        c.run('sudo shutdown -h now', warn=True) # Might need sudoers NOPASSWD
        return "🔌 Home PC Shutdown Signal Sent."
    except Exception as e:
        return f"❌ Shutdown Failed: {e}"

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Error: TELEGRAM_TOKEN not found in environment.")
    else:
        print("📡 S.P.A.R.K. Remote Listener Starting...")
        application = ApplicationBuilder().token(TOKEN).build()
        
        start_handler = CommandHandler('start', start)
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        
        application.add_handler(start_handler)
        application.add_handler(msg_handler)
        
        application.run_polling()
