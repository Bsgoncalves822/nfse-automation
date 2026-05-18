@echo off
title NFS-e Automation - Parte 2/2
setlocal EnableDelayedExpansion

set "INSTALL_DIR=%~1"
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=%~dp0"
if "%INSTALL_DIR:~-1%"=="\" set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

echo.
echo  ================================================================
echo   NFS-e Automation - Instalacao (Parte 2 de 2)
echo   Local: %INSTALL_DIR%
echo  ================================================================
echo.

:: Find Python
set "PYTHON_EXE="
for /f "delims=" %%i in ('where python.exe 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
)
if not defined PYTHON_EXE (
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
)
if not defined PYTHON_EXE (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYTHON_EXE (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)
if not defined PYTHON_EXE (
    for /f "delims=" %%i in ('dir /b /s "%LOCALAPPDATA%\Programs\Python\python.exe" 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    echo  ERRO: Python nao encontrado.
    echo  Por favor instale manualmente em https://www.python.org
    echo  Marque "Add Python to PATH" e execute install_part2.bat novamente.
    pause
    exit /b 1
)

echo  [OK] Python encontrado: !PYTHON_EXE!
echo.

echo  Instalando dependencias...
"!PYTHON_EXE!" -m pip install playwright openpyxl python-dateutil schedule flask --quiet --disable-pip-version-check
echo  [OK] Dependencias instaladas

echo  Instalando Chromium (pode demorar alguns minutos)...
"!PYTHON_EXE!" -m playwright install chromium
echo  [OK] Chromium instalado

echo  Configurando extensao...
if not exist "%INSTALL_DIR%\extension" (
    mkdir "%INSTALL_DIR%\extension" > nul 2>&1
    powershell -command "Expand-Archive -Path '%INSTALL_DIR%\extension.zip' -DestinationPath '%INSTALL_DIR%\extension' -Force"
)
echo  [OK] Extensao configurada

echo  Configurando caminhos...
"!PYTHON_EXE!" "%INSTALL_DIR%\setup_config.py" "%INSTALL_DIR%"
echo  [OK] Configuracoes atualizadas

echo  Criando atalho na area de trabalho...
"!PYTHON_EXE!" "%INSTALL_DIR%\setup_shortcut.py" "%INSTALL_DIR%"
echo  [OK] Atalho criado

echo.
echo  Ativando licenca da extensao...
"!PYTHON_EXE!" "%INSTALL_DIR%\activate_license.py"

echo.
echo  ================================================================
echo   Instalacao concluida!
echo   Use o atalho NFS-e Automation na area de trabalho.
echo  ================================================================
echo.
start "" wscript "%INSTALL_DIR%\launch.vbs"
pause