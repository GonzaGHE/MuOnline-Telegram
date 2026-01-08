import psutil
import subprocess
import time
import sys

def get_wmic():
    try:
        cmd = "wmic cpu get loadpercentage /Value"
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
        text = out.decode(sys.stdout.encoding or 'utf-8', errors='ignore')
        for line in text.splitlines():
            if "LoadPercentage" in line:
                return line.split('=')[1].strip()
        return "N/A"
    except:
        return "Error"

def get_typeperf_id():
    """Try to use numerical IDs for Processor(_Total)\% Processor Time
    238 = Processor
    6 = % Processor Time
    """
    try:
        # Note: In some localized Windows, the format might still need the localized name even with IDs, 
        # but pure numerical path \238(_Total)\6 works on mostly all recent versions.
        cmd = ['typeperf', r'\238(_Total)\6', '-sc', '1']
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        text = out.decode(sys.stdout.encoding or 'cp850', errors='ignore')
        lines = text.strip().splitlines()
        if len(lines) >= 2:
            return lines[-1].split(',')[-1].replace('"', '').strip()
        return "N/A"
    except Exception as e:
        return f"Error"

print("="*40)
print("     DIAGNOSTICO DE CPU")
print("="*40)
print("Midiendo... por favor espere 1 segundo.")

# PSUTIL
t0 = time.time()
ps_total = psutil.cpu_percent(interval=1)
print(f"\n1. PSUTIL (Promedio 1s): {ps_total}%")

# WMIC
print(f"2. WMIC: {get_wmic()}%")

# TYPEPERF (ID)
print(f"3. TYPEPERF (ID Neutro): {get_typeperf_id()}%")

print("\n--- PROCESOS MAS PESADOS (Top 5) ---")
# Get top processes
procs = []
for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
    try:
        p.cpu_percent(interval=None) # First call returns 0
    except: pass
time.sleep(0.5) # Wait to get a delta
for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
    try:
        # Divide by cpu_count is not needed for cpu_percent (it returns process % of a single core usually, or total? psutil docs: "The result is a float representing the current process usage as a percentage of a single CPU capacity if interval > 0" -> No wait, it can be > 100% on multicore. 
        # Actually psutil.cpu_percent() for process: "Since 2.0.0, this is a non-blocking call... returning a float... representing CPU utilization as a percentage." 
        # Logic: If process uses 50% of 2 cores, is it 100% or 25% (of 4 cores)? psutil reports sum of cores (can be > 100).
        # We need to normalize by cpu_count for "Total PC % contribution".
        
        cpu = p.info['cpu_percent']
        if cpu is None: cpu = 0
        
        # Normalize: If I have 10 cores, and process uses 10%, it's 10% of ONE core? 
        # psutil: "return a float representing the system-wide CPU utilization as a percentage" -> NO, that's cpu_percent(). 
        # Process.cpu_percent(): "compare system time... against system clock". 
        # It's usually % of one core. So we divide by cpu_count to get % of TOTAL system capacity.
        
        normalized_cpu = cpu / psutil.cpu_count()
        procs.append((p.info['name'], normalized_cpu))
    except:
        continue

procs.sort(key=lambda x: x[1], reverse=True)

for name, cpu in procs[:5]:
    print(f"   - {name}: {cpu:.2f}%")

print("="*40)
print("La suma de los procesos + sistema debería ser similar al total.")
print("Si 'Proceso Inactivo' (System Idle) es alto, el uso real es bajo.")
