@echo off
setlocal enabledelayedexpansion
title Convert Visualizer WebM to MP4
echo ==============================================================================
echo   Repository Evolution Visualizer - WebM to MP4 High-Quality Converter
echo ==============================================================================
echo.

set "LATEST_FILE="

if not "%~1"=="" (
    set "LATEST_FILE=%~1"
    goto :found
)

echo [*] Searching for downloaded visualizer webm files in Downloads directory...

rem 1. Check User Downloads for evolution recordings
for /f "delims=" %%i in ('dir /b /o-d "%USERPROFILE%\Downloads\*evolution*.webm" 2^>nul') do (
    if not defined LATEST_FILE set "LATEST_FILE=%USERPROFILE%\Downloads\%%i"
)

rem 2. Check general web visualizer downloads
if not defined LATEST_FILE (
    for /f "delims=" %%i in ('dir /b /o-d "%USERPROFILE%\Downloads\*visualizer*.webm" 2^>nul') do (
        if not defined LATEST_FILE set "LATEST_FILE=%USERPROFILE%\Downloads\%%i"
    )
)

rem 3. Check current folder
if not defined LATEST_FILE (
    for /f "delims=" %%i in ('dir /b /o-d "%~dp0*.webm" 2^>nul') do (
        if not defined LATEST_FILE set "LATEST_FILE=%~dp0%%i"
    )
)

if not defined LATEST_FILE (
    echo [-] No visualizer webm file found in Downloads or current folder.
    echo [*] Please drag and drop your downloaded .webm file onto this .bat script!
    echo.
    pause
    exit /b 1
)

:found
echo [+] Found input video: "!LATEST_FILE!"
set "OUT_FILE=!LATEST_FILE:~0,-5!.mp4"
echo [+] Output video path: "!OUT_FILE!"
echo.
echo [*] Converting WebM to ultra-sharp H.264 MP4 (CRF 14, 60fps)...
ffmpeg -y -i "!LATEST_FILE!" -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart "!OUT_FILE!"

if !ERRORLEVEL! EQU 0 (
    echo.
    echo ==============================================================================
    echo [OK] Successfully converted to MP4: "!OUT_FILE!"
    echo ==============================================================================
) else (
    echo.
    echo [-] Conversion failed with error code !ERRORLEVEL!.
)
echo.
pause
