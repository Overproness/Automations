@echo off
set /p choice="Which do you want to use? (shyft/dexscreener): "
if /i "%choice%"=="shyft" (
    python token_monitoring.py
) else if /i "%choice%"=="dexscreener" (
    python project.py
) else (
    echo Invalid choice.
    pause
)
