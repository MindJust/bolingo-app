import os
import logging
from fastapi import FastAPI, Request, HTTPException
from bot_logic import setup_bot_application
from telegram.ext import Application

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

# Crée l'application FastAPI
# L'objet 'application' du bot sera initialisé au démarrage
app = FastAPI()
application: Application = None

# --- Événements de démarrage et d'arrêt de FastAPI ---

@app.on_event("startup")
async def startup_event():
    """
    Action à exécuter au démarrage du serveur :
    1. Initialiser le bot.
    2. Configurer le webhook.
    """
    global application
    logger.info("Démarrage du serveur FastAPI...")
    
    # Étape 1: Initialiser le bot
    application = setup_bot_application()
    
    # Étape 2: Configurer le webhook
    if not WEBHOOK_URL:
        logger.error("RENDER_EXTERNAL_URL n'est pas définie ! Impossible de configurer le webhook.")
        return

    logger.info(f"Configuration du webhook sur {WEBHOOK_URL}/webhook")
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        allowed_updates=["message", "callback_query"] # On spécifie les types de mises à jour que l'on veut recevoir
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Action à exécuter à l'arrêt du serveur."""
    logger.info("Arrêt du serveur. Suppression du webhook.")
    if application:
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
        raise HTTPException(status_code=500, detail="Bot application not initialized")

    try:
        body = await request.json()
        logger.debug(f"Update reçu : {body}")
        await application.update_queue.put(body)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook : {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")
