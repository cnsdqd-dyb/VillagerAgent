import psutil
import subprocess
import time
import os

def is_script_running(script_name):
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] == 'python' or proc.info['name'] == 'python.exe':
                cmdline = proc.info['cmdline']
                if cmdline and script_name in ' '.join(cmdline):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def kill_script(script_name):
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] == 'python' or proc.info['name'] == 'python.exe':
                cmdline = proc.info['cmdline']
                if cmdline and script_name in ' '.join(cmdline):
                    proc.kill()
                    print(f"Killed {script_name}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def start_script(script_path):
    try:
        subprocess.Popen(['python', script_path], 
                        cwd=os.path.dirname(script_path))
        print(f"Started {script_path}")
    except Exception as e:
        print(f"Error starting script: {e}")

def main():
    script_path = r"/home/yubo/VillagerAgent-Minecraft-multiagent-framework/auto_gen_gpt_task.py"
    script_name = os.path.basename(script_path)

    while True:
        try:
            if not is_script_running(script_name):
                print(f"[Monitor]: [{script_name} is not running. Attempting to start...]")
                start_script(script_path)
            else:
                print(f"[Monitor]: [{script_name} is already running.]")
        except KeyboardInterrupt:
            print("[Monitor]: killed the running script.")
            kill_script(script_name)
            break
        # Wait for 30s before checking again
        time.sleep(30)

if __name__ == "__main__":
    main()
    # pkill -f "python|node.*bridge.js"