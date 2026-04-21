FROM python:3.12-slim

# Install system dependencies: ffmpeg + Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY bot/ bot/
COPY Cookie_Chat_Bubble_In_a_charming_animation_style_a_cheerful_round_24177oRz-ezgif.com-optimize.gif ./

# Downloads folder (created at runtime by the bot, but ensure it exists)
RUN mkdir -p downloads

CMD ["python", "-m", "bot.main"]
