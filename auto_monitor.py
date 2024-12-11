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

def start_script(script_path):
    try:
        subprocess.Popen(['python', script_path], 
                        cwd=os.path.dirname(script_path))
        print(f"Started {script_path}")
    except Exception as e:
        print(f"Error starting script: {e}")

def main():
    script_path = r"D:/我的文件/研究论文相关/VillagerAgent/VillagerAgent-Minecraft-multiagent-framework/auto_gen_gpt_task.py"
    script_name = os.path.basename(script_path)

    while True:
        if not is_script_running(script_name):
            print(f"[Monitor]: [{script_name} is not running. Attempting to start...]")
            start_script(script_path)
        else:
            print(f"[Monitor]: [{script_name} is already running.]")
        
        # Wait for 30s before checking again
        time.sleep(30)

if __name__ == "__main__":
    main()
