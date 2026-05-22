"""
Railway 啟動入口：同時跑 wycbotai_main.py 和 main.py
任一腳本 crash 後會自動重啟（10 秒後）
"""
import subprocess
import sys
import time
import threading


def run_forever(script: str):
    while True:
        print(f"[Launcher] 啟動 {script}...", flush=True)
        try:
            p = subprocess.Popen(
                [sys.executable, "-u", script],
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            p.wait()
            print(f"[Launcher] {script} 結束（exit code {p.returncode}），10 秒後重啟...", flush=True)
        except Exception as e:
            print(f"[Launcher] {script} 啟動失敗：{e}，10 秒後重試...", flush=True)
        time.sleep(10)


if __name__ == "__main__":
    scripts = ["wycbotai_main.py", "main.py"]
    threads = [
        threading.Thread(target=run_forever, args=(s,), daemon=True)
        for s in scripts
    ]
    for t in threads:
        t.start()
    print(f"[Launcher] 已啟動 {len(scripts)} 個服務：{scripts}", flush=True)
    for t in threads:
        t.join()
