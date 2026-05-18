import schedule
import time
import subprocess
from datetime import datetime

def run_automation():
    print(f"[{datetime.now()}] Iniciando execucao automatica...")
    subprocess.run(["python", r"C:\nfse-automation\main.py"])
    print(f"[{datetime.now()}] Execucao concluida")

# run on the 1st of every month at 06:00
schedule.every().day.at("06:00").do(lambda: run_automation() if datetime.now().day == 1 else None)

print("Scheduler ativo — aguardando dia 1 as 06:00...")
while True:
    schedule.run_pending()
    time.sleep(60)
