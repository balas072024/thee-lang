@echo off
chcp 65001 >nul 2>&1
echo.
echo  THEE Uninstaller
echo  ================
echo.
echo  This will remove THEE from C:\thee-lang
echo  and remove it from your PATH.
echo.
set /p CONFIRM=Are you sure? (y/n): 
if /i not "%CONFIRM%"=="y" (
    echo Cancelled.
    pause
    exit /b 0
)

REM Remove from PATH
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%B"
if defined USER_PATH (
    set "NEW_PATH=!USER_PATH:;C:\thee-lang\bin=!"
    set "NEW_PATH=!NEW_PATH:C:\thee-lang\bin;=!"
    set "NEW_PATH=!NEW_PATH:C:\thee-lang\bin=!"
    setx PATH "!NEW_PATH!" >nul 2>&1
    echo [OK] Removed from PATH
)

REM Remove files
if exist "C:\thee-lang" (
    rmdir /S /Q "C:\thee-lang"
    echo [OK] Files removed
)

echo.
echo THEE has been uninstalled.
pause
