import os
import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException
from bot_logic import setup_bot_application

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration de l'application ---

# URL de notre application sur Render (pour le webhook)
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") 
# Token du bot (utilisé pour configurer le webhook)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Crée l'application bot
application = setup_bot_application()

# Crée l'application FastAPI
app = FastAPI()

# --- Événements de démarrage et d'arrêt de FastAPI ---

@app.on_event("startup")
async def startup_event():
    """
    Action à exécuter au démarrage du serveur :
    1. Vérifier les variables d'environnement.
    2. Configurer le webhook de Telegram.
    """
    logger.info("Démarrage du serveur FastAPI...")
    if not WEBHOOK_URL:
        logger.error("RENDER_EXTERNAL_URL n'est pas définie !")
        return
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN n'est pas définie !")
        return

    # Configure le webhook
    webhook_info = await application.bot.get_webhook_info()
    if webhook_info.url != f"{WEBHOOK_URL}/webhook":
        logger.info(f"Configuration du webhook sur {WEBHOOK_URL}/webhook")
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    else:
        logger.info("Webhook déjà configuré.")

@app.on_event("shutdown")
async def shutdown_event():
    """Action à exécuter à l'arrêt du serveur."""
    logger.info("Arrêt du serveur. Suppression du webhook.")
    await application.bot.delete_webhook()

# --- Endpoints de l'API ---

@app.get("/")
async def root():
    """Endpoint racine pour vérifier que le serveur est en ligne."""
    return {"status": "KeteKete Backend is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint qui reçoit les mises à jour de Telegram.
    Il les transmet à la librairie python-telegram-bot pour traitement.
    """
    try:
        body = await request.json()
        logger.info(f"Update reçu : {body}")
        await application.update_queue.put(body)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook : {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")
