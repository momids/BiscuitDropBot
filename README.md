# BiscuitDropBot 🍪

A Telegram bot that downloads files, videos, and YouTube links, then forwards them to a Bale group in 16MB chunks.

## Pipeline

Telegram → Download → Zip/Split → Bale

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


Python Telegram bot project scaffold.