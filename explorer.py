#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DEPENDENCIES:
pip install python-telegram-bot psutil Pillow

DESCRIPTION:
Professional Mu Online Bot Manager.
- Process Monitoring (Main.exe)
- System Status (CPU/RAM/Clients)
- Remote Control (Shutdown/Restart)
- Desktop Screenshot
- Network Resilience (Auto-Retry)

No local logging. No emojis in comments.
"""

import asyncio
import logging
import os
import subprocess
import sys
import platform
import ctypes
from io import BytesIO
from datetime import datetime
from typing import Set, Tuple, List

# Third party libraries
try:
    import psutil
    from telegram import Update
    from telegram.constants import ParseMode
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        ContextTypes,
        Application,
    )
    # Optional dependency for screenshots
    try:
        from PIL import ImageGrab
        HAS_SCREENSHOT = True
    except ImportError:
        HAS_SCREENSHOT = False

except ImportError:
    print("Missing dependencies. Run: pip install python-telegram-bot psutil Pillow")
    sys.exit(1)

# --------------------------- CONFIGURATION --------------------------- #

import json

# Define AppData path for config
APPDATA_DIR = os.path.join(os.getenv('APPDATA'), 'MuGuardian')
CONFIG_FILE = os.path.join(APPDATA_DIR, 'config.json')

# Portable fallback (check local dir if AppData fails)
if not os.path.exists(CONFIG_FILE):
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

TELEGRAM_TOKEN = ""
CHAT_IDS = []

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        TELEGRAM_TOKEN = config.get("TELEGRAM_TOKEN", "")
        CHAT_IDS = config.get("CHAT_IDS", [])
except Exception:
    # Fallback to defaults
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
    CHAT_IDS = ["123456789"]

# Allowed User IDs (Ensure they are strings)
CHAT_IDS = [str(uid) for uid in CHAT_IDS]

# Process to Monitor
MU_PROCESS_NAME = "main.exe"
MU_DISPLAY_NAME = "Mu Online"

# Scan Interval (seconds)
SCAN_INTERVAL = 5

# --------------------------- LOGGING --------------------------- #
# Only critical errors to console, no file logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and ignore."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# --------------------------- UTILS --------------------------- #

def get_time() -> str:
    """Return formatted timestamp string."""
    return datetime.now().strftime("%H:%M:%S")

def get_date_time() -> str:
    """Return full date and time string."""
    return datetime.now().strftime("%d/%m/%Y %H:%M")

def is_admin(user_id: int) -> bool:
    """Check if user id is authorized."""
    return str(user_id) in CHAT_IDS

def run_silent(command_args: List[str]) -> bool:
    """Execute system command without showing a window."""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(command_args, startupinfo=startupinfo, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                         close_fds=True, shell=False)
        return True
    except Exception:
        return False

def get_mu_process_info() -> List[dict]:
    """Retrieve info for all active Mu Online processes."""
    instances = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == MU_PROCESS_NAME.lower():
                mem_mb = round(proc.info['memory_info'].rss / (1024**2), 1)
                instances.append({
                    'pid': proc.info['pid'],
                    'ram': f"{mem_mb} MB"
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return instances

def get_system_stats() -> str:
    """Generate a formatted system status report."""
    try:
        # System Stats
        cpu_usage = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        ram_used = round(ram.used / (1024**3), 2)
        ram_total = round(ram.total / (1024**3), 2)
        ram_percent = ram.percent
        
        # Game Stats
        instances = get_mu_process_info()
        count = len(instances)
        
        # Build Message
        instance_lines = ""
        if count > 0:
            for i, inst in enumerate(instances, 1):
                instance_lines += f"{i}️⃣ <b>PID {inst['pid']}</b>: {inst['ram']}\n"
        else:
            instance_lines = "   └─ Ninguno activo"

        msg = (
            f"📊 <b>ESTADO DEL SISTEMA</b>\n\n"
            f"💻 <b>CPU</b>: {cpu_usage}%  |  🧠 <b>RAM</b>: {ram_percent}%\n"
            f"🎮 <b>{MU_DISPLAY_NAME}</b>: {count} Clientes\n\n"
            f"{instance_lines}"
        )   
        return msg
    except Exception as e:
        return f"Error obteniendo stats: {str(e)}"

# --------------------------- COMMANDS --------------------------- #

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): return
    stats = get_system_stats()
    await update.message.reply_text(stats, parse_mode=ParseMode.HTML)

async def screen_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): return
    
    if not HAS_SCREENSHOT:
        await update.message.reply_text("❌ Falta librería `Pillow`. Instala: `pip install Pillow`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        shot = ImageGrab.grab()
        bio = BytesIO()
        shot.save(bio, 'PNG')
        bio.seek(0)
        
        caption = f"📸 <b>Captura de Escritorio</b>\n⏰ {get_time()}"
        await update.message.reply_photo(photo=bio, caption=caption, parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error tomando captura: {e}")

async def reiniciar_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): return
    msg = (
        f"⚠️ <b>ALERTA DE SISTEMA</b>\n"
        f"♻️ Reinicio solicitado por Admin\n"
        f"⏳ Ejecutando en 3 segundos..."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    run_silent(["shutdown", "/r", "/f", "/t", "3"])

async def apagar_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): return
    msg = (
        f"⚠️ <b>ALERTA DE SISTEMA</b>\n"
        f"⏻ Apagado solicitado por Admin\n"
        f"⏳ Ejecutando en 3 segundos..."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    run_silent(["shutdown", "/s", "/f", "/t", "3"])

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): return
    cmds = (
        f"🛡️ <b>MuGuardian Online</b>\n"
        f"🚀 Sistema Iniciado\n"
        f"📅 {get_date_time()}\n\n"
        f"/status - Ver estado y cuentas\n"
        f"/screen - Ver escritorio\n"
        f"/reiniciar - Reiniciar PC\n"
        f"/apagar - Apagar PC"
    )
    await update.message.reply_text(cmds, parse_mode=ParseMode.HTML)

# --------------------------- MONITOR LOOP --------------------------- #

async def monitor_loop(app: Application) -> None:
    bot = app.bot
    # Startup Notification
    startup_msg = (
        f"🛡️ <b>MuGuardian Online</b>\n"
        f"🚀 Sistema Iniciado\n"
        f"📅 {get_date_time()}"
    )
    for cid in CHAT_IDS:
        try: await bot.send_message(cid, startup_msg, parse_mode=ParseMode.HTML)
        except: pass

    last_instances: Set[Tuple[int, str]] = set()

    while True:
        try:
            current_instances: Set[Tuple[int, str]] = set()
            
            # Find Processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    p_name = proc.info['name']
                    if p_name and p_name.lower() == MU_PROCESS_NAME.lower():
                        current_instances.add((proc.info['pid'], MU_DISPLAY_NAME))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Detect Changes
            newly_opened = current_instances - last_instances
            newly_closed = last_instances - current_instances

            # Notify Opened
            for pid, name in newly_opened:
                msg = (
                    f"🟢 <b>VENTANA ABIERTA</b>\n"
                    f"🎮 <b>{name}</b>\n"
                    f"🆔 PID: {pid}\n"
                    f"⏰ {get_time()}"
                )
                for cid in CHAT_IDS:
                    try: await bot.send_message(cid, msg, parse_mode=ParseMode.HTML)
                    except: pass

            # Notify Closed
            for pid, name in newly_closed:
                msg = (
                    f"🔴 <b>VENTANA CERRADA</b>\n"
                    f"🎮 <b>{name}</b>\n"
                    f"🆔 PID: {pid}\n"
                    f"⏰ {get_time()}"
                )
                for cid in CHAT_IDS:
                    try: await bot.send_message(cid, msg, parse_mode=ParseMode.HTML)
                    except: pass

            last_instances = current_instances

        except Exception:
            # Silent catch to prevent loop exit
            await asyncio.sleep(5)

        await asyncio.sleep(SCAN_INTERVAL)

async def on_startup(app: Application):
    asyncio.create_task(monitor_loop(app))

# --------------------------- MAIN --------------------------- #

def run():
    print("Starting Bot...")
    # Network Resilience Loop
    while True:
        try:
            app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(on_startup).build()
            
            app.add_handler(CommandHandler("start", start_cmd))
            app.add_handler(CommandHandler("status", status_cmd))
            app.add_handler(CommandHandler("screen", screen_cmd))
            app.add_handler(CommandHandler("reiniciar", reiniciar_pc))
            app.add_handler(CommandHandler("apagar", apagar_pc))
            
            app.add_error_handler(error_handler)
            
            print("Bot Running. Press Ctrl+C to stop.")
            # run_polling blocks until stop signal or connection error
            app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            # If polling fails (e.g. Network Error), print and retry
            print(f"Connection lost or error: {e}. Retrying in 10s...")
            import time
            time.sleep(10)
        except KeyboardInterrupt:
            print("Bot stopped by user.")
            break

if __name__ == "__main__":
    run()