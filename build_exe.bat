@echo off
chcp 65001 > nul
title 윤슬 맞춤법 검사기 - EXE 및 설치 파일 빌더
cd /d "%~dp0"

echo ========================================================
echo   윤슬 맞춤법 검사기 (YUNSEUL-SPELLCHECK) 빌드 시작
echo   - YUNSEUL-SPELLCHECK-Setup.exe (설치 마법사)
echo   - YUNSEUL-SPELLCHECK.exe (포터블 단일 실행 파일)
echo ========================================================
echo.

python tools/build_setup.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [오류] 빌드 도중 문제가 발생했습니다.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo   모든 빌드가 성공적으로 완료되었습니다!
echo   생성된 파일:
echo   1. YUNSEUL-SPELLCHECK-Setup.exe (설치용 마법사)
echo   2. YUNSEUL-SPELLCHECK.exe       (무설치 포터블)
echo ========================================================
pause
