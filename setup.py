import os
import sys
import subprocess
import json
import shutil
import ctypes
import time

# -------------------- COLORES (ANSI) --------------------
class Colors:    
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.ENDC}")

def print_step(text):
    print(f"{Colors.CYAN}[*] {text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}[+] {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}[!] {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}[AVISO] {text}{Colors.ENDC}")

def print_input_prompt(text):
    return input(f"{Colors.WARNING}[?] {text}{Colors.ENDC} ")

# -------------------- SETUP PRINCIPAL --------------------

def check_environment():
    print_header("VERIFICACIÓN DE SISTEMA")
    
    # Verificar Versión de Python
    v = sys.version_info
    print_step(f"Versión de Python: {v.major}.{v.minor}.{v.micro}")
    
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print_error("Tu versión de Python es muy antigua. Por favor instala Python 3.8 o superior.")
        print_error("Descárgalo en: python.org")
        input("Presiona Enter para salir...")
        sys.exit(1)
        
    # Verificar PIP
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print_success("PIP está instalado y funcionando.")
    except Exception:
        print_error("Falta PIP (Gestor de Paquetes de Python).")
        print_error("Por favor reinstala Python y asegúrate de marcar 'Add to PATH' y 'pip'.")
        print_error("A veces es necesario reiniciar la PC después de instalar Python.")
        input("Presiona Enter para salir...")
        sys.exit(1)

def install_dependencies():
    print_header("INSTALANDO DEPENDENCIAS")
    print_step("Instalando librerías (python-telegram-bot, psutil, Pillow)...")
    
    libs = ["python-telegram-bot", "psutil", "Pillow"]
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + libs)
        print_success("Comando de instalación finalizado.")
    except subprocess.CalledProcessError:
        print_error("Falló la instalación con pip.")
        print_error("Verifica tu conexión a internet o ejecuta como Administrador.")
        sys.exit(1)

    # Verificar Importación
    print_step("Verificando instalación...")
    try:
        import telegram
        import psutil
        import PIL
        print_success("¡Todas las librerías verificadas correctamente!")
    except ImportError as e:
        print_error(f"Falló la verificación de librerías: {e}")
        print_warning("Si acabas de instalar Python, INTENTA REINICIAR TU PC.")
        print_warning("A veces Windows necesita un reinicio para reconocer las nuevas librerías.")
        input("Presiona Enter para salir e intenta reiniciar...")
        sys.exit(1)

def create_config_and_install():
    print_header("INSTALACIÓN Y CONFIGURACIÓN")
    
    # 1. Definir Rutas (AppData)
    appdata_dir = os.path.join(os.getenv('APPDATA'), 'MuGuardian')
    if not os.path.exists(appdata_dir):
        os.makedirs(appdata_dir)
        print_step(f"Directorio creado: {appdata_dir}")
    
    # 2. Copiar Script Principal (explorer.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    source_script = os.path.join(current_dir, 'explorer.py')
    dest_script = os.path.join(appdata_dir, 'explorer.py')
    
    try:
        shutil.copy2(source_script, dest_script)
        print_success("Bot copiado a carpeta segura (AppData).")
    except Exception as e:
        print_error(f"Error copiando script: {e}")
        sys.exit(1)

    # 3. Pedir Datos y Crear Config
    print_step("CONFIGURACIÓN DE CREDENCIALES")
    token = print_input_prompt("Ingresa tu Token del Bot:").strip()
    if not token: sys.exit(1)
        
    admin_ids_input = print_input_prompt("Ingresa IDs de Admin (ej: 123456789):").strip()
    admin_ids = [x.strip() for x in admin_ids_input.split(",") if x.strip()]
    if not admin_ids: sys.exit(1)

    config_data = {
        "TELEGRAM_TOKEN": token,
        "CHAT_IDS": admin_ids
    }
    
    config_path = os.path.join(appdata_dir, 'config.json')
    try:
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        print_success(f"Configuración guardada oculta en: {config_path}")
    except Exception as e:
        print_error(f"Error guardando config: {e}")

    return dest_script

def setup_persistence(target_script_path):
    print_header("INTEGRACIÓN DEL SISTEMA")
    
    # Usar pythonw.exe para ocultar consola
    pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable
    else:
        print_success("Modo invisible activo (pythonw.exe).")

    # Crear VBS en Inicio
    startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
    shortcut_path = os.path.join(startup_folder, 'MuSystemMonitor.vbs')
    
    vbs_content = f"""
Set WshShell = CreateObject("WScript.Shell") 
WshShell.Run chr(34) & "{pythonw_exe}" & chr(34) & " " & chr(34) & "{target_script_path}" & chr(34), 0
Set WshShell = Nothing 
"""
    try:
        with open(shortcut_path, 'w') as f:
            f.write(vbs_content)
        print_success("Inicio automático configurado.")
    except Exception as e:
        print_error(f"Error en persistencia: {e}")

    # Ejecutar
    choice = print_input_prompt("¿Iniciar el bot ahora? (s/n):").lower()
    if choice == 's' or choice == 'y':
        print_step("Iniciando servicio...")
        subprocess.Popen([pythonw_exe, target_script_path], close_fds=True)
        print_success("Bot iniciado en segundo plano.")

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    ctypes.windll.kernel32.SetConsoleTitleW("Instalador MuGuardian")
    
    print(f"{Colors.BLUE}")
    print("************************************************")
    print("*        INSTALACIÓN AUTOMÁTICA MUGUARDIAN     *")
    print("************************************************")
    print(f"{Colors.ENDC}")
    
    print(f"{Colors.FAIL}")
    print("DESCARGO DE RESPONSABILIDAD: USO BAJO TU PROPIO RIESGO.")
    print("Este software se entrega 'tal cual'.")
    print(f"{Colors.ENDC}")
    print(f"{Colors.WARNING}Al continuar, aceptas toda la responsabilidad.{Colors.ENDC}\n")
    
    check_environment()
    install_dependencies()
    
    # Nueva lógica combinada: Instalar (Copiar) + Configurar
    final_script_path = create_config_and_install()
    setup_persistence(final_script_path)
    
    print_header("INSTALACIÓN COMPLETA")
    print_success("El bot se ha instalado en el sistema.")
    print_step("Puedes borrar esta carpeta de instalación si deseas.")
    print_step("¡Recuerda enviar /start a tu bot!")
    input(f"\n{Colors.HEADER}Presiona Enter para cerrar.{Colors.ENDC}")

if __name__ == "__main__":
    main()
