@echo off
title Build Sword to EXE
echo ====================================================
echo             BUILDING SWORD TO EXE
echo ====================================================
echo.

SET CONDA_PATH="%USERPROFILE%\miniconda3\condabin\conda.bat"
IF NOT EXIST %CONDA_PATH% (
    SET CONDA_PATH="conda"
)

echo Calling build.py inside the sword environment...
%CONDA_PATH% run -n sword python ./build.py

echo.
echo ====================================================
echo Build process finished! Check the sword_v* folder.
echo ====================================================
pause
