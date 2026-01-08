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
import shutil
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
    asyncio.create_task(network_monitor_loop(app))

# --------------------------- NETWORK MONITOR --------------------------- #

async def check_ping(host: str = "8.8.8.8") -> int:
    """
    Realiza un ping y retorna la latencia en ms.
    Retorna -1 si hay timeout o error.
    """
    try:
        # Ejecuta ping de forma asíncrona pero invocando al sistema
        # -n 1: 1 paquete
        # -w 2000: tiempo de espera máximo 2000ms
        proc = await asyncio.create_subprocess_exec(
            "ping", "-n", "1", "-w", "2000", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            try:
                # Intentar decodificar con utf-8 o cp850 (común en windows latam)
                output = stdout.decode('cp850', errors='ignore')
                
                # Buscar tiempo=XXms o time=XXms (y soporte para frances temps=XX ms)
                import re
                # Soporta formatos: time=10ms, tiempo=10ms, time<1ms, temps=10 ms
                match = re.search(r'(?:time|tiempo|zeit|temps)[=<]\s*([0-9]+)\s*ms', output, re.IGNORECASE)
                if match:
                    return int(match.group(1))
                # Si es returncode 0 pero no encontramos el tiempo, asumimos que está OK pero sin medida
                # (A veces pasa con <1ms en algunos sistemas si el regex falla)
                if "<1" in output: return 1
                return 10 # Valor por defecto si responde OK pero falla regex
            except:
                return 10
        return -1
    except Exception:
        return -1

async def network_monitor_loop(app: Application) -> None:
    bot = app.bot
    print("Iniciando monitor de red inteligente...")
    
    # Configuración General
    PING_HOST = "8.8.8.8"
    CHECK_INTERVAL = 10  # Segundos entre checks
    
    # --- Lógica Adaptativa (Auto-Learning) ---
    # Valores iniciales conservadores
    avg_latency = 100.0   # Empezamos asumiendo 100ms
    ALPHA = 0.1           # Peso del nuevo valor en el promedio (10%)
    
    # Límites de seguridad para el Umbral Dinámico
    # No importa qué tan rápido sea el internet, menos de 150ms no es alerta.
    # No importa qué tan lento sea el promedio, más de 600ms siempre es alerta.
    MIN_SLOW_THRESHOLD = 150 
    MAX_SLOW_THRESHOLD = 600
    
    # Estados y Contadores (Hysteresis)
    # Estados: 'OK', 'SLOW', 'DOWN'
    last_state = 'OK'
    
    # Contadores para cambiar de estado (Anti-Flap)
    consecutive_slow = 0
    consecutive_ok = 0
    consecutive_down = 0
    
    # Umbrales de cambio (Cuantas veces seguidas debe pasar para cambiar estado)
    REQ_SLOW = 2  # OK -> SLOW requiere 2 fallos
    REQ_OK = 3    # SLOW -> OK requiere 3 aciertos (más estricto para asegurar estabilidad)
    REQ_DOWN = 2  # ANY -> DOWN requiere 2 fallos totales
    
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        
        try:
            latency = await check_ping(PING_HOST)
            
            # --- Determinación del Estado Crudo (Raw) ---
            new_state_raw = 'OK'
            
            if latency == -1:
                new_state_raw = 'DOWN'
            else:
                # Cálculo Dinámico del Umbral Lento
                # El umbral es el doble del promedio actual, pero respetando límites seguros
                dynamic_threshold = max(MIN_SLOW_THRESHOLD, min(avg_latency * 2.0, MAX_SLOW_THRESHOLD))
                
                if latency > dynamic_threshold:
                    new_state_raw = 'SLOW'
                else:
                    new_state_raw = 'OK'
                    
                # Aprendizaje Continuo con Exponential Moving Average (EMA)
                # Solo aprendemos si la latencia es "normal" (OK) para no ensuciar el promedio con lag spikes
                if new_state_raw == 'OK':
                    avg_latency = (avg_latency * (1.0 - ALPHA)) + (latency * ALPHA)

            # --- Lógica de Histéresis (Anti-Rebote) ---
            current_final_state = last_state # Por defecto mantenemos el estado anterior
            
            # Manejo de DOWN (Prioridad Alta)
            if new_state_raw == 'DOWN':
                consecutive_down += 1
                consecutive_ok = 0
                consecutive_slow = 0
                if consecutive_down >= REQ_DOWN:
                     current_final_state = 'DOWN'
            else:
                consecutive_down = 0 
                # Si no estamos DOWN, vemos si es SLOW u OK
                
                if new_state_raw == 'SLOW':
                    consecutive_slow += 1
                    consecutive_ok = 0
                    if consecutive_slow >= REQ_SLOW:
                        current_final_state = 'SLOW'
                    else:
                        # Si aún no llegamos al contador, mantenemos el estado previo
                        # Salvo que viniéramos de DOWN, en cuyo caso pasamos a SLOW preventivo o mantenemos DOWN?
                        # Mejor: Si venimos de DOWN, cualquier señal de vida es buena, pero esperemos a estabilizar.
                        if last_state == 'DOWN': pass 
                        else: current_final_state = last_state

                elif new_state_raw == 'OK':
                    consecutive_ok += 1
                    consecutive_slow = 0
                    if consecutive_ok >= REQ_OK:
                        current_final_state = 'OK'
                    else:
                        # Si venimos de SLOW/DOWN, necesitamos confirmar REQ_OK veces.
                        if last_state != 'OK': current_final_state = last_state
                        else: current_final_state = 'OK' # Si ya estábamos OK, seguimos OK

            # --- Notificaciones ---
            if current_final_state != last_state:
                msg = ""
                
                # Entrando a DOWN
                if current_final_state == 'DOWN':
                    msg = (
                        f"🚨 <b>ALERTA DE RED</b>\n"
                        f"📡 Conexión Perdida\n"
                        f"⚠️ Sin respuesta del servidor\n"
                        f"⏰ {get_time()}"
                    )
                
                # Saliendo de DOWN
                elif last_state == 'DOWN':
                    status_text = "Estable" if current_final_state == 'OK' else "Inestable"
                    msg = (
                        f"✅ <b>CONEXIÓN RESTAURADA</b>\n"
                        f"📡 Estado: {status_text}\n"
                        f"⏰ {get_time()}"
                    )

                # Entrando a SLOW (desde OK)
                elif current_final_state == 'SLOW' and last_state == 'OK':
                    msg = (
                        f"⚠️ <b>INTERNET LENTO</b>\n"
                        f"🐢 Latencia: {latency}ms (Promedio: {int(avg_latency)}ms)\n"
                        f"📉 Umbral dinámico: {int(dynamic_threshold)}ms\n"
                        f"⏰ {get_time()}"
                    )
                
                # Saliendo de SLOW (hacia OK)
                elif current_final_state == 'OK' and last_state == 'SLOW':
                    msg = (
                        f"✅ <b>LATENCIA NORMALIZADA</b>\n"
                        f"🚀 Ping actual: {latency}ms\n"
                        f"⏰ {get_time()}"
                    )

                if msg:
                    for cid in CHAT_IDS:
                        try: await bot.send_message(cid, msg, parse_mode=ParseMode.HTML)
                        except: pass
                
                last_state = current_final_state
                
        except Exception as e:
            print(f"Error en monitor de red: {e}")




# --------------------------- VERSION & UPDATES --------------------------- #
VERSION = "1.1.0"
RELEASE_NOTES = """
- ✅ Agregado monitor de red inteligente (Auto-Learning).
- ✅ Notificaciones de internet lento y desconexiones.
- ✅ Sistema de Auto-Actualización integrado.
"""
REPO_URL = "https://raw.githubusercontent.com/GonzaGHE/MuOnline-Telegram/main/explorer.py"

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def check_update_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): return
    
    msg = await update.message.reply_text("⏳ Verificando actualizaciones...")
    
    try:
        import urllib.request
        with urllib.request.urlopen(REPO_URL) as response:
            remote_code = response.read().decode('utf-8')
            
        # Extraer versión remota
        import re
        version_match = re.search(r'VERSION\s*=\s*"([^"]+)"', remote_code)
        remote_version = version_match.group(1) if version_match else "Unknown"
        
        # Extraer notas remotas
        notes_match = re.search(r'RELEASE_NOTES\s*=\s*"""(.*?)"""', remote_code, re.DOTALL)
        remote_notes = notes_match.group(1).strip() if notes_match else "Sin notas."
        
        # Comparar
        if remote_version == VERSION:
            text = (
                f"✅ <b>SISTEMA ACTUALIZADO</b>\n"
                f"🛡️ Versión instalada: v{VERSION}\n\n"
                f"📝 <b>Últimos cambios locales:</b>\n{RELEASE_NOTES}"
            )
            await msg.edit_text(text, parse_mode=ParseMode.HTML)
        else:
            text = (
                f"🚀 <b>NUEVA VERSIÓN DISPONIBLE: v{remote_version}</b>\n"
                f"📌 Actual: v{VERSION}\n\n"
                f"📝 <b>Novedades:</b>\n{remote_notes}\n\n"
                f"🔗 <a href='https://github.com/GonzaGHE/MuOnline-Telegram'>Ver Repositorio</a>"
            )
            
            keyboard = [[InlineKeyboardButton("✅ Instalar Actualización", callback_data="confirm_update")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True)

    except Exception as e:
        await msg.edit_text(f"❌ Error verificando actualización: {e}")

async def update_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.data != "confirm_update": return
    if not is_admin(query.from_user.id): return

    await query.answer()
    await query.edit_message_text("⏳ <b>Iniciando actualización...</b>\n1️⃣ Descargando código...\n2️⃣ Instalando dependencias...\n3️⃣ Reiniciando...", parse_mode=ParseMode.HTML)
    
    try:
        # 1. Backup
        shutil.copy2(__file__, __file__ + ".bak")
        
        # 2. Descargar código nuevo principal
        import urllib.request
        with urllib.request.urlopen(REPO_URL) as response:
            remote_code = response.read().decode('utf-8')
            
        with open(__file__, 'w', encoding='utf-8') as f:
            f.write(remote_code)
            
        # 3. Intentar instalar dependencias
        # Buscamos requirements.txt en el repo
        REQ_URL = "https://raw.githubusercontent.com/GonzaGHE/MuOnline-Telegram/main/requirements.txt"
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQ_URL])
        except:
            # Si falla (ej: no existe el archivo), seguimos igual
            pass
            
        # 4. Reiniciar
        print("Reiniciando proceso...")
        os.execv(sys.executable, ['python'] + sys.argv)
        
    except Exception as e:
        await query.message.reply_text(f"❌ Error crítico en actualización: {e}\nRestaurando backup...")
        shutil.copy2(__file__ + ".bak", __file__)


# --------------------------- MAIN --------------------------- #

def run():
    print("Starting Bot...")
    # Network Resilience Loop
    while True:
        try:
            # Añadir CallbackQueryHandler
            from telegram.ext import CallbackQueryHandler
            
            app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(on_startup).build()
            
            app.add_handler(CommandHandler("start", start_cmd))
            app.add_handler(CommandHandler("status", status_cmd))
            app.add_handler(CommandHandler("screen", screen_cmd))
            app.add_handler(CommandHandler("reiniciar", reiniciar_pc))
            app.add_handler(CommandHandler("apagar", apagar_pc))
            app.add_handler(CommandHandler(["actualizar", "update"], check_update_cmd))
            
            app.add_handler(CallbackQueryHandler(update_callback_handler))
            
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