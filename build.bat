@echo off
setlocal
echo ============================================
echo  IP Video Stream Publisher - Build Script
echo ============================================
echo.

:: Check for ffmpeg.exe in the current directory
if not exist ffmpeg.exe (
    echo ERROR: ffmpeg.exe not found in this directory.
    echo.
    echo Please download the ffmpeg Windows build from:
    echo   https://ffmpeg.org/download.html
    echo.
    echo Extract ffmpeg.exe and place it alongside this build.bat, then re-run.
    pause
    exit /b 1
)

echo [1/2] Installing / upgrading PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Building executable...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "IPVideoPublisher" ^
    --add-binary "ffmpeg.exe;." ^
    ip_video_test_publisher.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed. See output above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build complete!
echo  Executable: dist\IPVideoPublisher.exe
echo ============================================
pause
