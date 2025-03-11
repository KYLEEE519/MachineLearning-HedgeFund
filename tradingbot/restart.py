import time
import subprocess

script_path = "trade.py"  # 你的交易脚本路径

while True:
    print(f"🚀 正在启动交易脚本: {script_path}")
    
    # 启动交易脚本，并保持终端输出
    process = subprocess.Popen(["python", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 实时打印交易脚本的输出
    for line in iter(process.stdout.readline, ''):
        print(line, end='')  # **输出交易脚本日志**

    process.wait()  # **等待交易脚本运行结束**

    print("⚠️ 交易脚本被中断，1 秒后重新启动...")
    time.sleep(1)  # **防止无限快速重启**
