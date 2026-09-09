@echo off

REM Prompt user for the file path to be used in both main.py and bridge.py
set /p file="Enter the path of the Excel file: "

REM Run main.py with the user-provided file path and wait for it to finish
call python main.py "%file%"

REM Run bridge.py using the same file path for both inputs and wait for it to finish
call python bridge.py "%file%"

REM Run taptify.py (no input required) and wait for it to finish
call python taptify.py


REM Pause to keep the command prompt window open after execution
pause
