@echo off
chcp 65001 >nul
cd /d "%~dp0"
python "启动展示.py"
if errorlevel 1 pause
