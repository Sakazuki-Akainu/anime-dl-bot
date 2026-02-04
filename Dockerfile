FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# Install tools
RUN apt-get update && apt-get install -y \
    curl jq fzf aria2 ffmpeg nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python libs (including cloudscraper)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY . .

# Permissions
RUN chmod +x animepahe-dl.sh

# Aria2 Config
RUN mkdir -p /root/.config/yt-dlp && \
    echo '--external-downloader aria2c\n--external-downloader-args "-x 16 -k 1M"' > /root/.config/yt-dlp/config

CMD ["python", "main.py"]
