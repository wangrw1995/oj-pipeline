@echo off
setlocal
where python >nul 2>nul
if errorlevel 1 (
  echo 找不到 python，请先装 Python 3.10+
  exit /b 2
)
python "%~dp0oj.py" %*
exit /b %errorlevel%
