# book-algo
Binance - discord alerting bot, with simple discord CLI. The bot builds `order-book` for a `base-quote pair` and tracks it trough binance WS. Alerts if there are any limit orders bigger than 7 day average trading volume for the pair.


# How to run:

## Install requirements
- Create a venv with python 3.11
- Install the requirements

## Get your discord bot token
- Go to https://discord.com/developers/applications
- Create a new application
- Create a bot
- Copy the token
- Bot will chat inside `GENERAL = 'general'`. Can be changed in background_tasks.py file


## Build and run with docker compose
```bash
docker-compose build
docker-compose up -d
```

## You can find more instructions about running the bot inside the Discord chat
```
--- Commands ---
$ping - pong!
$Watch:BTC/USDC - Start watching a pair
$Cancel:BTC/USDC - Cancel watching a pair
$List - List all pairs being watched
```

## This bot is ment to be deployd on a GCP and run 24/7. 
- Image name can be changed in the docker-compose.yml file `gcr-project-name`
- push the image to GCP
- build for different architectures with `docker buildx build --platform linux/amd64,linux/arm64 -t gcr.io/gcr-project-name/bot:latest .`
