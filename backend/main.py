import os
import logging
from fastapi import FastAPI, Request, HTTPException
from bot_logic import setup_bot_application
from telegram import Update
from telegram.ext import Application

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crée l'application FastAPI
app = FastAPI()
# L'objet 'application' du bot sera initialisé au démarrage
application: Application = None

# --- Événements de démarrage et d'arrêt de FastAPI ---

@app.on_event("startup")
async def startup_event():
    """
    Action à exécuter au démarrage du serveur :
    1. Initialiser le bot ET son application.
    2. Configurer le webhook.
    """
    global application
    logger.info("Démarrage du serveur FastAPI...")
    
    # Étape 1: Initialiser le bot
    application = setup_bot_application()
    await application.initialize() # <--- LA CORRECTION CRUCIALE

    # Étape 2: Configurer le webhook
    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    if not webhook_url:
        logger.error("RENDER_EXTERNAL_URL n'est pas définie ! Impossible de configurer le webhook.")
        return

    logger.info(f"Configuration du webhook sur {webhook_url}/webhook")
    await application.bot.set_webhook(
        url=f"{webhook_url}/webhook",
        allowed_updates=Update.ALL_TYPES # On s'assure de recevoir tous les types d'updates
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Action à exécuter à l'arrêt du serveur."""
    if application:
        logger.info("Arrêt du serveur. Suppression du webhook.")
        await application.bot.delete_webhook()

# --- Endpoints de l'API ---

@app.get("/")
async def root():
    """Endpoint racine pour vérifier que le serveur est en ligne."""
    return {"status": "Bolingo Backend is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint qui reçoit les mises à jour de Telegram.
    Il les transmet à la librairie python-telegram-bot pour traitement.
    """
    if not application:
        logger.error("L'application bot n'est pas initialisée.")
        raise HTTPException(status_code=503, detail="Bot service unavailable")

    try:
        body = await request.json()
        update = Update.de_json(body, application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing error")
