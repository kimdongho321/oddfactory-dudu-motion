@echo off
cd /d "%~dp0web"
python -m http.server 8852 --bind 127.0.0.1
