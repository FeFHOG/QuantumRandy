@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo   QuantumRandy - Upload to GitHub
echo ============================================
echo.

REM Check git
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] git not found. Install Git for Windows first.
    pause
    exit /b 1
)

REM Check if already a git repo
if exist ".git" (
    echo [INFO] Git repo already initialized.
) else (
    echo [INFO] Initializing git repo...
    git init
)

REM Verify .env is gitignored
findstr /c:".env" .gitignore >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] .env might not be in .gitignore!
)

REM Verify .env.example exists and has no real key
if not exist ".env.example" (
    echo [WARN] .env.example not found, consider creating it.
)

echo.
echo Files to be committed:
echo   quantumrandy/*.py   (core library)
echo   scripts/*.py        (entry points)
echo   tests/*.py          (tests)
echo   configs/*.yaml      (config files)
echo   pyproject.toml
echo   requirements.txt
echo   .gitignore
echo   .env.example
echo   readme.md
echo.
echo Excluded by .gitignore: .env .venv/ reports/ backups/ __pycache__/ arXiv-2505.11122v3/ PROJECT_LOG.md
echo.

REM Stage files
git add quantumrandy/*.py scripts/*.py tests/*.py configs/*.yaml pyproject.toml requirements.txt .gitignore .env.example readme.md

echo.
echo Staged files:
git diff --cached --name-only

echo.
set /p CONFIRM="Proceed with commit? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Aborted.
    pause
    exit /b 0
)

set /p COMMIT_MSG="Commit message (default: Initial commit - QuantumRandy alpha mining framework): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Initial commit - QuantumRandy alpha mining framework

git commit -m "%COMMIT_MSG%"

echo.
set /p REPO_URL="GitHub repo URL (e.g. https://github.com/yourname/quantumrandy.git, leave blank to skip push): "
if "%REPO_URL%"=="" (
    echo Skipping push. You can push later with:
    echo   git remote add origin YOUR_URL
    echo   git push -u origin main
    pause
    exit /b 0
)

REM Check if remote origin already exists
git remote get-url origin >nul 2>&1
if %errorlevel% equ 0 (
    git remote set-url origin %REPO_URL%
) else (
    git remote add origin %REPO_URL%
)

echo Pushing to %REPO_URL% ...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo   Upload successful!
    echo ============================================
) else (
    echo.
    echo [ERROR] Push failed. If main branch doesn't exist, try:
    echo   git branch -M main
    echo   git push -u origin main
)

pause
