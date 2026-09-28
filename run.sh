#!/bin/sh
# Jalankan PayrollPro dari source (Linux/macOS). Butuh python3 + tkinter.
cd "$(dirname "$0")"
exec python3 payroll_gui.py
