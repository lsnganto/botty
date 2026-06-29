@ECHO OFF
CLS
SET CONDA_PATH="%USERPROFILE%\miniconda3\condabin\conda.bat"
IF NOT EXIST %CONDA_PATH% (
    SET CONDA_PATH="conda"
)

:MENU
ECHO.
ECHO ...............................................
ECHO PRESS 1, 2, 3, 4 or 5 to select your task
ECHO ...............................................
ECHO.
ECHO 1 - Install Env
ECHO 2 - Update Env
ECHO 3 - Compile
ECHO 4 - Run Sword
ECHO 5 - Exit
ECHO.
SET /P M=Type 1, 2, 3, 4 or 5 then press ENTER:
IF "%M%"=="1" GOTO INSTALL
IF "%M%"=="2" GOTO UPDATE
IF "%M%"=="3" GOTO COMPILE
IF "%M%"=="4" GOTO RUN
IF "%M%"=="5" GOTO EXIT
GOTO MENU

:INSTALL
start cmd /k %CONDA_PATH% env create -f environment.yml
GOTO MENU

:UPDATE
start cmd /k %CONDA_PATH% env update -f environment.yml
GOTO MENU

:COMPILE
%CONDA_PATH% run -n sword python -m PyInstaller --help > nul 2>&1
%CONDA_PATH% run -n sword python ./build.py
GOTO MENU

:RUN
%CONDA_PATH% run -n sword python src/main.py
GOTO MENU

:EXIT
EXIT
