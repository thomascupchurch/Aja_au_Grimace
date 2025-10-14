@echo off
REM Vols Signage App - Automated Updater
REM Usage: Place this script and the new release zip in your app folder, then double-click to update.

setlocal
REM Automatically find the latest release zip by date
for /f "delims=" %%F in ('dir /b /o-n release_*.zip') do set ZIP_NAME=%%F & goto :foundzip
:foundzip
set APP_EXE=Vols Signage.exe
set CONFIG_FILE=config.env
set BACKUP_CONFIG=config_backup.env
set BACKUP_DIR=backup_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%

REM Backup config.env if present
if exist %CONFIG_FILE% copy /Y %CONFIG_FILE% %BACKUP_CONFIG%

REM Backup old executable before update
if exist "%APP_EXE%" (
    if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
    copy /Y "%APP_EXE%" "%BACKUP_DIR%\%APP_EXE%"
    if exist VERSION copy /Y VERSION "%BACKUP_DIR%\VERSION"
)

REM Extract new release zip, overwrite files except config.env
REM Requires PowerShell (Windows 10+)
powershell -Command "Expand-Archive -Path '%ZIP_NAME%' -DestinationPath . -Force"

REM Restore config.env if overwritten
if exist %BACKUP_CONFIG% copy /Y %BACKUP_CONFIG% %CONFIG_FILE%
if exist %BACKUP_CONFIG% del %BACKUP_CONFIG%

REM Launch the app
start "" "%APP_EXE%"

endlocal
