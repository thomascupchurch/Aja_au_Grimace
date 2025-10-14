# Vols Signage App - Update Instructions

## How to Install and Run
1. Download and extract the release zip (e.g., `release_20251014_123853.zip`).
2. Open the extracted folder.
3. Edit `config.env` with your SQL Server details (ask your IT admin if unsure).
4. Double-click `Vols Signage.exe` to start the app.


## How to Update (Automated)
- When a new version is released:
  1. Place the new release zip (e.g., `release_20251014_123853.zip`) in your app folder and rename it to `release_latest.zip`.
  2. Double-click `update.bat`.
     - This will back up your config, extract the new files, restore your config, and launch the app.
  3. Your settings in `config.env` will be preserved.
- If only the configuration changes (e.g., new database info):
  1. Replace `config.env` with the new version.
  2. No need to update the executable unless instructed.

## Troubleshooting
- If the app won’t start, check that your `config.env` is correct and that you have access to the SQL Server.
- For further help, contact your IT admin or the app maintainer.

## Versioning
- Each release zip is named with a date and time (e.g., `release_20251014_123853.zip`).
- You can keep older versions for backup, but only run the latest for best results.

---
For questions or support, contact: [Your Name/IT Contact]
