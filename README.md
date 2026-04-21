# BiscuitDropBot 🍪

A Telegram bot that downloads files, videos, and YouTube links, then lets the user choose how to package them before forwarding to a Bale group in 16MB chunks when needed.

## Pipeline

Telegram → Download → Choose archive mode → Archive → Split if needed → Bale

## Setup (Ubuntu Server)

### 1. System dependencies

```bash
sudo apt update
sudo apt install -y ffmpeg nodejs python3 python3-pip python3-venv
```

### 2. Clone & install

```bash
git clone <your-repo-url> /opt/biscuitdropbot
cd /opt/biscuitdropbot
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
nano .env   # fill in TELEGRAM_TOKEN, BALE_TOKEN, BALE_CHAT_ID
```

### 4. Upload cookies.txt (for YouTube auth)

Export cookies from your browser using the "Get cookies.txt LOCALLY" extension, then:

```bash
scp cookies.txt user@your-server:/opt/biscuitdropbot/cookies.txt
```

### 5. Run as a service

```bash
sudo cp biscuitdropbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable biscuitdropbot
sudo systemctl start biscuitdropbot
sudo systemctl status biscuitdropbot
```

### Logs

```bash
journalctl -u biscuitdropbot -f
```

## Local development

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your tokens
python -m bot.main
```

## Archive Choice

After the download completes, Biscuit shows two inline buttons:

- `🖥️ PC-safe ZIP`: best for the current desktop flow. Multipart deliveries arrive as `.zip.part001`, `.zip.part002`, and so on.
- `📱 Mobile 7Z`: best for mobile archive apps that can often open `.7z.0001` directly.

The `.env` setting `ARCHIVE_MODE` only controls which option is shown first as the recommended choice. Users can still pick either mode for each file.

## Reassembly

Large files arrive as multiple parts of a zip archive. Download every part, join them back into a single `.zip`, then extract that zip to recover the original file.

Windows:

```cmd
copy /b "video.mp4.zip.part*" "video.mp4.zip"
```

Linux/macOS:

```bash
cat video.mp4.zip.part* > video.mp4.zip
```

## Archive Modes

The default recommended mode is `ARCHIVE_MODE=zip`. This keeps the existing PC-safe flow that already works:

- Single part: send one `.zip`
- Multi part: send `.zip.part001`, `.zip.part002`, and so on
- Reassembly: manually join the parts, then extract the `.zip`

You can optionally make the mobile-first option the recommended default with `ARCHIVE_MODE=7z`.

- Single or multi part output is created as a 7z archive
- Multi part files are named like `.7z.0001`, `.7z.0002`, and so on
- Many archive apps can open `.7z.0001` directly without a manual join step
- Recommended mobile apps: ZArchiver or RAR on Android, and any iOS archive app that explicitly supports multi-volume 7z archives

Add this to your `.env` to show `📱 Mobile 7Z` as the recommended option first:

```env
ARCHIVE_MODE=7z
```


Python Telegram bot project scaffold.