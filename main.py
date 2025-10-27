import logging
from contextlib import asynccontextmanager
from urllib.parse import urljoin

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application

from bot import register_handlers
from database import init_db
from settings import settings

bot_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

logger = logging.getLogger('uvicorn.error')


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    await bot_app.initialize()
    await register_handlers(bot_app)
    logger.info(f"Starting bot on {settings.HOST}")
    webhook_url = urljoin(settings.HOST, "tg-webhook")
    await bot_app.bot.set_webhook(url=webhook_url)
    logger.info("Bot started successfully")
    
    try:
        yield
    finally:
        logger.info("Shutting down bot application")
        await bot_app.shutdown()

app = FastAPI(lifespan=lifespan)


@app.post("/tg-webhook")
async def telegram_webhook(request: Request):
    update_data = await request.json()
    update = Update.de_json(update_data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}
