FROM python:3.10-slim

# Install system dependencies (NO ARIA2)
RUN apt-get update && apt-get install -y \
    curl jq ffmpeg nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your code files
COPY . .

# Make the shell script executable
RUN chmod +x animepahe-dl.sh

# Start the bot
CMD ["python", "main.py"]
