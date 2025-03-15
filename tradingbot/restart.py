import time
import subprocess

script_path = "trade.py"
max_restarts = 50  # **最多重启 5 次**
restart_count = 0

while restart_count < max_restarts:
    print(f"🚀 正在启动交易脚本: {script_path}")
    
    process = subprocess.run(["python", script_path])

    restart_count += 1
    print(f"⚠️ 交易脚本被终止，第 {restart_count} 次重启...")
    
    if restart_count >= max_restarts:
        print("❌ 交易脚本多次失败，停止自动重启！")
        break
    
    time.sleep(1)

