@echo off
py -3 "%~dp0thee_cli.py" %*
if errorlevel 9009 (
    python "%~dp0thee_cli.py" %*
    if errorlevel 9009 (
        python3 "%~dp0thee_cli.py" %*
        if errorlevel 9009 (
            echo ERROR: Python 3 not found. Install from https://python.org
            exit /b 1
        )
    )
)
