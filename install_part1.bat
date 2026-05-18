@echo off
title NFS-e Automation - Parte 1/2
setlocal EnableDelayedExpansion

set "INSTALL_DIR=%~dp0"
if "%INSTALL_DIR:~-1%"=="\" set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

echo.
echo  ================================================================
echo   NFS-e Automation - Instalacao (Parte 1 de 2)
echo   Local: %INSTALL_DIR%
echo  ================================================================
echo.

:: Check if already fully installed
if exist "%INSTALL_DIR%\chrome-profile\Default" (
    echo  [OK] Ja instalado. Abrindo app...
    start "" wscript "%INSTALL_DIR%\launch.vbs"
    pause
    exit /b 0
)

:: Check Python
echo  Verificando Python...
python --version > nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Python ja instalado.
    goto :start_part2
)

:: Python not found - download and run installer visibly
echo  Python nao encontrado. Baixando instalador...
powershell -command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"

if not exist "%TEMP%\python_installer.exe" (
    echo.
    echo  ERRO: Falha no download. Verifique a conexao de internet e tente novamente.
    pause
    exit /b 1
)

echo  Download concluido.
echo.
echo  ================================================================
echo   INSTALANDO PYTHON
echo   Uma janela de instalacao vai abrir.
echo   IMPORTANTE: Marque "Add Python to PATH" antes de clicar Install.
echo   Aguarde a instalacao terminar e feche a janela.
echo  ================================================================
echo.

:: Run installer visibly and WAIT for it to finish
"%TEMP%\python_installer.exe" InstallAllUsers=0 PrependPath=1 Include_test=0
echo  [OK] Instalacao do Python concluida.

:start_part2
echo.
echo  Abrindo parte 2 em nova janela...
start "NFS-e Automation - Parte 2/2" cmd /k ""%INSTALL_DIR%\install_part2.bat" "%INSTALL_DIR%""
echo  [OK] Parte 2 iniciada. Pode fechar esta janela.
pause
exit /b 0