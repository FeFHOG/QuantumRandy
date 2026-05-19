@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   QuantumRandy - Push to GitHub
echo ============================================
echo.

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] git not found
    pause
    exit /b 1
)

if not exist ".git" git init

REM Auto-detect changed files
for /f "delims=" %%d in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set NOW=%%d

echo [%NOW%] Staging files...
git add quantumrandy\*.py scripts\*.py tests\*.py configs\*.yaml pyproject.toml requirements.txt .gitignore .env.example readme.md PROJECT_LOG.md upload_to_github.bat

echo.
echo Staged:
git diff --cached --name-only

REM Check if anything to commit
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo.
    echo Nothing to commit.
) else (
    set MSG=Update %NOW%
    git commit -m "!MSG!"
    echo Committed: !MSG!
)

REM Push
git remote get-url origin >nul 2>&1 || git remote add origin https://github.com/FeFHOG/QuantumRandy
echo.
echo Pushing to origin/main...
git push -u origin main 2>&1

if %errorlevel% equ 0 (
    echo Done: https://github.com/FeFHOG/QuantumRandy
) else (
    echo [ERROR] Push failed - check network or run: git push -u origin main
)
pause
