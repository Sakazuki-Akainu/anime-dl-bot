FROM python:3.10-slim

# Install system tools required by your .sh script
RUN apt-get update && apt-get install -y \
    curl jq fzf aria2 ffmpeg nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Set permissions
RUN chmod +x animepahe-dl.sh

# Fast downloader config
RUN mkdir -p /root/.config/yt-dlp && \
    echo '--external-downloader aria2c\n--external-downloader-args "-x 16 -k 1M"' > /root/.config/yt-dlp/config

# Launch the bot
CMD ["python", "main.py"]
