@echo off
title Blind Assistance System — Multilingual Startup
color 0A
echo.
echo ================================================================
echo   BLIND ASSISTANCE SYSTEM — MULTILINGUAL
echo   Supported Languages: English / Telugu / Hindi
echo   TTS Engine         : Google TTS (gTTS) + pygame
echo   Detection Model    : YOLO11n (2024)
echo ================================================================
echo.
echo   To change language, open Blind_assistant_MULTILANG.py
echo   and change the line:
echo       LANGUAGE = "en"   ^<-- English
echo       LANGUAGE = "te"   ^<-- Telugu
echo       LANGUAGE = "hi"   ^<-- Hindi
echo.
echo ================================================================
echo.

REM ── Check Python 3.11 ──────────────────────────────────────────
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 not found.
    echo.
    echo Please download and install Python 3.11.9 from:
    echo https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo.
    echo During installation tick both:
    echo   - Add python.exe to PATH
    echo   - Install for all users
    echo.
    pause
    exit /b 1
)
echo [OK] Python 3.11 found.
echo.

REM ── Install required libraries ──────────────────────────────────
echo [SETUP] Installing / updating libraries...
echo         (ultralytics, opencv-python, pywin32, gtts, pygame)
echo         This may take a few minutes on first run.
echo.

py -3.11 -m pip install --quiet --upgrade ultralytics opencv-python pywin32 gtts pygame

if errorlevel 1 (
    echo.
    echo [ERROR] Library installation failed.
    echo         Check your internet connection and try again.
    pause
    exit /b 1
)
echo [OK] All libraries ready.
echo.

REM ── Move to script folder ───────────────────────────────────────
cd /d "%~dp0"

REM ── Check main script exists ────────────────────────────────────
if not exist "Blind_assistant_MULTILANG.py" (
    echo [ERROR] Blind_assistant_MULTILANG.py not found in:
    echo         %~dp0
    echo.
    echo Make sure this .bat file and the .py file are in the same folder.
    pause
    exit /b 1
)

REM ── Internet check warning ──────────────────────────────────────
echo [NOTE] gTTS requires an internet connection.
echo        If offline, the system will fall back to Windows SAPI
echo        which speaks English only.
echo.

REM ── Launch ──────────────────────────────────────────────────────
echo ================================================================
echo   Starting system... Press Q in the camera window to quit.
echo ================================================================
echo.

py -3.11 Blind_assistant_MULTILANG.py

REM ── After exit ──────────────────────────────────────────────────
echo.
echo ================================================================
echo   System stopped.
echo ================================================================
pause