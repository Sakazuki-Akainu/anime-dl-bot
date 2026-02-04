FROM python:3.10-slim

# Force logs to show immediately
ENV PYTHONUNBUFFERED=1

# Install tools (Node, FFmpeg, OpenSSL, jq)
RUN apt-get update && apt-get install -y \
    curl jq fzf aria2 ffmpeg nodejs npm openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY . .

# Make script executable
RUN chmod +x animepahe-dl.sh

# Start Bot
CMD ["python", "main.py"]
