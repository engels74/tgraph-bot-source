# Stage 1: Builder
FROM python:3.11-alpine as builder
WORKDIR /app

# Install Python utilities and minimal build tools
RUN apk add --no-cache \
    gcc musl-dev python3-dev cargo

# Create virtual environment for Python
RUN python3 -m venv /app/venv

# Activate virtual environment and install Python requirements
COPY requirements.txt .
RUN /app/venv/bin/pip install --no-cache-dir setuptools_rust
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Stage 2: Final image
FROM python:3.11-alpine
WORKDIR /app

# Install pm2 and clean up
RUN apk add --no-cache nodejs npm && \
    npm install pm2 -g && \
    apk del npm

# Copy virtual environment and source code from builder stage
COPY --from=builder /app/venv /app/venv
COPY --from=builder /app /app

# Make Docker /logs volume for log file
VOLUME /logs

# Set environment variables
ENV PATH="/app/venv/bin:$PATH"
ENV TZ=Etc/UTC
ENV TAUTULLI_API_KEY=your_tautulli_api_key
ENV TAUTULLI_URL=http://your_tautulli_ip:port/api/v2
ENV DISCORD_TOKEN=your_discord_bot_token
ENV CHANNEL_ID=your_channel_id
ENV UPDATE_DAYS=7
ENV IMG_FOLDER=img
ENV KEEP_DAYS=7
ENV TIME_RANGE_DAYS=30

# Run the app
CMD ["pm2-runtime", "start", "ecosystem.config.json"]
