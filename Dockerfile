FROM python:3.10-slim

# Install Aria2, FFmpeg, Node, and tools
RUN apt-get update && apt-get install -y \
    curl jq fzf aria2 ffmpeg nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY . .

# Make script executable
RUN chmod +x animepahe-dl.sh

# 🚀 INJECT ARIA2 CONFIG FOR MAX SPEED 🚀
RUN mkdir -p /root/.config/yt-dlp && \
    echo '--external-downloader aria2c\n--external-downloader-args "-x 16 -k 1M"' > /root/.config/yt-dlp/config

# Start Bot
CMD ["python", "main.py"]
