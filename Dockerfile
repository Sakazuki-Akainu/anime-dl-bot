FROM python:3.10-slim

# 1. Force Python to show logs instantly (Fixes "No Logs" issue)
ENV PYTHONUNBUFFERED=1

# 2. Install Aria2, FFmpeg, Node, and tools
RUN apt-get update && apt-get install -y \
    curl jq fzf aria2 ffmpeg nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. Install Python libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy scripts
COPY . .

# 5. Make script executable
RUN chmod +x animepahe-dl.sh

# 6. Inject Aria2 Config
RUN mkdir -p /root/.config/yt-dlp && \
    echo '--external-downloader aria2c\n--external-downloader-args "-x 16 -k 1M"' > /root/.config/yt-dlp/config

# 7. Start Bot
CMD ["python", "main.py"]
