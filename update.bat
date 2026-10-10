@echo off
title Cheat Clip PRO Updater

:: Fork kustom: update otomatis dinonaktifkan agar kustomisasi tidak tertimpa repo asli.
:: Skrip ini sengaja tidak menjalankan git, npm, atau pip.

echo ===================================================
echo   Update otomatis DINONAKTIFKAN (fork kustom)
echo ===================================================
echo.
echo Lakukan update secara manual via git:
echo   1. git fetch upstream
echo   2. git checkout custom
echo   3. git merge upstream/master   (selesaikan konflik bila ada)
echo   4. npm install
echo   5. venv\Scripts\python.exe -m pip install -r backend\requirements.txt
echo   6. git push origin custom
echo.
pause
exit /b 0
