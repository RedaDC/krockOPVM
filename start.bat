@echo off
echo ====================================================================
echo   OPCVM Analytics Maroc - Quick Start
echo ====================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found!
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Check if requirements are installed
echo Checking installation...
python launch_local.py --check
if errorlevel 1 (
    echo.
    echo ====================================================================
    echo   Dependencies not installed
    echo ====================================================================
    echo.
    echo This will download and install:
    echo   - TensorFlow (~500 MB)
    echo   - PyTorch (~800 MB)
    echo   - Transformers (~500 MB)
    echo   - And other dependencies
    echo.
    echo Total size: ~2-3 GB
    echo Installation time: 10-30 minutes (depends on internet speed)
    echo.
    set /p confirm="Do you want to install now? (y/n): "
    if /i "%confirm%"=="y" (
        echo.
        echo Installing dependencies...
        python launch_local.py --install
        if errorlevel 1 (
            echo.
            echo Installation failed! Check error messages above.
            pause
            exit /b 1
        )
        echo.
        echo Installation complete!
    ) else (
        echo.
        echo Installation cancelled. Run this script again when ready.
        pause
        exit /b 0
    )
)

echo.
echo ====================================================================
echo   Launch Menu
echo ====================================================================
echo.

:menu
echo Select an option:
echo   1. Run complete pipeline (all steps)
echo   2. Start Streamlit dashboard
echo   3. Start Telegram bot
echo   4. Run historical data collector
echo   5. Run sentiment analysis
echo   6. Run LSTM model training
echo   7. Run backtesting
echo   8. Check installation
echo   0. Exit
echo.

set /p choice="Enter choice [0-8]: "

if "%choice%"=="1" python launch_local.py --pipeline
if "%choice%"=="2" python launch_local.py --streamlit
if "%choice%"=="3" python launch_local.py --telegram
if "%choice%"=="4" python src\historical_collector.py
if "%choice%"=="5" python src\news_sentiment_pipeline.py
if "%choice%"=="6" python src\lstm_model.py
if "%choice%"=="7" python src\backtester.py
if "%choice%"=="8" python launch_local.py --check
if "%choice%"=="0" goto end

echo.
pause
cls
goto menu

:end
echo.
echo Thank you for using OPCVM Analytics Maroc!
pause
