@echo off
chcp 65001 > nul
title 윤슬 맞춤법 & 띄어쓰기 검사기 실행기
cd /d "%~dp0"

echo ========================================================
echo   윤슬 맞춤법 ^& 띄어쓰기 검사기 (Windows Universal)
echo ========================================================
echo.
echo 프로그램을 실행합니다...
echo (웹 브라우저, 메모장 어디서든 텍스트를 드래그하거나 우클릭해 보세요!)
echo.

python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 실행 중 오류가 발생했습니다.
    pause
)
