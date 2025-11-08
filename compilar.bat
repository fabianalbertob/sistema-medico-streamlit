@echo off echo ======================================== echo Compilando Registro Clinico echo ========================================

REM Limpiar compilaciones anteriores if exist build rmdir /s /q build if exist dist rmdir /s /q dist

REM Compilar pyinstaller --onefile ^ --windowed ^ --name="RegistroClinico" ^ --hidden-import=pandas ^ --hidden-import=openpyxl ^ --hidden-import=reportlab ^ --hidden-import=xlsxwriter ^ app.py

echo. echo ======================================== echo Compilacion completada! echo El ejecutable esta en: dist\RegistroClinico.exe echo ======================================== pause