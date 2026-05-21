@echo off
echo Encerrando processos...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im chrome.exe >nul 2>&1
timeout /t 2 >nul
echo Reiniciando...
wscript C:\nfse-automation\launch.vbs