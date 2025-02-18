@echo off

:: Check if a commit message was provided as an argument
if "%~1"=="" (
    echo No commit message provided. Using default message: "Auto-commit"
    set "commitMessage=Auto-commit"
) else (
    set "commitMessage=%~1"
)

:: Navigate to the desired directory
cd C:\Users\goblo\Downloads\imnotliieing web

:: Perform Git operations
git pull origin main
git add .
git commit -m "%commitMessage%"
git push origin main

:: Optional: Notify the user that the process is complete
echo Sync completed successfully!