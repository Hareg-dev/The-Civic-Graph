@echo off
REM Cleanup script for development artifacts

echo Cleaning up development artifacts...

REM Remove Python cache
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
del /s /q *.pyd 2>nul

REM Remove test databases
del /q *.db 2>nul
del /q *.sqlite3 2>nul

REM Remove pytest cache
if exist .pytest_cache rd /s /q .pytest_cache

REM Remove coverage reports
if exist htmlcov rd /s /q htmlcov
del /q .coverage 2>nul

REM Remove build artifacts
if exist build rd /s /q build
if exist dist rd /s /q dist
for /d %%d in (*.egg-info) do @if exist "%%d" rd /s /q "%%d"

echo Cleanup complete!
