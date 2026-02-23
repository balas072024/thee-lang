@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo  ================================================================
echo    THEE v6.0 INSTALLER — Tamil-English Programming Language
echo    443+ builtins, Classes, Agents, Events, Tamil keywords
echo  ================================================================
echo.

SET INSTALL_DIR=C:\thee-lang

REM ═══ STEP 1: Check Python ═══
echo [1/4] Checking Python 3...
py -3 --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%v in ('py -3 --version 2^>^&1') do echo   [OK] %%v
    goto :py_found
)
python --version 2>&1 | findstr "Python 3" >nul
if %errorlevel%==0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   [OK] %%v
    goto :py_found
)
echo.
echo   [FAIL] Python 3 not found!
echo.
echo   THEE needs Python 3.8 or later.
echo   Download from: https://www.python.org/downloads/
echo.
echo   IMPORTANT: During Python install, check the box:
echo   [x] "Add Python to PATH"
echo.
pause
exit /b 1

:py_found

REM ═══ STEP 2: Copy files ═══
echo.
echo [2/4] Installing THEE to %INSTALL_DIR%...

if exist "%INSTALL_DIR%" (
    echo   Updating existing installation...
) else (
    mkdir "%INSTALL_DIR%" 2>nul
)

SET SRC=%~dp0

REM Copy source
if not exist "%INSTALL_DIR%\src\thee_lang" mkdir "%INSTALL_DIR%\src\thee_lang" 2>nul
copy /Y "%SRC%src\thee_lang\interpreter.py" "%INSTALL_DIR%\src\thee_lang\" >nul 2>&1
copy /Y "%SRC%src\thee_lang\parser.py" "%INSTALL_DIR%\src\thee_lang\" >nul 2>&1
copy /Y "%SRC%src\thee_lang\lexer.py" "%INSTALL_DIR%\src\thee_lang\" >nul 2>&1
echo. 2>"%INSTALL_DIR%\src\thee_lang\__init__.py"
echo. 2>"%INSTALL_DIR%\src\__init__.py"

REM Copy bin
if not exist "%INSTALL_DIR%\bin" mkdir "%INSTALL_DIR%\bin" 2>nul
copy /Y "%SRC%bin\thee.bat" "%INSTALL_DIR%\bin\" >nul 2>&1
copy /Y "%SRC%bin\thee_cli.py" "%INSTALL_DIR%\bin\" >nul 2>&1

REM Copy examples
if not exist "%INSTALL_DIR%\examples" mkdir "%INSTALL_DIR%\examples" 2>nul
copy /Y "%SRC%examples\*.thee" "%INSTALL_DIR%\examples\" >nul 2>&1

echo   [OK] Files installed

REM ═══ STEP 3: Add to PATH ═══
echo.
echo [3/4] Adding THEE to system PATH...

REM Check if already in PATH
echo %PATH% | findstr /C:"%INSTALL_DIR%\bin" >nul
if %errorlevel%==0 (
    echo   [OK] Already in PATH
    goto :path_done
)

REM Add to user PATH (no admin needed)
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%B"

if defined USER_PATH (
    setx PATH "%USER_PATH%;%INSTALL_DIR%\bin" >nul 2>&1
) else (
    setx PATH "%INSTALL_DIR%\bin" >nul 2>&1
)

if %errorlevel%==0 (
    echo   [OK] Added to user PATH
    echo   NOTE: Open a NEW terminal for 'thee' command to work
) else (
    echo   [WARN] Could not add to PATH automatically
    echo   Manual step: Add this to your PATH:
    echo     %INSTALL_DIR%\bin
)
:path_done

REM Also set PATH for current session
set "PATH=%PATH%;%INSTALL_DIR%\bin"

REM ═══ STEP 4: Verify ═══
echo.
echo [4/4] Verifying installation...

if exist "%INSTALL_DIR%\src\thee_lang\interpreter.py" (
    echo   [OK] interpreter.py
) else (
    echo   [FAIL] interpreter.py missing
)
if exist "%INSTALL_DIR%\src\thee_lang\parser.py" (
    echo   [OK] parser.py
) else (
    echo   [FAIL] parser.py missing
)
if exist "%INSTALL_DIR%\src\thee_lang\lexer.py" (
    echo   [OK] lexer.py
) else (
    echo   [FAIL] lexer.py missing
)
if exist "%INSTALL_DIR%\bin\thee.bat" (
    echo   [OK] thee.bat
) else (
    echo   [FAIL] thee.bat missing
)

REM Run quick test
echo.
echo   Running test...
"%INSTALL_DIR%\bin\thee.bat" -e "moochhu \"THEE v6.0 installed successfully!\""
if %errorlevel%==0 (
    echo   [OK] THEE execution works!
) else (
    echo   [FAIL] Execution test failed
)

echo.
echo  ================================================================
echo    INSTALLATION COMPLETE!
echo  ================================================================
echo.
echo  Install location: %INSTALL_DIR%
echo.
echo  Usage (open a NEW terminal):
echo.
echo    thee                          Start REPL (interactive mode)
echo    thee hello.thee               Run a .thee file
echo    thee -e "moochhu 42"          Run inline code
echo    thee -v                       Show version
echo.
echo  Quick start:
echo.
echo    thee -e "na name = \"Bala\"; moochhu \"Hello \" + name"
echo    thee -e "ozhugu for i ul range(1,6) { moochhu i * i }"
echo    thee %INSTALL_DIR%\examples\hello.thee
echo.
echo  Examples folder: %INSTALL_DIR%\examples
echo.
pause
endlocal
