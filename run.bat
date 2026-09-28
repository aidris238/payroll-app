@echo off
REM Jalankan PayrollPro dari source (Windows). Butuh Python 3.10+ terinstall.
cd /d "%~dp0"
python payroll_gui.py
if errorlevel 1 (
  echo.
  echo Gagal jalan. Pastikan Python terinstall: https://www.python.org/downloads/
  pause
)
