@echo off
title Build Sword to EXE
echo ====================================================
echo             BUILDING SWORD TO EXE
echo ====================================================
echo.
echo   Targets:
echo     main.exe          ^(CLI bot^)
echo     shopper.exe       ^(Shopper bot^)
echo     launcher_gui.exe  ^(GUI configuration launcher^)
echo.
echo   Use --no-gui flag to skip launcher_gui.exe build:
echo     build.bat --no-gui
echo.

SET CONDA_PATH="%USERPROFILE%\miniconda3\condabin\conda.bat"
IF NOT EXIST %CONDA_PATH% (
    SET CONDA_PATH="conda"
)

echo Calling build.py inside the sword environment...
%CONDA_PATH% run -n sword python ./build.py %*

echo.
echo ====================================================
echo Build process finished! Check the dist/sword_v* folder.
echo ====================================================
pause
