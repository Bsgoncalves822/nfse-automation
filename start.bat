@echo off
title NFS-e Automation
start "" /B python C:\nfse-automation\app.py

:wait
ping -n 2 127.0.0.1 > nul
powershell -command "try { Invoke-WebRequest -Uri 'http://localhost:5000/health' -UseBasicParsing -TimeoutSec 1 > $null; exit 0 } catch { exit 1 }" > nul 2>&1
if %errorlevel% neq 0 goto :wait

start "" http://localhost:5000