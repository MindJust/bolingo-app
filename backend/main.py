import os
import logging
from fastapi import APIRouter, Request, Response
from contextlib import asynccontextmanager
from telegram import Update
from .bot_logic import setup_bot_application # Notez le '.' devant bot_logic

# Crée un "routeur" au lieu d'une application FastAPI complète
# C'est un mini-générateur de routes que l'on peut inclure ailleurs
api_router = APIRouter()
bot_app = None

@asynccontextmanager
async def lifespan(router: APIRouter):
    global bot_app
    logger.info("Démarrage du service bot...")
    try:
        bot_app = setup_bot_application()
        await bot_app.initialize()
        webhook_url = os.getenv("RENDER_EXTERNAL_URL")
        if webhook_url:
            await bot_app.bot.set_webhook(
                url=f"{webhook_url}/api/webhook", # Le webhook pointe maintenant vers /api/webhook
                allowed_updates=Update.ALL_TYPES
            )
            logger.info(f"Webhook configuré sur {webhook_url}/api/webhook")
        yield
    finally:
        if bot_app:
            logger.info("Arrêt du service bot...")
            await bot_app.bot.delete_webhook()
            await bot_app.shutdown()

# Attache le lifespan au routeur
api_router.router.lifespan_context = lifespan

@api_router.get("/health")
async def health_check():
    return Response(status_code=200)

@api_router.post("/webhook")
async def webhook(request: Request):
    global bot_app
    try:
        update = Update.de_json(await request.json(), bot_app.bot)
        await bot_app.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logging.error(f"Erreur lors du traitement du webhook : {e}", exc_info=True)
        return Response(status_code=500)
