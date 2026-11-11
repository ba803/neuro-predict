@echo off
title Push NeuroPredict to GitHub (ba803)
echo ===================================================================
echo   Pushing NeuroPredict to https://github.com/ba803/neuro-predict
echo ===================================================================
echo.
cd /d "%~dp0"
echo Running: git push -u origin main
echo (If prompted, please sign in with your GitHub account: ba803)
echo.
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo ===================================================================
    echo   SUCCESS! The project is now live on GitHub!
    echo   View repository at: https://github.com/ba803/neuro-predict
    echo ===================================================================
) else (
    echo ===================================================================
    echo   Push encountered an error.
    echo   If permission is denied, ensure you are signed in as 'ba803'.
    echo ===================================================================
)
echo.
pause

