# Verify Changed Files

Runs daily at 1am (via cron), hashes your important files, compares with stored hashes in **VerifyFile**, and sends a Telegram message listing any new or changed files.
                              !!! make sure all the paths are correct before running the script !!!

## How it works

1. **Hash**: SHA256 of each configured important file is computed.
2. **Compare**: Each hash is compared to the one stored in **VerifyFile** for that path.
3. **New file**: If there is no entry in VerifyFile for that path, a new label/entry is created and the hash is stored (first run or newly added file).
4. **Changed**: If the stored hash differs from the new hash, the file is reported as changed.
5. **Notify**: A Telegram message is sent with all new/changed (and optionally missing) files. VerifyFile is updated with the latest hashes.

## Setup

### 1. Config

Copy the example config and edit:

```bash
cp config.example.json config.json
```

Edit `config.json`:

- **important_files**: List of `{"path": "/absolute/path/to/file", "label": "Short name"}`. Use absolute paths.
- **telegram_bot_token**: From [@BotFather](https://t.me/BotFather) (Create bot → copy token).
- **telegram_chat_id**: Your user or group ID (e.g. from [@userinfobot](https://t.me/userinfobot), or create a group and add your bot, then use the group ID).

### 2. VerifyFile

**VerifyFile** is created automatically on first run. It stores one line per file: `path|hash`. Do not use `|` in file paths (fix this bug next time).

### 3. Run at 1am (cron)

Make the script and runner executable:

```bash
chmod +x verify_files.py schedule_1am.sh
```

Add a cron job (run at 1:00 every day):

```bash
crontab -e
```

Add this line (replace with your real path):

```
0 1 * * * /home/path/to/veriChangedFiles/schedule_1am.sh
```

Cron runs only when the system is on. If the laptop is suspended at 1am, the job runs when it next wakes (or use wake-from-suspend below).

### 4. Alternative: systemd timer (instead of cron)

If you prefer systemd, install a user service and timer:

```bash
mkdir -p ~/.config/systemd/user
# Copy and replace /home/path/to/veriChangedFiles with your actual path in the .service file
cp verify-files.service.example ~/.config/systemd/user/verify-files.service
cp verify-files.timer.example ~/.config/systemd/user/verify-files.timer
# Edit verify-files.service and set your paths in ExecStart and WorkingDirectory
systemctl --user daemon-reload
systemctl --user enable --now verify-files.timer
```

The timer runs the service daily at 1am.

### 5. Optional: wake laptop at 1am

To wake the machine from suspend so the job runs at 1am:

- **rtcwake**: Schedule wake and run the job after wake:

  ```bash
  # Example: suspend now, wake at 01:00 and run verify
  sudo rtcwake -m mem -t $(date -d "01:00" +%s) -s 0
  ```

  Or use a separate cron entry that runs when the system is already up (e.g. after you wake it manually), or combine with a systemd timer that runs at 1am and, if you use suspend, set BIOS/OS “wake at RTC” to 01:00 so the machine wakes and cron can run.

- **BIOS**: Some laptops have “Wake on RTC” or “Scheduled power on” — set to 01:00 so the laptop is on when cron runs.

## Usage

- **Manual run** (e.g. test):

  ```bash
  python3 verify_files.py
  ```

- **Dry run** (no VerifyFile update, no Telegram):

  ```bash
  python3 verify_files.py --dry-run
  ```

- **Custom paths**:

  ```bash
  python3 verify_files.py --config /path/to/config.json --verify-file /path/to/VerifyFile
  ```

## Requirements

- Linux
- Python 3.9+ (uses `str | None` type hint; for older Python use `Optional[str]`)
- Network access for Telegram API

No extra Python packages: uses only the standard library (`hashlib`, `json`, `urllib`).
