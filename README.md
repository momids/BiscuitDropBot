# BiscuitDropBot 🍪

A Telegram bot that downloads files, videos, and YouTube links, then forwards them to a Bale group as zip archives split into 16MB chunks when needed.

## Pipeline

Telegram → Download → Zip → Split if needed → Bale

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


Python Telegram bot project scaffold.